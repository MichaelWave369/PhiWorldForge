"""Engine-neutral scene manifest, local export ingestion, reproducible ZIP."""
from __future__ import annotations
import json
import math
import re
import shutil
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

SCHEMA = "phiworldforge.scene/0.1"
SLUG = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")

def vec3(value, positive=False):
    return isinstance(value, list) and len(value) == 3 and all(
        isinstance(x, (int, float)) and not isinstance(x, bool)
        and math.isfinite(x) and (not positive or x > 0) for x in value
    )

def read_world(root: Path) -> dict:
    path = root / "world.json"
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("world.json escapes world directory")
    if not path.is_file():
        raise ValueError("world.json not found")
    if path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("world.json exceeds 2 MiB")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as error:
        raise ValueError("invalid world.json") from error
    if not isinstance(data, dict):
        raise ValueError("world.json must be an object")
    return data

def asset_error(root: Path, path, extensions: set[str]):
    if not isinstance(path, str) or not path or ":" in path or "\\" in path:
        return "must be a relative POSIX path"
    pure = PurePosixPath(path)
    if pure.is_absolute() or not path.startswith("assets/") or any(p in (".", "..") for p in pure.parts):
        return "must stay within assets/ without traversal"
    if pure.suffix.lower() not in extensions:
        return "unsupported extension"
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        return "symlink escapes scene directory"
    if not resolved.is_file():
        return "file not found"
    return None

def asset_paths(data: dict) -> list[str]:
    files = []
    for entity in data.get("entities", []):
        if isinstance(entity, dict) and entity.get("kind") == "mesh" and isinstance(entity.get("asset"), str):
            files.append(entity["asset"])
    for field in ("environment_splat", "ambient_audio"):
        if isinstance(data.get(field), str):
            files.append(data[field])
    return sorted(set(files))

def validate_world(root: Path) -> list[str]:
    try:
        data = read_world(root)
    except (ValueError, OSError) as error:
        return [str(error)]
    errors = []
    if data.get("schema") != SCHEMA:
        errors.append("unexpected schema")
    if not isinstance(data.get("id"), str) or not SLUG.fullmatch(data["id"]):
        errors.append("id must be a lowercase slug")
    title = data.get("title")
    if not isinstance(title, str) or not title.strip() or len(title) > 120:
        errors.append("title must have 1-120 characters")
    if data.get("units") != "meters" or data.get("up_axis") != "Y":
        errors.append("units must be meters and up_axis must be Y")
    if not vec3(data.get("spawn")):
        errors.append("spawn must be a finite vec3")
    entities = data.get("entities")
    if not isinstance(entities, list):
        errors.append("entities must be a list")
        entities = []
    if len(entities) > 4096:
        errors.append("too many entities")
    seen = set()
    for i, item in enumerate(entities):
        field = "entities[" + str(i) + "]"
        if not isinstance(item, dict):
            errors.append(field + " must be an object")
            continue
        eid = item.get("id")
        if not isinstance(eid, str) or not SLUG.fullmatch(eid):
            errors.append(field + ".id invalid")
        elif eid in seen:
            errors.append(field + ".id duplicated")
        else:
            seen.add(eid)
        kind = item.get("kind")
        if kind not in ("box", "mesh"):
            errors.append(field + ".kind must be box or mesh")
            continue
        if not vec3(item.get("position")):
            errors.append(field + ".position invalid")
        if "rotation" in item and not vec3(item["rotation"]):
            errors.append(field + ".rotation invalid")
        if "collidable" in item and not isinstance(item["collidable"], bool):
            errors.append(field + ".collidable invalid")
        if kind == "box":
            if not vec3(item.get("size"), positive=True):
                errors.append(field + ".size invalid")
            if not isinstance(item.get("color"), str) or not COLOR.fullmatch(item["color"]):
                errors.append(field + ".color invalid")
            opacity = item.get("opacity", 1)
            if not isinstance(opacity, (int, float)) or isinstance(opacity, bool) or not math.isfinite(opacity) or not 0 <= opacity <= 1:
                errors.append(field + ".opacity invalid")
        else:
            if "scale" in item and not vec3(item["scale"], positive=True):
                errors.append(field + ".scale invalid")
            issue = asset_error(root, item.get("asset"), {".glb", ".obj"})
            if issue:
                errors.append(field + ".asset " + issue)
    for field, extensions in (("environment_splat", {".spz"}), ("ambient_audio", {".mp3", ".wav", ".ogg"})):
        if field in data:
            issue = asset_error(root, data[field], extensions)
            if issue:
                errors.append(field + " " + issue)
    return errors

def pack_world(root: Path, destination: Path) -> list[str]:
    errors = validate_world(root)
    if errors:
        raise ValueError("; ".join(errors))
    if destination.resolve().is_relative_to(root.resolve()):
        raise ValueError("archive destination must be outside world folder")
    paths = ["world.json", *asset_paths(read_world(root))]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, "w") as archive:
        for name in paths:
            info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with (root / name).open("rb") as source, archive.open(info, "w") as target:
                shutil.copyfileobj(source, target)
    return paths

def ingest_exports(output: Path, title: str, mesh: Path | None = None, splat: Path | None = None, audio: Path | None = None) -> Path:
    inputs = [(k, p) for k, p in (("mesh", mesh), ("splat", splat), ("audio", audio)) if p is not None]
    if not inputs:
        raise ValueError("provide at least one asset")
    if not title.strip() or len(title) > 120:
        raise ValueError("title must have 1-120 characters")
    if output.is_symlink() or (output.exists() and (not output.is_dir() or any(output.iterdir()))):
        raise ValueError("output must be a new or empty directory")
    allowed = {"mesh": {".glb", ".obj"}, "splat": {".spz"}, "audio": {".mp3", ".wav", ".ogg"}}
    names = set()
    for kind, source in inputs:
        if not source.is_file() or source.suffix.lower() not in allowed[kind]:
            raise ValueError(kind + " input missing or unsupported")
        if source.name in names:
            raise ValueError("duplicate input asset names")
        names.add(source.name)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:58].rstrip("-")
    identifier = slug if slug and slug[0].isalpha() else "world-" + slug
    data = {
        "schema": SCHEMA, "id": identifier, "title": title, "units": "meters",
        "up_axis": "Y", "spawn": [0, 1.7, 5], "entities": [],
        "source": {"type": "local-import", "notes": "No remote generation performed"},
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "assets").mkdir(exist_ok=True)
    for kind, source in inputs:
        shutil.copyfile(source, output / "assets" / source.name)
        rel = "assets/" + source.name
        if kind == "mesh":
            data["entities"].append({
                "id": "imported-mesh", "kind": "mesh", "asset": rel,
                "position": [0, 0, 0], "scale": [1, 1, 1], "collidable": False
            })
        elif kind == "splat":
            data["environment_splat"] = rel
        else:
            data["ambient_audio"] = rel
    path = output / "world.json"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path
