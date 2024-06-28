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

    assert resource.files == [  # pylint: disable=no-member
        {
            "filename": "the_name_of_the_file.txt",
            "source_uri": "file://path/to/file",
        },
        {
            "filename": "the_name_of_second_file.json",
            "source_uri": "file://path/to/second/file",
        },
    ]
    assert resource.input == {  # pylint: disable=no-member
        "ss3:AluminiumMaterialCard": [
            {
                "function": {
                    "functionType": "application/vnd.dlite-generate",
                    "configuration": {
                        "datamodel": "http://www.sintef.no/calm/0.1/"
                        "AluminiumMaterialCard",
                        "driver": "plugin_abaqus_material",
                        "location": "Section_materials.inp",
                    },
                },
            }
        ]
    }

    assert resource.output == {  # pylint: disable=no-member
        "ss3:AbaqusDeformationHistory": [
            {
                "dataresource": {
                    "mediaType": "application/vnd.dlite-parse",
                    "downloadUrl": "abaqus_deformation_history.txt",
                    "configuration": {
                        "datamodel": "http://www.sintef.no/calm/0.1/"
                        "AbaqusDeformationHistory",
                        "driver": "plugin_abaqus_output",
                    },
                },
            }
        ]
    }

    assert resource.aiida_plugin == "execwrapper"
    assert resource.command == "run_abaqus.sh"
    assert resource.install_command.strip() == (
        "pip install git+ssh://git@github.com:H2020-OpenModel/SS3_wrappers.git"
        "@master"
    )
