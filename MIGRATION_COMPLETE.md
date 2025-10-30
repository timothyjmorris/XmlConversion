# Migration Complete: generate_mock_xml.py

## Summary of Changes

### ✅ Moved File
- **From**: `c:\Users\merrickuser\Documents\Development\XmlConversionKiro\MB_XmlConversionKiro\generate_mock_xml.py`
- **To**: `c:\Users\merrickuser\Documents\Development\XmlConversionKiro\MB_XmlConversionKiro\env_prep\generate_mock_xml.py`

### ✅ Fixed Import Path
- **Old**: `project_root = Path(__file__).parent`
- **New**: `project_root = Path(__file__).parent.parent`
- **Reason**: Script now one level deeper in env_prep/ folder, needs to reference parent project root

### ✅ Added IDENTITY_INSERT SQL
- **Before Insert**: `cursor.execute("SET IDENTITY_INSERT app_xml ON")`
- **After Insert**: `cursor.execute("SET IDENTITY_INSERT app_xml OFF")`
- **Purpose**: Allows explicit app_id values instead of auto-increment

### ✅ Created Documentation
- **File**: `env_prep/README.md`
- **Contents**: Usage instructions, how IDENTITY_INSERT works, Phase II integration

---

## New Usage

### From Project Root:
```bash
python env_prep/generate_mock_xml.py
```

### From env_prep Folder:
```bash
cd env_prep
python generate_mock_xml.py
```

---

## What IDENTITY_INSERT Does

| Setting | Effect |
|---------|--------|
| `SET IDENTITY_INSERT app_xml ON` | Allows explicit app_id values |
| Insert with explicit ID | Works normally |
| `SET IDENTITY_INSERT app_xml OFF` | Re-enables auto-increment |

This ensures:
✅ No conflicts with auto-increment
✅ Can generate test data with specific IDs
✅ Next insertion uses proper auto-increment value

---

## Key Code Changes

### Path Fix
```python
# Was:
project_root = Path(__file__).parent

# Now:
project_root = Path(__file__).parent.parent
```

### IDENTITY_INSERT Addition
```python
# Before the loop:
cursor.execute("SET IDENTITY_INSERT app_xml ON")

# After the loop:
cursor.execute("SET IDENTITY_INSERT app_xml OFF")
```

---

## File Status

| File | Status | Location |
|------|--------|----------|
| generate_mock_xml.py | ✅ Moved | env_prep/ |
| Path | ✅ Fixed | Updated for new location |
| IDENTITY_INSERT | ✅ Added | Before/after insert block |
| README.md | ✅ Created | env_prep/README.md |
| Original file | ⏳ Still exists | Root directory (should be deleted if desired) |

---

## Next Steps

1. ✅ Move/copy is complete
2. ⏳ Delete original file from root (optional)
3. ✅ Update any references to use new path: `python env_prep/generate_mock_xml.py`
4. ✅ Ready to use for Phase II.1 batch size testing

---

## Test Run

To verify everything works:

```bash
python env_prep/generate_mock_xml.py
# Select: 1 (Small, 50 records)
# Should output:
# ✅ Inserted 50 mock XML records
```

If successful, you're ready for Phase II!
