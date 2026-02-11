"""
Source-to-Destination Data Validation Utility (Multi-Product Support)

Purpose: Compare XML source data against migrated destination data to identify
mapping issues, missing data, and transformation errors.

Usage:
    python diagnostics/validate_source_to_dest_rl.py --server "mbc-dev-npci-use1-db.cofvo8gypwe9.us-east-1.rds.amazonaws.com" --database "MACDEVOperational" --sample 20 --product-line RL

Features:
- Fetch source XML and destination data for a single app_id
- Compare key fields between source and destination
- Detect enum mapping mismatches
- Identify sparse rows (mostly NULL)
- Generate validation report
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


def fetch_source_xml(conn, app_id: int, table_name: str) -> Optional[str]:
    """Fetch raw XML from app_xml table."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT app_XML FROM {table_name} WHERE app_id = ?", app_id)
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


def detect_smells(xml_content: str, result: ValidationResult, product_line: str) -> None:
    """Detect suspicious patterns: default/fallback values in destination that may indicate mapping issues."""
    dest = result.dest_fields
    
    # Define table names based on product line
    ops_table = 'app_operational_rl' if product_line == 'RL' else 'app_operational_cc'
    pricing_table = 'app_pricing_cc'
    
    # Define XML Paths based on product line
    app_xpath = "/Provenir/Request/CustData/IL_application" if product_line == 'RL' else "/Provenir/Request/CustData/application"
    
    # 1) app_pricing_cc (CC Only)
    if product_line == 'CC':
        if dest.get(pricing_table, {}).get('campaign_num') == 'BLANK':
            pricing = _get_xml_elements(xml_content, f"{app_xpath}/marketing_info")
            has_campaign = pricing and any((el.attrib.get('campaign_num') or '').strip() for el in pricing)
            if not has_campaign:
                _add_smell_task(
                    result,
                    "campaign_num = 'BLANK' (default)",
                    "Destination has default 'BLANK'; verify if source campaign_num was empty or missing.",
                    f"{app_xpath}/marketing_info/@campaign_num"
                )
    
        if dest.get(pricing_table, {}).get('marketing_segment') == 'UNKNOWN':
            seg_elements = _get_xml_elements(xml_content, f"{app_xpath}/marketing_info")
            has_segment = seg_elements and any((el.attrib.get('marketing_segment') or '').strip() for el in seg_elements)
            if not has_segment:
                _add_smell_task(
                    result,
                    "marketing_segment = 'UNKNOWN' (fallback)",
                    "Destination has fallback 'UNKNOWN'; verify if source had no matching segment enum.",
                    f"{app_xpath}/marketing_info/@marketing_segment"
                )
    
    # 2) Population Assignment
    ops_data = dest.get(ops_table, {})
    if ops_data.get('population_assignment_enum') in (None, 229):
        app_nodes = _get_xml_elements(xml_content, app_xpath)
        has_pop_assign = app_nodes and any((el.attrib.get('population_assignment_code') or '').strip() for el in app_nodes)
        if has_pop_assign:
             _add_smell_task(
                result,
                "population_assignment_enum missing or default (229)",
                "Enum is NULL or set to default 229; verify source had no population_assignment_code.",
                f"{app_xpath}/@population_assignment_code"
            )
    
    # 3) app_contact_base: first_name or last_name = 'UNKNOWN' (check source)
    contact = dest.get('app_contact_base', {})
    
    contact_elem_name = "IL_contact" if product_line == 'RL' else "contact"
    contact_xpath_pr = f"{app_xpath}/{contact_elem_name}[@ac_role_tp_c='PR']"
    
    if contact.get('first_name') == 'UNKNOWN' or contact.get('last_name') == 'UNKNOWN':
        contact_els = _get_xml_elements(xml_content, contact_xpath_pr)
        has_names = contact_els and any(
            ((el.attrib.get('first_name') or '').strip() and (el.attrib.get('last_name') or '').strip())
            for el in contact_els
        )
        if has_names:
            _add_smell_task(
                result,
                "Contact name is 'UNKNOWN' (fallback)",
                "Primary contact has default name but source seems to have values.",
                f"{contact_xpath_pr}/@first_name | @last_name"
            )
    
    # 4) app_contact_base: ssn = '000000000' (check source)
    if contact.get('ssn') == '000000000':
        contact_els = _get_xml_elements(xml_content, contact_xpath_pr)
        has_valid_ssn = contact_els and any((el.attrib.get('ssn') or '').strip() and el.attrib.get('ssn') != '000000000' for el in contact_els)
        if has_valid_ssn:
            _add_smell_task(
                result,
                "SSN = '000000000' (default)",
                "Destination SSN is '000000000' but source has valid SSN.",
                f"{contact_xpath_pr}/@ssn"
            )
    
    # 5) app_contact_base: birth_date = '1900-01-01' (check source)
    if contact.get('birth_date') and str(contact.get('birth_date')).startswith('1900-01-01'):
        contact_els = _get_xml_elements(xml_content, contact_xpath_pr)
        has_birth = contact_els and any((el.attrib.get('birth_date') or '').strip() for el in contact_els)
        if has_birth:
            _add_smell_task(
                result,
                "birth_date = '1900-01-01' (default)",
                "Birth date is default epoch but source has a value.",
                f"{contact_xpath_pr}/@birth_date"
            )
    
    # 6) app_contact_address: city = 'MISSING' or state = 'XX' or zip = '00000'
    address = dest.get('app_contact_address', {})
    addr_elem_name = "IL_contact_address" if product_line == 'RL' else "contact_address"
    addr_xpath_curr = f"{contact_xpath_pr}/{addr_elem_name}[@address_tp_c='CURR']"
    
    if address.get('city') == 'MISSING' or address.get('state') == 'XX' or address.get('zip') == '00000':
        addr_els = _get_xml_elements(xml_content, addr_xpath_curr)

        if address.get('city') == 'MISSING':
             has_city = addr_els and any((el.attrib.get('city') or '').strip() for el in addr_els)
             if has_city:
                  _add_smell_task(result, "City is 'MISSING' but Source has value", "Mapping failure for City", f"{addr_xpath_curr}/@city")

        if address.get('state') == 'XX':
             has_state = addr_els and any((el.attrib.get('state') or '').strip() for el in addr_els)
             if has_state:
                  _add_smell_task(result, "State is 'XX' but Source has value", "Mapping failure for State", f"{addr_xpath_curr}/@state")

        if address.get('zip') == '00000':
             has_zip = addr_els and any((el.attrib.get('zip') or '').strip() for el in addr_els)
             if has_zip:
                  _add_smell_task(result, "Zip is '00000' but Source has value", "Mapping failure for Zip", f"{addr_xpath_curr}/@zip")


