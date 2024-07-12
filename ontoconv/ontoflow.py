"""Module for parsing output from ontoflow.

A first implementation just to fetch the information required to create
the oteapi pipelines.

"""

from pathlib import Path

import yaml

from ontoconv.pipelines import generate_pipeline, generate_ontoflow_pipeline, load_simulation_resource
from tripper.convert import load_container

class Node:
    def __init__(self, data, nodes):
        self.inputs = []
        self.outputs = []
        self.depth = data['depth']
        self.iri = data['iri']
        self.resource_type = {"output": "dataset" if 'children' not in data else "", "input": ""}

        if not self.resource_type["output"] == "dataset":
            for n in data['children']:
                node = Node(n, nodes)
                if n['predicate'] == 'hasOutput':
                    node.outputs.append(self)
                    self.resource_type["output"] = node.iri
                else:
                    self.inputs.append(node) # individual is singular input I guess
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
            s+= "\noutputs: "
            for i in self.outputs:
                s += f"\n{i.id}: {i.iri}"
        return s

    def var_name(self, dtype):
        return f"datanode_{self.id}_{dtype}"

    def step_name(self):
        return f"step_{self.id}"

    def is_dataset(self):
        return len(self.inputs) == 1 and self.inputs[0].resource_type["output"] == "dataset"

    def is_step(self):
        return len(self.outputs) != 0

    def is_ctx_node(self):
        return self.resource_type['output'] != '' and len(self.inputs) == 0 and len(self.outputs) == 0

    def suffix(self):
        return self.iri.split("#", 1)[-1] if "#" in self.iri else self.iri.rsplit("/", 1)[-1]

    def kb_suffix(self):
        return self.iri.rsplit("/", 1)[-1].replace("#", ":")

def save_pipeline(name, pipeline, outdir):
    with open(
        Path(outdir) / f"generated_pipeline_{name}.yaml", "w", encoding="utf8"
    ) as f:
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

    fc = 0
    # first we set up all the individuals
    last_outputs = None
    for n in nodes:
        if n.is_step():
            resource = load_simulation_resource(kb, n.iri)
            files = {}
            pipeline = generate_ontoflow_pipeline(kb, n.inputs)
            stepname = n.step_name()
            save_pipeline(stepname, pipeline, outdir)



            inputs = {"pipeline": f"generated_pipeline_{stepname}.yaml","run_pipeline": "pipe","from_cuds": [ni.var_name("input") for ni in n.inputs]}
            to_cuds = [ni.var_name("output") for ni in n.inputs if ni.is_ctx_node()]
            if len(to_cuds) != 0:
                inputs["to_cuds"] = to_cuds

            chain["steps"].append({"workflow": "execflow.oteapipipeline",
                                   "inputs": inputs,
                                   "postprocess": [f"{{{{ ctx.current_outputs.results[\'{ni.var_name('input')}\']|to_ctx(\'{ni.var_name('input')}\') }}}}" for ni in n.inputs]
                                   })
            for input in n.inputs:
                varname = input.var_name("input") 
                files[f"in_file_{len(files)}"] = {
                    "filename": resource["input"][input.kb_suffix()][-1]["function"]["configuration"]["location"],
                    "node": f"{{{{ ctx.{varname} }}}}" 
                }
            if "files" in resource:
                for static_file in resource["files"]:
                    files[f"in_file_{len(files)}"] = {
                        "filename": static_file["target_file"],
                        "template": static_file["source_uri"]
                    }

            output_filenames=[{f"file_{i}": "missing_filename_{f.iri}.json"} for (i, f) in enumerate(n.outputs)]
            chain["steps"].append({"workflow": resource["aiida_plugin"],
                                   "inputs": {
                                       "command": resource["command"],
                                       "files": files
                                   },
                                   "outputs": output_filenames,

                                   "postprocess": [f"{{{{ ctx.current_outputs.results['file_{i}']|to_ctx('{on.var_name('output')}') }}}}" for (i, on) in enumerate(n.outputs)]
                                   })

            last_outputs = n.outputs
    if last_outputs is not None:
        pipeline = generate_ontoflow_pipeline(kb, last_outputs, True)
        to_cuds = [ni.var_name("output") for ni in last_outputs if ni.is_ctx_node()]
        save_pipeline("generated_pipeline_final_result.yaml", pipeline, outdir)
        chain["steps"].append({"workflow": "execflow.oteapipipeline",
                               "inputs": {
                                   "pipeline": f"generated_pipeline_final_result.yaml",
                                   "run_pipeline": "pipe",
                                   "to_cuds": to_cuds,
                               },
                               })

            

    with open(
        Path(outdir) / f"generated_workchain.yaml", "w", encoding="utf8"
    ) as f:
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
