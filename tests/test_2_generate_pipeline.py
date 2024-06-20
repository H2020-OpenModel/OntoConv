"""Test generating a declarative pipeline file for ExecFlow."""


# if True:
def test_generate_pipeline():
    """Test generating declarative pipeline."""
    import yaml
    from paths import outdir
    from tripper import Triplestore

    from ontoconv.pipelines import generate_pipeline

    ts = Triplestore(backend="rdflib")
    ts.parse(outdir / "kb.ttl")
    SS3 = ts.bind("ss3", "http://open-model.eu/ontologies/ss3#")

    pipeline = generate_pipeline(
        ts,
        steps=[
            SS3.aluminium_material_card,
            SS3.concrete_material_card,
        ],
    )

    with open(outdir / "pipeline.yml", "w", encoding="utf8") as f:
        yaml.safe_dump(pipeline, f, sort_keys=False)


def test_generate_execflow_pipeline():
    """Test generating declarative pipeline."""
    import yaml
    from paths import outdir
    from tripper import Triplestore

    from ontoconv.pipelines import generate_ontoflow_pipeline

    ts = Triplestore(backend="rdflib")
    ts.parse(outdir / "kb.ttl")

    resources = {
        "sinks": [
            {
                "iri": "http://open-model.eu/ontologies/ss3"
                "#AluminiumMaterialCard",
                "resourcetype": "http://open-model.eu/ontologies/ss3"
                "#AbaqusSimulation",
            },
        ],
        "sources": [
            {
                "iri": "http://open-model.eu/ontologies/ss3"
                "#AbaqusDeformationHistory",
                "resourcetype": "http://open-model.eu/ontologies/ss3"
                "#AbaqusSimulation",
            },
            {
                "iri": "http://open-model.eu/ontologies/ss3"
                "#concrete_material_card",
                "resourcetype": "dataset",
            },
        ],
    }

    pipeline = generate_ontoflow_pipeline(
        ts,
        resources=resources,
    )

    with open(outdir / "pipeline2.yml", "w", encoding="utf8") as f:
        yaml.safe_dump(pipeline, f, sort_keys=False)
