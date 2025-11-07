# Contract-Driven Refactoring Plan for data_mapper.py

## Executive Summary

This document identifies all hard-coded product-specific references in `data_mapper.py` (excluding `Provenir/Request/CustData/` scaffolding which is already contract-driven via `xml_application_path`) and proposes incremental, testable refactoring tasks to make the system fully multi-product capable.

**Goal**: Enable IL Lending (or any new product) with **contract changes only, zero code changes**.

---

## Hard-Coded References Identified

### 1. **Contact Type Values: 'PR' and 'AUTHU'**
**Locations**:
- Line 508: `if ac_role_tp_c not in ('PR', 'AUTHU'):`
- Line 521: `if ac_role_tp_c == 'PR':`
- Line 524: `elif con_id_map[con_id].get('ac_role_tp_c', '').strip() != 'PR':`
- Line 649: `if ac_role_tp_c == 'AUTHU' and con_id and con_id not in seen_con_ids_authu:`
- Line 1878: `pr_contacts = self._current_xml_root.xpath('.//contact[@ac_role_tp_c="PR"]')`
- Line 2009: `pr_contacts = [c for c in valid_contacts if c.get('ac_role_tp_c') == 'PR']`

**Issue**: The concept of "primary contact" exists across all products but may use different codes (e.g., IL Lending might use 'PRIMARY', 'BORROWER', etc.).

**Current Contract Support**: 
- `element_filtering.filter_rules[0].required_attributes.ac_role_tp_c: ["PR", "AUTHU"]` ✅ Already exists!
- `enum_mappings.contact_type_enum: {"PR": 281, "AUTHU": 280}` ✅ Already exists!

**Opportunity**: The contract already defines valid contact types. We can **derive** primary contact logic from this.

---

### 2. **Address Type Values: 'CURR', 'PREV', 'MAIL'**
**Locations**:
- Line 1608: `curr_address_elements = contact_element.xpath("contact_address[@address_tp_c='CURR']")`
- Line 1898: `curr_address_elements = [addr for addr in address_elements if addr.get('address_tp_c') == 'CURR']`

**Issue**: Hard-coded assumption that "current address" = 'CURR'. Other products might use 'PRIMARY', 'HOME', etc.

**Current Contract Support**:
- `element_filtering.filter_rules[1].required_attributes.address_tp_c: ["CURR", "PREV", "PATR"]` ✅ Already exists!
- `enum_mappings.address_type_enum: {"CURR": 320, "PREV": 321}` ✅ Already exists!

**Opportunity**: Use contract to define address type priority/filtering.

---

### 3. **Table Names: 'contact_base', 'contact_address', 'contact_employment'**
**Locations**:
- Line 666: `if (mapping.target_table == 'contact_base' and ...`
- Line 1221: `if table_name == 'contact_base':`
- Line 1232: `elif table_name == 'contact_address':`
- Line 1236: `elif table_name == 'contact_employment':`
- Lines 682-683: Pattern matching on `'contact_address' in mapping.xml_path` and `'contact_employment' in mapping.xml_path`

**Issue**: Hard-coded table names won't work if IL Lending uses different naming (e.g., `borrower_base`, `borrower_address`).

**Current Contract Support**:
- `table_insertion_order` ✅ Already lists all tables!
- Each `mapping` has `target_table` field ✅

**Opportunity**: Derive table categories from contract metadata rather than hard-coding names.

---

### 4. **XPath Pattern Strings in Logic**
**Locations**:
- Line 546: `# Find contact elements (not child elements like contact_address)`
- Line 582: `employment_elems = contact_elem.xpath('./contact_employment')`
- Line 586: `address_elems = contact_elem.xpath('./contact_address')`

**Issue**: Hard-coded XPath element names ('contact', 'contact_address', 'contact_employment').

**Current Contract Support**:
- `element_filtering.filter_rules` has `xml_child_path` for each element type ✅
- Can extract element names from these paths!

**Opportunity**: Derive XPath patterns from `xml_child_path` in filter rules.

---

