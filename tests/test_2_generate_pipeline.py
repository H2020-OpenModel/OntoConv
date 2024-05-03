"""Test generating a declarative pipeline file for ExecFlow."""


if True:
<<<<<<< Updated upstream
#def test_generate_pipeline():
=======
# def test_generate_pipeline():
    """Test generating declarative pipeline."""
>>>>>>> Stashed changes
    import yaml

    from tripper import Triplestore

    from ontoconv.utils import generate_pipeline
    from ontoconv.testutils import outdir

    ts = Triplestore(backend="rdflib")
    ts.parse(outdir / "kb.ttl")
    SS3 = ts.bind("ss3", "http://openmodel.eu/ss3/")

<<<<<<< Updated upstream
    pipeline = generate_pipeline(ts, steps=[
        SS3.aluminium_material_card,
        SS3.create_abaqus_input_material_card,
        SS3.concrete_material_card,
        SS3.append_abaqus_input_material_card,
    ])

    with open(outdir / "pipeline.yml", "w") as f:
=======
    pipeline = generate_pipeline(
        ts,
        steps=[
            SS3.aluminium_material_card,
            SS3.create_abaqus_input_material_card,
            SS3.concrete_material_card,
            SS3.append_abaqus_input_material_card,
        ],
    )
    with open(outdir / "pipeline.yml", "w", encoding="utf8") as f:
>>>>>>> Stashed changes
        yaml.safe_dump(pipeline, f)


    pipeline2 = generate_pipeline(
        ts,
        steps=[
            SS3.aluminium_material_card,
            SS3.create_abaqus_input_material_card,
            SS3.concrete_material_card,
            SS3.append_abaqus_input_material_card,
            SS3.file2collection_mat,
            SS3.cuds2datanode,
        ],
    )
    with open(outdir / "pipeline2.yml", "w", encoding="utf8") as f:
        yaml.safe_dump(pipeline2, f)
