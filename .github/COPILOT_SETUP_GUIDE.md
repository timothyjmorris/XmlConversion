# How to Configure GitHub Copilot to Use These Skills

**Date:** January 22, 2026  
**Purpose:** Make these skills discoverable and actionable for GitHub Copilot and AI agents.

---

## Option 1: GitHub Copilot Chat Context (Recommended)

### What: Copilot Chat Instructions
GitHub Copilot Chat can be configured with `.github/copilot-instructions.md` to provide context for inline suggestions.

### How to Set Up

1. **You already have this set up** ✅
   - File: `.github/copilot-instructions.md`
   - This is the primary context for all Copilot interactions

2. **Enhance it with skill references**

   Add this section to your `.github/copilot-instructions.md`:

   ```markdown
   ## Decision-Making Resources
   
   For specific guidance on architecture, patterns, and tradeoffs, refer to:
   - `.github/skills/SYSTEM_CONSTRAINTS.md` - Non-negotiable principles
   - `.github/skills/DECISION_FRAMEWORKS.md` - How to make decisions
   - `.github/skills/COMMON_PATTERNS.md` - Reusable code patterns
   
   ### When to Consult Skills
   - **Adding a feature:** See COMMON_PATTERNS.md for tested examples
   - **Uncertain about design:** See DECISION_FRAMEWORKS.md for decision trees
   - **Code review:** See SYSTEM_CONSTRAINTS.md for checklist
   - **Stuck on a bug:** See SYSTEM_CONSTRAINTS.md "Known Gotchas"
   ```

### What Happens
- Copilot reads `.github/copilot-instructions.md` for every interaction
- Copilot knows about these skills and can reference them in responses
- When you ask ambiguous questions, Copilot can say "see DECISION_FRAMEWORKS.md for decision tree"

---

## Option 2: VS Code Settings (Local Development)

### What: Workspace-Specific Prompt Engineering

### How to Set Up

1. **Create `.vscode/settings.json` with Copilot context:**

```json
{
  "github.copilot.advanced": {
    "chatTurnCount": 5,
    "chatTurnCountBeforeRequest": 4
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.python",
    "editor.formatOnSave": true
  },
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true
}
```

2. **Create `.vscode/tasks.json` for quick access to skills:**

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Show System Constraints",
      "command": "cat",
      "args": [".github/skills/SYSTEM_CONSTRAINTS.md"],
      "type": "shell",
      "group": "none"
    },
    {
      "label": "Show Decision Frameworks",
      "command": "cat",
      "args": [".github/skills/DECISION_FRAMEWORKS.md"],
      "type": "shell",
      "group": "none"
    },
    {
      "label": "Show Common Patterns",
      "command": "cat",
      "args": [".github/skills/COMMON_PATTERNS.md"],
      "type": "shell",
      "group": "none"
    }
  ]
}
```

### What Happens
- `Cmd+Shift+D` (Run Task) → Quick access to skills
- When Copilot is uncertain, you can paste skill section into chat
- Local context for IDE-level completions

---

## Option 3: GitHub README (Discovery)

### What: Make Skills Visible in Repository

### How to Set Up

1. **Update main README.md** with skill references:

```markdown
## AI-Assisted Development

This project includes GitHub Copilot skills to enable AI agents to:
- Understand architecture and design decisions
- Avoid reintroducing known bugs
- Make consistent decisions
- Reuse proven patterns

**See `.github/skills/README.md` for guidance.**

Quick Links:
- [System Constraints & Non-Negotiables](.github/skills/SYSTEM_CONSTRAINTS.md)
- [Decision Frameworks](.github/skills/DECISION_FRAMEWORKS.md)
- [Common Code Patterns](.github/skills/COMMON_PATTERNS.md)
```

2. **Add to main `copilot-instructions.md`**:

```markdown
## Extending the System with AI Assistance

This repository includes detailed skills in `.github/skills/`:
- SYSTEM_CONSTRAINTS.md - What you must not change
- DECISION_FRAMEWORKS.md - How to make architecture decisions
- COMMON_PATTERNS.md - Tested, reusable code patterns

Use these when asking AI for help with:
- New product-line expansions
- Feature development
- Architecture decisions
- Code review feedback
```

### What Happens
- Developers see these skills when exploring repository
- New team members understand where to find guidance
- Skills are discoverable through GitHub web interface

---

## Option 4: Prompt Engineering Templates

### What: Copy-Paste Prompts for Common Tasks

### How to Use

**Create `docs/COPILOT_PROMPTS.md` with templates:**

```markdown
# Copilot Prompts for XML Extraction System

## Adding a New Field to Product Line