### 5. **Business Logic: "PR takes precedence over AUTHU"**
**Locations**:
- Lines 513-527: Contact deduplication logic with hardcoded precedence

**Issue**: Priority rules between contact types are product-specific business logic.

**Current Contract Support**:
- `element_filtering.filter_rules[0].required_attributes.ac_role_tp_c: ["PR", "AUTHU"]` - array order could imply priority?

**Opportunity**: Define explicit priority/ranking in contract.

---

### 6. **Attribute Names: 'con_id', 'ac_role_tp_c', 'address_tp_c', 'employment_tp_c'**
**Locations**:
- Throughout the file for ID extraction and type checking

**Issue**: While these are used in validation, they might have different names in other products.

**Current Contract Support**:
- `element_filtering.filter_rules[*].required_attributes` ✅ Defines these per element type!

**Opportunity**: Extract attribute names dynamically from filter rules.

---

## Refactoring Tasks (Prioritized)

Each task includes:
- **Complexity**: Low/Medium/High
- **Risk**: Low/Medium/High
- **Configurability Gain**: +/++/+++
- **Code Sprawl Risk**: Low/Medium/High
- **Dependencies**: What must be done first
- **Test Coverage**: Required test scenarios

---

### **TASK 1: Make Contact Type Filtering Contract-Driven** ⭐ START HERE
**Priority**: HIGHEST (Foundation for all contact logic)

**Current Hard-Coding**:
```python
# Line 508
if ac_role_tp_c not in ('PR', 'AUTHU'):
    continue
```

**Proposed Solution**:
```python
# Extract valid contact types from contract filter rules
valid_contact_types = self._get_valid_contact_types_from_contract()
if ac_role_tp_c not in valid_contact_types:
    continue
```

**Contract Enhancement** (Option A - Use existing):
```json
"element_filtering": {
  "filter_rules": [
    {
      "element_type": "contact",
      "required_attributes": {
        "con_id": true,
        "ac_role_tp_c": ["PR", "AUTHU"]  // ✅ Already exists! Just read this
      }
    }
  ]
}
```

**Contract Enhancement** (Option B - Add explicit config):
```json
"contact_validation": {
  "valid_contact_types": ["PR", "AUTHU"],
  "primary_contact_type": "PR",
  "contact_type_priority": ["PR", "AUTHU"]
}
```

**Recommendation**: **Option A** - reuse existing `element_filtering.filter_rules[0].required_attributes.ac_role_tp_c`

**Implementation**:
1. Add method `_get_valid_contact_types_from_contract()` that reads from filter rules
2. Replace all hard-coded `('PR', 'AUTHU')` checks with this method
3. Update `_extract_valid_contacts()` to use dynamic list

**Testing**:
- Modify contract to use different contact types (e.g., `["PRIMARY", "SECONDARY"]`)
- Verify extraction logic works with new types
- Verify existing tests still pass with default types

**Metrics**:
- **Complexity**: Low (simple lookup)
- **Risk**: Low (read-only from existing contract field)
- **Configurability Gain**: +++
- **Code Sprawl Risk**: Low (single helper method)
- **Dependencies**: None
- **Lines Changed**: ~8-10 locations

---

### **TASK 2: Make Primary Contact Precedence Contract-Driven**
**Priority**: HIGH (Depends on Task 1)

**Current Hard-Coding**:
```python
# Lines 513-527: PR always beats AUTHU
if ac_role_tp_c == 'PR':
    con_id_map[con_id] = contact
elif con_id_map[con_id].get('ac_role_tp_c', '').strip() != 'PR':
    con_id_map[con_id] = contact
```

**Proposed Solution**:
```python
contact_priority = self._get_contact_type_priority_from_contract()
current_priority = contact_priority.get(ac_role_tp_c, 999)
existing_priority = contact_priority.get(con_id_map[con_id].get('ac_role_tp_c'), 999)
if current_priority < existing_priority:  # Lower number = higher priority
    con_id_map[con_id] = contact
```

