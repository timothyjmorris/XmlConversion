"""
Generate mapping_contract_rl.json from the RL CSV contract definition.

This script reads the authoritative CSV at:
  docs/onboard_reclending/xml-source-to-database-contract-rl.csv

And produces:
  config/mapping_contract_rl.json

All fixes from user review are embedded here:
  - RL-specific enum IDs (not CC)
  - smallint for all enum data_types
  - Single-line expressions (no literal \\n)
  - add_collateral(N) row-creating pattern
  - warranty_field(N) row-creating pattern
  - policy_exceptions(N) row-creating pattern
  - funding_validation_indicator_rl for checklist enums
  - officer_code_to_email_enum
  - contact-by-type-to-fixed-field → last_valid_pr_contact / last_valid_sec_contact
  - supervisor_review_indicator_rl
  - check_requested_by_user (CASE + officer_code_to_email_enum fallback)
  - bank_account_type_rl
  - Proper table naming (contact_base → app_contact_base, etc.)
  - Deduplication of exact-match entries
"""
import csv
import json
import re
from pathlib import Path
from typing import Any

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DOCS_DIR = BASE_DIR / "docs" / "onboard_reclending"

CSV_PATH = DOCS_DIR / "xml-source-to-database-contract-rl.csv"
OUTPUT_CONTRACT_PATH = CONFIG_DIR / "mapping_contract_rl.json"

