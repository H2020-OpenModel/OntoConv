"""Module for storing/loading OTEAPI pipelines to/from a knowledge base."""

import warnings
from typing import Sequence

import yaml
from otelib import OTEClient
from tripper import OTEIO, RDF, Triplestore
from tripper.convert import load_container, save_container
from tripper.convert.convert import BASIC_RECOGNISED_KEYS

# Get rid of FutureWarning from csv.py
warnings.filterwarnings("ignore", category=FutureWarning)

# Extend the recognised keys used by tripper.convert
RECOGNISED_KEYS = BASIC_RECOGNISED_KEYS.copy()
RECOGNISED_KEYS.update(
    {
        "aiida_plugin": "http://open-model.eu/oip#AiidaPlugin",
        "command": "http://open-model.eu/oip#Command",
        "install_command": "http://open-model.eu/oip#InstallCommand",
        ""
    }
)


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
        document = yaml.safe_load(f)

    prefixes = document.get("prefixes", {})
    for prefix, namespace in prefixes.items():
        ts.bind(prefix, namespace)

    # Data resources
    datadoc = document["data_resources"]
    for iri, resource in datadoc.items():
        iri = ts.expand_iri(iri)
        save_container(ts, resource, iri, recognised_keys="basic")

        # Add rdf:type relations
        for rtype in get_resource_types(resource):
            ts.add((iri, RDF.type, ts.expand_iri(rtype)))

    # Simulation resources
    simdoc = document["simulation_resources"]
    for iri, resource in datadoc.items():
        iri = ts.expand_iri(iri)
        save_container(ts, resource, iri, recognised_keys=RECOGNISED_KEYS)



def get_simulation_info(ts: Triplestore, iri: str):
    """Return documentation of simulation tool with given iri.

    Arguments:
        ts: Tripper triplestore documenting the simulation tools.
        iri: IRI of the simulation tool.

    Returns
        A dict documentating the simulation tool.

    """
    resource = load_container(ts, iri)
    return resource


def generate_pipeline(
    ts: Triplestore,
    steps: Sequence[str],
) -> dict:
    """Return a declarative ExecFlow pipeline as a string.

    Arguments:
        ts: Tripper triplestore documenting data sources and sinks.
        steps: Sequence of names of data sources and sinks to combine.
            The order is important and should go from source to sink.
        client_iri: IRI of OTELib client to use.

    Returns:
        Dict-representation of a declarative ExecFlow pipeline.
    """
    names = []
    strategies = []
    for step in steps:
        if "#" in step:
            name_suffix = step.split("#", 1)[-1]
        else:
            name_suffix = step.rsplit("/", 1)[-1]
        resource = load_container(ts, step, recognised_keys="basic")

        for strategy in resource:
            for stype, conf in strategy.items():
                name = f"{name_suffix}_{stype}"
                d = {stype: name}
                d.update(conf)
            names.append(name)
            strategies.append(d)
    return {
        "version": 1,
        "strategies": strategies,
        "pipelines": {"pipe": " | ".join(names)},
    }


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
        strategies = load_container(ts, step, recognised_keys="basic")
        for filtertype, config in strategies.items():
            creator = getattr(client, f"create_{filtertype}")
            pipe = creator(**config)
            pipeline = pipeline >> pipe if pipeline else pipe

    pipeline.get()  # type: ignore
