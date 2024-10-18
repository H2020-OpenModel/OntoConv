"""Test parsing ourput from OntoFlow and generating
pipelines and workchain."""


# if True:
def test_full_ontoconv():
    """Test generating oteapi pipelines and workchain
    from a given workflow description and a kb."""
    from os import listdir
    from os.path import isfile, join

    import deepdiff
    from paths import expecteddir, indir, outdir
    from tripper.triplestore import Triplestore
    from yaml import safe_load

    from ontoconv.ontoflow import parse_ontoflow

    ts = Triplestore(backend="rdflib")
    ts.parse(indir / "SS3kb.ttl")

    with open(indir / "testflow.yaml", encoding="utf8") as f:
        data = safe_load(f)

    parse_ontoflow(data, ts, outdir=outdir)

    # compare the generated files with the expected ones
    def test_compare_file(filename, pipeline=True):
        # use deepdiff to compare the yaml files

        generated_file = outdir / filename
        expected_file = expecteddir / filename
        # Read the files with yaml safe_load
        with open(generated_file, encoding="utf8") as f:
            generated_pipeline = safe_load(f)
        with open(expected_file, encoding="utf8") as f:
            expected_pipeline = safe_load(f)

        if pipeline:
            diff = deepdiff.DeepDiff(
                generated_pipeline["strategies"],
                expected_pipeline["strategies"],
                ignore_order=True,
            )
            assert not diff

            pipe1 = generated_pipeline["pipelines"]["pipe"].split(" | ")
            pipe2 = expected_pipeline["pipelines"]["pipe"].split(" | ")
            # Since the order of steps in the pipeline is not guaranteed,
            # we compare the sets.
            # Note that we thus do not compare that all sources
            # come before all sinks.
            assert set(pipe1) == set(pipe2)
        else:
            diff = deepdiff.DeepDiff(
                generated_pipeline,
                expected_pipeline,
                ignore_order=True,
            )
            assert not diff

    files = [
        f
        for f in listdir(expecteddir)
        if isfile(join(expecteddir, f)) and "pipeline" in f
    ]
    for filename in files:
        test_compare_file(filename)

    test_compare_file("workchain.yaml", False)
