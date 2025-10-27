
import sys
import os
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)
import pytest
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.models import FieldMapping

@pytest.fixture
def mapper():
    return DataMapper()

def test_string_truncation(mapper):
    mappings = [
        FieldMapping(
            xml_path='/Provenir/Request/CustData/application',
            xml_attribute='IP_address',
            target_table='app_operational_cc',
            target_column='IP_address',
            data_type='varchar(15)',
            mapping_type='default',
        ),
        FieldMapping(
            xml_path='/Provenir/Request/CustData/application',
            xml_attribute='backend_risk_grade',
            target_table='app_operational_cc',
            target_column='backend_risk_grade',
            data_type='char(10)',
            mapping_type='default',
        ),
        FieldMapping(
            xml_path='/Provenir/Request/CustData/application/contact',
            xml_attribute='cell_phone',
            target_table='contact_base',
            target_column='cell_phone',
            data_type='varchar(12)',
            mapping_type='default',
        ),
        FieldMapping(
            xml_path='/Provenir/Request/CustData/application/contact',
            xml_attribute='zip',
            target_table='contact_base',
            target_column='zip',
            data_type='varchar(5)',
            mapping_type='numbers_only',
        ),
        FieldMapping(
            xml_path='/Provenir/Request/CustData/application/contact',
            xml_attribute='ssn',
            target_table='contact_base',
            target_column='ssn',
            data_type='char(9)',
            mapping_type='numbers_only',
        ),
        FieldMapping(
            xml_path='/Provenir/Request/CustData/application/contact/contact_address',
            xml_attribute='cell_phone',
            target_table='contact_base',
            target_column='cell_phone_cur_addr',
            data_type='char(9)',
            mapping_type='curr_address_only',
        ),
    ]
    values = {
        'IP_address': '10.20.135.83 - overflow address should truncate',
        'backend_risk_grade': 'too many characters',
        'cell_phone': '(555) 555-5555 ext. 21',
        'zip': '11234-and-3120',
        'ssn': '664-50-2346-1331',
        'cell_phone_cur_addr': '(555) 555-5555',
    }
    results = {}
    for mapping in mappings:
        val = values[mapping.target_column]
        transformed = mapper._apply_field_transformation(val, mapping)
        results[mapping.target_column] = transformed
    assert results['IP_address'] == '10.20.135.83 -'
    assert results['backend_risk_grade'] == 'too many c'
    assert results['cell_phone'] == '(555) 555-55'
    assert results['zip'] == '11234'
    assert results['ssn'] == '664502346'
    # For curr_address_only, expect only digits, truncated to 10
    assert results['cell_phone_cur_addr'] == '5555555555'
