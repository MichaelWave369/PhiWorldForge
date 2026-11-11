"""Build a static scene gallery for use with plain HTTP servers."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .core import read_world, validate_world


def build_catalog(worlds: Path, output: Path, check: bool = False) -> dict:
    if not worlds.is_dir():
        raise ValueError("world directory does not exist: " + str(worlds))
    entries = []
    seen = set()
    for folder in sorted(worlds.iterdir()):
        if not folder.is_dir() or folder.is_symlink() or not (folder / "world.json").exists():
            continue
        errors = validate_world(folder)
        if errors:
            raise ValueError(folder.name + ": " + "; ".join(errors))
        scene = read_world(folder)
        if scene["id"] in seen:
            raise ValueError("duplicate scene id: " + scene["id"])
        seen.add(scene["id"])
        relpath = os.path.relpath(folder / "world.json", output.parent).replace(os.sep, "/")
        entries.append({"id": scene["id"], "title": scene["title"], "manifest": relpath})
    if not entries:
        raise ValueError("no valid scene folders found")
    catalog = {"schema": "phiworldforge.catalog/0.1", "worlds": entries}
    expected = json.dumps(catalog, indent=2) + "\n"
    if check:
        if not output.is_file() or output.read_text(encoding="utf-8") != expected:
            raise ValueError("catalog is stale; run phiworldforge catalog")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(expected, encoding="utf-8")
    return catalog
