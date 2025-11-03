# Project Restructuring Guide
## Rename: MB_XmlConversionKiro → XmlConversion

**Date:** November 2, 2025  
**Impact:** Repository name, folder structure, import paths

---

## Part 1: Rename GitHub Repository ✅ (Do First)

### Steps:
1. Go to: https://github.com/timothyjmorris/MB_XmlConversionKiro/settings
2. Scroll to "Repository name"
3. Change to: `XmlConversion`
4. Click "Rename"

### Update Local Git Remote:
```powershell
cd C:\Users\merrickuser\Documents\Development\XmlConversionKiro\MB_XmlConversionKiro

# Update remote URL to new repo name
git remote set-url origin https://github.com/timothyjmorris/XmlConversion.git

# Verify the change
git remote -v
```

**Expected output:**
```
origin  https://github.com/timothyjmorris/XmlConversion.git (fetch)
origin  https://github.com/timothyjmorris/XmlConversion.git (push)
```

---

## Part 2: Flatten Directory Structure ✅ (Do Second)

### Current Structure Problem:
```
XmlConversionKiro\              ← Outer folder (confusing name)
└── MB_XmlConversionKiro\       ← Nested folder (redundant)
    ├── xml_extractor\
    ├── tests\
    ├── config\
    ├── production_processor.py
    └── ...
```

### Target Structure:
```
XmlConversion\                  ← Clean, single root folder
├── xml_extractor\
├── tests\
├── config\
├── production_processor.py
└── ...
```

### Commands to Execute:

```powershell
# Navigate to Development folder
cd C:\Users\merrickuser\Documents\Development

# IMPORTANT: Commit any uncommitted changes first!
cd .\XmlConversionKiro\MB_XmlConversionKiro
git status
git add .
git commit -m "Pre-restructure commit: Save all changes before folder reorganization"
git push

# Now back to Development folder
cd C:\Users\merrickuser\Documents\Development

# Create temporary folder
New-Item -ItemType Directory -Path "XmlConversion_temp"

# Move all contents from nested folder up one level
# This preserves .git folder and all your work
Copy-Item -Path ".\XmlConversionKiro\MB_XmlConversionKiro\*" -Destination ".\XmlConversion_temp\" -Recurse -Force

# Verify .git folder was copied
Test-Path ".\XmlConversion_temp\.git"  # Should return True

# Remove old structure
Remove-Item -Path ".\XmlConversionKiro" -Recurse -Force

# Rename temp to final name
Rename-Item -Path ".\XmlConversion_temp" -NewName "XmlConversion"

# Navigate to new location
cd XmlConversion

# Verify git is still working
git status
git log --oneline -3
```

---

## Part 3: Update Code References ✅ (Do Third)

### Files That Need Changes:

**Note:** These changes are ONLY needed if you're using absolute imports with the old package name. If you're using relative imports (`from ..mapping import`), you're fine!

### 1. Update Test File Import (if using absolute imports)
**File:** `tests/contracts/test_mapping_types_and_expressions.py`

**Find and replace:**
- `from MB_XmlConversionKiro.xml_extractor` → `from xml_extractor`

Or use this PowerShell command after restructuring:
```powershell
cd C:\Users\merrickuser\Documents\Development\XmlConversion

# Update imports in test file
$file = "tests\contracts\test_mapping_types_and_expressions.py"
$content = Get-Content $file -Raw
$content = $content -replace 'from MB_XmlConversionKiro\.xml_extractor', 'from xml_extractor'
$content | Set-Content $file -NoNewline
```

### 2. Update Performance Testing File
**File:** `performance_tuning/phase_2_investigation/test_phase2_3b_implementation.py`

```powershell
$file = "performance_tuning\phase_2_investigation\test_phase2_3b_implementation.py"
$content = Get-Content $file -Raw
$content = $content -replace 'from MB_XmlConversionKiro\.xml_extractor', 'from xml_extractor'
$content | Set-Content $file -NoNewline
```

### 3. Update Documentation References

**Files to update manually (low priority, just for cleanliness):**
- `__init__.py` (line 1 comment)
- `performance_tuning/test_modules/README.md` (example paths)
- `performance_tuning/archived_analysis/BENCHMARK_GUIDE.md` (example paths)

These are just comments/docs, not breaking changes.

---

## Part 4: Update setup.py (if applicable) ✅

Check your `setup.py` file. If it references the old package name, update it:

