import json
from pathlib import Path
from xml_extractor.config.config_manager import get_config_manager

CONTRACT_PATH = Path(__file__).parents[3] / 'config' / 'mapping_contract_IL.json'


def test_il_contract_loads():
    assert CONTRACT_PATH.exists(), f"IL contract not found at {CONTRACT_PATH}"
    with open(CONTRACT_PATH, 'r', encoding='utf-8') as f:
        contract = json.load(f)
    # basic sanity checks
    assert 'target_schema' in contract
    assert 'relationships' in contract
    assert 'element_filtering' in contract


def test_contract_has_enum_mappings():
    with open(CONTRACT_PATH, 'r', encoding='utf-8') as f:
        contract = json.load(f)
    assert 'enum_mappings' in contract
    # ensure at least one mapping exists
    assert len(contract['enum_mappings']) > 0
