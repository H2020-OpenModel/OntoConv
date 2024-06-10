"""Test generating a declarative workchain file for ExecFlow."""


# if True:
def test_get_simulation_info():
    """Test accessing simulation documentation of simulations."""
    from paths import outdir
    from tripper import Triplestore

    from ontoconv.pipelines import get_simulation_info

    ts = Triplestore(backend="rdflib")
    ts.parse(outdir / "kb.ttl")
    SS3 = ts.namespaces["ss3"]
    siminfo = get_simulation_info(ts, SS3.AbaqusSimulation)

    assert siminfo.aiida_plugin == "execwrapper"
    assert siminfo.command == "run_abaqus.sh"
    assert siminfo.install_command.strip() == (
        "pip install git+ssh://git@github.com:H2020-OpenModel/SS3_wrappers.git"
        "@master"
    )