# ---------------------------------------------------------------------------
# RL-specific enum mappings (from insert_enum_values.sql)
# ---------------------------------------------------------------------------
RL_ENUM_MAPPINGS = {
    "product_line_enum": {
        "": 602
    },
    "app_source_enum": {
        "APPONE": 10,
        "DEALERTRACK": 11,
        "FAXED-IN": 12,
        "S": 13,
        "DEALER DIRECT": 14
    },
    "app_type_enum": {
        "HT": 38,
        "MARINE": 39,
        "MC": 40,
        "OR": 41,
        "RV": 42,
        "UT": 43
    },
    "sub_type_enum": {
        "ATV": 45,
        "PWC": 46,
        "SNOWMOBILE": 47,
        "UTV": 48
    },
    "decision_enum": {
        "APPROVED": 610,
        "DECLINED": 611,
        "PENDING": 612,
        "WITHDRAWN": 613
    },
    "collateral_type_enum": {
        "ATV": 410,
        "BOAT (NO MOTOR)": 411,
        "BOAT W/ MOTOR": 412,
        "MOTOR ONLY": 413,
        "MOTOR UNIT (TRIKE)": 414,
        "MOTORHOME/TRAVEL TRAILER": 415,
        "MOTORCYCLE": 416,
        "OTHER": 417,
        "PWC": 418,
        "RV/CAMPER": 419,
        "SNOWMOBILE": 420,
        "TRAILER": 421,
        "UTV": 422,
        "UNDETERMINED": 423
    },
    "warranty_type_enum": {
        "Credit Disability": 620,
        "Credit Life": 621,
        "Extended Warranty": 622,
        "GAP": 623,
        "Other": 624,
        "Roadside Assistance": 625,
        "Service Contract": 626
    },
    "policy_exception_type_enum": {
        "Capacity": 630,
        "Collateral/Program": 631,
        "Credit": 632
    },
    "mrv_model_type_enum": {
        "MRV": 640,
        "Vantage": 641
    },
    "bank_account_type_enum": {
        "22": 650,
        "CHECKING": 650,
        "32": 651,
        "SAVINGS": 651
    },
    "fund_loan_indicator_enum": {
        "Y": 655,
        "N": 656,
        "P": 657
    },
    "y_n_d_enum": {
        "Y": 660,
        "N": 661,
        "D": 662
    },
    "process_enum": {
        "03800": 670,
        "04000": 671,
        "04500": 672,
        "05000": 673,
        "06000": 674,
        "07000": 675,
        "08000": 676,
        "09000": 677,
        "99800": 678
    },
    "status_enum": {
        "F": 690,
        "P": 691
    },
    "supervisor_review_indicator_enum": {
        "C": 700,
        "R": 701
    },
    "audit_flag_enum": {
        "R": 706,
        "P": 707
    },
    "contact_type_enum": {
        "PR": 281,
        "SEC": 282,
        "AUTHU": 280
    },
    "address_type_enum": {
        "CURR": 320,
        "PREV": 321,
        "PATR": 322,
        "COLL": 323
    },
    "ownership_type_enum": {
        "O": 330,
        "F": 331,
        "R": 332,
        "L": 333,
        "T": 334,
        "W": 324,
        "X": 335
    },
    "employment_type_enum": {
        "CURR": 350,
        "PREV": 351
    },
    "income_type_enum": {
        "ALLOW": 360,
        "EMPLOY": 361,
        "GOVAST": 362,
        "INVEST": 363,
        "OTHER": 364,
        "RENTAL": 365
    },
    "other_income_type_enum": {
        "ALLOW": 380,
        "ALMONY": 381,
        "BONUS": 382,
        "CHDSUP": 383,
        "CTPYMT": 384,
        "DISINC": 385,
        "EMPLOY": 386,
        "INVEST": 387,
        "MILTRY": 388,
        "OTHER": 389,
        "PNSION": 390,
        "PUBAST": 391,
        "RENTAL": 392,
        "2NDJOB": 393,
        "SOCSEC": 394,
        "SPOUSE": 395,
        "TRUST": 396,
        "UEMBEN": 397,
        "UNEMPL": 397,
        "UNKN": 398,
        "VA": 399
    },
    "officer_code_to_email_enum": {
        "6009": "abbey.harrison@merrickbank.com",
        "6019": "alyssa.rapotez@merrickbank.com",
        "6014": "angie.hays@merrickbank.com",
        "6025": "ashley.haase@merrickbank.com",
        "6033": "autumn.turner@merrickbank.com",
        "6011": "briann.siplinger@merrickbank.com",
        "6020": "charissa.green@merrickbank.com",
        "6000": "cindy.beason@merrickbank.com",
        "6027": "diana.johns@merrickbank.com",
        "6032": "emily.crandall@merrickbank.com",
        "6005": "jona.keller@merrickbank.com",
        "6022": "karissa.white@merrickbank.com",
        "6015": "katie.vance@merrickbank.com",
        "6008": "kristy.lotte@merrickbank.com",
        "6017": "maria.campos@merrickbank.com",
        "6029": "margarita.garcia@merrickbank.com",
        "6035": "melina.manalansan@merrickbank.com",
        "6024": "mia.hyde@merrickbank.com",
        "6030": "michelle.preston@merrickbank.com",
        "6026": "pam.mietchen@merrickbank.com",
        "6002": "shauna.carter@merrickbank.com",
        "6006": "sherry.bittle@merrickbank.com",
        "6010": "wendy.dotson@merrickbank.com",
        "6018": "whitney.heywood@merrickbank.com",
        "6016": "allie.gagne@merrickbank.com",
        "6003": "kari.cook@merrickbank.com",
        "6001": "lori.delossantos@merrickbank.com",
        "6021": "marsha.baxter@merrickbank.com",
        "6004": "tami.kearl@merrickbank.com"
    },
    "priority_enum": {},
}

# Enum columns that share a named enum set (not their own column name)
# Maps target_column -> enum_name for the enum_name field in the contract
SHARED_ENUM_NAMES = {}

