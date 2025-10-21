#!/usr/bin/env python3

from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.config.config_manager import get_config_manager

def test_phone_extraction():
    print("Testing phone number and months_at_address extraction...")
    
    # Load the sample XML
    with open('config/samples/sample-source-xml-contact-test.xml', 'r') as f:
        xml_content = f.read()

    # Parse and extract
    parser = XMLParser()
    root = parser.parse_xml_stream(xml_content)
    xml_data = parser.extract_elements(root)

    # Apply mapping
    config_manager = get_config_manager()
    mapper = DataMapper()
    
    # Extract app_id and valid contacts first
    app_id = '443306'
    
    # Use map_xml_to_database which properly handles XML root
    result = mapper.map_xml_to_database(xml_data, app_id, [], xml_root=root)

    print('=== CONTACT_BASE PHONE NUMBERS ===')
    if 'contact_base' in result:
        for contact in result['contact_base']:
            con_id = contact.get('con_id')
            cell_phone = contact.get('cell_phone')
            home_phone = contact.get('home_phone')
            print(f'Contact {con_id}: cell_phone={repr(cell_phone)}, home_phone={repr(home_phone)}')
    else:
        print('No contact_base records found')

    print('\n=== CONTACT_ADDRESS MONTHS_AT_ADDRESS ===')
    if 'contact_address' in result:
        for address in result['contact_address']:
            con_id = address.get('con_id')
            months_at_address = address.get('months_at_address')
            print(f'Address {con_id}: months_at_address={repr(months_at_address)}')
    else:
        print('No contact_address records found')

    print('\n=== CONTACT_EMPLOYMENT ALL FIELDS ===')
    if 'contact_employment' in result:
        for employment in result['contact_employment']:
            con_id = employment.get('con_id')
            phone = employment.get('phone')
            street_name = employment.get('street_name')
            street_number = employment.get('street_number')
            zip_code = employment.get('zip')
            other_income_type_enum = employment.get('other_income_type_enum')
            print(f'Employment {con_id}: phone={repr(phone)}, street_name={repr(street_name)}, street_number={repr(street_number)}, zip={repr(zip_code)}, other_income_type_enum={repr(other_income_type_enum)}')
    else:
        print('No contact_employment records found')

if __name__ == "__main__":
    test_phone_extraction()