**Prompt:**
```
I need to add a new field "region_name" to the healthcare provider product line.

Before suggesting code, verify:
1. From SYSTEM_CONSTRAINTS.md: Should this be in mapping_contract.json?
2. From DECISION_FRAMEWORKS.md: Is this a contract extension (yes) or code change (no)?
3. From COMMON_PATTERNS.md: Find similar enum mapping patterns

Then suggest how to extend config/mapping_contract.json and test it.
```

## Addressing Performance Issues

**Prompt:**
```
Throughput is 2000 records/min but target is 3500. 

From DECISION_FRAMEWORKS.md (Performance section):
1. What was baseline? (current: 2000 records/min, target: 3500)
2. What's the bottleneck? (need measurement, not guess)
3. Suggest measurements for: batch-size sensitivity and worker concurrency

Don't suggest optimizations yet. Show me what to measure.
```

## Code Review: New Product Line

**Prompt:**
```
Please review this new product line implementation.

Use SYSTEM_CONSTRAINTS.md code review checklist:
- [ ] All field mappings in mapping_contract.json (not hardcoded)?
- [ ] target_schema read from contract (not hardcoded)?
- [ ] Atomic transactions present?
- [ ] FK ordering respected?
- [ ] Cursor-based pagination (not OFFSET)?
- [ ] WITH (NOLOCK) on duplicate detection?
- [ ] Three-layer validation?
- [ ] Tests verify data integrity?

Flag any violations.
```
```

### What Happens
- Standardized way to ask AI for help
- Ensures AI reads relevant skills before responding
- Reduces miscommunications about expectations

---

## Option 5: CI/CD Integration (Advanced)

### What: Enforce Skills in Code Review

### How to Set Up (GitHub Actions)

**Create `.github/workflows/ai-review.yml`:**

```yaml
name: AI-Assisted Code Review

on: [pull_request]

jobs:
  skill-compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Check SYSTEM_CONSTRAINTS compliance
        run: |
          # Verify hardcoded schema names don't appear
          if grep -r "\[dbo\]\." xml_extractor/ --include="*.py" 2>/dev/null; then
            echo "❌ Found hardcoded [dbo] schema in code"
            echo "See .github/skills/SYSTEM_CONSTRAINTS.md: Schema Isolation"
            exit 1
          fi
          
          # Verify contract file changes (not code-based mappings)
          if git diff --name-only | grep -q "xml_extractor/mapping/"; then
            echo "⚠️  Code change in mapping module"
            echo "Consider: Should this be in config/mapping_contract.json instead?"
          fi
      
      - name: Check OFFSET pagination
        run: |
          if grep -r "OFFSET" xml_extractor/ --include="*.py"; then
            echo "❌ Found OFFSET pagination"
            echo "See .github/skills/SYSTEM_CONSTRAINTS.md: Use cursor-based pagination"
            exit 1
          fi
      
      - name: Check WITH NOLOCK
        run: |
          if grep -r "SELECT.*FROM.*app_base" xml_extractor/ --include="*.py" | grep -v "NOLOCK"; then
            echo "⚠️  Found SELECT without NOLOCK on duplicate detection"
            echo "See .github/skills/SYSTEM_CONSTRAINTS.md: Lock Contention Prevention"
          fi
```

### What Happens
- Automated checks prevent reintroducing known gotchas
- PR feedback enforces skill compliance
- Reduces manual code review burden

---

## Option 6: Interactive Copilot Chat

### What: Guide Copilot Through Complex Decisions

### How to Use

1. **Copy relevant skill section into chat**

   When uncertain, paste decision framework from skill file:

   ```
   I'm not sure whether to hardcode this mapping or use the contract.
   
   [PASTE FROM DECISION_FRAMEWORKS.md: When to Extend Config vs. Code]
   
   Which approach should I take?
   ```

2. **Reference by file name**

   ```
   Before suggesting code, consult SYSTEM_CONSTRAINTS.md section "Contract-Driven Architecture"
   and then propose the change.
   ```

3. **Request specific pattern**

   ```
   Show me how to implement this using the pattern from COMMON_PATTERNS.md: Pattern 3.3
   ```

### What Happens
- Copilot has concrete guidance to follow
- Avoids vague "best practices" conversations
- Gets actionable recommendations

---

## Option 7: Custom Copilot Extensions (Future)

### What: Build Domain-Specific Copilot Behaviors

### Advanced Setup (Requires VS Code Extension)

```typescript
// .vscode/extensions/xml-extraction-skills/extension.ts

import * as vscode from 'vscode';
import * as fs from 'fs';