# All app_funding_checklist_rl enum columns use funding_validation_indicator_enum
_FUNDING_CHECKLIST_ENUM_COLUMNS = [
    "credit_app_signed_pr_enum",
    "credit_app_signed_sec_enum",
    "collateral_percent_used_confirmed_enum",
    "collateral_worksheet_unit_confirmed_enum",
    "addendum_signed_pr_enum",
    "addendum_signed_sec_enum",
    "guarantee_of_lien_enum",
    "insurance_deductible_within_policy_enum",
    "insurance_mb_lienholder_enum",
    "insurance_motor_vin_confirm_enum",
    "insurance_rv_boat_vin_confirm_enum",
    "insurance_trailer_vin_confirm_enum",
    "motor_title_mb_lienholder_enum",
    "motor_title_vin_confirmed_enum",
    "motor_ucc_mb_lienholder_enum",
    "motor_ucc_vin_confirmed_enum",
    "new_motor_1_invoice_confirmed_enum",
    "new_motor_2_invoice_confirmed_enum",
    "new_rv_boat_invoice_confirmed_enum",
    "new_trailer_invoice_confirmed_enum",
    "payoff_mb_loan_verified_enum",
    "rv_boat_title_mb_lienholder_enum",
    "rv_boat_title_vin_confirmed_enum",
    "rv_boat_ucc_mb_lienholder_enum",
    "rv_boat_ucc_vin_confirmed_enum",
    "trailer_title_mb_lienholder_enum",
    "trailer_title_vin_confirmed_enum",
    "trailer_ucc_mb_lienholder_enum",
    "trailer_ucc_vin_confirmed_enum",
    "ucc_filed_by_mb_enum",
    "drivers_license_confirmed_pr_enum",
    "drivers_license_dob_confirmed_pr_enum",
    "drivers_license_confirmed_sec_enum",
    "drivers_license_dob_confirmed_sec_enum",
]
for _col in _FUNDING_CHECKLIST_ENUM_COLUMNS:
    SHARED_ENUM_NAMES[_col] = "y_n_d_enum"

# assigned_funding_analyst uses officer_code_to_email_enum
SHARED_ENUM_NAMES["assigned_funding_analyst"] = "officer_code_to_email_enum"

# Bit conversions (same as CC)
BIT_CONVERSIONS = {
    "char_to_bit": {
        "Y": 1,
        "N": 0,
        "R": 1,
        "P": 0,
        "C": 1,
        "": 0,
        "null": 0,
        " ": 0
    },
    "boolean_to_bit": {
        "true": 1,
        "false": 0,
        "1": 1,
        "0": 0,
        "yes": 1,
        "no": 0,
        "y": 1,
        "n": 0,
        "": 0,
        "null": 0
    }
}

# Table name normalization: CSV shorthand -> contract table name
TABLE_NAME_MAP = {
    "contact_base": "app_contact_base",
    "contact_address": "app_contact_address",
    "contact_employment": "app_contact_employment",
}

# RL table insertion order (logical dependency order)
RL_TABLE_INSERTION_ORDER = [
    "app_base",
    "app_contact_base",
    "app_operational_rl",
    "app_pricing_rl",
    "app_transactional_rl",
    "app_dealer_rl",
    "app_contact_address",
    "app_contact_employment",
    "app_collateral_rl",
    "app_warranties_rl",
    "app_policy_exceptions_rl",
    "app_funding_rl",
    "app_funding_contract_rl",
    "app_funding_checklist_rl",
    "app_historical_lookup",
    "scores",
    "processing_log",
]

# RL element filtering rules
RL_ELEMENT_FILTERING = {
    "filter_rules": [
        {
            "element_type": "contact",
            "description": "Filter contacts by con_id and valid contact type. Array order determines priority (first = highest).",
            "xml_parent_path": "/Provenir/Request/CustData/IL_application",
            "xml_child_path": "/Provenir/Request/CustData/IL_application/IL_contact",
            "required_attributes": {
                "con_id": True,
                "ac_role_tp_c": ["PR", "SEC"]
            }
        },
        {
            "element_type": "address",
            "description": "Filter address elements by valid address type",
            "xml_parent_path": "/Provenir/Request/CustData/IL_application/IL_contact",
            "xml_child_path": "/Provenir/Request/CustData/IL_application/IL_contact/IL_contact_address",
            "required_attributes": {
                "address_type_code": ["CURR", "PREV"]
            }
        },
        {
            "element_type": "employment",
            "description": "Filter employment elements by valid employment_type",
            "xml_parent_path": "/Provenir/Request/CustData/IL_application/IL_contact",
            "xml_child_path": "/Provenir/Request/CustData/IL_application/IL_contact/IL_contact_employment",
            "required_attributes": {
                "employment_type_code": ["CURR", "PREV"]
            }
        }
    ]
}


