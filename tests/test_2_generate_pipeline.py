"""Test generating a declarative pipeline file for ExecFlow."""


if True:
#def test_generate_pipeline():
    import yaml

    from tripper import Triplestore

    from ontoconv.pipelines import generate_pipeline
    from ontoconv.testutils import outdir

    ts = Triplestore(backend="rdflib")
    ts.parse(outdir / "kb.ttl")
    SS3 = ts.bind("ss3", "http://openmodel.eu/ss3/")

    pipeline = generate_pipeline(ts, steps=[
        SS3.aluminium_material_card,
        SS3.create_abaqus_input_material_card,
        SS3.concrete_material_card,
        SS3.append_abaqus_input_material_card,
    ])

    with open(outdir / "pipeline.yml", "w") as f:
        yaml.safe_dump(pipeline, f)
