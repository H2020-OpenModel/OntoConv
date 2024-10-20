"""Module for storing/loading OTEAPI pipelines to/from a knowledge base."""

import warnings
from typing import Sequence

import yaml
from otelib import OTEClient
from tripper import OTEIO, RDF, Triplestore
from tripper.convert import load_container, save_container
from tripper.convert.convert import BASIC_RECOGNISED_KEYS

from ontoconv.attrdict import AttrDict

# Get rid of FutureWarning from csv.py
warnings.filterwarnings("ignore", category=FutureWarning)

# Extend the recognised keys used by tripper.convert
RECOGNISED_KEYS = BASIC_RECOGNISED_KEYS.copy()
RECOGNISED_KEYS.update(
    {
        "aiida_plugin": "http://open-model.eu/ontologies/oip#AiidaPlugin",
        "aiida_datanodes": "http://open-model.eu/ontologies/oip#AiidaDataNode",
        "command": "http://open-model.eu/ontologies/oip#Command",
        "files": "http://open-model.eu/ontologies/oip#Files",
        "input": "http://open-model.eu/ontologies/oip#SimulationToolInput",
        "output": "http://open-model.eu/ontologies/oip#SimulationToolOutput",
        "install_command": (
            "http://open-model.eu/ontologies/oip#InstallCommand"
        ),
        "datamodel": "http://emmo.info/datamodel#DataModel",  # NB needs update
    }
)

# Extra prefixes used by OntoConv
EXTRA_PREFIXES = {
    "oip": "http://open-model.eu/ontologies/oip#",
}


def get_resource_types(resource: list) -> list:
    """Returns the type(s) of a given resource.

    Heuristics is applied to determine if a resource is a source or
    sink if it is not explicitly defined in a `resource` strategy.

    Arguments:
        resource: List with OTEAPI configurations for a data resource.

    Returns:
        List with all ontological classes that the resource individual
        is an instance of.
    """
    if isinstance(resource, str) or not isinstance(resource, Sequence):
        raise TypeError(
            f"Expected data resource configuration to be a list: {resource!r}"
        )
    for item in resource:
        if isinstance(item, dict):
            dataresource = item.get("dataresource", {})
        else:
            dataresource = {}

    if dataresource:
        types = dataresource.get("type", [])
        if isinstance(types, str):
            types = [types]
        # Assume data source if partial pipeline has a dataresource
        # strategy with no explicitly type.
        resource_type_iris = (
            OTEIO.DataSource,
            OTEIO.DataSink,
            "oteio:DataSource",
            "oteio:DataSink",
        )
        if not any(iri in types for iri in resource_type_iris):
            types.append(OTEIO.DataSource)
    else:
        # Assume data sink if partial pipeline has no dataresource strategy.
        types = [OTEIO.DataSink]

    return types


def populate_triplestore(
    ts: Triplestore,
    yamlfile: str,
) -> None:
    """Populate the triplestore with data documentation from a
    standardised yaml file.

    Arguments:
        ts: Tripper triplestore documenting data sources and sinks.
        yamlfile: Standardised YAML file to load the data documentation
            from.
    """
    with open(yamlfile, encoding="utf8") as f:
        documentation = yaml.safe_load(f)

    prefixes = EXTRA_PREFIXES.copy()
    prefixes.update(documentation.get("prefixes", {}))
    for prefix, namespace in prefixes.items():
        ts.bind(prefix, namespace)

    # Data resources
    datadoc = documentation.get("data_resources", {})
    for iri, resource in datadoc.items():
        iri = ts.expand_iri(iri)
        save_container(ts, resource, iri, recognised_keys="basic")

        # Add rdf:type relations
        for rtype in get_resource_types(resource):
            ts.add((iri, RDF.type, ts.expand_iri(rtype)))

    # Simulation resources
    simdoc = documentation.get("simulation_resources", {})
    for iri, resource in simdoc.items():
        iri = ts.expand_iri(iri)
        save_simulation_resource(ts, iri, resource)


