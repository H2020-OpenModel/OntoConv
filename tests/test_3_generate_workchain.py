"""Test generating a declarative workchain file for ExecFlow."""


# if True:
def test_load_simulation_resource():
    """Test accessing simulation documentation of simulations."""
    from paths import outdir
    from tripper import Triplestore

    from ontoconv.pipelines import load_simulation_resource

    ts = Triplestore(backend="rdflib")
    ts.parse(outdir / "kb.ttl")
    SS3 = ts.namespaces["ss3"]
    resource = load_simulation_resource(ts, SS3.AbaqusSimulation)

    print("need to check content of resource.files")
    # assert resource.files == ?

    assert resource.aiida_plugin == "execwrapper"
    assert resource.command == "run_abaqus.sh"
    assert resource.install_command.strip() == (
        "pip install git+ssh://git@github.com:H2020-OpenModel/SS3_wrappers.git"
        "@master"
    )