**Contract Enhancement** (Recommended):
```json
"element_filtering": {
  "filter_rules": [
    {
      "element_type": "contact",
      "required_attributes": {
        "con_id": true,
        "ac_role_tp_c": ["PR", "AUTHU"]  // Array order = priority order
      },
      "priority_order": ["PR", "AUTHU"]  // Explicit (clearer)
    }
  ]
}
```

**Alternative** (simpler but less clear):
```json
"contact_validation": {
  "primary_contact_type": "PR"  // Just identify which is primary
}
```

**Recommendation**: Add `priority_order` array to contact filter rule for clarity.

**Implementation**:
1. Add `priority_order` field to contact filter rule in contract
2. Add `_get_contact_type_priority_from_contract()` method
3. Refactor deduplication logic to use priority scores
4. Update `_extract_from_last_valid_pr_contact` to use dynamic primary type

**Testing**:
- Modify priority order (e.g., `["AUTHU", "PR"]`) and verify AUTHU wins
- Test with equal priority (first-wins or last-wins behavior)
- Test with unknown types (should use fallback priority)

**Metrics**:
- **Complexity**: Medium (requires priority comparison logic)
- **Risk**: Medium (changes core deduplication behavior)
- **Configurability Gain**: +++
- **Code Sprawl Risk**: Low (contained in deduplication logic)
- **Dependencies**: Task 1
- **Lines Changed**: ~15-20 locations

---

### **TASK 3: Make Address Type Filtering Contract-Driven**
**Priority**: HIGH (Similar to Task 1 but for addresses)

**Current Hard-Coding**:
```python
# Line 1608
curr_address_elements = contact_element.xpath("contact_address[@address_tp_c='CURR']")

# Line 1898
curr_address_elements = [addr for addr in address_elements if addr.get('address_tp_c') == 'CURR']
```

**Proposed Solution**:
```python
preferred_address_type = self._get_preferred_address_type_from_contract()
curr_address_elements = contact_element.xpath(f"contact_address[@address_tp_c='{preferred_address_type}']")
```

**Contract Enhancement** (Option A - Use existing):
```json
"element_filtering": {
  "filter_rules": [
    {
      "element_type": "address",
      "required_attributes": {
        "address_tp_c": ["CURR", "PREV", "PATR"]  // ✅ Already exists
      },
      "preferred_type": "CURR"  // ⭐ Add this
    }
  ]
}
```

**Contract Enhancement** (Option B - Separate config):
```json
"address_validation": {
  "valid_address_types": ["CURR", "PREV", "PATR"],
  "preferred_address_type": "CURR"
}
```

**Recommendation**: **Option A** - extend existing address filter rule with `preferred_type`

**Implementation**:
1. Add `preferred_type` field to address filter rule
2. Add `_get_preferred_address_type_from_contract()` method
3. Replace hard-coded `'CURR'` with dynamic lookup
4. Update `curr_address_only` mapping type handler

**Testing**:
- Change `preferred_type` to `"PREV"` and verify address extraction changes
- Test fallback when preferred type not found
- Verify `curr_address_only` mapping type respects new config

**Metrics**:
- **Complexity**: Low (simple lookup)
- **Risk**: Low (isolated to address extraction)
- **Configurability Gain**: ++
- **Code Sprawl Risk**: Low (single helper method)
- **Dependencies**: None (parallel to Task 1)
- **Lines Changed**: ~5-8 locations

---

### **TASK 4: Make Table Name Detection Contract-Driven**
**Priority**: MEDIUM (Enables different table naming schemes)

**Current Hard-Coding**:
```python
# Line 1221
if table_name == 'contact_base':
    ...
elif table_name == 'contact_address':
    ...
elif table_name == 'contact_employment':
    ...
```

**Proposed Solution**:
```python
# Derive table categories from contract metadata
if self._is_contact_base_table(table_name):
    ...
elif self._is_contact_child_table(table_name):
    ...
elif self._is_app_table(table_name):
    ...
```

