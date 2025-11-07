# Architectural Decision: Element Filtering Configuration Options

## Executive Summary

**Key Finding**: `key_identifiers` is currently **defined but NOT implemented** in any production code. This gives us **full flexibility** to design a clean contract-driven element filtering system without disrupting existing functionality.

**Current State Investigation Results**:
- ✅ `key_identifiers` defined in `mapping_contract.json` (lines 17-20) and `models.py` (line 113)
- ❌ NO active code implements or uses `key_identifiers` anywhere
- ✅ `relationships` section exists and maps XML structure to database schema (7 relationship definitions)
- ✅ `enum_mappings` section has 100+ enum definitions for attribute value transformations

---

## Problem Statement

`element_filter.py` (190 lines) currently uses hard-coded constants and attribute names, preventing multi-product schema support:

**Hard-Coded Dependencies**:
- Lines 63-66: Enum value sets (`VALID_AC_ROLE_TP_C`, `VALID_ADDRESS_TP_C`, `VALID_EMPLOYMENT_TP_C`)
- Lines 92-93: App ID XPath (`.//Request/@ID`)
- Lines 110, 130, 138: Attribute names (`ac_role_tp_c`, `address_tp_c`, `employment_tp_c`)

**Business Reality**: Different products have different XML schemas
- Standard: `/Provenir/Request/CustData/application/contact[@ac_role_tp_c='PR']`
- Illinois Lending: `/Provenir/Request/CustData/IL_application/IL_contact[@ac_role_tp_c='PR']`
- Need contract-driven configuration to support product variations without code changes

---

## Current Contract Structure Analysis

### `key_identifiers` (Currently Unused)
```json
"key_identifiers": {
  "app_id": ".//Request/@ID",
  "con_id_primary": ".//Request/CustData/application/contact/@con_id",
  "con_id_auth": ".//Request/CustData/application/contact[@ac_role_tp_c='AUTHU']/@con_id"
}
```
**Status**: Defined but not referenced in any code  
**Purpose**: Extract primary identifiers from XML (app_id, primary contact, auth contact)  
**Scope**: Application-level entity identification

### `relationships` Section (Already in Use)
```json
"relationships": [
  {
    "parent_table": "app_base",
    "child_table": "contact_base",
    "foreign_key_column": "app_id",
    "xml_parent_path": "/Provenir/Request",
    "xml_child_path": "/Provenir/Request/CustData/application/contact"
  },
  // 6 more relationships...
]
```
**Status**: Currently used for schema mapping  
**Purpose**: Define parent-child relationships between database tables  
**Scope**: Database schema structure (not element filtering)

### `enum_mappings` Section (Already in Use)
```json
"enum_mappings": {
  "contact_type_enum": {
    "PR": 1,           // Primary
    "AUTHU": 2,        // Authorized User
    "CO": 3             // Co-applicant
  },
  "address_type_enum": {
    "CURR": 1,         // Current
    "PREV": 2,         // Previous
    "PATR": 3          // Patrimonial
  },
  "employment_type_enum": {
    "CURR": 1,         // Current
    "PREV": 2          // Previous
  }
  // ~100+ more enums...
}
```
**Status**: Currently used for enum value transformation  
**Purpose**: Map XML attribute values to database enum IDs  
**Scope**: Data transformation/translation (not element filtering)

---

## Architectural Options

### Option A: Extend `key_identifiers` (Quick Win - 30 mins)

**Approach**: Expand `key_identifiers` to include element filtering rules alongside identity extraction.

**Contract Structure**:
```json
"key_identifiers": {
  "app_id": ".//Request/@ID",
  "con_id_primary": ".//Request/CustData/application/contact[@ac_role_tp_c='PR']/@con_id",
  "con_id_auth": ".//Request/CustData/application/contact[@ac_role_tp_c='AUTHU']/@con_id",
  "element_filtering": {
    "contact_elements": {
      "attribute": "ac_role_tp_c",
      "valid_values": ["PR", "AUTHU", "CO"]
    },
    "address_elements": {
      "attribute": "address_tp_c",
      "valid_values": ["CURR", "PREV", "PATR"]
    },
    "employment_elements": {
      "attribute": "employment_tp_c",
      "valid_values": ["CURR", "PREV"]
    }
  }
}
```

