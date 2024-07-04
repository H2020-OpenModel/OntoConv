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

    with open(outdir / "pipeline2.yml", encoding="utf8") as f:
        data = yaml.safe_load(f)

    assert data["version"] == 1
    assert len(data["strategies"]) == 6

    # check that the following strategies are present
    strategies = [
        "datanode2cuds",
        "AbaqusDeformationHistory_function_1",
        "concrete_material_card_dataresource_2",
        "AluminiumMaterialCard_function_3",
        "AluminiumMaterialCard_function_3_file_to_aiida_datanode",
        "cuds2datanode",
    ]
    # In strategies, find all the values of the keys
    # 'function' and 'dataresource'
    names = []
    for strategy in data["strategies"]:
        if "function" in strategy:
            names.append(strategy["function"])
        if "dataresource" in strategy:
            names.append(strategy["dataresource"])
    # Check that the same strategies are present in the pipeline
    assert set(strategies) == set(names)

    # check a dataset
    strat = next(
        strategy
        for strategy in data["strategies"]
        if strategy.get("dataresource")
        == "concrete_material_card_dataresource_2"
    )
    assert strat == {
        "downloadUrl": "file://tests/tests_dlite_plugins/testfiles"
        "/input/material_card_concrete.json",
        "mediaType": "application/vnd.dlite-parse",
        "type": "ss3:ConcreteMaterialCard",
        "configuration": {
            "label": "materialcard_concrete",
            "driver": "json",
            "metadata": "http://www.sintef.no/calm/0.1/"
            "AbaqusSimpleMaterialCard",
        },
        "dataresource": "concrete_material_card_dataresource_2",
    }
    # check a function sepcified in the documentation
    strat = next(
        strategy
        for strategy in data["strategies"]
        if strategy.get("function") == "AbaqusDeformationHistory_function_1"
    )
    assert strat == {
        "configuration": {
            "function_name": "singlefile_converter",
            "module_name": "execflow.data.singlefile_converter",
            "inputs": [
                {
                    "label": "AbaqusDeformationHistory_aiida_datanode",
                    "datamodel": "http://onto-ns.com/meta/2.0/"
                    "core.singlefile",
                }
            ],
            "outputs": [
                {
                    "label": "AbaqusDeformationHistory_oteapi_instance",
                    "datamodel": "http://www.sintef.no/calm/0.1/"
                    "AbaqusDeformationHistory",
                }
            ],
            "parse_driver": "plugin_abaqus_output",
        },
        "functionType": "application/vnd.dlite-convert",
        "function": "AbaqusDeformationHistory_function_1",
    }
    # Check the function that converts a file to an AiiDA data node
    strat = next(
        strategy
        for strategy in data["strategies"]
        if strategy.get("function")
        == "AluminiumMaterialCard_function_3_file_to_aiida_datanode"
    )
    assert strat == {
        "function": "AluminiumMaterialCard_function_3_file_to_aiida_datanode",
        "functionType": "aiidacuds/file2collection",
        "configuration": {
            "path": "Section_materials.inp",
            "label": "AluminiumMaterialCard_function_3_file",
        },
    }
