"""Test populating a knowledge base from yaml file documenting data resources.
"""


# if True:
def test_populate_kb():
    """Test populating the KB."""
    from paths import indir, outdir
    from tripper import Triplestore

    from ontoconv.pipelines import populate_triplestore

    ts = Triplestore(backend="rdflib")
    populate_triplestore(ts, indir / "resources.yaml")
    ts.serialize(outdir / "kb.ttl")

    # Note, we do not check directly against the KB. Instead we use our
    # APIs for such tests. This is done in `test_2_generate_pipeline` and 
    `test_3_generate_workchain`. 
    