def clean_expression(expr):
    """Convert multi-line CSV expression to single-line JSON string.
    
    Removes literal newlines, collapses whitespace, preserves CASE structure.
    """
    if not expr:
        return ""
    # Replace newlines with spaces
    cleaned = expr.replace("\n", " ").replace("\r", " ")
    # Collapse multiple spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def normalize_table_name(raw):
    """Normalize CSV table names to contract table names."""
    raw = raw.strip().split("[")[0].strip()
    return TABLE_NAME_MAP.get(raw, raw)


def determine_data_type(target_column, mapping_types):
    """Determine data_type and data_length from column name and mapping type.
    
    Returns (data_type, data_length) where data_length may be None.
    Schema corrections will override these later.
    """
    col = target_column.lower()

    # mapping_type overrides
    if "identity_insert" in mapping_types:
        return "int", None
    if "enum" in mapping_types:
        return "smallint", None
    if "char_to_bit" in mapping_types:
        return "bit", None

    # For row-creating prefixes, check combined types
    for mt in mapping_types:
        if mt.startswith(("add_collateral(", "warranty_field(", "policy_exceptions(")):
            if col.endswith("_enum"):
                return "smallint", None
            if col.endswith("_flag"):
                return "bit", None

    # calculated_field with enum result
    if "calculated_field" in mapping_types and col.endswith("_enum"):
        return "smallint", None
    if "calculated_field" in mapping_types and (col.endswith("_date") or col.endswith("_time")):
        return "datetime", None

    # Enum columns by name
    if col.endswith("_enum"):
        return "smallint", None
    # Flag columns
    if col.endswith("_flag"):
        return "bit", None
    # Date/time columns
    if col.endswith("_date") or col == "birth_date" or col == "boarding_date":
        return "datetime", None
    # Numeric columns
    if any(p in col for p in ["_amount", "_price", "_rate", "_ratio", "salary", "income",
                               "monthly_payment", "_payment", "_value", "_proceeds",
                               "_percentage", "_fee", "subtotal", "finance_charge",
                               "payoff_", "total_of_", "_charge", "_allowance",
                               "cash_down", "selling_price", "invoice_amount",
                               "loan_amount", "apr", "taxes"]):
        return "decimal", 2
    if col in ("app_id", "con_id"):
        return "int", None
    if col in ("year", "term_months", "sort_order", "months_at_address", "months_at_job"):
        return "smallint", None

    # Default to string
    return "string", None


def parse_mapping_types(raw_mt):
    """Parse mapping_type column from CSV.
    
    Handles complex cases like:
      - "enum"
      - "add_collateral(1), calculated_field"
      - "char_to_bit, warranty_field(623)"
      - "contact-by-type-to-fixed-field"
      - "check_requested_by_user"
      - "officer_code_to_email_enum"
      - "supervisor_review_indicator_enum"
      - "bank_account_type_enum"
    """
    if not raw_mt:
        return []
    parts = []
    for part in raw_mt.split(","):
        part = part.strip()
        if part:
            parts.append(part)
    return parts


def convert_contact_split(mapping_types, target_column, expression):
    """Convert contact-by-type-to-fixed-field to appropriate mapping types.
    
    CSV uses:
      mapping_type=contact-by-type-to-fixed-field
      expression="filtered by ac_role_tp_c=PR" or "filtered by ac_role_tp_c=SEC"
    
    Contract should use:
      mapping_type=["last_valid_pr_contact"] or ["last_valid_sec_contact"]
    """
    if "contact-by-type-to-fixed-field" not in mapping_types:
        return mapping_types

    new_types = [t for t in mapping_types if t != "contact-by-type-to-fixed-field"]

    if "PR" in expression.upper():
        new_types.insert(0, "last_valid_pr_contact")
    elif "SEC" in expression.upper():
        new_types.insert(0, "last_valid_sec_contact")

    return new_types