```powershell
cd C:\Users\merrickuser\Documents\Development\XmlConversion

# Check current setup.py
Get-Content setup.py | Select-String "MB_XmlConversionKiro"
```

If found, update:
```python
# Old
name="MB_XmlConversionKiro"

# New  
name="XmlConversion"
```

---

## Part 5: Verify Everything Works ✅ (Final Check)

```powershell
cd C:\Users\merrickuser\Documents\Development\XmlConversion

# 1. Verify git still works
git status
git remote -v

# 2. Reinstall package with new structure
pip uninstall xml-extractor -y
pip install -e .

# 3. Run tests to verify nothing broke
python -m pytest tests/ -q

# 4. Verify imports work
python -c "from xml_extractor.mapping.data_mapper import DataMapper; print('Import successful!')"

# 5. Test production processor
python production_processor.py --help
```

---

## Quick Reference: One-Time Migration Script

**Execute this after renaming GitHub repo:**

```powershell
# Save this as: migrate_structure.ps1
# Run with: .\migrate_structure.ps1

# Step 1: Commit current work
cd C:\Users\merrickuser\Documents\Development\XmlConversionKiro\MB_XmlConversionKiro
git add .
git commit -m "Pre-migration commit"
git push

# Step 2: Update remote URL
git remote set-url origin https://github.com/timothyjmorris/XmlConversion.git
git remote -v

# Step 3: Restructure folders
cd C:\Users\merrickuser\Documents\Development
New-Item -ItemType Directory -Path "XmlConversion_temp" -Force
Copy-Item -Path ".\XmlConversionKiro\MB_XmlConversionKiro\*" -Destination ".\XmlConversion_temp\" -Recurse -Force

# Verify .git folder copied
if (Test-Path ".\XmlConversion_temp\.git") {
    Write-Host "✅ Git folder preserved" -ForegroundColor Green
} else {
    Write-Host "❌ ERROR: Git folder missing!" -ForegroundColor Red
    exit 1
}

# Remove old structure and rename
Remove-Item -Path ".\XmlConversionKiro" -Recurse -Force
Rename-Item -Path ".\XmlConversion_temp" -NewName "XmlConversion"

# Step 4: Update imports
cd XmlConversion

$files = @(
    "tests\contracts\test_mapping_types_and_expressions.py",
    "performance_tuning\phase_2_investigation\test_phase2_3b_implementation.py"
)

foreach ($file in $files) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        $content = $content -replace 'from MB_XmlConversionKiro\.xml_extractor', 'from xml_extractor'
        $content | Set-Content $file -NoNewline
        Write-Host "✅ Updated: $file" -ForegroundColor Green
    }
}

# Step 5: Verify
Write-Host "`n=== Verification ===" -ForegroundColor Cyan
git status
python -m pytest tests/ -q

Write-Host "`n✅ Migration complete!" -ForegroundColor Green
Write-Host "New location: C:\Users\merrickuser\Documents\Development\XmlConversion" -ForegroundColor Green
```

---

## Rollback Plan (Just in Case)

If something goes wrong:

```powershell
# Option 1: Restore from git
cd C:\Users\merrickuser\Documents\Development\XmlConversion
git reset --hard HEAD
git clean -fd

# Option 2: Clone fresh from GitHub
cd C:\Users\merrickuser\Documents\Development
Remove-Item -Path "XmlConversion" -Recurse -Force
git clone https://github.com/timothyjmorris/XmlConversion.git
cd XmlConversion
pip install -e .
```

---

## Summary Checklist

- [ ] **1. Rename GitHub repo** (Settings → Repository name → XmlConversion)
- [ ] **2. Update git remote URL** (`git remote set-url origin`)
- [ ] **3. Commit all changes** before restructuring
- [ ] **4. Execute folder restructure** (move MB_XmlConversionKiro contents up)
- [ ] **5. Update import statements** (MB_XmlConversionKiro → xml_extractor)
- [ ] **6. Run tests** (`python -m pytest tests/ -q`)
- [ ] **7. Reinstall package** (`pip install -e .`)
- [ ] **8. Verify production_processor** works
- [ ] **9. Update VS Code workspace settings** (if any)
- [ ] **10. Commit restructure changes** to git

---

**Estimated Time:** 20-30 minutes  
**Risk Level:** Low (git preserves history, easy to rollback)  
**Best Practice:** Do this during low-activity time, commit frequently
