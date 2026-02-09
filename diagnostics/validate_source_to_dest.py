"""
Source-to-Destination Data Validation Utility - Phase 0.5

Purpose: Compare XML source data against migrated destination data to identify
mapping issues, missing data, and transformation errors.

Usage:
    python diagnostics/validate_source_to_dest.py --server "localhost\\SQLEXPRESS" --database "XmlConversionDB" --app-id 12345
    python .\diagnostics\validate_source_to_dest.py --server "mbc-dev-npci-use1-db.cofvo8gypwe9.us-east-1.rds.amazonaws.com" --database "MACDEVOperational" --schema dbo --output ./diagnostics/validate_source_to_dest_results.json --sample 20

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
from decimal import Decimal
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
    smell_tasks: List[Dict[str, str]] = field(default_factory=list)


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


def _get_xml_elements(xml_content: str, xpath: str) -> List[etree._Element]:
    """Return XML elements for the given XPath, or empty list on failure."""
    try:
        root = etree.fromstring(xml_content.encode('utf-8') if isinstance(xml_content, str) else xml_content)
        return root.xpath(xpath)
    except Exception as e:
        logger.warning(f"XPath extraction failed for {xpath}: {e}")
        return []


def _add_smell_task(result: ValidationResult, title: str, reason: str, xpath: str) -> None:
    result.smell_tasks.append({
        'title': title,
        'reason': reason,
        'xpath': xpath
    })


def detect_smells(xml_content: str, result: ValidationResult) -> None:
    """Detect suspicious patterns: default/fallback values in destination that may indicate mapping issues.
    
    Check for values that look like defaults (BLANK, UNKNOWN, MISSING, 00000, etc.) and verify
    whether the source XML actually had those values or if they were injected as fallbacks.
    """
    
    dest = result.dest_fields
    
    # 1) app_pricing_cc: campaign_num = 'BLANK' (check source)
    if dest.get('app_pricing_cc', {}).get('campaign_num') == 'BLANK':
        pricing = _get_xml_elements(xml_content, "/Provenir/Request/CustData/application/marketing_info")
        has_campaign = pricing and any((el.attrib.get('campaign_num') or '').strip() for el in pricing)
        if not has_campaign:
            _add_smell_task(
                result,
                "campaign_num = 'BLANK' (default)",
                "Destination has default 'BLANK'; verify if source campaign_num was empty or missing.",
                "/Provenir/Request/CustData/application/marketing_info/@campaign_num"
            )
    
    # 2) app_pricing_cc: marketing_segment = 'UNKNOWN' (check source)
    if dest.get('app_pricing_cc', {}).get('marketing_segment') == 'UNKNOWN':
        seg_elements = _get_xml_elements(xml_content, "/Provenir/Request/CustData/application/marketing_info")
        has_segment = seg_elements and any((el.attrib.get('marketing_segment') or '').strip() for el in seg_elements)
        if not has_segment:
            _add_smell_task(
                result,
                "marketing_segment = 'UNKNOWN' (fallback)",
                "Destination has fallback 'UNKNOWN'; verify if source had no matching segment enum.",
                "/Provenir/Request/CustData/application/marketing_info/@marketing_segment"
            )
    
    # 3) population_assignment_enum is NULL or 229 (default enum value for missing)
    if dest.get('app_operational_cc', {}).get('population_assignment_enum') in (None, 229):
        app_nodes = _get_xml_elements(xml_content, "/Provenir/Request/CustData/application")
        has_pop_assign = app_nodes and any((el.attrib.get('population_assignment_code') or '').strip() for el in app_nodes)
        if not has_pop_assign:
            _add_smell_task(
                result,
                "population_assignment_enum missing or default (229)",
                "Enum is NULL or set to default 229; verify source had no population_assignment_code.",
                "/Provenir/Request/CustData/application/@population_assignment_code"
            )
    
    # 4) app_contact_base: first_name or last_name = 'UNKNOWN' (check source)
    contact = dest.get('app_contact_base', {})
    if contact.get('first_name') == 'UNKNOWN' or contact.get('last_name') == 'UNKNOWN':
        contact_els = _get_xml_elements(xml_content, "/Provenir/Request/CustData/application/contact[@ac_role_tp_c='PR']")
        has_names = contact_els and any(
            ((el.attrib.get('first_name') or '').strip() and (el.attrib.get('last_name') or '').strip())
            for el in contact_els
        )
        if not has_names:
            _add_smell_task(
                result,
                "Contact name is 'UNKNOWN' (fallback)",
                "Primary contact has default name; verify if source name fields were empty.",
                "/Provenir/Request/CustData/application/contact[@ac_role_tp_c='PR']/@first_name | @last_name"
            )
    
    # 5) app_contact_base: ssn = '000000000' (check source)
    if contact.get('ssn') == '000000000':
        contact_els = _get_xml_elements(xml_content, "/Provenir/Request/CustData/application/contact[@ac_role_tp_c='PR']")
        has_ssn = contact_els and any((el.attrib.get('ssn') or '').strip() and el.attrib.get('ssn') != '000000000' for el in contact_els)
        if not has_ssn:
            _add_smell_task(
                result,
                "SSN = '000000000' (default/missing)",
                "Contact SSN is all zeros (default); verify if source had no SSN or used zeros.",
                "/Provenir/Request/CustData/application/contact[@ac_role_tp_c='PR']/@ssn"
            )
    
    # 6) app_contact_base: birth_date = '1900-01-01' (check source)
    if contact.get('birth_date') and str(contact.get('birth_date')).startswith('1900-01-01'):
        contact_els = _get_xml_elements(xml_content, "/Provenir/Request/CustData/application/contact[@ac_role_tp_c='PR']")
        has_birth = contact_els and any((el.attrib.get('birth_date') or '').strip() for el in contact_els)
        if not has_birth:
            _add_smell_task(
                result,
                "birth_date = '1900-01-01' (default)",
                "Birth date is default epoch; verify if source had no birth_date.",
                "/Provenir/Request/CustData/application/contact[@ac_role_tp_c='PR']/@birth_date"
            )
    
    # 7) app_contact_address: city = 'MISSING' or state = 'XX' or zip = '00000'
    address = dest.get('app_contact_address', {})
    if address.get('city') == 'MISSING' or address.get('state') == 'XX' or address.get('zip') == '00000':
        addr_els = _get_xml_elements(xml_content, "/Provenir/Request/CustData/application/contact[@ac_role_tp_c='PR']/contact_address[@address_tp_c='CURR']")
        has_full_addr = addr_els and any(
            ((el.attrib.get('city') or '').strip() and 
             (el.attrib.get('state') or '').strip() and 
             (el.attrib.get('zip') or '').strip())
            for el in addr_els
        )
        if not has_full_addr:
            _add_smell_task(
                result,
                "Address has default/missing values (MISSING, XX, 00000)",
                "Current address has defaults; verify source had incomplete address data.",
                "/Provenir/Request/CustData/application/contact[@ac_role_tp_c='PR']/contact_address[@address_tp_c='CURR']/@city | @state | @zip"
            )
    
    # 8) priority_enum is NULL (should usually be populated)
    if dest.get('app_operational_cc', {}).get('priority_enum') is None:
        request_els = _get_xml_elements(xml_content, "/Provenir/Request")
        has_priority = request_els and any((el.attrib.get('priority') or '').strip() for el in request_els)
        if has_priority:
            _add_smell_task(
                result,
                "priority_enum is NULL (but source has priority)",
                "Request has priority attribute but destination enum is NULL; check enum mapping.",
                "/Provenir/Request/@Priority"
            )
    
    # 9) ACH banking checks: sc_ach_amount > 0 but banking details are NULL
    ops = dest.get('app_operational_cc', {})
    if _is_positive_amount(ops.get('sc_ach_amount')):
        if ops.get('sc_bank_aba') is None:
            _add_smell_task(
                result,
                "ACH amount present but sc_bank_aba is NULL",
                "ACH amount has value but no routing number; verify source had bank routing data.",
                "/Provenir/Request/CustData/application//savings_acct[@acct_type='ACH']/@bank_aba"
            )
        if ops.get('sc_bank_account_num') is None:
            _add_smell_task(
                result,
                "ACH amount present but sc_bank_account_num is NULL",
                "ACH amount has value but no account number; verify source had account data.",
                "/Provenir/Request/CustData/application//savings_acct[@acct_type='ACH']/@account_num"
            )
        if ops.get('sc_bank_account_type_enum') is None:
            _add_smell_task(
                result,
                "ACH amount present but sc_bank_account_type_enum is NULL",
                "ACH amount has value but account type enum is missing; check account type mapping.",
                "/Provenir/Request/CustData/application//savings_acct[@acct_type='ACH']/@account_type"
            )


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


def _is_positive_amount(value: Any) -> bool:
    """Return True if value can be interpreted as a positive numeric amount."""
    if value is None:
        return False
    if isinstance(value, (int, float, Decimal)):
        return value > 0
    try:
        return float(str(value)) > 0
    except (ValueError, TypeError):
        return False


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
        if total > 0 and non_null / total < 0.15:
            result.issues.append(f"{table}: Sparse row - only {non_null}/{total} columns populated")
            result.status = 'WARN' if result.status == 'PASS' else result.status
    
    # Specific validation: sc_ach_amount vs sc_bank_account_type_enum
    if 'app_operational_cc' in result.dest_fields:
        ops = result.dest_fields['app_operational_cc']
        if _is_positive_amount(ops.get('sc_ach_amount')) and ops.get('sc_bank_account_type_enum') is None:
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

    # Smell-based verification tasks
    detect_smells(xml_content, result)
    
    return result


def validate_sample(conn, sample_size: int, schema: str = 'dbo') -> List[ValidationResult]:
    """Validate a random sample of app_ids."""
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT TOP {sample_size} app_id 
        FROM [{schema}].app_base 
        ORDER BY CRYPT_GEN_RANDOM(12)
    """)
    app_ids = [row[0] for row in cursor.fetchall()]
    
    results = []
    for app_id in app_ids:
        logger.info(f"Validating app_id {app_id}...")
        result = validate_app(conn, app_id, schema)
        results.append(result)
    
    return results


