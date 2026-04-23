"""
God-Level Skill Suite
=====================
50 battle-hardened AI skills for Claude Code, Codex, Cursor, Windsurf, Gemini CLI and more.

Usage:
    from god_skill_suite import install
    install.main()

Or via CLI:
    god-skills
    install-god-skills
"""

__version__ = "1.0.0"
__author__ = "God Skill Suite Contributors"
__license__ = "MIT"

from pathlib import Path

# The skills directory ships inside this package
SKILLS_DIR = Path(__file__).parent.parent / "skills"
INSTALLER_DIR = Path(__file__).parent.parent / "installer"


def get_skills_dir() -> Path:
    """Return the path to the bundled skills directory."""
    if SKILLS_DIR.exists():
        return SKILLS_DIR
    # Fallback: installed via pip, skills may be in package data
    pkg_skills = Path(__file__).parent / "skills"
    if pkg_skills.exists():
        return pkg_skills
    raise FileNotFoundError(
        f"Skills directory not found. Expected at: {SKILLS_DIR}\n"
        "Try reinstalling: pip install --force-reinstall god-skill-suite"
    )


def list_skills() -> list[dict]:
    """Return list of all available skills with metadata."""
    skills_dir = get_skills_dir()
    skills = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            skill_file = skill_dir / "SKILL.md"
            content = skill_file.read_text(encoding="utf-8")
            # Extract description from frontmatter
            desc = ""
            in_frontmatter = False
            for line in content.splitlines():
                if line.strip() == "---":
                    in_frontmatter = not in_frontmatter
                    continue
                if in_frontmatter and line.startswith("description:"):
                    desc = line.replace("description:", "").strip().strip('"')
                    break
            skills.append({
                "name": skill_dir.name,
                "path": skill_dir,
                "description": desc[:100] + "..." if len(desc) > 100 else desc,
            })
    return skills