**Contract Enhancement** (Option A - Derive from mappings):
```python
# No contract change needed! Derive from existing data:
# - Tables with xml_path containing 'contact' but not 'contact_address/employment' = contact_base
# - Tables with xml_path containing 'contact_address' = contact_address tables
# - Tables with xml_path containing 'contact_employment' = contact_employment tables
```

**Contract Enhancement** (Option B - Explicit metadata):
```json
"table_metadata": {
  "contact_base": {
    "category": "contact_base",
    "requires_contact_context": true
  },
  "contact_address": {
    "category": "contact_child",
    "parent_table": "contact_base"
  },
  "contact_employment": {
    "category": "contact_child",
    "parent_table": "contact_base"
  },
  "app_base": {
    "category": "application"
  }
}
```

**Recommendation**: **Option A initially** (derive from mappings to avoid contract bloat), **Option B if needed** (for complex hierarchies)

**Rationale**:
- Option A: No contract changes, smart inference from existing fields
- Option B: More explicit but adds configuration overhead

**Implementation** (Option A):
1. Add `_get_table_category(table_name)` method that analyzes mappings
2. Build table category cache at contract load time
3. Replace hard-coded table name checks with category checks

**Implementation** (Option B):
1. Add `table_metadata` section to contract JSON
2. Load into MappingContract dataclass
3. Add helper methods to query table categories

**Testing**:
- Rename tables in contract (e.g., `borrower_base` instead of `contact_base`)
- Verify correct categorization
- Test edge cases (app tables with 'contact' in unrelated field names)

**Metrics**:
- **Complexity**: Medium (requires smart inference logic)
- **Risk**: Medium (affects table processing dispatch)
- **Configurability Gain**: +++
- **Code Sprawl Risk**: Medium (Option A) / High (Option B - adds contract section)
- **Dependencies**: None
- **Lines Changed**: ~10-15 locations

---

### **TASK 5: Make XPath Element Names Contract-Driven**
**Priority**: MEDIUM-LOW (Nice to have for complete flexibility)

**Current Hard-Coding**:
```python
# Line 582
employment_elems = contact_elem.xpath('./contact_employment')

# Line 586
address_elems = contact_elem.xpath('./contact_address')
```

**Proposed Solution**:
```python
# Extract element names from filter rules
address_element_name = self._get_child_element_name('address')
employment_element_name = self._get_child_element_name('employment')

employment_elems = contact_elem.xpath(f'./{employment_element_name}')
address_elems = contact_elem.xpath(f'./{address_element_name}')
```

**Contract Support** (Already exists!):
```json
"element_filtering": {
  "filter_rules": [
    {
      "element_type": "address",
      "xml_child_path": "/Provenir/Request/CustData/application/contact/contact_address"
      // ✅ Extract 'contact_address' from this path!
    },
    {
      "element_type": "employment",
      "xml_child_path": "/Provenir/Request/CustData/application/contact/contact_employment"
      // ✅ Extract 'contact_employment' from this path!
    }
  ]
}
```

**Implementation**:
1. Add `_get_child_element_name(element_type)` that extracts from `xml_child_path`
2. Build element name cache at initialization
3. Replace hard-coded element names with dynamic lookups

**Testing**:
- Change `xml_child_path` to use different element names
- Verify XPath queries still work
- Test with nested/complex paths

**Metrics**:
- **Complexity**: Low (path splitting)
- **Risk**: Low (XPath pattern extraction is straightforward)
- **Configurability Gain**: ++
- **Code Sprawl Risk**: Low (single helper method)
- **Dependencies**: None (uses existing contract field)
- **Lines Changed**: ~5-8 locations

---

### **TASK 6: Make Required Attribute Names Contract-Driven**
**Priority**: LOW (Attribute names likely consistent across products)

**Current Hard-Coding**:
```python
con_id = contact.get('con_id', '').strip()
ac_role_tp_c = contact.get('ac_role_tp_c', '').strip()
address_tp_c = address.get('address_tp_c', '').strip()
```

**Issue**: If IL Lending uses `borrower_id` instead of `con_id`, this breaks.

