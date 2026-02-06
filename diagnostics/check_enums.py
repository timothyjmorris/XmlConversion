"""
Comprehensive enum column inspection tool.

Checks all enum columns in destination tables and correlates them with:
1. Contract enum mappings (source value -> numeric code)
2. Actual database values
3. Source XML data availability

Usage:
    python diagnostics/check_enums.py [--schema dbo|migration] [--table TABLE_NAME] [--verbose]
"""
import argparse
import json
import pyodbc
from collections import Counter
from xml_extractor.config.config_manager import get_config_manager


def get_connection():
    """Get database connection using centralized config."""
    config = get_config_manager()
    db_config = config.database_config
    
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={db_config.server};"
        f"DATABASE={db_config.database};"
        f"Trusted_Connection=yes;"
        f"TrustServerCertificate=yes;"
        f"Encrypt=no"
    )
    return pyodbc.connect(conn_str)


def load_enum_mappings():
    """Load enum mappings from contract."""
    with open('config/mapping_contract.json') as f:
        contract = json.load(f)
    return contract.get('enum_mappings', {})


def load_field_mappings():
    """Load field mappings from contract to find XML source for each enum column."""
    with open('config/mapping_contract.json') as f:
        contract = json.load(f)
    
    # Build a lookup: target_column -> {xml_path, xml_attribute, mapping_type}
    field_map = {}
    for mapping in contract.get('mappings', []):
        target_col = mapping.get('target_column', '')
        if '_enum' in target_col:
            field_map[target_col] = {
                'target_table': mapping.get('target_table'),
                'xml_path': mapping.get('xml_path'),
                'xml_attribute': mapping.get('xml_attribute'),
                'mapping_type': mapping.get('mapping_type', []),
            }
    return field_map


def get_enum_columns(cursor, schema):
    """Get all enum columns from information schema."""
    cursor.execute("""
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ?
          AND COLUMN_NAME LIKE '%_enum'
          AND TABLE_NAME LIKE 'app_%'
        ORDER BY TABLE_NAME, COLUMN_NAME
    """, (schema,))
    return cursor.fetchall()


def analyze_enum_column(cursor, schema, table, column, enum_mappings, field_mappings, verbose=False):
    """Analyze a single enum column."""
    result = {
        'table': table,
        'column': column,
        'total_rows': 0,
        'non_null_count': 0,
        'null_count': 0,
        'distinct_values': [],
        'value_counts': {},
        'enum_mapping': None,
        'xml_source': None,
        'status': 'UNKNOWN',
        'issues': []
    }
    
    # Get row counts and value distribution
    try:
        cursor.execute(f"""
            SELECT [{column}], COUNT(*) as cnt 
            FROM [{schema}].[{table}] WITH (NOLOCK)
            GROUP BY [{column}]
            ORDER BY cnt DESC
        """)
        rows = cursor.fetchall()
        
        result['total_rows'] = sum(r[1] for r in rows)
        result['null_count'] = sum(r[1] for r in rows if r[0] is None)
        result['non_null_count'] = result['total_rows'] - result['null_count']
        result['distinct_values'] = [r[0] for r in rows if r[0] is not None]
        result['value_counts'] = {r[0]: r[1] for r in rows}
    except Exception as e:
        result['issues'].append(f"Query error: {e}")
        return result
    
    # Look up enum mapping from contract
    # The contract key is usually the column name itself
    if column in enum_mappings:
        result['enum_mapping'] = enum_mappings[column]
    
    # Look up XML source from field mappings
    if column in field_mappings:
        result['xml_source'] = field_mappings[column]
    
    # Determine status
    if result['total_rows'] == 0:
        result['status'] = 'EMPTY TABLE'
    elif result['non_null_count'] == 0:
        result['status'] = 'NEVER POPULATED'
    elif result['null_count'] / result['total_rows'] > 0.95:
        result['status'] = f'SPARSE ({result["non_null_count"]:,} populated)'
    else:
        null_pct = result['null_count'] / result['total_rows'] * 100
        result['status'] = f'OK ({null_pct:.1f}% NULL)'
    
    # Check for values not in enum mapping
    if result['enum_mapping']:
        valid_codes = set(result['enum_mapping'].values())
        unknown_values = [v for v in result['distinct_values'] if v not in valid_codes]
        if unknown_values:
            result['issues'].append(f"Values not in enum mapping: {unknown_values}")
    
    return result


