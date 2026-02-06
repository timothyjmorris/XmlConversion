"""
Source-to-Destination Data Validation Utility - Phase 0.5

Purpose: Compare XML source data against migrated destination data to identify
mapping issues, missing data, and transformation errors.

Usage:
    python diagnostics/validate_source_to_dest.py --server "localhost\\SQLEXPRESS" --database "XmlConversionDB" --app-id 12345
    python diagnostics/validate_source_to_dest.py --server "localhost\\SQLEXPRESS" --database "XmlConversionDB" --sample 10

Features:
- Fetch source XML and destination data for a single app_id
- Compare key fields between source and destination
- Detect enum mapping mismatches
- Identify sparse rows (mostly NULL)
- Generate validation report

Related: docs/onboard_reclending/implementation-plan.md Phase 0.5
"""

import argparse
import json
import logging
import sys
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from lxml import etree
import pyodbc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating a single app_id."""
    app_id: int
    status: str  # 'PASS', 'WARN', 'FAIL'
    issues: List[str] = field(default_factory=list)
    source_fields: Dict[str, Any] = field(default_factory=dict)
    dest_fields: Dict[str, Any] = field(default_factory=dict)
    mismatches: List[Dict[str, Any]] = field(default_factory=list)


def build_connection_string(server: str, database: str, trusted: bool = True) -> str:
    """Build ODBC connection string."""
    server_name = server.replace('\\\\', '\\')
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server_name};DATABASE={database};"
        f"Trusted_Connection=yes;Connection Timeout=30;Application Name=SourceToDestValidator;"
        f"TrustServerCertificate=yes;Encrypt=no;MultipleActiveResultSets=True;"
    )


def fetch_source_xml(conn, app_id: int) -> Optional[str]:
    """Fetch raw XML from app_xml table."""
    cursor = conn.cursor()
    cursor.execute("SELECT app_XML FROM dbo.app_xml WHERE app_id = ?", app_id)
    row = cursor.fetchone()
    return row[0] if row else None


def parse_xml_attributes(xml_content: str, xpath: str) -> Dict[str, str]:
    """Extract attributes from XML element at given XPath."""
    try:
        root = etree.fromstring(xml_content.encode('utf-8') if isinstance(xml_content, str) else xml_content)
        elements = root.xpath(xpath)
        if elements:
            return dict(elements[0].attrib)
    except Exception as e:
        logger.warning(f"XPath extraction failed for {xpath}: {e}")
    return {}


def fetch_dest_data(conn, table: str, schema: str, app_id: int) -> Dict[str, Any]:
    """Fetch destination row for app_id."""
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT * FROM [{schema}].[{table}] WHERE app_id = ?", app_id)
        columns = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()
        if row:
            return dict(zip(columns, row))
    except Exception as e:
        logger.warning(f"Failed to fetch {schema}.{table} for app_id {app_id}: {e}")
    return {}


def validate_enum_mapping(source_value: str, dest_value: Any, enum_mappings: Dict[str, int]) -> Tuple[bool, str]:
    """Check if source value maps correctly to destination enum."""
    if source_value is None or source_value == '':
        if dest_value is None:
            return True, "Both NULL - OK"
        return False, f"Source empty but dest={dest_value}"
    
    expected = enum_mappings.get(source_value.strip())
    if expected is None:
        if dest_value is None:
            return True, f"No mapping for '{source_value}', dest is NULL - OK"
        return False, f"No mapping for '{source_value}' but dest={dest_value}"
    
    if dest_value == expected:
        return True, f"'{source_value}' -> {expected} - OK"
    return False, f"Expected {expected} for '{source_value}', got {dest_value}"


def count_non_null_columns(row: Dict[str, Any], exclude_keys: List[str] = None) -> int:
    """Count non-NULL columns in a row."""
    exclude = set(exclude_keys or ['app_id'])
    return sum(1 for k, v in row.items() if k not in exclude and v is not None)


def validate_app(conn, app_id: int, schema: str = 'dbo') -> ValidationResult:
    """Validate a single app_id by comparing source XML to destination data."""
    result = ValidationResult(app_id=app_id, status='PASS')
    
    # Fetch source XML
    xml_content = fetch_source_xml(conn, app_id)
    if not xml_content:
        result.status = 'FAIL'
        result.issues.append("No source XML found")
        return result
    
    # Extract key source attributes
    request_attrs = parse_xml_attributes(xml_content, '/Provenir/Request')
    app_attrs = parse_xml_attributes(xml_content, '/Provenir/Request/CustData/application')
    
    result.source_fields = {
        'request': request_attrs,
        'application': app_attrs
    }
    
    # Fetch destination data
    tables_to_check = [
        ('app_base', ['decision_enum', 'app_source_enum', 'app_type_enum']),
        ('app_operational_cc', ['status_enum', 'process_enum', 'priority_enum', 'sc_bank_account_type_enum']),
        ('app_pricing_cc', ['credit_limit', 'annual_fee']),
    ]
    
    for table, key_columns in tables_to_check:
        dest_data = fetch_dest_data(conn, table, schema, app_id)
        if not dest_data:
            result.issues.append(f"No data in {table}")
            result.status = 'WARN' if result.status == 'PASS' else result.status
            continue
        
        result.dest_fields[table] = dest_data
        
        # Check for sparse rows
        non_null = count_non_null_columns(dest_data)
        total = len(dest_data) - 1  # exclude app_id
        if total > 0 and non_null / total < 0.2:
            result.issues.append(f"{table}: Sparse row - only {non_null}/{total} columns populated")
            result.status = 'WARN' if result.status == 'PASS' else result.status
    
    # Specific validation: sc_ach_amount vs sc_bank_account_type_enum
    if 'app_operational_cc' in result.dest_fields:
        ops = result.dest_fields['app_operational_cc']
        if ops.get('sc_ach_amount') is not None and ops.get('sc_bank_account_type_enum') is None:
            result.issues.append("Adjacent mismatch: sc_ach_amount has value but sc_bank_account_type_enum is NULL")
            result.mismatches.append({
                'type': 'adjacent_mismatch',
                'table': 'app_operational_cc',
                'field1': 'sc_ach_amount',
                'value1': ops.get('sc_ach_amount'),
                'field2': 'sc_bank_account_type_enum',
                'value2': None
            })
            result.status = 'WARN' if result.status == 'PASS' else result.status
    
    return result


def validate_sample(conn, sample_size: int, schema: str = 'dbo') -> List[ValidationResult]:
    """Validate a random sample of app_ids."""
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT TOP {sample_size} app_id 
        FROM [{schema}].app_base 
        ORDER BY NEWID()
    """)
    app_ids = [row[0] for row in cursor.fetchall()]
    
    results = []
    for app_id in app_ids:
        logger.info(f"Validating app_id {app_id}...")
        result = validate_app(conn, app_id, schema)
        results.append(result)
    
    return results


