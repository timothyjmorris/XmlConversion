import pytest
from pathlib import Path
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.config.config_manager import get_config_manager

CONTRACT_PATH = Path(__file__).parents[3] / 'config' / 'mapping_contract_IL.json'
SAMPLE_XML = Path(__file__).parents[4] / 'config' / 'samples' / 'sample-source-xml-reclending-schema.xml'


def test_data_mapper_instantiation():
    # This test is a light-weight smoke test: instantiate DataMapper with contract
    with open(CONTRACT_PATH, 'r', encoding='utf-8') as f:
        contract = __import__('json').load(f)
    config = get_config_manager()
    # DataMapper should be importable and instantiable. The internals will be exercised in later integration tests.
    dm = DataMapper(contract=contract, config_manager=config)
    assert dm is not None


@pytest.mark.skip("Integration fixture: run when DB/test harness is available")
def test_full_map_dry_run():
    # Placeholder: run a dry-run mapping of SAMPLE_XML using DataMapper and assert no exceptions
    pass