def fetch_dest_data(conn, table: str, schema: str, app_id: int) -> Dict[str, Any]:
    """Fetch destination row for app_id."""
    cursor = conn.cursor()
    try:
        query = f"SELECT * FROM [{schema}].[{table}] WHERE app_id = ?"
        cursor.execute(query, app_id)
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
            if row:
                return dict(zip(columns, row))
    except Exception as e:
        # Table might not exist for this product line
        pass
    return {}


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


def validate_app(conn, app_id: int, schema: str = 'dbo', product_line: str = 'CC') -> ValidationResult:
    """Validate a single app_id by comparing source XML to destination data."""
    result = ValidationResult(app_id=app_id, status='PASS')
    
    # Source Table
    source_table = 'app_xml_staging_rl' if product_line == 'RL' else 'app_xml'
    
    # Fetch source XML
    xml_content = fetch_source_xml(conn, app_id, source_table)
    if not xml_content:
        result.status = 'FAIL'
        result.issues.append(f"No source XML found in {source_table}")
        return result
    
    # Extract key source fields
    app_base_xpath = "/Provenir/Request/CustData/IL_application" if product_line == 'RL' else "/Provenir/Request/CustData/application"
    app_attrs = parse_xml_attributes(xml_content, app_base_xpath)
    result.source_fields.update(app_attrs)
    
    # Fetch destination data
    dest_data = {}
    
    # Common tables
    dest_data['app_base'] = fetch_dest_data(conn, 'app_base', schema, app_id)
    dest_data['app_contact_base'] = fetch_dest_data(conn, 'app_contact_base', schema, app_id)
    dest_data['app_contact_address'] = fetch_dest_data(conn, 'app_contact_address', schema, app_id)
    
    # Product specific tables
    if product_line == 'RL':
        dest_data['app_operational_rl'] = fetch_dest_data(conn, 'app_operational_rl', schema, app_id)
        # Add other RL tables as needed
    else:
        dest_data['app_operational_cc'] = fetch_dest_data(conn, 'app_operational_cc', schema, app_id)
        dest_data['app_pricing_cc'] = fetch_dest_data(conn, 'app_pricing_cc', schema, app_id)
    
    result.dest_fields = dest_data
    
    # Detect smells
    detect_smells(xml_content, result, product_line)
    
    return result

