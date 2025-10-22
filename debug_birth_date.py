import sys
import logging
sys.path.append('.')

# Set up debug logging
logging.basicConfig(level=logging.WARNING, format='%(levelname)s - %(message)s')

from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.config.config_manager import get_config_manager
import pyodbc

# Get XML for app_id 8 (207748)
conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS;DATABASE=XmlConversionDB;Trusted_Connection=yes;')
cursor = conn.cursor()
cursor.execute('SELECT xml FROM app_xml WHERE app_id = 8')
xml_content = cursor.fetchone()[0]
conn.close()

# Initialize components
parser = XMLParser()
mapper = DataMapper()

# Parse XML
xml_root = parser.parse_xml_stream(xml_content)
# xml_data = parser.extract_xml_data(xml_root)  # Skip this for now

print("Testing birth_date transformation for app 207748...")

# Get contact_base mappings
config_manager = get_config_manager()
mapping_contract = config_manager.load_mapping_contract('config/credit_card_mapping_contract.json')
contact_base_mappings = [m for m in mapping_contract.mappings if m.target_table == 'contact_base']

print(f"Found {len(contact_base_mappings)} contact_base mappings")

# Find birth_date mapping
birth_date_mapping = None
for mapping in contact_base_mappings:
    if mapping.target_column == 'birth_date':
        birth_date_mapping = mapping
        break

if birth_date_mapping:
    print(f"Birth_date mapping found:")
    print(f"  xml_path: {birth_date_mapping.xml_path}")
    print(f"  xml_attribute: {birth_date_mapping.xml_attribute}")
    print(f"  data_type: {birth_date_mapping.data_type}")
    print(f"  default_value attr: {getattr(birth_date_mapping, 'default_value', 'NOT_SET')}")
    print(f"  All attributes: {dir(birth_date_mapping)}")
    
    # Check the raw mapping data
    print(f"\nChecking raw mapping object...")
    for attr in ['default_value', 'defaultValue', 'default']:
        if hasattr(birth_date_mapping, attr):
            val = getattr(birth_date_mapping, attr)
            print(f"  {attr}: {val}")
    
    # Test transformation with empty string
    print(f"\nTesting transformation with empty string...")
    result = mapper._apply_field_transformation('', birth_date_mapping, None)
    print(f"Transformation result: {result}")
    
    # Test default value retrieval
    default_val = mapper._get_default_for_mapping(birth_date_mapping)
    print(f"Default value from mapping: {default_val}")
else:
    print("ERROR: No birth_date mapping found for contact_base!")