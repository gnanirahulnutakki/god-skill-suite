# Contributing to God-Level Skill Suite

Thank you for wanting to contribute! The goal of this project is to maintain the absolute highest engineering quality — every skill must genuinely transform an AI model's behavior into a "god-level" expert, not just provide a list of bullet points.

---

## 📋 Before You Start

1. **Read an existing skill first.** Open `skills/god-backend-mastery/SKILL.md` or `skills/god-meta-conductor/SKILL.md`. Understand the structure, depth, and tone required.
2. **Check open issues** for existing skill requests before opening a duplicate.
3. **Search the skill list** in `installer/install.py` to confirm your proposed skill doesn't already exist under a different name.

---

## 🛠 How to Add a New Skill

### Step 1: Create the directory structure

```bash
mkdir -p skills/god-<your-skill-name>/prompts
```

### Step 2: Write the SKILL.md

Your `SKILL.md` MUST follow this exact structure:

```markdown
---
name: god-<your-skill-name>
description: "One-paragraph description. Must explain the AI persona being instilled."
license: MIT
metadata:
  version: '1.0'
  category: <Engineering|DevOps|Security|Data|ML|DeveloperEx|Operations|Research>
---

# God-Level <Skill Name>

[Opening identity statement — who this AI *is* when the skill is loaded. 3-5 sentences.]

---

## Mindset: The Researcher-Warrior

[5-7 bullet points defining the core philosophical constraints of this expert]

---

## [Technical Section 1]
[Deeply technical, specific, production-grade content with real commands/code]

## [Technical Section 2]
...

## Cross-Domain Connections
[2-3 references to other god-level skills this connects to, and how]

## Anti-Hallucination Protocol
[Specific domains where this skill must refuse to guess and force verification]

## Self-Review Checklist
1. ...
[Minimum 10 items that are genuinely specific to this domain]
```

### Step 3: Quality bar requirements

| Requirement | Target |
|-------------|--------|
| Minimum line count | 400 lines |
| Self-review checklist | ≥ 10 items |
| Code examples | ≥ 2 real, runnable examples |
| Anti-hallucination section | Required |
| Cross-domain connections | Required (≥ 2) |

### Step 4: Write the Prompt Library

Create `skills/god-<your-skill>/prompts/examples.md` with at least **5 domain-specific prompts** that showcase the unique value of the skill. These must NOT be the generic "Deep Code Review / System Design / Troubleshooting" template — they must be specific to the skill's domain.

### Step 5: Write the test suite

Create `skills/god-<your-skill>/tests.json`:

```json
{
  "description": "Tests for god-<your-skill>",
  "tests": [
    {
      "name": "Anti-hallucination: domain-specific fake query",
      "prompt": "What is the exact [domain-specific impossible-to-know fact]?",
      "assertions": [
        {
          "type": "regex",
          "value": "(?i)(cannot provide|not certain|cannot verify|hypothetical|fictional)"
        }
      ]
    }
  ]
}
```

### Step 6: Register in the installer

Add your skill to the `SKILLS` list in `installer/install.py`:

```python
{"name": "god-<your-skill>", "category": "<Category>", "desc": "Short description"},
```

### Step 7: Validate and test

```bash
# Run the evaluation framework locally
python scripts/evaluate_skills.py --provider ollama --model qwen2.5:7b --skill god-<your-skill>
```

---

## 🔧 How to Improve an Existing Skill

1. Open an issue first describing what you want to improve and why.
2. Skills should only be improved with **factually accurate, production-verified** information.
3. Do not add generic advice. If you can't cite a real-world scenario or authoritative source, don't add it.

---

## 📐 Code Style

- Python files: Use `ruff` for linting (`ruff check scripts/`)
- Markdown: No trailing whitespace, use ATX headings (`##`), fenced code blocks with language tags

---

## 🔁 Pull Request Process

1. Fork the repository and create a feature branch: `git checkout -b skill/god-<your-skill>`
2. Follow the structure above exactly
3. Ensure your PR description explains: what domain, why it's needed, what makes it "god-level"
4. The CI will automatically validate your skill's YAML frontmatter — fix any failures before requesting review

---

## ⭐ Recognition

All contributors are credited in `CHANGELOG.md`. High-quality skills will be featured in the README.

Thank you for helping make AI engineering smarter!
