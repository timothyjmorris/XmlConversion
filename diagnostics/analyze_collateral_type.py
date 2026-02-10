"""Analyze collateral_type_enum mapping issue for app 132709"""
import pyodbc
import json
from lxml import etree

# Extract XML
conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=mbc-dev-npci-use1-db.cofvo8gypwe9.us-east-1.rds.amazonaws.com;'
    'DATABASE=MACDEVOperational;'
    'Trusted_Connection=yes;'
    'MARS_Connection=yes'
)

cursor = conn.cursor()
cursor.execute('SELECT app_id, app_XML FROM migration.app_xml_staging_rl WHERE app_id = 132709')
row = cursor.fetchone()
xml_str = row[1]
conn.close()

# Parse XML
root = etree.fromstring(xml_str.encode('utf-8'))

# Extract relevant elements
app = root.find('.//IL_application')
collateral = root.find('.//IL_collateral')

print("=" * 80)
print("APP 132709 - Collateral Type Enum Analysis")
print("=" * 80)

print("\nIL_application attributes:")
print(f"  app_type_code = '{app.get('app_type_code')}'")
print(f"  sub_type_code = '{app.get('sub_type_code')}'")

print("\nIL_collateral attributes:")
for attr in ['coll1_type', 'coll1_make', 'coll1_model', 'coll1_year']:
    print(f"  {attr} = '{collateral.get(attr)}'")

print("\nMapping Expression Logic:")
app_type = app.get('app_type_code', '')
sub_type = app.get('sub_type_code', '')

print(f"  app_type_code = '{app_type}'")
print(f"  sub_type_code = '{sub_type}'")

# Simulate the CASE expression
if app_type == 'MARINE':
    expected_enum = 412
    print(f"  → MATCH: app_type_code = 'MARINE' → collateral_type_enum = 412")
elif app_type == 'RV':
    expected_enum = 419
    print(f"  → MATCH: app_type_code = 'RV' → collateral_type_enum = 419")
elif app_type and app_type.strip():
    expected_enum = 423
    print(f"  → MATCH: app_type_code IS NOT EMPTY → collateral_type_enum = 423")
else:
    expected_enum = None
    print(f"  → NO MATCH: Expression returns NULL")

print(f"\nExpected collateral_type_enum: {expected_enum}")

# Check contract mapping
with open('config/mapping_contract_rl.json', 'r') as f:
    contract = json.load(f)

coll_type_mappings = [m for m in contract['mappings'] 
                      if m.get('target_column') == 'collateral_type_enum' 
                      and m.get('target_table') == 'app_collateral_rl']

print(f"\nContract Mappings for collateral_type_enum ({len(coll_type_mappings)} found):")
for i, mapping in enumerate(coll_type_mappings, 1):
    print(f"\n  Mapping {i}:")
    print(f"    xml_attribute: {mapping.get('xml_attribute')}")
    print(f"    nullable: {mapping.get('nullable')}")
    print(f"    required: {mapping.get('required')}")
    print(f"    default_value: {mapping.get('default_value', 'NOT SET')}")
    print(f"    mapping_type: {mapping.get('mapping_type')}")
    if 'expression' in mapping:
        print(f"    expression: {mapping['expression'][:100]}...")

print("\n" + "=" * 80)
print("DIAGNOSIS:")
print("=" * 80)
if collateral.get('coll1_type') is None:
    print("❌ coll1_type attribute is MISSING from XML")
    print("   → Calculated field should still evaluate expression")
    print(f"   → Expression should return: {expected_enum}")
    print("   → If returning NULL, check expression evaluation logic")
else:
    print(f"✓ coll1_type = '{collateral.get('coll1_type')}'")