def save_simulation_resource(ts: Triplestore, iri: str, resource: dict):
    """Save documentation of simulation tools to the triplestore.

    Arguments:
        ts: Tripper triplestore documenting the simulation tools.
        iri: IRI of the simulation tool.
        siminfo: A dict with the documentation to save.
    """
    # pylint: disable=redefined-builtin

    # TODO: Since simulation resources are classes in the KB, the
    # correct way would be to add the additional documentation as
    # restrictions.
    # What we do here, will be interpreted as annotation properties
    # by Protege.
    save_container(ts, resource, iri, recognised_keys=RECOGNISED_KEYS)

    # Ensure that all input and output are datasets
    for input in resource.get("input", {}):
        ts.add((input, RDF.type, OTEIO.DataSink))

    for output in resource.get("output", {}):
        ts.add((output, RDF.type, OTEIO.DataSource))


def load_simulation_resource(ts: Triplestore, iri: str):
    """Loads documentation of simulation tool from the triplestore.

    Arguments:
        ts: Tripper triplestore documenting the simulation tools.
        iri: IRI of the simulation tool.

    Returns
        A dict with attribute access documentating the simulation tool.

    """
    resource = load_container(
        ts, iri, recognised_keys=RECOGNISED_KEYS, ignore_unrecognised=True
    )
    return AttrDict(**resource)


