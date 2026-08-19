#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 ProKanban.org
# SPDX-License-Identifier: MIT

"""Build byte-for-byte reproducible Professional Kanban skill archives."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "professional-kanban"
ARCHIVE_ROOT = "professional-kanban"
ARCHIVE_NAMES = ("professional-kanban.skill", "professional-kanban.zip")
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
EXCLUDED_NAMES = {".DS_Store", "__pycache__"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".swp", ".tmp"}
TEXT_SUFFIXES = {".csv", ".json", ".md", ".py", ".txt", ".yaml", ".yml"}
TEXT_NAMES = {"LICENSE"}


def _source_files(source: Path) -> list[Path]:
    """Return canonical distributable files in stable POSIX-path order."""
    files = []
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        if any(part in EXCLUDED_NAMES for part in relative.parts):
            continue
        if path.name.startswith("._") or path.suffix in EXCLUDED_SUFFIXES:
            continue
        if path.is_symlink():
            raise ValueError("Release sources must not contain symlinks: %s" % relative)
        if path.is_file():
            files.append(path)
    return sorted(files, key=lambda path: path.relative_to(source).as_posix())


def _canonical_bytes(path: Path) -> bytes:
    """Return checkout-independent bytes for known text resources."""
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES or path.name in TEXT_NAMES:
        return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return data


def build_archive(source: Path, target: Path) -> str:
    """Build one deterministic archive and return its SHA-256 digest."""
    source = Path(source).resolve()
    target = Path(target).resolve()
    if not (source / "SKILL.md").is_file():
        raise ValueError("Skill source must contain SKILL.md: %s" % source)
    try:
        target.relative_to(source)
    except ValueError:
        pass
    else:
        raise ValueError("Release target must be outside the skill source: %s" % target)
    target.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(
        target,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in _source_files(source):
            relative = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo("%s/%s" % (ARCHIVE_ROOT, relative), ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(
                info,
                _canonical_bytes(path),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )

    return hashlib.sha256(target.read_bytes()).hexdigest()


def _manifest_version(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    if path.name == "marketplace.json":
        return str(data["plugins"][0]["version"])
    return str(data["version"])


def validate_release_version(version: str) -> str:
    """Require a semver tag to agree with every public version declaration."""
    normalized = version.removeprefix("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+", normalized):
        raise ValueError("release version must be vMAJOR.MINOR.PATCH")

    declared = {
        ".codex-plugin/plugin.json": _manifest_version(
            REPO_ROOT / ".codex-plugin" / "plugin.json"
        ),
        ".claude-plugin/plugin.json": _manifest_version(
            REPO_ROOT / ".claude-plugin" / "plugin.json"
        ),
        ".claude-plugin/marketplace.json": _manifest_version(
            REPO_ROOT / ".claude-plugin" / "marketplace.json"
        ),
    }
    skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r'^\s+version:\s*["\']?([^"\'\s]+)', skill_text, re.MULTILINE)
    declared["skills/professional-kanban/SKILL.md"] = match.group(1) if match else "missing"

    mismatches = [
        "%s declares %s" % (path, found)
        for path, found in declared.items()
        if found != normalized
    ]
    if mismatches:
        raise ValueError(
            "release %s does not match metadata: %s"
            % (normalized, "; ".join(mismatches))
        )
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if "## [%s]" % normalized not in changelog:
        raise ValueError("CHANGELOG.md has no [%s] release entry" % normalized)
    return normalized


def build_release(
    output_dir: Path = REPO_ROOT / "dist",
    source: Path = SKILL_ROOT,
    version: str | None = None,
) -> Path:
    """Build both release extensions and their stable checksum file."""
    if version is not None:
        validate_release_version(version)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    zip_path = output_dir / "professional-kanban.zip"
    build_archive(source, zip_path)
    skill_path = output_dir / "professional-kanban.skill"
    shutil.copyfile(zip_path, skill_path)

    checksums = []
    for name in ARCHIVE_NAMES:
        digest = hashlib.sha256((output_dir / name).read_bytes()).hexdigest()
        checksums.append("%s  %s" % (digest, name))
    (output_dir / "SHA256SUMS").write_text(
        "\n".join(checksums) + "\n", encoding="ascii", newline="\n"
    )
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "dist",
        help="artifact directory (default: dist)",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=SKILL_ROOT,
        help="canonical skill source directory",
    )
    parser.add_argument(
        "--version",
        help="validate vMAJOR.MINOR.PATCH against manifests and changelog",
    )
    args = parser.parse_args()
    try:
        output = build_release(args.output, args.source, args.version)
    except ValueError as exc:
        parser.error(str(exc))
    for name in (*ARCHIVE_NAMES, "SHA256SUMS"):
        print(output / name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