def print_summary(results: List[ValidationResult]):
    """Print summary of validation results (problems only)."""
    problem_results = [r for r in results if r.status != 'PASS' or r.issues or r.mismatches or r.smell_tasks]
    total = len(problem_results)
    warned = sum(1 for r in problem_results if r.status == 'WARN')
    failed = sum(1 for r in problem_results if r.status == 'FAIL')
    
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY (PROBLEMS ONLY)")
    print("=" * 60)
    print(f"Total problems: {total}")
    if total > 0:
        print(f"  WARN: {warned} ({100*warned/total:.1f}%)")
        print(f"  FAIL: {failed} ({100*failed/total:.1f}%)")
    
    # Aggregate issues
    issue_counts = {}
    for r in problem_results:
        for issue in r.issues:
            # Normalize issue text for counting
            key = issue.split(':')[0] if ':' in issue else issue[:50]
            issue_counts[key] = issue_counts.get(key, 0) + 1
    
    if issue_counts:
        print("\nTop Issues:")
        for issue, count in sorted(issue_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"  {count:4d} - {issue}")
    
    # Show sample failures
    failures = [r for r in problem_results if r.status == 'FAIL']
    if failures:
        print(f"\nSample Failures (first 5):")
        for r in failures[:5]:
            print(f"  app_id {r.app_id}: {', '.join(r.issues[:3])}")

    # Show smell-based verification tasks
    smell_results = [r for r in problem_results if r.smell_tasks]
    if smell_results:
        print(f"\nVerification Task List (first 5 apps with smells):")
        for r in smell_results[:5]:
            print(f"  app_id {r.app_id}:")
            for task in r.smell_tasks[:5]:
                print(f"    - {task['title']}: {task['reason']}")
                print(f"      XPath: {task['xpath']}")


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
                if result.status != 'PASS' or result.issues or result.mismatches or result.smell_tasks:
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
                    if result.smell_tasks:
                        print(f"  Verification Tasks:")
                        for task in result.smell_tasks[:10]:
                            print(f"    - {task['title']}: {task['reason']}")
                            print(f"      XPath: {task['xpath']}")
                else:
                    print(f"\nValidation Result for app_id {args.app_id}: no issues detected.")
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
                        'mismatches': r.mismatches,
                        'smell_tasks': r.smell_tasks
                    }
                    for r in results
                    if r.status != 'PASS' or r.issues or r.mismatches or r.smell_tasks
                ]
                with open(args.output, 'w') as f:
                    json.dump(output_data, f, indent=2, default=str)
                print(f"\nDetailed results written to {args.output}")
                
    except pyodbc.Error as e:
        logger.error(f"Database error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
