#!/usr/bin/env python3
"""Package the repository's skills as upload-ready zip archives.

claude.ai and the Skills API accept a zip whose single top-level folder is
named after the skill's frontmatter ``name`` and contains ``SKILL.md``. The
repository folders do not use those names (``Humanizer/`` holds ``humanizer``;
``aiproofing/`` holds ``aiproofing-text``), so each skill is staged under its
declared name before zipping. Archives are deterministic: file order is sorted
and timestamps are fixed, so the same tree always produces the same bytes.

Standard library only. No network access.

Usage:
    python scripts/package_skills.py                     # dist/humanizer.zip, dist/aiproofing-text.zip
    python scripts/package_skills.py --output-dir build  # choose another output folder
    python scripts/package_skills.py --skill humanizer   # package one skill
    python scripts/package_skills.py --check             # validate only, write nothing
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import re
import sys
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

# Frontmatter keys permitted by the Agent Skills specification. Any other
# top-level key is rejected by the upload validators.
ALLOWED_FRONTMATTER_KEYS = {
    "name", "description", "license", "allowed-tools", "metadata", "compatibility",
}
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NAME_MAX_LENGTH = 64
DESCRIPTION_MAX_LENGTH = 1024
RESERVED_NAME_WORDS = ("anthropic", "claude")

# Directories and files never shipped inside a skill archive.
EXCLUDED_DIR_NAMES = {"__pycache__", "node_modules", ".git"}
EXCLUDED_FILE_GLOBS = ("*.pyc", ".DS_Store")

# Fixed timestamp for deterministic archives (the zip epoch).
FIXED_DATE_TIME = (1980, 1, 1, 0, 0, 0)

# Source folder and optional allow-list of files, keyed by the skill's name.
# ``include`` of None means "everything under the source folder".
SKILLS: Dict[str, Dict[str, object]] = {
    "humanizer": {
        "source": "Humanizer",
        "include": ("SKILL.md", "README.md"),
    },
    "aiproofing-text": {
        "source": "aiproofing",
        "include": None,
    },
}


class PackagingError(Exception):
    """Raised when a skill cannot be packaged as a valid upload."""


def parse_frontmatter(skill_md: Path) -> Dict[str, str]:
    """Return the top-level frontmatter keys and their raw scalar values.

    This is a deliberately small parser: it recognises top-level ``key: value``
    lines, block scalars introduced with ``|`` or ``>``, and nested blocks
    (indented lines), which is all the skill frontmatter uses. It exists so the
    packager stays dependency-free.
    """
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise PackagingError(f"{skill_md}: SKILL.md must start with YAML frontmatter")
    end = text.find("\n---", 4)
    if end == -1:
        raise PackagingError(f"{skill_md}: frontmatter is not closed with ---")
    lines = text[4:end].splitlines()

    fields: Dict[str, str] = {}
    current: Optional[str] = None
    block: List[str] = []
    for line in lines:
        if line and not line[0].isspace():
            if current is not None:
                fields[current] = "\n".join(block).strip()
            if ":" not in line:
                raise PackagingError(f"{skill_md}: malformed frontmatter line {line!r}")
            key, _, value = line.partition(":")
            current = key.strip()
            value = value.strip()
            block = [] if value in ("|", ">", "|-", ">-", "") else [value]
        elif current is not None:
            block.append(line.strip())
    if current is not None:
        fields[current] = "\n".join(block).strip()
    return fields


def validate_frontmatter(skill_md: Path, expected_name: str) -> Tuple[str, str]:
    fields = parse_frontmatter(skill_md)
    unexpected = sorted(set(fields) - ALLOWED_FRONTMATTER_KEYS)
    if unexpected:
        raise PackagingError(
            f"{skill_md}: unexpected frontmatter key(s) {', '.join(unexpected)}; "
            f"allowed keys are {', '.join(sorted(ALLOWED_FRONTMATTER_KEYS))}"
        )
    name = fields.get("name", "").strip().strip("'\"")
    description = fields.get("description", "").strip()
    if not name:
        raise PackagingError(f"{skill_md}: frontmatter is missing name")
    if name != expected_name:
        raise PackagingError(f"{skill_md}: frontmatter name {name!r} != packaged name {expected_name!r}")
    if len(name) > NAME_MAX_LENGTH or not NAME_PATTERN.match(name):
        raise PackagingError(f"{skill_md}: name {name!r} must be kebab-case and at most {NAME_MAX_LENGTH} characters")
    if any(word in name for word in RESERVED_NAME_WORDS):
        raise PackagingError(f"{skill_md}: name {name!r} contains a reserved word")
    if not description:
        raise PackagingError(f"{skill_md}: frontmatter is missing description")
    if len(description) > DESCRIPTION_MAX_LENGTH:
        raise PackagingError(f"{skill_md}: description is {len(description)} characters; maximum is {DESCRIPTION_MAX_LENGTH}")
    if "<" in description or ">" in description:
        raise PackagingError(f"{skill_md}: description must not contain angle brackets")
    return name, description


def _excluded(relative: Path) -> bool:
    if any(part in EXCLUDED_DIR_NAMES for part in relative.parts[:-1]):
        return True
    return any(fnmatch.fnmatch(relative.name, pattern) for pattern in EXCLUDED_FILE_GLOBS)


def collect_files(source_dir: Path, include: Optional[Iterable[str]]) -> List[Tuple[Path, Path]]:
    """Return (absolute path, archive-relative path) pairs in sorted order."""
    if not source_dir.is_dir():
        raise PackagingError(f"skill source folder does not exist: {source_dir}")
    if include is not None:
        candidates = [source_dir / name for name in include]
        missing = [str(path) for path in candidates if not path.is_file()]
        if missing:
            raise PackagingError(f"missing skill file(s): {', '.join(missing)}")
    else:
        candidates = [path for path in source_dir.rglob("*") if path.is_file()]
    pairs = []
    for path in candidates:
        relative = path.relative_to(source_dir)
        if _excluded(relative):
            continue
        pairs.append((path, relative))
    pairs.sort(key=lambda item: item[1].as_posix())
    skill_md_count = sum(1 for _, relative in pairs if relative.name == "SKILL.md")
    if skill_md_count != 1 or Path("SKILL.md") not in {relative for _, relative in pairs}:
        raise PackagingError(f"{source_dir}: a skill must contain exactly one SKILL.md at its root")
    return pairs


def write_archive(name: str, pairs: List[Tuple[Path, Path]], destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, relative in pairs:
            info = zipfile.ZipInfo(f"{name}/{relative.as_posix()}", date_time=FIXED_DATE_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return hashlib.sha256(destination.read_bytes()).hexdigest()


def package_skill(name: str, output_dir: Path, check_only: bool = False) -> Optional[Path]:
    spec = SKILLS[name]
    source_dir = REPOSITORY_ROOT / str(spec["source"])
    pairs = collect_files(source_dir, spec["include"])  # type: ignore[arg-type]
    validate_frontmatter(source_dir / "SKILL.md", name)
    total_bytes = sum(path.stat().st_size for path, _ in pairs)
    if check_only:
        print(f"{name}: valid ({len(pairs)} files, {total_bytes} bytes)")
        return None
    destination = output_dir / f"{name}.zip"
    digest = write_archive(name, pairs, destination)
    print(f"{name}: wrote {destination} ({len(pairs)} files, {total_bytes} bytes uncompressed, sha256 {digest})")
    return destination


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Package the repository's skills as claude.ai upload archives.")
    parser.add_argument("--output-dir", default=str(REPOSITORY_ROOT / "dist"), help="folder for the zip archives (default: dist/)")
    parser.add_argument("--skill", choices=sorted(SKILLS), action="append", help="package only this skill (repeatable)")
    parser.add_argument("--check", action="store_true", help="validate frontmatter and layout without writing archives")
    args = parser.parse_args(argv)
    names = args.skill or sorted(SKILLS)
    try:
        for name in names:
            package_skill(name, Path(args.output_dir), check_only=args.check)
    except PackagingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