def generate_ontoflow_pipeline(  # pylint: disable=too-many-branches,too-many-locals,too-many-statements
    ts: Triplestore,
    nodes,
    save_final_output=False,
    recognised_keys: "Optional[Union[dict, str]]" = "basic",
    target_ts: "Optional[Triplestore]" = None,
) -> dict:
    """Return a declarative ExecFlow pipeline as a dict.

    Arguments:
        ts: Tripper triplestore documenting data sources and model
            inputs and outputs.
        resources: A dict referring to OTEAPI partial pipelines for
            a set of data sources and sinks.
            See the example below for the expected structure.
        client_iri: IRI of OTELib client to use.
        recognised_keys: Dict that maps keys to IRIs (in an ontology).
            These are used to detect keys in the knowledge base.
            E.g. 'downloadUrl' is recognised in the kb as such a key.
            Recognised keys are found in the global variable
            ontoconv.pipelines.RECOGNISED_KEYS
        target_ts: Tripper triplestore in which generated output of
            the pipeline is to be documented. Defaults to the same
            triplestore in which sources and models are documented.
    Returns:
        Dict-representation of a declarative ExecFlow pipeline.

    Examples:
        Example of the `resources` argument:

        ```python
        {'sinks': [
           {'iri': 'ss3:AbaqusConfiguration',
            'resource_type': 'ss3:AbaqusSimulation'},
           {'iri': 'ss3:AluminiumMaterialCard',
            'resource_type': 'ss3:AbaqusSimulation'},
           {'iri': 'ss3:ConcreteMaterialCard',
            'resource_type': 'ss3:AbaqusSimulation'}],
         'sources': [
           {'iri': 'ss3kb:abaqus_config1', 'resource_type': 'dataset'},
           {'iri': 'ss3:AluminiumMaterialCard',
            'resource_type': 'ss3:MaterialCardGenerator'},
           {'iri': 'ss3kb:abaqus_materialcard_concrete1',
            'resource_type': 'dataset'}]}
        ```
    """
    if target_ts is None:
        target_ts = ts

    names = {"input": [], "output": [], "triplestore": []}
    strategies = []
    i = 0

    def add_resource(resource, dtype):
        for strategy in resource:
            for stype, conf in strategy.items():
                name = n.var_name(dtype)
                conf[stype] = name
                nonlocal i
                i += 1
                names[dtype].append(name)
                strategies.append(conf)

    for n in nodes:
        iri = n.iri
        for n1 in n.inputs:
            if n1.resource_type["output"] == "dataset":
                add_resource(
                    load_container(
                        ts,
                        n1.iri,
                        recognised_keys=recognised_keys,
                        ignore_unrecognised=True,
                    ),
                    "output",
                )
        if n.resource_type["input"] != "":
            resource_type = n.resource_type["input"]

            r = load_simulation_resource(ts, resource_type)
            try:
                add_resource(r["input"][iri], "input")
            except KeyError:
                try:
                    add_resource(r["input"][ts.prefix_iri(iri)], "input")
                except KeyError as exc:
                    raise KeyError(
                        f"Could not find input {iri} in {resource_type}"
                    ) from exc
        if n.resource_type["output"] != "":
            resource_type = n.resource_type["output"]
            r = load_simulation_resource(ts, resource_type)
            try:
                resource_info = r["output"][iri]
            except KeyError:
                try:
                    resource_info = r["output"][ts.prefix_iri(iri)]
                except KeyError as exc:
                    raise KeyError(
                        f"Could not find output {iri} in {resource_type}"
                    ) from exc
            if n.resource_type["output"] == "dataset":
                if save_final_output:
                    warnings.warn(
                        "There is no sink, therefor it does not make sense to "
                        "create a pipeline with an already existing dataset "
                        "as source."
                    )
                add_resource(
                    load_container(
                        ts,
                        iri,
                        recognised_keys=recognised_keys,
                        ignore_unrecognised=True,
                    ),
                    "output",
                )
            elif save_final_output:
                add_resource(
                    [
                        {
                            "function": {
                                "functionType": "application/"
                                "vnd.dlite-generate",
                                "configuration": {
                                    "datamodel": "http://onto-ns.com/"
                                    "meta/0.1/Blob",
                                    "driver": "blob",
                                    "label": f"{n.var_name('output')}",
                                    "location": resource_info[0][
                                        "dataresource"
                                    ]["downloadUrl"],
                                    "kb_document_class": iri,
                                    "kb_document_computation": n.resource_type[
                                        "output"
                                    ],
                                    "kb_document_base_iri": iri.split("#")[0]
                                    + "kb#",
                                    "kb_document_update": resource_info[0],
                                },
                            },
                        }
                    ],
                    "output",
                )
                if target_ts.backend_name == "rdflib":
                    settings = {
                        "backend": "rdflib",
                        "triplestore_url": target_ts.backend.triplestore_url,
                    }
                elif target_ts.backend_name == "fuseki":
                    settings = {
                        "backend": "fuseki",
                        "triplestore_url": target_ts.kwargs["triplestore_url"],
                        "database": target_ts.database,
                    }
                else:
                    raise KeyError(
                        f"Triplestore backend {target_ts.backend}, "
                        "not suppoorted by OntoConv"
                    )

                add_resource(
                    [
                        {
                            "filter": {
                                "filterType": "application/"
                                "vnd.dlite-settings",
                                "configuration": {
                                    "label": "tripper.triplestore",
                                    "settings": settings,
                                },
                            },
                        }
                    ],
                    "triplestore",
                )

            else:
                try:
                    datanodetype = r["aiida_datanodes"][iri]
                except KeyError:
                    try:
                        datanodetype = r["aiida_datanodes"][ts.prefix_iri(iri)]
                    except KeyError as exc:
                        raise KeyError(
                            f"Could not find {iri} in {r['aiida_datanodes']}"
                        ) from exc
                add_resource(
                    [
                        {
                            "function": {
                                "functionType": "application/"
                                "vnd.dlite-convert",
                                "configuration": {
                                    "function_name": "singlefile_converter",
                                    "module_name": "execflow.data."
                                    "singlefile_converter",
                                    "inputs": [
                                        {
                                            "label": f"{n.var_name('output')}",
                                            "datamodel": datanodetype,
                                        }
                                    ],
                                    "outputs": [
                                        {
                                            "label": f"{n.suffix()}_"
                                            "oteapi_instance",
                                            "datamodel": resource_info[0][
                                                "dataresource"
                                            ]["configuration"]["datamodel"],
                                        }
                                    ],
                                    "kwargs": {
                                        "parse_driver": resource_info[0][
                                            "dataresource"
                                        ]["configuration"]["driver"]
                                    },
                                },
                            }
                        }
                    ],
                    "output",
                )
    strategies, names = add_execflow_decoration_to_pipeline(strategies, names)

    source_pp = " | ".join(names["output"])
    sink_pp = " | ".join(names["input"])
    if len(sink_pp) == 0:
        pipe = source_pp
    elif len(source_pp) == 0:
        pipe = sink_pp
    else:
        pipe = source_pp.strip(" ") + " | " + sink_pp
    if len(names["triplestore"]) == 1:
        pipe = pipe + " | " + names["triplestore"][0]

    return {
        "version": 1,
        "strategies": strategies,
        "pipelines": {"pipe": pipe},
    }


