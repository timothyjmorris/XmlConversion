#!/usr/bin/env python3
"""
Diagnostic script to verify contract-driven enum fallback/default logic and mapping pipeline integrity for population_assignment_enum.
- Loads mapping contract
- Loads sample XML
- Runs DataMapper mapping
- Prints mapped value for population_assignment_enum
- Verifies fallback/default logic
- Optionally checks database for inserted value
"""
import sys
import json
from pathlib import Path
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.validation.pre_processing_validator import PreProcessingValidator

# Paths
project_root = Path(__file__).parent
contract_path = project_root / "config" / "mapping_contract.json"
sample_xml_path = project_root / "config" / "samples" / "sample-source-xml-contact-test.xml"

# Load mapping contract
with open(contract_path, "r", encoding="utf-8") as f:
    contract = json.load(f)

# Load sample XML
with open(sample_xml_path, "r", encoding="utf-8-sig") as f:
    sample_xml = f.read()

# Parse XML
parser = XMLParser()
root = parser.parse_xml_stream(sample_xml)
xml_data = parser.extract_elements(root)

# Validate XML
validator = PreProcessingValidator()
validation_result = validator.validate_xml_for_processing(sample_xml, "diagnostic_test")
app_id = validation_result.app_id
valid_contacts = validation_result.valid_contacts

# Initialize DataMapper
mapper = DataMapper(mapping_contract_path=str(contract_path))

# Map XML to database
mapped_data = mapper.map_xml_to_database(xml_data, app_id, valid_contacts, root)

# Print mapped value for population_assignment_enum
pricing_records = mapped_data.get("app_pricing_cc", [])
print("\n--- Diagnostic: population_assignment_enum mapping ---")
for record in pricing_records:
    print(f"app_id: {record.get('app_id')}, population_assignment_enum: {record.get('population_assignment_enum')}")
    if record.get('population_assignment_enum') is None:
        print("[ERROR] population_assignment_enum is None! Should fallback to default if missing.")
    elif record.get('population_assignment_enum') == 229:
        print("[INFO] population_assignment_enum fallback/default applied (229)")
    else:
        print(f"[INFO] population_assignment_enum mapped value: {record.get('population_assignment_enum')}")

# Print contract enum mapping for population_assignment_enum
print("\n--- Contract enum mapping for population_assignment_enum ---")
enum_mappings = contract.get("enum_mappings", {})
pop_enum_map = enum_mappings.get("population_assignment_enum", {})
print(json.dumps(pop_enum_map, indent=2))

# Optionally: Check database for inserted value (requires pyodbc and connection string)
# Uncomment and configure connection string if needed
# import pyodbc
# connection_string = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS;DATABASE=XmlConversionDB;Trusted_Connection=yes;"
# with pyodbc.connect(connection_string) as conn:
#     cursor = conn.cursor()
#     cursor.execute("SELECT population_assignment_enum FROM app_pricing_cc WHERE app_id = ?", app_id)
#     db_value = cursor.fetchone()[0]
#     print(f"[DB] population_assignment_enum in DB: {db_value}")

print("\nDiagnostic complete.")
