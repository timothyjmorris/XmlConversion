# ElementFilter Contract Alignment Opportunities

**Purpose**: Evaluate ElementFilter for contract-driven flexibility to support different product configurations without code changes.

---

## Executive Summary

ElementFilter currently has **3 major hard-coded dependencies** that should be moved to the mapping contract:

| Hard-Coded | Current Value | Contract Location | Benefit |
|-----------|---------------|-------------------|---------|
| **Contact type attribute** | `ac_role_tp_c` | `key_identifiers` (NEW) | Support different attribute names per product |
| **Contact type enum values** | `{"PR", "AUTHU"}` | `enum_mappings.contact_type_enum` | EXISTING - already in contract |
| **Address type enum values** | `{"CURR", "PREV", "PATR"}` | `enum_mappings.address_type_enum` | EXISTING - already in contract |
| **Employment type enum values** | `{"CURR", "PREV"}` | `enum_mappings.employment_type_enum` | EXISTING - already in contract |
| **App ID extraction** | Hardcoded xpath `//Request/@ID` | `key_identifiers.app_id` | EXISTING - already in contract |

---

## Current Implementation Analysis

### Hard-Coded Values (Lines 63-66)
```python
VALID_AC_ROLE_TP_C = {"PR", "AUTHU"}
VALID_ADDRESS_TP_C = {"CURR", "PREV", "PATR"}  
VALID_EMPLOYMENT_TP_C = {"CURR", "PREV"}
```

**Issue**: Hard-coded enum validation values prevent product customization.

**Contract Already Has This**: `enum_mappings` section contains:
```json
{
  "enum_mappings": {
    "contact_type_enum": {
      "PR": 279,
      "AUTH": 280
    },
    "address_type_enum": {
      "CURR": 320,
      "PREV": 321,
      "PATR": 322
    },
    "employment_type_enum": {
      "CURR": 350,
      "PREV": 351
    }
  }
}
```

**Opportunity**: Replace class constants with contract-driven lookups.

---

### Hard-Coded Attribute Names (Lines 92-93, 110, 130, 138)

```python
# Line 92-93: app_id extraction
request_elem = xml_root.find('.//Request')
app_id = request_elem.get('ID')

# Line 110: contact attribute name
ac_role_tp_c = contact_elem.get('ac_role_tp_c')

# Line 130: address attribute name
address_tp_c = addr_elem.get('address_tp_c')

# Line 138: employment attribute name
employment_tp_c = emp_elem.get('employment_tp_c')
```

**Issue**: 
- Hardcoded attribute names (`ac_role_tp_c`, `address_tp_c`, `employment_tp_c`)
- Hardcoded xpath for app_id
- If product schema changes, code must change

**Contract Already Has This (Partially)**:
```json
{
  "key_identifiers": {
    "app_id": {
      "xml_path": "/Provenir/Request",
      "xml_attribute": "ID",
      "required": true
    }
  }
}
```

**Opportunity**: Add contact/address/employment type attributes to contract.

---

## Implementation Opportunities

### **Opportunity 1: Use contract.key_identifiers for app_id (Low-hanging fruit) ✅ EASY**

**Current Code (Lines 92-93)**:
```python
request_elem = xml_root.find('.//Request')
app_id = request_elem.get('ID') if request_elem is not None else None
```

**Contract-Driven Alternative**:
```python
app_id_config = self.contract['key_identifiers']['app_id']
xml_path = app_id_config['xml_path']  # "/Provenir/Request"
xml_attr = app_id_config['xml_attribute']  # "ID"

request_elem = xml_root.find(xml_path)
app_id = request_elem.get(xml_attr) if request_elem is not None else None
```

**Benefit**: 
- If app_id moves to different xpath or attribute name, no code change
- Consistent with data mapping philosophy

**Effort**: 15 minutes

---

### **Opportunity 2: Move contact_type_attribute to key_identifiers (MEDIUM) ⚡ RECOMMENDED**

**Add to mapping_contract.json**:
```json
{
  "key_identifiers": {
    "app_id": { ... },
    "con_type_attribute": {
      "xml_attribute": "ac_role_tp_c",
      "description": "Attribute name for contact type (PR/AUTHU)",
      "note": "Used by ElementFilter to identify contact type; enum values in contact_type_enum"
    }
  }
}
```

**Current Code (Lines 110)**:
```python
ac_role_tp_c = contact_elem.get('ac_role_tp_c')
```

**Contract-Driven Alternative**:
```python
con_type_attr = self.contract['key_identifiers']['con_type_attribute']['xml_attribute']
con_type_value = contact_elem.get(con_type_attr)
```

**Benefit**:
- Support products where contact type attribute is named differently
- All attribute names in one place (contract)
- Product teams can see schema flexibility at a glance

**Effort**: 20 minutes

---

### **Opportunity 3: Use contract enum_mappings for validation (MEDIUM-HIGH) ⭐ BEST VALUE**

**Current Code (Lines 63-66)**:
```python
VALID_AC_ROLE_TP_C = {"PR", "AUTHU"}
VALID_ADDRESS_TP_C = {"CURR", "PREV", "PATR"}  
VALID_EMPLOYMENT_TP_C = {"CURR", "PREV"}
```

**Contract-Driven Alternative** (Constructor):
```python
def __init__(self, contract: Dict, logger=None):
    self.logger = logger or logging.getLogger(__name__)
    self.contract = contract
    
    # Load valid enum values from contract
    self.VALID_CONTACT_TYPES = set(
        self.contract['enum_mappings']['contact_type_enum'].keys()
    )
    self.VALID_ADDRESS_TYPES = set(
        self.contract['enum_mappings']['address_type_enum'].keys()
    )
    self.VALID_EMPLOYMENT_TYPES = set(
        self.contract['enum_mappings']['employment_type_enum'].keys()
    )
```