**Pros**:
- ✅ Minimal contract changes
- ✅ Fast implementation (30 min)
- ✅ Reuses existing `key_identifiers` pattern
- ✅ Works for standard schema

**Cons**:
- ❌ Semantic confusion (mixing identity extraction + filtering)
- ❌ `element_filtering` doesn't match `key_identifiers` purpose
- ❌ Unclear at contract level what fields do
- ❌ Doesn't handle product-specific XPath variations
- ❌ Not extensible for future filtering rules

**Recommendation**: ❌ **Not Recommended** - Violates single responsibility principle

---

### Option B: Create Separate `element_filtering` Section (Clean - 1-2 hours)

**Approach**: Create a new dedicated section in contract for element filtering configuration, separate from identifiers and enums.

**Contract Structure**:
```json
"key_identifiers": {
  "app_id": ".//Request/@ID",
  "con_id_primary": ".//Request/CustData/application/contact/@con_id",
  "con_id_auth": ".//Request/CustData/application/contact[@ac_role_tp_c='AUTHU']/@con_id"
},
"element_filtering": {
  "filter_rules": [
    {
      "element_type": "contact",
      "xml_path": "/Provenir/Request/CustData/application/contact",
      "attribute": "ac_role_tp_c",
      "valid_values": ["PR", "AUTHU", "CO"],
      "required": true,
      "description": "Only process contacts with valid role types"
    },
    {
      "element_type": "address",
      "xml_path": "/Provenir/Request/CustData/application/contact/contact_address",
      "attribute": "address_tp_c",
      "valid_values": ["CURR", "PREV", "PATR"],
      "required": true,
      "description": "Only process addresses with valid types"
    },
    {
      "element_type": "employment",
      "xml_path": "/Provenir/Request/CustData/application/contact/contact_employment",
      "attribute": "employment_tp_c",
      "valid_values": ["CURR", "PREV"],
      "required": false,
      "description": "Optional employment elements must have valid type if present"
    }
  ],
  "extraction_rules": [
    {
      "name": "app_id_extraction",
      "xml_path": ".//Request",
      "attribute": "@ID",
      "target_identifier": "app_id"
    }
  ]
}
```

