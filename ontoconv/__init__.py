"""OntoConv is a Python package for connecting OntoFlow to ExecFlow."""

__version__ = "0.1.0"

from .pipelines import (
    generate_pipeline,
    get_data,
    get_simulation_info,
    populate_triplestore,
)

__all__ = (
    "__version__",
    "populate_triplestore",
    "get_simulation_info",
    "generate_pipeline",
    "get_data",
)
