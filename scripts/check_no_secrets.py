"""Basic repository secret scanner for local governance checks."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    ".venv",
    "venv",
}
SKIP_FILES = {".env.example"}
SKIP_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".pyc"}
PATTERNS = {
    "openai_api_key": re.compile(r"OPENAI_API_KEY\s*=\s*[^\r\n\s\"']+"),
    "generic_secret_assignment": re.compile(
        r"(API_KEY|SECRET_KEY|ACCESS_TOKEN)\s*=\s*[^\r\n\s\"']+"
    ),
    "openai_key_value": re.compile(r"sk-[A-Za-z0-9_-]{10,}"),
}


def should_skip(path: Path) -> bool:
    return (
        any(part in SKIP_DIRS for part in path.parts)
        or path.name in SKIP_FILES
        or path.suffix in SKIP_SUFFIXES
    )


def scan_file(path: Path) -> list[str]:
    findings: list[str] = []
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return findings

    for name, pattern in PATTERNS.items():
        if pattern.search(content):
            findings.append(f"{path.relative_to(REPO_ROOT)} matched {name}")
    return findings


def main() -> int:
    findings: list[str] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or should_skip(path):
            continue
        findings.extend(scan_file(path))

    if findings:
        print("Potential secrets found:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("No obvious secrets found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