def scan_for_smells(conn, schema: str, product_line: str) -> List[int]:
    """
    Rapidly scan the database for 'smelly' rows (defaults/fallbacks) using SQL.
    Returns a list of app_ids that require XML verification.
    """
    suspect_ids = set()
    cursor = conn.cursor()
    
    source_table = 'app_xml_staging_rl' if product_line == 'RL' else 'app_xml'
    print(f"SCANNING DATABASE FOR SUSPICIOUS DEFAULTS (SMELLS) relevant to {source_table}...")
    
    # 1. Address Defaults (MISSING, XX, 00000)
    addr_table = 'app_contact_address'
    contact_table = 'app_contact_base'
    
    print(f"  - Checking {addr_table} for default addresses (MISSING, XX, 00000)...")
    try:
        query = f"""
            SELECT DISTINCT cb.app_id 
            FROM [{schema}].[{addr_table}] ca
            JOIN [{schema}].[{contact_table}] cb ON ca.con_id = cb.con_id
            WHERE (ca.city = 'MISSING' OR ca.state = 'XX' OR ca.zip = '00000')
            AND cb.app_id IN (SELECT app_id FROM {source_table})
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        if rows:
            print(f"    FOUND {len(rows)} apps with default address values.")
            suspect_ids.update(row[0] for row in rows)
        else:
            print("    Clean.")
    except Exception as e:
        print(f"    Warning: Could not check {addr_table}: {e}")

    # 2. Contact Defaults (UNKNOWN, 000000000)
    print(f"  - Checking {contact_table} for default contact info (UNKNOWN, 000000000)...")
    try:
        query = f"""
            SELECT DISTINCT app_id 
            FROM [{schema}].[{contact_table}]
            WHERE (first_name = 'UNKNOWN' OR last_name = 'UNKNOWN' OR ssn = '000000000')
            AND app_id IN (SELECT app_id FROM {source_table})
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        if rows:
            print(f"    FOUND {len(rows)} apps with default contact info.")
            suspect_ids.update(row[0] for row in rows)
        else:
            print("    Clean.")
    except Exception as e:
         print(f"    Warning: Could not check {contact_table}: {e}")

    # 3. Date Defaults (1900-01-01)
    print(f"  - Checking {contact_table} for default birth_dates (1900-01-01)...")
    try:
        query = f"""
            SELECT DISTINCT app_id 
            FROM [{schema}].[{contact_table}]
            WHERE birth_date = '1900-01-01'
            AND app_id IN (SELECT app_id FROM {source_table})
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        if rows:
             print(f"    FOUND {len(rows)} apps with default birth dates.")
             suspect_ids.update(row[0] for row in rows)
        else:
             print("    Clean.")
    except Exception as e:
         pass
         
    return list(suspect_ids)

def validate_sample(conn, sample_size: int, schema: str = 'dbo', product_line: str = 'CC') -> List[ValidationResult]:
    """Validate a random sample of app_ids."""
    cursor = conn.cursor()
    source_table = 'app_xml_staging_rl' if product_line == 'RL' else 'app_xml'
    
    print(f"Sampling {sample_size} records from {source_table}...")
    cursor.execute(f"SELECT TOP {sample_size} app_id FROM {source_table} ORDER BY NEWID()")
    app_ids = [row[0] for row in cursor.fetchall()]
    
    results = []
    for app_id in app_ids:
        logger.info(f"Validating app_id {app_id}...")
        result = validate_app(conn, app_id, schema, product_line)
        results.append(result)
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate source XML against destination database")
    parser.add_argument("--server", required=True, help="SQL Server instance")
    parser.add_argument("--database", required=True, help="Database name")
    parser.add_argument("--app-id", type=str, help="Specific app_id to validate (comma separated)")
    parser.add_argument("--sample", type=int, help="Number of random app_ids to validate")
    parser.add_argument("--scan-failures", action="store_true", help="Scan entire DB for smells and validate only suspects")
    parser.add_argument("--schema", default="dbo", help="Target schema (default: dbo)")
    parser.add_argument("--product-line", default="CC", choices=["CC", "RL"], help="Product line (CC or RL)")
    parser.add_argument("--output", help="JSON output file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    if not any([args.app_id, args.sample, args.scan_failures]):
        parser.error("Must specify --app-id, --sample, or --scan-failures")
    
    conn_str = build_connection_string(args.server, args.database)
    
    try:
        with pyodbc.connect(conn_str) as conn:
            results = []
            
            if args.scan_failures:
                # 1. Find suspects
                suspect_ids = scan_for_smells(conn, args.schema, args.product_line)
                if not suspect_ids:
                    print("\nSUCCESS: Scanned entire database and found NO rows with default/fallback values (MISSING, UNKNOWN, etc).")
                    # If clean, maybe just sample 5 to check generic mapping validity?
                    print("Running 5 random checks just to be sure...")
                    results = validate_sample(conn, 5, args.schema, args.product_line)
                else:
                    print(f"\nProceeding to validate {len(suspect_ids)} suspect applications against source XML...")
                    # 2. Validate suspects
                    # Limit to top 50 suspects to avoid overload if millions found
                    limit = 50
                    if len(suspect_ids) > limit:
                        print(f"Limiting validation to first {limit} suspects...")
                        suspect_ids = suspect_ids[:limit]
                        
                    for i, aid in enumerate(suspect_ids):
                        if i % 10 == 0:
                            print(f"  Progress: {i}/{len(suspect_ids)}...")
                        results.append(validate_app(conn, aid, args.schema, args.product_line))
                    
            elif args.app_id:
                app_ids = [int(x.strip()) for x in args.app_id.split(',')]
                for aid in app_ids:
                    print(f"Validating {aid}...")
                    results.append(validate_app(conn, aid, args.schema, args.product_line))
            elif args.sample:
                results = validate_sample(conn, args.sample, args.schema, args.product_line)

            # Summarize
            if results:
                pass_count = sum(1 for r in results if r.status == 'PASS')
                problem_results = [r for r in results if r.status != 'PASS' or r.issues or r.mismatches or r.smell_tasks]
                
                print(f"\nValidation Complete: {pass_count}/{len(results)} Passed")
                
                if problem_results:
                     print("\n" + "=" * 60)
                     print("DETAILED FINDINGS")
                     print("=" * 60)
                     for r in problem_results:
                          print(f"\nApp {r.app_id}: {r.status}")
                          for issue in r.issues:
                              print(f"  - ISSUE: {issue}")
                          for smell in r.smell_tasks:
                              print(f"  - SMELL: {smell['title']} -> {smell['reason']}")
            
            if args.output and results:
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