def add_execflow_decoration_to_pipeline(strategies, names):
    """Add ExecFlow decoration to the pipeline.

    Arguments:
        strategies: List of strategies in the pipeline.
        names: Dict with one list of names for the output (source)
          strategies and one list of names for the input (sink) strategies.
    """
    functions = [f for f in strategies if "function" in f.keys()]

    # Add datanode2cuds if not already present, if a function is present
    # in the source strategies.
    if not any(f["function"] == "datanode2cuds" for f in functions):
        original_ouput_names = names["output"].copy()
        for name in original_ouput_names:
            func = [f for f in functions if f["function"] == name]
            if len(func) > 1:
                raise ValueError(f"Multiple functions with name {name}")
            if len(func) == 1:
                strategies.append(
                    {
                        "function": "datanode2cuds",
                        "functionType": "aiidacuds/datanode2cuds",
                        "configuration": {"names": "to_cuds"},
                    }
                )
                names["output"].insert(0, "datanode2cuds")
                break

    # Add cuds2datanode if not already present, and files are created
    # in the sink strategies. Also add corresponding functions to convert
    # file to AiiDA datanode.
    func = [f for f in functions if f["function"] in names["input"]]

    locations = set(
        f["configuration"]["location"]
        for f in func
        if "location" in f["configuration"]
    )

    numfile = 1
    labels = []
    for loc in locations:
        # find the function that has the location in its configuration
        namebasis = [f for f in func if f["configuration"]["location"] == loc][
            0
        ]["function"]
        label = f"{namebasis}"
        function_name = label + "_to_aiida_datanode"
        strategies.append(
            {
                "function": function_name,
                "functionType": "aiidacuds/file2collection",
                "configuration": {"path": loc, "label": label},
            }
        )
        names["input"].append(function_name)
        labels.append(label)
        numfile += 1
    if len(labels) > 0:
        strategies.append(
            {
                "function": "cuds2datanode",
                "functionType": "aiidacuds/cuds2datanode",
                "configuration": {"names": "from_cuds"},
            }
        )
        names["input"].append("cuds2datanode")

    return strategies, names


def get_data(
    ts: Triplestore,
    steps: Sequence[str],
    client_iri: str = "python",
):
    """Get the data specified by the user.

    From the sequence of IRIs provided in the `steps` argument, this
    function ensembles an OTEAPI pipeline and calls its `get()` method.

    Arguments:
        ts: Tripper triplestore documenting data sources and sinks.
        steps: Sequence of names of data sources and sinks to combine.
            The order is important and should go from source to sink.
        client_iri: IRI of OTELib client to use.
    """
    client = OTEClient(client_iri)
    pipeline = None

    for step in steps:
        strategies = load_container(
            ts, step, recognised_keys="basic", ignore_unrecognised=True
        )
        for filtertype, config in strategies.items():
            creator = getattr(client, f"create_{filtertype}")
            pipe = creator(**config)
            pipeline = pipeline >> pipe if pipeline else pipe

    pipeline.get()  # type: ignore
