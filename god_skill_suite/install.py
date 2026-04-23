"""Entry point for 'god-skills' and 'install-god-skills' CLI commands."""
import sys
from pathlib import Path

def main():
    # Add installer to path and run it
    installer_path = Path(__file__).parent.parent / "installer"
    sys.path.insert(0, str(installer_path.parent))

    # Patch the skills dir discovery to use package-bundled skills
    try:
        from god_skill_suite import get_skills_dir
        import installer.install as install_module
        # Monkey-patch get_skills_source_dir to use bundled skills
        install_module.get_skills_source_dir = get_skills_dir
    except ImportError:
        pass

    # Run the installer main
    if (installer_path / "install.py").exists():
        import installer.install as install_module
        install_module.main()
    else:
        print("Installer not found. Please run from the god-skill-suite repository directory.")
        sys.exit(1)


if __name__ == "__main__":
    main()
