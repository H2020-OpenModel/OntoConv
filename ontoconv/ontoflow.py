"""Module for parsing output from ontoflow.

A first implementation just to fetch the information required to create
the oteapi pipelines.

"""

from pathlib import Path

import yaml

from ontoconv.pipelines import generate_ontoflow_pipeline


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
    outdir = Path(outdir)
    # Fetch the pipeline specifications
    pipelines = get_all_pipelines_spec(data=workflow_data)
    i = 1

    # Generate each pipeline separately and save it
    for pl in pipelines:
        pipeline = generate_ontoflow_pipeline(
            kb,
            resources=pl,
        )

        with open(
            outdir / f"generated_pipeline_{i}.yaml", "w", encoding="utf8"
        ) as f:
            yaml.safe_dump(pipeline, f, sort_keys=False)
        i += 1

    # Generate the workchain

    # Make the correct connections between the workchain and the pipelines
    # 1. make sure that the pipelie is placed in the correct order
    #    in the workchains
    # 2. make sure that the generated files are placed in the correct
    #    place in the workchain
    #    (i.e. the correct data is passed to the correct AiiDA datanode)
    # 3. make sure that the correct labels are passed between
    #    workchain and pipelines


def get_pipeline_spec(data):
    """
    Get the information needed to create an oteapi pipeline for
    the first step in a workflow specification created by ontoflow.

    Arguments:
    data: dict
        The workflow specification as provided by ontoflow

    return: dict
        The oteapi pipeline as a dictionary, in which sinks and sources
        are provided as lists of dictionaries.
        Each sink and source is described
        with the keys 'iri' and 'resourcetype'.
        An example of the output is:

        ```python
        {'sinks': [
           {'iri': 'ss3:AbaqusConfiguration',
            'resourcetype': 'ss3:AbaqusSimulation'},
           {'iri': 'ss3:AluminiumMaterialCard',
            'resourcetype': 'ss3:AbaqusSimulation'},
           {'iri': 'ss3:ConcreteMaterialCard',
            'resourcetype': 'ss3:AbaqusSimulation'}],
         'sources': [
           {'iri': 'ss3kb:abaqus_config1', 'resourcetype': 'dataset'},
           {'iri': 'ss3:AluminiumMaterialCard',
            'resourcetype': 'ss3:MaterialCardGenerator'},
           {'iri': 'ss3kb:abaqus_materialcard_concrete1',
            'resourcetype': 'dataset'}]}
        ```
    """
    pipeline = {"sinks": [], "sources": []}
    if (
        len(data["children"]) == 1
        and data["children"][0]["predicate"] == "hasOutput"
    ):
        pipeline["sources"] = get_partial_pipeline_in_spec(data)
    else:
        for child in data["children"]:  #
            if child["predicate"] == "individual":
                resourcetype = "dataset"
            else:
                resourcetype = data["iri"]
            pipeline["sinks"].append(
                {
                    "iri": child["iri"],  # "predicate": child["predicate"],
                    "resourcetype": resourcetype,
                }
            )
            input_partial_pipeline = get_partial_pipeline_in_spec(child)
            pipeline["sources"].extend(input_partial_pipeline)
    return pipeline


def get_partial_pipeline_in_spec(data):
    """
    Get the partial pipeline specification as
    dictionary for the sources in the pipeline.
    """
    partial_pipeline = []
    for child in data["children"]:
        if child["predicate"] == "individual":
            iri = child["iri"]
            resourcetype = "dataset"
        else:
            iri = data["iri"]
            resourcetype = child["iri"]

        partial_pipeline.append(
            {
                "iri": iri,
                "resourcetype": resourcetype,
            }
        )
    return partial_pipeline


def get_all_pipelines_spec(data, pipelines=None):
    """
    Get the information needed to create all oteapi pipelines
    relevant for a workflow specification created by ontoflow.
    Each model in the workflow is connected with an oteapi pipeline.

    Arguments:
    data: dict
        The data as provided by ontoflow
    pipelines: list
        A list of dictionaries, each representing an oteapi pipeline.
        Eeach dictionary has the keys 'sinks' and 'sources', which are
        lists of dictionaries with the keys 'iri' and 'resourcetype'.

    Each pipeline is in the format:
    ```python
        {'sinks': [
           {'iri': 'ss3:AbaqusConfiguration',
            'resourcetype': 'ss3:AbaqusSimulation'},
           {'iri': 'ss3:AluminiumMaterialCard',
            'resourcetype': 'ss3:AbaqusSimulation'},
           {'iri': 'ss3:ConcreteMaterialCard',
            'resourcetype': 'ss3:AbaqusSimulation'}],
         'sources': [
           {'iri': 'ss3kb:abaqus_config1', 'resourcetype': 'dataset'},
           {'iri': 'ss3:AluminiumMaterialCard',
            'resourcetype': 'ss3:MaterialCardGenerator'},
           {'iri': 'ss3kb:abaqus_materialcard_concrete1',
            'resourcetype': 'dataset'}]}
    """
    if not pipelines:
        pipelines = []
    p = get_pipeline_spec(data)
    pipelines.append(p)
    for v in p["sources"]:  # pylint: disable=too-many-nested-blocks
        if v["resourcetype"] != "dataset":
            children = data["children"]
            for child in children:
                remaining_data = None
                if child["iri"] == v["resourcetype"]:
                    remaining_data = child
                else:
                    for grandchild in child["children"]:
                        if grandchild["iri"] == v["resourcetype"]:
                            remaining_data = grandchild
                if remaining_data:
                    get_all_pipelines_spec(remaining_data, pipelines)
    return pipelines
