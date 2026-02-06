"""
Check what the mapping object looks like
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from xml_extractor.config.config_manager import get_config_manager

config_manager = get_config_manager()
mapping_contract = config_manager.load_mapping_contract(str(Path(__file__).parent.parent / "config" / "mapping_contract.json"))

# Find the auth_user_issue_card_flag mapping
for mapping in mapping_contract.mappings:
    if mapping.target_column == 'auth_user_issue_card_flag':
        print(f"Found mapping for {mapping.target_column}:")
        print(f"  xml_path: {mapping.xml_path}")
        print(f"  xml_attribute: {mapping.xml_attribute}")
        print(f"  mapping_type (raw): {repr(mapping.mapping_type)}")
        print(f"  mapping_type (type): {type(mapping.mapping_type)}")
        print(f"  'authu_contact' in mapping_type: {'authu_contact' in mapping.mapping_type if isinstance(mapping.mapping_type, list) else 'N/A (not list)'}")
        break