export function activate(context: vscode.ExtensionContext) {
  
  // Register command: Insert System Constraints snippet
  let command1 = vscode.commands.registerCommand(
    'xmlExtraction.insertConstraints',
    () => {
      const constraints = fs.readFileSync(
        '.github/skills/SYSTEM_CONSTRAINTS.md',
        'utf8'
      );
      
      // Insert into active editor
      const editor = vscode.window.activeTextEditor;
      if (editor) {
        editor.edit(editBuilder => {
          editBuilder.insert(
            editor.selection.start,
            constraints
          );
        });
      }
    }
  );
  
  context.subscriptions.push(command1);
}
```

**Usage:** `Cmd+Shift+P` → "Insert XML Extraction Skills"

(Note: This is advanced and optional—skills files work well without this)

---

## Recommended Setup for Your Team

### Step 1: Essential (5 minutes)
✅ You've done this—created the skill files

### Step 2: Core Setup (10 minutes)
1. Add to `copilot-instructions.md`:
   ```markdown
   ## For Decision-Making & Architecture
   See `.github/skills/` for:
   - SYSTEM_CONSTRAINTS.md
   - DECISION_FRAMEWORKS.md
   - COMMON_PATTERNS.md
   ```

2. Add to main `README.md`:
   ```markdown
   ## AI-Assisted Development
   This project includes skills for GitHub Copilot in `.github/skills/`.
   See [.github/skills/README.md](.github/skills/README.md).
   ```

### Step 3: Team Enablement (15 minutes)
1. Create `.vscode/settings.json` for consistent IDE setup
2. Share `docs/COPILOT_PROMPTS.md` with team
3. Document in onboarding: "See `.github/skills/` when asking AI for help"

### Step 4: Advanced (Optional, 30+ minutes)
- Add automated checks to CI/CD
- Create custom VS Code extension
- Build Copilot Chat context injection

---

## Testing Your Setup

### Verify Copilot Can Access Skills

1. **Open Copilot Chat:** `Cmd+I` or `Cmd+Shift+I`

2. **Ask a question that requires skills:**
   ```
   I want to add a new product line field. Should I modify the mapping code or 
   extend the mapping_contract.json? Refer to DECISION_FRAMEWORKS.md.
   ```

3. **Expected response:**
   - Copilot references the skill file
   - Proposes contract-driven approach
   - Suggests using COMMON_PATTERNS.md example

4. **If Copilot doesn't reference skills:**
   - Copy relevant section into chat manually
   - Copilot will then apply the guidance

---

## Keeping Skills in Sync with Copilot

### Monthly Review
```
- [ ] Do the skills still match our approach?
- [ ] Have we found new patterns to document?
- [ ] Any new constraints discovered?
- [ ] Update "Last Updated" date in each file
```

### When Adding New Product Lines
```
- [ ] Did Copilot avoid the known gotchas?
- [ ] Were decision frameworks helpful?
- [ ] Should we add new patterns?
- [ ] Update skills based on learnings
```

---

## Troubleshooting

### "Copilot doesn't seem to know about the skills"

**Solution 1:** Reference manually
```
Here's the relevant section from .github/skills/SYSTEM_CONSTRAINTS.md:

[paste skill section]

Given this, how should I approach X?
```

**Solution 2:** Check Copilot settings
- Ensure `.github/copilot-instructions.md` exists
- Verify it's committed to repository
- Reload VS Code (`Cmd+R`)

### "The skill file is outdated"

**Solution:** Tag with date and review quarterly
```markdown
**Last Updated:** January 22, 2026
**Next Review:** April 22, 2026
```

### "Copilot's suggestion violates SYSTEM_CONSTRAINTS"

**Solution:** Provide feedback in chat
```
This violates SYSTEM_CONSTRAINTS.md section "Atomic Transactions".
Please revise to ensure all-or-nothing semantics.
```

---

## Success Indicators

You'll know the setup is working when:

✅ **Team doesn't ask permission for changes**  
→ They reference skills to make decisions confidently

✅ **Fewer code review cycles**  
→ Developers use DECISION_FRAMEWORKS before proposing

✅ **Copilot avoids common mistakes**  
→ No lock contention, OFFSET pagination, or hardcoded schemas

✅ **New product lines ship faster**  
→ Developers use COMMON_PATTERNS instead of inventing new ones

✅ **Easier to onboard new people**  
→ They see the skills in `.github/` and understand the system

---

## Next Steps

1. **Commit these files:**
   ```powershell
   git add .github/skills/
   git add .github/COPILOT_SKILLS_STRATEGY.md
   git commit -m "Add GitHub Copilot skills for product-line expansion"
   ```

2. **Share with team:**
   ```
   "Check .github/skills/ for guidance on architecture decisions,
   code patterns, and system constraints."
   ```

3. **Test with first new feature:**
   ```
   Use Copilot with prompts that reference the skills.
   See docs/COPILOT_PROMPTS.md for examples.
   ```

4. **Iterate:**
   ```
   After first product-line expansion:
   - Review what worked/didn't
   - Update skills based on learnings
   - Plan Phase 2 (PRODUCT_LINE_EXPANSION.md, etc.)
   ```

---

*Last Updated: January 22, 2026*
