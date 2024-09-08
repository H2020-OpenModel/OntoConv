"""Module for parsing output from ontoflow.

A first implementation just to fetch the information required to create
the oteapi pipelines.

"""

from pathlib import Path

import yaml
from tripper.convert import load_container

from ontoconv.pipelines import (
    generate_ontoflow_pipeline,
    load_simulation_resource,
)


class Node:
    def __init__(self, data, nodes):
        self.inputs = []
        self.outputs = []
        self.depth = data["depth"]
        self.iri = data["iri"]
        self.resource_type = {
            "output": "dataset" if "children" not in data else "",
            "input": "",
        }

        if not self.resource_type["output"] == "dataset":
            for n in data["children"]:
                node = Node(n, nodes)
                if n["predicate"] == "hasOutput":
                    node.outputs.append(self)
                    self.resource_type["output"] = node.iri
                else:
                    self.inputs.append(
                        node
                    )  # individual is singular input I guess
                    if len(node.resource_type["input"]) == 0:
                        node.resource_type["input"] = self.iri
        self.id = len(nodes)
        nodes.append(self)

    def __str__(self):
        s = f"Node: {self.id}:\niri:           {self.iri}\nresource_type: {self.resource_type}"
        if len(self.inputs) != 0:
            s += "\ninputs: "
            for i in self.inputs:
                s += f"\n{i.id}: {i.iri}"
        if len(self.outputs) != 0:
            s += "\noutputs: "
            for i in self.outputs:
                s += f"\n{i.id}: {i.iri}"
        return s

    def var_name(self, dtype):
        return f"datanode_{self.id}_{dtype}"

    def step_name(self):
        return f"step_{self.id}"

    def is_dataset(self):
        return (
            len(self.inputs) == 1
            and self.inputs[0].resource_type["output"] == "dataset"
        )

    def is_step(self):
        return len(self.outputs) != 0

    def is_ctx_node(self):
        return (
            self.resource_type["output"] != ""
            and len(self.inputs) == 0
            and len(self.outputs) == 0
        )

    def suffix(self):
        return (
            self.iri.split("#", 1)[-1]
            if "#" in self.iri
            else self.iri.rsplit("/", 1)[-1]
        )

    def kb_suffix(self):
        return self.iri.rsplit("/", 1)[-1].replace("#", ":")

    def filename(self, resource):
        return resource["input"][self.kb_suffix()][-1]["function"][
            "configuration"
        ]["location"]

    def input_postprocess(self):
        return f"{{{{ ctx.current.outputs.results['{self.var_name('input')}']|to_ctx('{self.var_name('input')}') }}}}"

    def output_postprocess_execwrapper(self, filename):
        f = filename.replace(".", "_")
        return f"{{{{ ctx.current.outputs['{f}']|to_ctx('{self.var_name('output')}') }}}}"

    def pipeline_step(self, pipeline_file, is_last=False):

        inputs = {
            "pipeline": {"$ref": f"file:__DIR__/{pipeline_file}"},
            "run_pipeline": "pipe",
        }

        if not is_last:
            inputs["from_cuds"] = [ni.var_name("input") for ni in self.inputs]
            to_cuds = [
                ni.var_name("output") for ni in self.inputs if ni.is_ctx_node()
            ]
        else:
            to_cuds = [
                ni.var_name("output")
                for ni in self.outputs
                if ni.is_ctx_node()
            ]

        if len(to_cuds) != 0:
            inputs["to_cuds"] = to_cuds
            for output in to_cuds:
                var = "ctx." + output
                inputs[output] = f"{{{{ ctx.{output} }}}}"
        ret = {"workflow": "execflow.oteapipipeline", "inputs": inputs}

        if not is_last:
            ret["postprocess"] = [ni.input_postprocess() for ni in self.inputs]

        return ret

    def calculation_step(self, resource):
        # This is only for execwrapper at the moment
        files = {}

        for input in self.inputs:
            varname = input.var_name("input")
            files[f"in_file_{len(files)}"] = {
                "filename": input.filename(resource),
                "node": f"{{{{ ctx.{varname} }}}}",
            }

        if "files" in resource:
            for static_file in resource["files"]:
                files[f"in_file_{len(files)}"] = {
                    "filename": static_file["target_file"],
                    "template": static_file["source_uri"],
                }
        full_command = resource["command"].replace("\ ", "").split()
        outfiles = output_filenames(resource)

        return {
            "workflow": resource["aiida_plugin"],
            "inputs": {
                "command": full_command.pop(0),
                "arguments": full_command,
                "files": files,
                "outputs": outfiles,
            },
            "postprocess": [
                on.output_postprocess_execwrapper(f)
                for (f, on) in zip(outfiles, self.outputs)
            ],
        }


def output_filenames(resource):
    return [
        f"{resource['output'][o][0]['dataresource']['downloadUrl']}"
        for o in resource["output"]
    ]


def save_pipeline(name, pipeline, outdir):
    with open(Path(outdir) / name, "w", encoding="utf8") as f:
        yaml.safe_dump(pipeline, f, sort_keys=False)


def parse_ontoflow(workflow_data, kb, outdir="."):
    """
    Function to parse ontoflow and create declarative workchain
    and corresponding pipelines.

    Arguments:
    data: dict
        The data as provided by ontoflow
    kb: knowledge base as tripper.TriplesStore
    outdir: str
        The directory to save the output files.
        Pipeline and workchain files are saved as yaml.

    """
    nodes = []
    root = Node(workflow_data, nodes)

    chain = {"steps": []}

    istep = 0
    # first we set up all the individuals
    last = None
    for n in nodes:
        if n.is_step():
            pipeline = generate_ontoflow_pipeline(kb, n.inputs)
            pipeline_file = f"pipeline_{istep}.yaml"
            save_pipeline(pipeline_file, pipeline, outdir)

            chain["steps"].append(n.pipeline_step(pipeline_file))

            resource = load_simulation_resource(kb, n.iri)
            chain["steps"].append(n.calculation_step(resource))
            last = n
            istep += 1

    if last is not None:
        pipeline = generate_ontoflow_pipeline(kb, last.outputs, True)
        pipeline_file = f"pipeline_final.yaml"
        save_pipeline(pipeline_file, pipeline, outdir)

        chain["steps"].append(last.pipeline_step(pipeline_file, True))

    with open(Path(outdir) / f"workchain.yaml", "w", encoding="utf8") as f:
        yaml.safe_dump(chain, f, sort_keys=False)

    # Generate the workchain

    # Make the correct connections between the workchain and the pipelines
    # 1. make sure that the pipelie is placed in the correct order
    #    in the workchains
    # 2. make sure that the generated files are placed in the correct
    #    place in the workchain
    #    (i.e. the correct data is passed to the correct AiiDA datanode)
    # 3. make sure that the correct labels are passed between
    #    workchain and pipelines
