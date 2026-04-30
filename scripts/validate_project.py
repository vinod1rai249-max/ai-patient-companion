"""Validate basic repository governance expectations."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_FOLDERS = ["backend", "docs", "tests", "scripts"]
REQUIRED_FILES = [
    ".env.example",
    "README.md",
    "CLAUDE.md",
    "docs/requirements_traceability.md",
    "docs/definition_of_done.md",
    "docs/adr/ADR-001-llm-provider-strategy.md",
    "scripts/check_no_secrets.py",
    "scripts/validate_project.py",
]
REQUIRED_TESTS = ["tests/test_safety.py"]


def check_required_paths() -> list[str]:
    errors: list[str] = []

    for folder in REQUIRED_FOLDERS:
        if not (REPO_ROOT / folder).is_dir():
            errors.append(f"Missing required folder: {folder}")

    for file_name in REQUIRED_FILES:
        if not (REPO_ROOT / file_name).is_file():
            errors.append(f"Missing required file: {file_name}")

    for test_file in REQUIRED_TESTS:
        if not (REPO_ROOT / test_file).is_file():
            errors.append(f"Missing safety test: {test_file}")

    return errors


def check_env_not_committed() -> list[str]:
    env_path = REPO_ROOT / ".env"
    errors: list[str] = []

    if env_path.exists():
        errors.append(".env exists in the repository root; keep secrets out of committed files.")

    try:
        result = subprocess.run(
            ["git", "ls-files", ".env"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return errors

    if result.returncode == 0 and result.stdout.strip():
        errors.append(".env appears to be tracked by git.")

    return errors


def main() -> int:
    errors = check_required_paths()
    errors.extend(check_env_not_committed())

    if errors:
        print("Project validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Project validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