def convert_special_enum_types(mapping_types, target_column):
    """Convert special enum mapping types to standard format.
    
    CSV uses column-specific enum type names as mapping_type.
    Contract needs ["enum"] with the lookup handled by enum_mappings.
    
    Special cases:
      - supervisor_review_indicator_enum -> enum
      - bank_account_type_enum -> enum
      - officer_code_to_email_enum -> enum
      - check_requested_by_user -> calculated_field (CASE expression with officer fallback)
      - mrv_lead_indicator_*_enum with calculated_field -> drop enum
        (CASE expression already returns enum IDs directly)
    """
    # mrv_lead_indicator columns: CASE returns enum IDs (640/641) directly,
    # so "enum" lookup would fail. Drop "enum", keep only "calculated_field".
    if target_column.startswith("mrv_lead_indicator") and "calculated_field" in mapping_types:
        return [mt for mt in mapping_types if mt != "enum"]

    new_types = []
    for mt in mapping_types:
        if mt == "supervisor_review_indicator_enum":
            new_types.append("enum")
        elif mt == "bank_account_type_enum":
            new_types.append("enum")
        elif mt == "officer_code_to_email_enum":
            new_types.append("enum")
        elif mt == "check_requested_by_user":
            new_types.append("calculated_field")
        else:
            new_types.append(mt)
    return new_types


def build_mapping(xml_path, xml_attribute, target_table, target_column,
                  mapping_types, expression):
    """Build a single mapping dict from parsed CSV row."""
    if not target_table:
        return None

    target_table = normalize_table_name(target_table)

    # Handle contact-by-type-to-fixed-field conversion
    if "contact-by-type-to-fixed-field" in mapping_types:
        mapping_types = convert_contact_split(mapping_types, target_column, expression)
        expression = ""  # The expression was just a filter description

    # Handle special enum type names used as mapping_types
    mapping_types = convert_special_enum_types(mapping_types, target_column)

    # Determine data type
    data_type, data_length = determine_data_type(target_column, mapping_types)

    mapping = {
        "xml_path": xml_path,
        "xml_attribute": xml_attribute,
        "target_table": target_table,
        "target_column": target_column,
        "data_type": data_type,
    }

    if data_length is not None:
        mapping["data_length"] = data_length

    if mapping_types:
        mapping["mapping_type"] = mapping_types

    if expression:
        mapping["expression"] = clean_expression(expression)

    mapping["nullable"] = True
    mapping["required"] = False

    # Add enum_name for columns that share a named enum set
    if target_column in SHARED_ENUM_NAMES:
        mapping["enum_name"] = SHARED_ENUM_NAMES[target_column]

    # Special cases for required fields
    if target_column == "app_id":
        mapping["nullable"] = False
        mapping["required"] = True
    elif target_column == "con_id":
        mapping["nullable"] = False
        mapping["required"] = True
    elif target_column == "receive_date":
        mapping["nullable"] = False
        mapping["required"] = True
        mapping["data_type"] = "datetime"
        mapping["default_value"] = "1900-01-01"
        mapping["exclude_default_when_record_empty"] = True

    # Add defaults for bit columns
    if data_type == "bit" and "char_to_bit" in mapping_types:
        mapping["default_value"] = "0"

    return mapping


