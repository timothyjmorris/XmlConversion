import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from xml_extractor.validation.pre_processing_validator import PreProcessingValidator
from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.mapping.data_mapper import DataMapper

# Load the sample XML using the same method as the working test
sample_path = Path("config/samples/sample-source-xml-contact-test.xml")
with open(sample_path, 'r', encoding='utf-8-sig') as f:
    sample_xml = f.read()

print("=== Testing Contact Deduplication ===")

# Step 1: Use the validator to extract contacts (this handles deduplication)
validator = PreProcessingValidator()
validation_result = validator.validate_xml_for_processing(sample_xml, "dedup_test")

print(f"Validation result: valid={validation_result.is_valid}")
print(f"Valid contacts found: {len(validation_result.valid_contacts)}")

for i, contact in enumerate(validation_result.valid_contacts):
    con_id = contact.get('con_id', 'MISSING')
    ac_role = contact.get('ac_role_tp_c', 'MISSING')
    first_name = contact.get('first_name', 'MISSING')
    print(f"  {i+1}: con_id={con_id}, ac_role_tp_c={ac_role}, first_name={first_name}")

# Step 2: Test the DataMapper's deduplication
parser = XMLParser()
mapper = DataMapper()

root = parser.parse_xml_stream(sample_xml)
xml_data = parser.extract_elements(root)

# Use DataMapper's _extract_valid_contacts method
valid_contacts = mapper._extract_valid_contacts(xml_data)
print(f"\nDataMapper valid contacts: {len(valid_contacts)}")

for i, contact in enumerate(valid_contacts):
    con_id = contact.get('con_id', 'MISSING')
    ac_role = contact.get('ac_role_tp_c', 'MISSING')
    first_name = contact.get('first_name', 'MISSING')
    print(f"  {i+1}: con_id={con_id}, ac_role_tp_c={ac_role}, first_name={first_name}")

# Check for duplicates in the final result
con_ids = [c.get('con_id') for c in valid_contacts]
duplicates = [x for x in con_ids if con_ids.count(x) > 1]
if duplicates:
    print(f"\n⚠️ DUPLICATES FOUND: {set(duplicates)}")
    print("This explains the PK violation in the integration test!")
else:
    print(f"\n✅ No duplicates found - deduplication working correctly")