**Proposed Solution**:
```python
id_attr = self._get_id_attribute_for_element('contact')
type_attr = self._get_type_attribute_for_element('contact')

contact_id = contact.get(id_attr, '').strip()
contact_type = contact.get(type_attr, '').strip()
```

**Contract Enhancement** (Explicit naming):
```json
"element_filtering": {
  "filter_rules": [
    {
      "element_type": "contact",
      "id_attribute": "con_id",        // ⭐ Add this
      "type_attribute": "ac_role_tp_c", // ⭐ Add this
      "required_attributes": {
        "con_id": true,
        "ac_role_tp_c": ["PR", "AUTHU"]
      }
    }
  ]
}
```

**Recommendation**: **Only implement if needed** - this adds significant complexity for uncertain benefit. Most products likely use consistent attribute naming.

**Metrics**:
- **Complexity**: High (pervasive attribute name usage)
- **Risk**: High (affects every attribute access)
- **Configurability Gain**: +++
- **Code Sprawl Risk**: High (changes dozens of locations)
- **Dependencies**: Tasks 1-5
- **Lines Changed**: 50+ locations
- **DEFER** until proven necessary

---

### **TASK 7: Create 'Primary Contact' Abstraction**
**Priority**: MEDIUM (Consolidates scattered primary contact logic)

**Current State**: "Primary contact" concept scattered across multiple methods:
- `_extract_valid_contacts` (deduplication)
- `_extract_from_last_valid_pr_contact` (XPath filtering)
- `_build_app_level_context` (PR filtering)

**Proposed Solution**:
```python
class ContactTypeResolver:
    """Resolves contact type business logic from contract."""
    
    def __init__(self, contract: MappingContract):
        self._contract = contract
        self._valid_types = self._load_valid_types()
        self._priority_map = self._load_priority_map()
        self._primary_type = self._load_primary_type()
    
    def is_valid_contact_type(self, ac_role_tp_c: str) -> bool:
        return ac_role_tp_c in self._valid_types
    
    def get_primary_type(self) -> str:
        return self._primary_type
    
    def compare_priority(self, type_a: str, type_b: str) -> int:
        """Returns -1 if type_a has higher priority, 1 if type_b, 0 if equal."""
        priority_a = self._priority_map.get(type_a, 999)
        priority_b = self._priority_map.get(type_b, 999)
        return -1 if priority_a < priority_b else (1 if priority_a > priority_b else 0)
```

**Contract Enhancement**: Same as Tasks 1-2

**Benefits**:
- Centralized contact type business logic
- Easier to test in isolation
- Clearer separation of concerns

**Metrics**:
- **Complexity**: Medium (new abstraction layer)
- **Risk**: Low (encapsulates existing logic)
- **Configurability Gain**: ++ (enables future extensions)
- **Code Sprawl Risk**: Medium (new class, but consolidates logic)
- **Dependencies**: Tasks 1-2
- **Lines Changed**: ~100 (new class + refactoring call sites)

---

## Recommendations by Configurability vs. Code Sprawl

### **High Configurability, Low Code Sprawl** ⭐ BEST ROI
1. **Task 1** - Contact Type Filtering (reuses existing contract field)
2. **Task 3** - Address Type Filtering (minimal contract addition)
3. **Task 5** - XPath Element Names (derives from existing paths)

### **High Configurability, Medium Code Sprawl** ✅ GOOD VALUE
4. **Task 2** - Primary Contact Precedence (adds priority logic)
5. **Task 4 (Option A)** - Table Categories (smart inference)

### **High Configurability, High Code Sprawl** ⚠️ EVALUATE NEED
6. **Task 4 (Option B)** - Table Metadata (explicit config)
7. **Task 7** - Primary Contact Abstraction (new class)

### **High Configurability, Very High Code Sprawl** ❌ DEFER
8. **Task 6** - Attribute Name Mapping (pervasive changes)

---

## Recommended Implementation Order

### **Phase 1: Foundation (Low-Hanging Fruit)**
1. Task 1: Contact Type Filtering ⭐ (~2 hours)
2. Task 3: Address Type Filtering ⭐ (~1 hour)
3. Task 5: XPath Element Names ⭐ (~1 hour)

