"""OntoConv is a Python package for connecting OntoFlow to ExecFlow."""

__version__ = "0.1.0"

from .pipelines import (
    generate_ontoflow_pipeline,
    get_data,
    load_simulation_resource,
    populate_triplestore,
    save_simulation_resource,
)

__all__ = (
    "__version__",
    "generate_ontoflow_pipeline",
    "get_data",
    "load_simulation_resource",
    "populate_triplestore",
    "save_simulation_resource",
)