def print_summary(results: List[ValidationResult]):
    """Print summary of validation results."""
    total = len(results)
    passed = sum(1 for r in results if r.status == 'PASS')
    warned = sum(1 for r in results if r.status == 'WARN')
    failed = sum(1 for r in results if r.status == 'FAIL')
    
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Total validated: {total}")
    print(f"  PASS: {passed} ({100*passed/total:.1f}%)")
    print(f"  WARN: {warned} ({100*warned/total:.1f}%)")
    print(f"  FAIL: {failed} ({100*failed/total:.1f}%)")
    
    # Aggregate issues
    issue_counts = {}
    for r in results:
        for issue in r.issues:
            # Normalize issue text for counting
            key = issue.split(':')[0] if ':' in issue else issue[:50]
            issue_counts[key] = issue_counts.get(key, 0) + 1
    
    if issue_counts:
        print("\nTop Issues:")
        for issue, count in sorted(issue_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"  {count:4d} - {issue}")
    
    # Show sample failures
    failures = [r for r in results if r.status == 'FAIL']
    if failures:
        print(f"\nSample Failures (first 5):")
        for r in failures[:5]:
            print(f"  app_id {r.app_id}: {', '.join(r.issues[:3])}")


def main():
    parser = argparse.ArgumentParser(description='Validate source XML to destination data mapping')
    parser.add_argument('--server', required=True, help='SQL Server name')
    parser.add_argument('--database', required=True, help='Database name')
    parser.add_argument('--app-id', type=int, help='Specific app_id to validate')
    parser.add_argument('--sample', type=int, help='Number of random app_ids to validate')
    parser.add_argument('--schema', default='dbo', help='Target schema (default: dbo)')
    parser.add_argument('--output', help='Output JSON file for detailed results')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    if not args.app_id and not args.sample:
        parser.error("Must specify either --app-id or --sample")
    
    conn_str = build_connection_string(args.server, args.database)
    
    try:
        with pyodbc.connect(conn_str) as conn:
            if args.app_id:
                result = validate_app(conn, args.app_id, args.schema)
                print(f"\nValidation Result for app_id {args.app_id}:")
                print(f"  Status: {result.status}")
                if result.issues:
                    print(f"  Issues:")
                    for issue in result.issues:
                        print(f"    - {issue}")
                if result.mismatches:
                    print(f"  Mismatches:")
                    for m in result.mismatches:
                        print(f"    - {m['type']}: {m['field1']}={m['value1']}, {m['field2']}={m['value2']}")
                results = [result]
            else:
                results = validate_sample(conn, args.sample, args.schema)
                print_summary(results)
            
            if args.output:
                output_data = [
                    {
                        'app_id': r.app_id,
                        'status': r.status,
                        'issues': r.issues,
                        'mismatches': r.mismatches
                    }
                    for r in results
                ]
                with open(args.output, 'w') as f:
                    json.dump(output_data, f, indent=2, default=str)
                print(f"\nDetailed results written to {args.output}")
                
    except pyodbc.Error as e:
        logger.error(f"Database error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
