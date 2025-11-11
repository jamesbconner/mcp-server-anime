#!/usr/bin/env python3
"""
Package validation script for mcp-server-anime.

This script validates the package configuration and build artifacts.
"""

import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path


def check_pyproject_toml() -> bool:
    """Validate pyproject.toml configuration."""
    print("Checking pyproject.toml...")

    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            print("✗ Cannot import TOML parser")
            return False

    try:
        with open("pyproject.toml", "rb") as f:
            config = tomllib.load(f)

        # Check required fields
        poetry_config = config.get("tool", {}).get("poetry", {})
        required_fields = ["name", "version", "description", "authors", "license"]

        for field in required_fields:
            if field not in poetry_config:
                print(f"✗ Missing required field: {field}")
                return False

        # Check entry points
        scripts = poetry_config.get("scripts", {})
        if "mcp-server-anime" not in scripts:
            print("✗ Missing entry point: mcp-server-anime")
            return False

        print("✓ pyproject.toml validation passed")
        return True

    except Exception as e:
        print(f"✗ pyproject.toml validation failed: {e}")
        return False


def check_required_files() -> bool:
    """Check that all required files exist."""
    print("Checking required files...")

    required_files = [
        "README.md",
        "LICENSE",
        "CHANGELOG.md",
        "pyproject.toml",
        "src/mcp_server_anime/__init__.py",
        "src/mcp_server_anime/server.py",
    ]

    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        print("✗ Missing required files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False

    print("✓ All required files present")
    return True


def check_package_structure() -> bool:
    """Validate package structure."""
    print("Checking package structure...")

    src_dir = Path("src/mcp_server_anime")
    if not src_dir.exists():
        print("✗ Source directory not found")
        return False

    # Check for __init__.py
    if not (src_dir / "__init__.py").exists():
        print("✗ Missing __init__.py in package")
        return False

    # Check for main modules
    expected_modules = [
        "server.py",
        "config.py",
        "models.py",
        "tools.py",
        "anidb_service.py",
    ]

    missing_modules = []
    for module in expected_modules:
        if not (src_dir / module).exists():
            missing_modules.append(module)

    if missing_modules:
        print("✗ Missing expected modules:")
        for module in missing_modules:
            print(f"  - {module}")
        return False

    print("✓ Package structure validation passed")
    return True


def check_build_artifacts() -> bool:
    """Check build artifacts if they exist."""
    print("Checking build artifacts...")

    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("INFO: No dist directory found (run 'poetry build' first)")
        return True

    # Look for wheel and sdist
    wheels = list(dist_dir.glob("*.whl"))
    sdists = list(dist_dir.glob("*.tar.gz"))

    if not wheels:
        print("⚠ No wheel files found")
    else:
        print(f"✓ Found {len(wheels)} wheel file(s)")

        # Check wheel contents
        for wheel in wheels:
            try:
                with zipfile.ZipFile(wheel, "r") as zf:
                    files = zf.namelist()
                    if not any(f.startswith("mcp_server_anime/") for f in files):
                        print(f"✗ Wheel {wheel.name} missing package files")
                        return False
                    print(f"✓ Wheel {wheel.name} contains package files")
            except Exception as e:
                print(f"✗ Error reading wheel {wheel.name}: {e}")
                return False

    if not sdists:
        print("⚠ No source distribution files found")
    else:
        print(f"✓ Found {len(sdists)} source distribution file(s)")

        # Check sdist contents
        for sdist in sdists:
            try:
                with tarfile.open(sdist, "r:gz") as tf:
                    files = tf.getnames()
                    if not any("src/mcp_server_anime/" in f for f in files):
                        print(f"✗ Sdist {sdist.name} missing source files")
                        return False
                    print(f"✓ Sdist {sdist.name} contains source files")
            except Exception as e:
                print(f"✗ Error reading sdist {sdist.name}: {e}")
                return False

    return True


def check_poetry_lock() -> bool:
    """Check poetry.lock file."""
    print("Checking poetry.lock...")

    if not Path("poetry.lock").exists():
        print("⚠ poetry.lock not found (run 'poetry lock' to create)")
        return True

    try:
        # Try to validate lock file
        result = subprocess.run(
            ["poetry", "check", "--lock"], capture_output=True, text=True
        )

        if result.returncode == 0:
            print("✓ poetry.lock is valid")
            return True
        else:
            print(f"✗ poetry.lock validation failed: {result.stderr}")
            return False

    except FileNotFoundError:
        print("⚠ Poetry not found, skipping lock file validation")
        return True
    except Exception as e:
        print(f"✗ Error validating poetry.lock: {e}")
        return False


def main():
    """Main validation function."""
    print("MCP Server Anime - Package Validation")
    print("=" * 40)

    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("Error: pyproject.toml not found. Please run from project root.")
        return 1

    validation_checks = [
        ("pyproject.toml configuration", check_pyproject_toml),
        ("Required files", check_required_files),
        ("Package structure", check_package_structure),
        ("Poetry lock file", check_poetry_lock),
        ("Build artifacts", check_build_artifacts),
    ]

    failed_checks = []

    for description, check_func in validation_checks:
        print(f"\n{description}:")
        print("-" * len(description))

        try:
            success = check_func()
            if not success:
                failed_checks.append(description)
        except Exception as e:
            print(f"✗ Validation error: {e}")
            failed_checks.append(description)

    # Summary
    print("\nValidation Summary:")
    print("=" * 20)

    if not failed_checks:
        print("✓ All validation checks passed!")
        print("\nPackage is ready for distribution.")
        return 0
    else:
        print("✗ Some validation checks failed:")
        for check in failed_checks:
            print(f"  - {check}")
        print("\nPlease resolve the issues before distribution.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