def parse_csv():
    """Parse the RL CSV file into a list of mapping dicts."""
    mappings = []
    seen = set()  # For deduplication

    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            xml_path = (row.get("xml_path") or "").strip()
            xml_attr = (row.get("xml_attribute") or "").strip()
            target_table = (row.get("target_table") or "").strip()
            target_column = (row.get("target_column") or "").strip()
            mt_raw = (row.get("mapping_type") or "").strip()
            expression = (row.get("expression") or "").strip()

            # Skip rows without xml_attribute
            if not xml_attr:
                continue

            # For calculated fields with empty xml_path, infer from target_table context
            if not xml_path and (expression or "calculated_field" in mt_raw):
                # Collateral fields use IL_collateral parent
                if target_table and "collateral" in target_table:
                    xml_path = "/Provenir/Request/CustData/IL_application/IL_collateral"
                else:
                    xml_path = "/Provenir/Request/CustData/IL_application"

            # Skip rows with no target table unless they are add_history/add_score
            if not target_table:
                if any(p in mt_raw for p in ["add_history", "add_score"]):
                    # add_history and add_score rows may have target_table
                    # in the CSV, but scores rows may have empty target_table
                    # with just a target_column - handle below
                    pass
                elif not target_column:
                    continue
                else:
                    # Has target_column but no target_table - skip unless it's
                    # a known pattern like scores or Vantage cb_score_factor fields
                    # These fields have empty target_table in CSV - check if
                    # target_column suggests it belongs to app_operational_rl
                    if target_column.startswith("cb_score_factor"):
                        target_table = "app_operational_rl"
                    else:
                        continue

            # Handle scores target_table - the CSV uses "scores" 
            if target_table == "scores":
                pass  # Keep as-is

            # Parse mapping types
            mapping_types = parse_mapping_types(mt_raw)

            # Build the mapping
            mapping = build_mapping(
                xml_path, xml_attr, target_table, target_column,
                mapping_types, expression,
            )

            if mapping is None:
                continue

            # Deduplication key
            dedup_key = (
                mapping["target_table"],
                mapping["target_column"],
                mapping["xml_path"],
                mapping["xml_attribute"],
                mapping.get("expression", ""),
            )
            if dedup_key in seen:
                print(f"  SKIPPING duplicate: {dedup_key[0]}.{dedup_key[1]} from {dedup_key[3]}")
                continue
            seen.add(dedup_key)

            mappings.append(mapping)

    # Second pass: remove non-row-creating duplicates (same table + same column)
    # For these, last-write-wins (later CSV row takes precedence).
    row_creating_prefixes = (
        'add_score', 'add_indicator', 'add_history', 'add_report_lookup',
        'policy_exceptions', 'warranty_field', 'add_collateral',
    )
    contact_split_types = ('last_valid_pr_contact', 'last_valid_sec_contact')

    final_mappings = []
    table_col_index = {}  # (table, col) -> index in final_mappings

    for mapping in mappings:
        tbl = mapping["target_table"]
        col = mapping.get("target_column", "")
        mt_list = mapping.get("mapping_type", [])

        # Row-creating and contact-split mappings are always kept
        is_row_creating = any(
            str(mt).strip().startswith(row_creating_prefixes) for mt in mt_list
        )
        is_contact_split = any(
            str(mt).strip() in contact_split_types for mt in mt_list
        )

        if not col or is_row_creating or is_contact_split:
            final_mappings.append(mapping)
            continue

        key = (tbl, col)
        if key in table_col_index:
            old_idx = table_col_index[key]
            old_m = final_mappings[old_idx]
            print(f"  REPLACING: {tbl}.{col} from {old_m['xml_attribute']} with {mapping['xml_attribute']}")
            final_mappings[old_idx] = mapping  # Replace in-place
        else:
            table_col_index[key] = len(final_mappings)
            final_mappings.append(mapping)

    if len(final_mappings) < len(mappings):
        print(f"  Removed {len(mappings) - len(final_mappings)} non-row-creating duplicates")

    return final_mappings


