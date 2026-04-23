#!/usr/bin/env python3
"""Validate all skills in the suite using agentskills CLI."""
import subprocess
import sys
import os
from pathlib import Path

skills_dir = Path(__file__).parent.parent / "skills"
passed = []
failed = []

print(f"Validating skills in {skills_dir}\n")

for skill_dir in sorted(skills_dir.iterdir()):
    if not skill_dir.is_dir():
        continue
    skill_name = skill_dir.name
    result = subprocess.run(
        ["agentskills", "validate", str(skill_dir) + "/"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        passed.append(skill_name)
        print(f"  ✅ {skill_name}")
    else:
        failed.append((skill_name, result.stdout + result.stderr))
        print(f"  ❌ {skill_name}")
        for line in (result.stdout + result.stderr).strip().split('\n')[:3]:
            print(f"     {line}")

print(f"\n{'='*50}")
print(f"PASSED: {len(passed)} / {len(passed) + len(failed)}")
print(f"FAILED: {len(failed)}")

if failed:
    print("\nFailed skills:")
    for name, err in failed:
        print(f"  {name}: {err.strip()[:100]}")
    sys.exit(1)
else:
    print("\n✅ All skills valid!")