def print_enum_analysis(result, verbose=False):
    """Print analysis for a single enum column."""
    status_first_word = result['status'].split()[0]
    
    if status_first_word == 'NEVER':
        icon = '❌'
    elif status_first_word == 'EMPTY':
        icon = '⚪'
    elif 'SPARSE' in result['status']:
        icon = '⚠️'
    else:
        icon = '✅'
    
    print(f"\n{icon} {result['table']}.{result['column']}")
    print(f"   Rows: {result['total_rows']:,} total, {result['non_null_count']:,} populated, {result['null_count']:,} NULL")
    print(f"   Status: {result['status']}")
    
    if result['distinct_values']:
        values_display = result['distinct_values'][:10]
        suffix = f"... (+{len(result['distinct_values']) - 10} more)" if len(result['distinct_values']) > 10 else ""
        print(f"   Values in DB: {values_display}{suffix}")
    
    if verbose:
        if result['enum_mapping']:
            print(f"   Contract mapping: {result['enum_mapping']}")
        if result['xml_source']:
            src = result['xml_source']
            print(f"   XML source: {src['xml_path']}/@{src['xml_attribute']}")
            print(f"   Mapping type: {src['mapping_type']}")
    
    if result['issues']:
        for issue in result['issues']:
            print(f"   ⚠️ {issue}")


def check_related_fields(cursor, schema, verbose=False):
    """Check related field consistency (e.g., ACH amount vs bank account type)."""
    print("\n" + "="*80)
    print("RELATED FIELD CONSISTENCY CHECKS")
    print("="*80)
    
    checks = [
        {
            'name': 'ACH Banking Fields',
            'table': 'app_operational_cc',
            'description': 'When sc_ach_amount > 0, banking fields should be populated',
            'queries': [
                ('Total with sc_ach_amount > 0', 
                 f'SELECT COUNT(*) FROM [{schema}].app_operational_cc WITH (NOLOCK) WHERE sc_ach_amount > 0'),
                ('... but sc_bank_account_type_enum IS NULL', 
                 f'SELECT COUNT(*) FROM [{schema}].app_operational_cc WITH (NOLOCK) WHERE sc_ach_amount > 0 AND sc_bank_account_type_enum IS NULL'),
                ('... but sc_bank_aba IS NULL', 
                 f'SELECT COUNT(*) FROM [{schema}].app_operational_cc WITH (NOLOCK) WHERE sc_ach_amount > 0 AND sc_bank_aba IS NULL'),
                ('... but sc_bank_account_num IS NULL', 
                 f'SELECT COUNT(*) FROM [{schema}].app_operational_cc WITH (NOLOCK) WHERE sc_ach_amount > 0 AND sc_bank_account_num IS NULL'),
            ]
        },
    ]
    
    for check in checks:
        print(f"\n{check['name']}: {check['description']}")
        for name, query in check['queries']:
            try:
                cursor.execute(query)
                count = cursor.fetchone()[0]
                print(f"   {name}: {count:,}")
            except Exception as e:
                print(f"   {name}: ERROR - {e}")


def main():
    parser = argparse.ArgumentParser(description='Check enum column population and mappings')
    parser.add_argument('--schema', default='dbo', help='Database schema to check (default: dbo)')
    parser.add_argument('--table', help='Specific table to check (optional)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed mapping info')
    parser.add_argument('--issues-only', action='store_true', help='Only show columns with issues')
    args = parser.parse_args()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    enum_mappings = load_enum_mappings()
    field_mappings = load_field_mappings()
    
    print(f"Enum Column Inspection - Schema: {args.schema}")
    print("="*80)
    print(f"Contract defines {len(enum_mappings)} enum mappings")
    print(f"Contract defines {len(field_mappings)} enum field mappings")
    
    # Get all enum columns
    enum_columns = get_enum_columns(cursor, args.schema)
    
    if args.table:
        enum_columns = [c for c in enum_columns if c[0] == args.table]
    
    print(f"Found {len(enum_columns)} enum columns in {args.schema} schema")
    
    # Analyze each column
    results = []
    never_populated = []
    sparse = []
    ok = []
    
    for table, column, data_type in enum_columns:
        result = analyze_enum_column(cursor, args.schema, table, column, 
                                     enum_mappings, field_mappings, args.verbose)
        results.append(result)
        
        if 'NEVER POPULATED' in result['status']:
            never_populated.append(result)
        elif 'SPARSE' in result['status']:
            sparse.append(result)
        else:
            ok.append(result)
    
    # Print summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"  ✅ OK: {len(ok)}")
    print(f"  ⚠️ Sparse (>95% NULL): {len(sparse)}")
    print(f"  ❌ Never Populated: {len(never_populated)}")
    
    # Print details
    if not args.issues_only:
        if ok:
            print(f"\n{'='*80}")
            print("POPULATED ENUMS")
            print(f"{'='*80}")
            for r in ok:
                print_enum_analysis(r, args.verbose)
    
    if sparse:
        print(f"\n{'='*80}")
        print("SPARSE ENUMS (>95% NULL)")
        print(f"{'='*80}")
        for r in sparse:
            print_enum_analysis(r, args.verbose)
    
    if never_populated:
        print(f"\n{'='*80}")
        print("NEVER POPULATED ENUMS")
        print(f"{'='*80}")
        for r in never_populated:
            print_enum_analysis(r, args.verbose)
    
    # Run related field checks
    check_related_fields(cursor, args.schema, args.verbose)
    
    conn.close()


if __name__ == "__main__":
    main()