def build_relationships(mappings):
    """Generate relationship definitions for the RL contract."""
    relationships = []

    # Contact hierarchy
    relationships.append({
        "parent_table": "app_base",
        "child_table": "app_contact_base",
        "foreign_key_column": "app_id",
        "xml_parent_path": "/Provenir/Request",
        "xml_child_path": "/Provenir/Request/CustData/IL_application/IL_contact",
    })
    relationships.append({
        "parent_table": "app_contact_base",
        "child_table": "app_contact_address",
        "foreign_key_column": "con_id",
        "xml_parent_path": "/Provenir/Request/CustData/IL_application/IL_contact",
        "xml_child_path": "/Provenir/Request/CustData/IL_application/IL_contact/IL_contact_address",
    })
    relationships.append({
        "parent_table": "app_contact_base",
        "child_table": "app_contact_employment",
        "foreign_key_column": "con_id",
        "xml_parent_path": "/Provenir/Request/CustData/IL_application/IL_contact",
        "xml_child_path": "/Provenir/Request/CustData/IL_application/IL_contact/IL_contact_employment",
    })

    # Direct child tables of app_base
    direct_children = [
        ("app_operational_rl", "/Provenir/Request/CustData/IL_application"),
        ("app_pricing_rl", "/Provenir/Request/CustData/IL_application"),
        ("app_transactional_rl", "/Provenir/Request/CustData/IL_application"),
        ("app_dealer_rl", "/Provenir/Request/CustData/IL_application"),
        ("app_collateral_rl", "/Provenir/Request/CustData/IL_application/IL_collateral"),
        ("app_warranties_rl", "/Provenir/Request/CustData/IL_application/IL_backend_policies"),
        ("app_policy_exceptions_rl", "/Provenir/Request/CustData/IL_application/IL_app_decision_info"),
        ("app_funding_rl", "/Provenir/Request/CustData/IL_application/IL_fund_checklist"),
        ("app_funding_contract_rl", "/Provenir/Request/CustData/IL_application/IL_fund_checklist"),
        ("app_funding_checklist_rl", "/Provenir/Request/CustData/IL_application/IL_fund_checklist"),
    ]

    for child_table, child_path in direct_children:
        relationships.append({
            "parent_table": "app_base",
            "child_table": child_table,
            "foreign_key_column": "app_id",
            "xml_parent_path": "/Provenir/Request",
            "xml_child_path": child_path,
        })

    return relationships


def generate_rl_contract():
    """Main entry point: generate the RL mapping contract."""
    print(f"Reading CSV from {CSV_PATH}...")
    mappings = parse_csv()
    print(f"  Parsed {len(mappings)} mappings (after dedup)")

    # Count tables
    tables = sorted(set(m["target_table"] for m in mappings if m["target_table"]))
    print(f"  Target tables: {tables}")

    # Ensure all tables from mappings are in insertion order
    for tbl in tables:
        if tbl not in RL_TABLE_INSERTION_ORDER:
            print(f"  WARNING: Table '{tbl}' found in mappings but not in insertion order!")

    # Build relationships
    relationships = build_relationships(mappings)

    # Build the contract
    contract = {
        "xml_root_element": "Provenir",
        "xml_application_path": "/Provenir/Request/CustData/IL_application",
        "source_table": "app_xml_staging_rl",
        "source_column": "app_XML",
        "source_application_table": "IL_application",
        "target_schema": "migration",
        "table_insertion_order": RL_TABLE_INSERTION_ORDER,
        "element_filtering": RL_ELEMENT_FILTERING,
        "relationships": relationships,
        "mappings": mappings,
        "enum_mappings": RL_ENUM_MAPPINGS,
        "bit_conversions": BIT_CONVERSIONS,
    }

    # Write output
    print(f"Writing contract to {OUTPUT_CONTRACT_PATH}...")
    with open(OUTPUT_CONTRACT_PATH, "w", encoding="utf-8") as f:
        json.dump(contract, f, indent=2)

    # Summary
    print(f"\nContract generated successfully:")
    print(f"  Mappings: {len(mappings)}")
    print(f"  Tables: {len(tables)}")
    print(f"  Enum sets: {len(RL_ENUM_MAPPINGS)}")
    print(f"  Relationships: {len(relationships)}")

    # Print mapping type breakdown
    mt_counts = {}
    for m in mappings:
        for mt in m.get("mapping_type", []):
            key = re.sub(r"\(.*?\)", "(*)", mt)
            mt_counts[key] = mt_counts.get(key, 0) + 1
    print(f"\n  Mapping type breakdown:")
    for mt, count in sorted(mt_counts.items()):
        print(f"    {mt}: {count}")


if __name__ == "__main__":
    generate_rl_contract()