**Updated Filter Logic**:
```python
# Line 110-113: Use contract-driven validation
if not con_id or con_type_value not in self.VALID_CONTACT_TYPES:
    self.logger.warning(
        f"Filtering out contact {first_name} - con_id: {con_id}, "
        f"{con_type_attr}: {con_type_value} (must be one of: {self.VALID_CONTACT_TYPES})"
    )
```

**Benefit**:
- ✅ Eliminates 3 hard-coded class constants
- ✅ Enum validation always matches mapping contract
- ✅ Add new enum value → automatically accepted (no code change)
- ✅ Product-specific enum values supported
- ✅ Single source of truth for valid values

**Effort**: 30 minutes

**Risk**: None - contract already has these values

---

### **Opportunity 4: Add filtering rules to contract (FUTURE - Nice to have)**

**Proposed Contract Extension**:
```json
{
  "element_filtering": {
    "contact_filtering": {
      "required_attributes": ["con_id"],
      "required_type_attribute": "ac_role_tp_c",
      "enum_mapping_name": "contact_type_enum"
    },
    "address_filtering": {
      "parent_attribute": "con_id",
      "type_attribute": "address_tp_c",
      "enum_mapping_name": "address_type_enum"
    },
    "employment_filtering": {
      "parent_attribute": "con_id",
      "type_attribute": "employment_tp_c",
      "enum_mapping_name": "employment_type_enum"
    }
  }
}
```

**Benefit**: 
- Complete schema flexibility
- No code changes for different products
- Non-developers can update filtering rules

**Effort**: 1-2 hours

**Priority**: Low (current hard-coded approach works)

---

## Implementation Priority & Recommendation

### Phase 1: Quick Wins (30 minutes) 🟢 START HERE
1. **Opportunity 1**: Use contract for app_id extraction
2. **Opportunity 2**: Move con_type_attribute to key_identifiers

### Phase 2: High Value (30 minutes) 🟡 RECOMMENDED
3. **Opportunity 3**: Use contract enum_mappings for validation

### Phase 3: Future Enhancement (Not blocking)
4. **Opportunity 4**: Full filtering rules in contract

---

## Code Changes Required

### Required Contract Addition
```json
{
  "key_identifiers": {
    "con_type_attribute": {
      "xml_attribute": "ac_role_tp_c",
      "description": "Contact type attribute name for filtering"
    }
  }
}
```

### Required Code Changes (ElementFilter)
1. Add `contract` parameter to constructor
2. Move constant initialization to contract lookups
3. Update filter logic to use contract values
4. Add informative warnings showing contract-based valid values

### Impact Analysis
- ✅ **Backwards compatible**: New version can accept contract parameter
- ✅ **No DB changes**: Contract is configuration-only
- ✅ **Testable**: Can mock contract for unit tests
- ✅ **Deployable**: No breaking changes

---

## Code Example: Complete Refactor

### Before
```python
class ElementFilter:
    VALID_AC_ROLE_TP_C = {"PR", "AUTHU"}
    VALID_ADDRESS_TP_C = {"CURR", "PREV", "PATR"}  
    VALID_EMPLOYMENT_TP_C = {"CURR", "PREV"}
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
    
    def filter_valid_elements(self, xml_root):
        request_elem = xml_root.find('.//Request')
        app_id = request_elem.get('ID')
        
        for contact_elem in xml_root.findall('.//contact'):
            ac_role_tp_c = contact_elem.get('ac_role_tp_c')
            if ac_role_tp_c not in self.VALID_AC_ROLE_TP_C:
                continue
```

### After
```python
class ElementFilter:
    def __init__(self, contract: Dict, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.contract = contract
        
        # Load from contract
        self.app_id_config = contract['key_identifiers']['app_id']
        self.con_type_attr = contract['key_identifiers']['con_type_attribute']['xml_attribute']
        self.VALID_CONTACT_TYPES = set(
            contract['enum_mappings']['contact_type_enum'].keys()
        )
        self.VALID_ADDRESS_TYPES = set(
            contract['enum_mappings']['address_type_enum'].keys()
        )
        self.VALID_EMPLOYMENT_TYPES = set(
            contract['enum_mappings']['employment_type_enum'].keys()
        )
    
    def filter_valid_elements(self, xml_root):
        request_elem = xml_root.find(self.app_id_config['xml_path'])
        app_id = request_elem.get(self.app_id_config['xml_attribute'])
        
        for contact_elem in xml_root.findall('.//contact'):
            con_type_value = contact_elem.get(self.con_type_attr)
            if con_type_value not in self.VALID_CONTACT_TYPES:
                continue
```

---

## Summary: What Should Happen

✅ **Implement (High Priority)**:
- Use `key_identifiers.app_id` for app_id extraction
- Add `con_type_attribute` to `key_identifiers`
- Load enum validation values from `contract['enum_mappings']`

🟡 **Consider (Medium Priority)**:
- Add full element filtering rules to contract (future enhancement)

❌ **Leave Alone**:
- `con_id` attribute (stable, universal across all products)
- General logic flow (works well, no need to change)

**Estimated Total Effort**: 1 hour for full Phase 1+2 implementation
**Expected Outcome**: ElementFilter becomes fully contract-driven, supporting multi-product deployments without code changes
