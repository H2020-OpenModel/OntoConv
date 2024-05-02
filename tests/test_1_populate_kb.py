"""Test populating a knowledge base from yaml file documenting data resources."""


if True:
#def test_populate_kb():
    from tripper import Triplestore

    from ontoconv.utils import populate_triplestore
    from ontoconv.testutils import indir, outdir

    ts = Triplestore(backend="rdflib")
    populate_triplestore(ts, indir / "resources.yaml")
    ts.serialize(outdir / "kb.ttl")