**Deliverable**: Basic multi-product support for contact/address types
**Test**: Modify contract with different type names, verify system works

### **Phase 2: Business Logic**
4. Task 2: Contact Precedence ✅ (~3 hours)

**Deliverable**: Configurable primary contact rules
**Test**: Reverse priority order, verify correct contact selection

### **Phase 3: Architecture (If Needed)**
5. Task 4 (Option A): Table Category Inference ✅ (~4 hours)
6. Task 7: Contact Type Abstraction (optional) (~6 hours)

**Deliverable**: Table-agnostic processing
**Test**: Rename tables in contract, verify correct behavior

### **Phase 4: Deep Refactoring (Only If Required)**
7. Task 4 (Option B): Explicit Table Metadata (if Option A insufficient)
8. Task 6: Attribute Name Mapping (only if product needs it)

---

## Testing Strategy

### **For Each Task**:
1. **Contract Variation Test**: Modify contract values, verify code adapts
2. **Regression Test**: Ensure existing tests pass with original contract
3. **Edge Case Test**: Missing values, unknown types, empty lists
4. **Multi-Product Test**: Create IL Lending contract variant, verify extraction

### **Integration Tests**:
- Full pipeline with modified contract (different types/priorities)
- Performance benchmarks (contract parsing overhead)
- Error handling (malformed contract configurations)

### **Documentation**:
- Update `mapping-principles.md` with new contract fields
- Add examples of multi-product configuration
- Document fallback behavior for missing config

---

## Risk Mitigation

### **Backwards Compatibility**:
- All contract enhancements should have **sensible defaults**
- If new field missing, fall back to hard-coded values with warning
- Gradual migration path (old contracts still work)

### **Performance**:
- Cache contract-derived values at initialization
- Avoid repeated parsing in hot loops
- Profile before/after for each task

### **Code Quality**:
- Each task = separate commit with tests
- Code review focused on contract parsing correctness
- Document contract schema with JSON Schema validation

---

## Appendix: Contract Fields Summary

### **Already Exists in Contract** ✅
- `element_filtering.filter_rules[0].required_attributes.ac_role_tp_c` - Valid contact types
- `element_filtering.filter_rules[1].required_attributes.address_tp_c` - Valid address types
- `element_filtering.filter_rules[*].xml_child_path` - Element names for XPath
- `enum_mappings.contact_type_enum` - Contact type to integer mapping
- `enum_mappings.address_type_enum` - Address type to integer mapping

### **Proposed Additions** ⭐
```json
{
  "element_filtering": {
    "filter_rules": [
      {
        "element_type": "contact",
        "priority_order": ["PR", "AUTHU"],  // Task 2
        "required_attributes": { ... }
      },
      {
        "element_type": "address",
        "preferred_type": "CURR",  // Task 3
        "required_attributes": { ... }
      }
    ]
  }
}
```

### **Optional Additions** (Only if needed)
```json
{
  "table_metadata": { /* Task 4 Option B */ },
  "element_filtering": {
    "filter_rules": [
      {
        "id_attribute": "con_id",  /* Task 6 */
        "type_attribute": "ac_role_tp_c"  /* Task 6 */
      }
    ]
  }
}
```

---

## Conclusion

**Recommended Approach**:
1. **Start with Phase 1** (Tasks 1, 3, 5) - ~4 hours of work, huge configurability gain
2. **Validate with IL Lending contract** - Does this solve 80% of the problem?
3. **Proceed to Phase 2** (Task 2) only if needed
4. **Defer Phase 3-4** until concrete multi-product requirements emerge

**Key Insight**: The contract **already contains most needed information** in `element_filtering.filter_rules`. We can derive a lot without adding new fields, minimizing contract bloat while maximizing flexibility.

**Success Criteria**: 
- Create `mapping_contract_IL_lending.json` with different contact types
- Run full test suite and production processor with IL contract
- Zero code changes required ✅
