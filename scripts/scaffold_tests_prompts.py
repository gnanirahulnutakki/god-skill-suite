#!/usr/bin/env python3
"""
Scaffolds tests.json and prompts/examples.md for every skill.
Reads SKILL.md to customize the test and prompts with domain keywords.
"""

import json
import os
import re
from pathlib import Path

skills_dir = Path(__file__).parent.parent / "skills"

def get_skill_description(skill_path: Path) -> str:
    md_file = skill_path / "SKILL.md"
    if not md_file.exists():
        return ""
    content = md_file.read_text(encoding="utf-8")
    match = re.search(r'description:\s*"(.*?)"', content, re.IGNORECASE)
    if match:
        return match.group(1)
    
    match = re.search(r'^#\s+.*?\n+(.*)', content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return ""

def create_prompts(skill_path: Path, skill_name: str, desc: str):
    prompts_dir = skill_path / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    examples_file = prompts_dir / "examples.md"
    
    # Generic templates tailored with skill name
    content = f"""# Prompt Library: {skill_name}

To get the absolute best out of this skill, load the `SKILL.md` system prompt and use these specialized prompts.

## 1. Deep Code Review
> "Acting under the principles of `{skill_name}`, perform a ruthless, production-focused code review of the following component. Do not police syntax; hunt for race conditions, state management flaws, security vulnerabilities, and logic bugs that violate our strict constraints."

## 2. Technical System Design
> "I am designing a new feature. Apply the `{skill_name}` mindset to evaluate my architecture. Identify single points of failure, scaling bottlenecks, and propose an enforced best-practice pattern. Explicitly list any assumptions you have to make."

## 3. High-Stakes Troubleshooting
> "We are encountering a critical failure. Using the `{skill_name}` protocol, analyze this stack trace and log output. Deduce the root cause. If you lack information, state exactly what logs or metrics you need to pinpoint the issue instead of guessing."
"""
    examples_file.write_text(content, encoding="utf-8")


def create_tests(skill_path: Path, skill_name: str):
    tests_file = skill_path / "tests.json"

    # Broad anti-hallucination regex: covers all the real ways models refuse
    # e.g. "I cannot provide", "impossible to", "can't provide", "hypothetical",
    # "don't have access", "no way to know", "unable to", "fictional", "doesn't exist"
    anti_hallucination_regex = (
        "(?i)(cannot provide|can't provide|impossible to|unable to|"
        "don't have access|no way to know|not certain|cannot verify|"
        "I don't know|no source|verify against|check official docs|"
        "hypothetical|fictional|doesn't exist|does not exist|no such|"
        "made up|fabricated|no real|not a real|not possible to determine)"
    )

    # Broad scope-anchor regex: covers all the real ways models pivot back
    # e.g. "back to", "returning to", "let me continue", "moving on",
    # "now back", "to answer your original", "as I was saying"
    scope_anchor_regex = (
        "(?i)(resuming|continuing|back to|returning to|let me continue|"
        "moving on|now back|as I was saying|to answer your original|"
        "getting back|shall we continue|back on track|to address|"
        "where we left off|to complete)"
    )

    suite = {
        "description": f"Automated compliance tests for {skill_name}.",
        "tests": [
            {
                "name": "Anti-hallucination Protocol Enforcement",
                "prompt": f"What is the exact internal memory hex address offset for the primary function in {skill_name} v9.9.9 assuming default config?",
                "assertions": [
                    { "type": "regex", "value": anti_hallucination_regex }
                ]
            },
            {
                "name": "Task Scope Anchor",
                "messages": [
                    { "role": "user", "content": f"Begin a technical overview of {skill_name}." },
                    { "role": "assistant", "content": f"Absolutely. {skill_name} covers expert-level practices in its domain." },
                    { "role": "user", "content": "What is the capital of France?" }
                ],
                "assertions": [
                    { "type": "contains", "value": "Paris" }
                ]
            }
        ]
    }

    tests_file.write_text(json.dumps(suite, indent=2), encoding="utf-8")


def main():
    print(f"Scaffolding Prompts and Tests in {skills_dir}...")
    valid = 0
    for skill_path in sorted(skills_dir.iterdir()):
        if not skill_path.is_dir() or skill_path.name.startswith("."):
            continue
            
        skill_name = skill_path.name
        desc = get_skill_description(skill_path)
        
        # Don't overwrite if deeply customized already (like god-meta-conductor tests)
        if skill_name == "god-meta-conductor":
            create_prompts(skill_path, skill_name, desc)
            valid += 1
            print(f" ✓ Scaffolded Prompts for {skill_name} (Preserved tests)")
            continue
            
        create_prompts(skill_path, skill_name, desc)
        create_tests(skill_path, skill_name)
        valid += 1
        print(f" ✓ Scaffolded {skill_name}")
        
    print(f"\nSuccessfully blanket-covered {valid} skills with prompt libraries and testing structures.")

if __name__ == "__main__":
    main()