**Pros**:
- ✅ Clear semantic separation
- ✅ Dedicated section signals element filtering intent
- ✅ Reusable across multiple products
- ✅ Extensible (easy to add new filter types)
- ✅ Self-documenting with descriptions
- ✅ Backward compatible (doesn't touch other sections)

**Cons**:
- ⚠️ Adds new contract section to maintain
- ⚠️ Doesn't solve multi-product XPath variations (yet)
- ⚠️ Medium implementation effort (1-2 hours)

**Recommendation**: ✅ **Recommended as baseline** - Clean, extensible, semantic clarity

---

### Option C: Hybrid - Product-Specific Contract Files (Enterprise - 2-3 hours)

**Approach**: Create base contract template + product-specific overrides in separate files.

**Contract Structure**:
```
config/
  mapping_contract.json                 # Base contract (shared enums, relationships)
  mapping_contract_standard.json        # Standard product overrides
  mapping_contract_il_lending.json      # IL Lending product overrides
  mapping_contract_secure_cc.json       # Secure CC product overrides
```

**Base Contract** (`mapping_contract.json`):
```json
{
  "contract_version": "2.0",
  "target_schema": "sandbox",
  "product_variant": "base",
  "key_identifiers": { ... },
  "element_filtering": {
    "contact_attribute": "ac_role_tp_c",
    "address_attribute": "address_tp_c",
    "employment_attribute": "employment_tp_c"
  },
  "enum_mappings": { ... },
  "relationships": [ ... ]
}
```

**Product Override** (`mapping_contract_il_lending.json`):
```json
{
  "contract_version": "2.0",
  "target_schema": "sandbox",
  "product_variant": "il_lending",
  "base_contract": "mapping_contract.json",
  "element_filtering": {
    "contact_xpath": "/Provenir/Request/CustData/IL_application/IL_contact",
    "contact_attribute": "ac_role_tp_c",
    "address_xpath": "/Provenir/Request/CustData/IL_application/IL_contact/IL_address",
    "address_attribute": "address_tp_c"
  },
  "mappings": [
    // IL-specific field mappings override base
  ]
}
```

**Pros**:
- ✅ Handles product-specific XPath variations
- ✅ Base contract shared across products (DRY principle)
- ✅ Can override sections per product
- ✅ Scales to N products
- ✅ Each product has single source of truth

**Cons**:
- ❌ More complex configuration management
- ❌ Higher implementation effort (2-3 hours)
- ❌ Requires contract inheritance/merge logic
- ❌ Harder to understand contract at a glance
- ❌ Risk of override conflicts

**Recommendation**: ⚠️ **Consider for Phase 2** - Good long-term, but adds complexity now

---

### Option D: Comprehensive Schema-Driven (Ambitious - 4+ hours)

**Approach**: Auto-generate element filtering from mappings + schema introspection + product manifest.

**Contract Structure**:
```json
{
  "contract_version": "2.0",
  "target_schema": "sandbox",
  "product_manifest": {
    "product_id": "contact_secure_cc",
    "product_name": "Contact Secure Credit Card",
    "xml_root": "Provenir",
    "schema_profile": "standard_app_contact_v2",
    "element_strategies": {
      "contact": {
        "discovery": "auto",         // Auto-discover from mappings
        "xpath_template": "/Provenir/Request/CustData/{application_type}/{contact_element}",
        "role_attribute": "ac_role_tp_c",
        "role_enum_map": "contact_type_enum",
        "required_roles": ["PR", "AUTHU"]
      }
    }
  },
  "mappings": [ ... ]  // Same as before
}
```

**Pros**:
- ✅ Single source of truth (contract + schema)
- ✅ Minimal explicit configuration
- ✅ Auto-generates filtering from mappings
- ✅ Highly scalable

**Cons**:
- ❌ Complex to implement correctly (4+ hours)
- ❌ Hard to debug when auto-generation doesn't match expectations
- ❌ Requires significant refactoring of parsing/mapping code
- ❌ High risk of over-engineering
- ❌ Steep learning curve for maintenance

**Recommendation**: ❌ **Not Recommended for MVP** - Over-engineered for current needs

---

## Recommendation & Next Steps

### Immediate Action: **Option B (Separate `element_filtering` Section)**

**Why**:
1. **Semantic clarity** - Filters ≠ Identifiers ≠ Enums (three distinct concerns)
2. **Low risk** - Doesn't break existing code (`key_identifiers` unused)
3. **Reasonable scope** - 1-2 hours, solid ROI
4. **Extensible** - Foundation for Options C/D later
5. **Contract-driven** - Removes hard-coded constants from `element_filter.py`
6. **Data-driven** - Configuration lives in contract, not code

### Phase 2 (Future): **Option C (Product-Specific Overrides)**
- After Option B proven in production
- When second product variant needed
- Can extend existing contract structure incrementally

---

## Implementation Roadmap (Option B)

### 1. Update `mapping_contract.json`
- Add `element_filtering` section with filter rules
- Extract hard-coded values from `element_filter.py` into contract
- Include XML paths for each element type

### 2. Refactor `element_filter.py`
- Replace hard-coded constants with contract lookups
- Load filter rules from config during initialization
- Support per-element-type filtering from contract rules

### 3. Update `DataMapper` & Validation Integration
- Ensure filtering config respected during mapping
- Update validation/pre-processing validators if needed
- No changes to existing mapping logic

### 4. Update `models.py`
- Extend `MappingContract` dataclass with `ElementFiltering` nested class
- Maintain backward compatibility

### 5. Test & Verify
- Existing tests should pass (contract-driven behavior)
- Add tests for contract-driven filtering
- Verify no regressions in multi-product scenarios

---

## Questions for Confirmation Before Implementation

1. **Single Contract or Per-Product?**
   - Use base `mapping_contract.json` for all products initially?
   - Or separate files from day one?
   → **Recommendation**: Single contract for now, refactor to per-product when needed

2. **Filter Persistence in Contract?**
   - Should filtered elements be marked in contract or only validated?
   - Should `element_filtering` rules be reusable across similar elements?
   → **Recommendation**: Reusable rules keyed by element type

3. **Dataclass Updates?**
   - Should `MappingContract` model have nested `ElementFiltering` class?
   - Or keep contract as flexible dict?
   → **Recommendation**: Type-safe dataclass with nested class for clarity

4. **Backward Compatibility?**
   - Should `element_filter.py` work with/without contract filtering?
   - Or require new contract format?
   → **Recommendation**: Graceful fallback (use hard-coded if contract missing)

