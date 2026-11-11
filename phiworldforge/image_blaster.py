"""Import locally generated Image-Blaster world outputs.

No provider API calls, network requests, or remote asset URL downloads.
Reference source: https://github.com/neilsonnn/image-blaster
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from .core import SCHEMA, validate_world

WORLD_RESPONSE = re.compile(r"^([0-9]+)-world\.json$")
QUALITY_ORDER = ("full_res", "500k", "150k", "100k")
SLUG = re.compile(r"^[a-z][a-z0-9-]{0,63}$")


def _local_file(project: Path, relative: Path) -> Path | None:
    """Resolve only regular files contained by the project, never remote URLs."""
    candidate = project / relative
    if not candidate.exists():
        return None
    resolved = candidate.resolve()
    if not resolved.is_relative_to(project.resolve()) or not resolved.is_file():
        raise ValueError("unsafe project asset path: " + relative.as_posix())
    return resolved


def _json_file(path: Path) -> dict:
    if path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("oversized metadata file: " + path.name)
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("invalid JSON in " + path.name) from exc
    if not isinstance(content, dict):
        raise ValueError(path.name + " must contain a JSON object")
    return content


def import_project(
    project: Path, output: Path, *,
    world_index: int | None = None, quality: str = "auto",
) -> dict:
    """Convert a local worlds/<slug> project into a portable scene.

    Never downloads URLs from provider metadata. Dynamic-object model placement
    and real splat rendering require future integration work.
    """
    project = project.resolve()
    if not project.is_dir():
        raise ValueError("Image-Blaster project directory missing")
    project_meta_file = _local_file(project, Path("project.json"))
    if not project_meta_file:
        raise ValueError("project.json missing in Image-Blaster project")
    metadata = _json_file(project_meta_file)
    slug = metadata.get("slug") or project.name
    if not isinstance(slug, str) or not SLUG.fullmatch(slug):
        raise ValueError("project slug is invalid")
    title = metadata.get("display_name") or slug.replace("-", " ").title()
    if not isinstance(title, str) or not title.strip() or len(title) > 120:
        raise ValueError("project display name invalid")

    if output.is_symlink() or (output.exists() and (not output.is_dir() or any(output.iterdir()))):
        raise ValueError("output must be a new or empty directory; nothing overwritten")
    if quality != "auto" and quality not in QUALITY_ORDER:
        raise ValueError("quality must be auto, full_res, 500k, 150k, or 100k")
    if world_index is not None and world_index < 0:
        raise ValueError("world_index must be nonnegative")

    world_dir = project / "output" / "world"
    if not world_dir.is_dir():
        raise ValueError("output/world directory missing")
    generations = []
    for entry in world_dir.iterdir():
        match = WORLD_RESPONSE.fullmatch(entry.name)
        if match:
            if not _local_file(project, Path("output/world") / entry.name):
                continue
            generations.append(int(match.group(1)))
    if not generations:
        raise ValueError("no indexed N-world.json files found")
    generation = max(generations) if world_index is None else world_index
    response_path = _local_file(project, Path("output/world") / f"{generation}-world.json")
    if not response_path:
        raise ValueError(f"generation {generation} does not have a local world response")
    response = _json_file(response_path)

    # Upstream downloads a collider mesh and each available SPZ resolution
    # alongside the JSON response, using these indexed local file names.
    mesh = _local_file(project, Path("output/world") / f"{generation}-world.glb")
    found_splats = {
        key: asset
        for key in QUALITY_ORDER
        if (asset := _local_file(project, Path("output/world") / f"{generation}-world-{key}.spz"))
    }
    if quality == "auto":
        selected_quality = next(iter(found_splats), None)
    else:
        selected_quality = quality if quality in found_splats else None
        if selected_quality is None:
            raise ValueError(f"requested SPZ quality {quality} is not downloaded locally")
    splat = found_splats.get(selected_quality) if selected_quality else None
    if mesh is None and splat is None:
        raise ValueError("no local collider GLB or selected SPZ file found; run upstream local-asset repair first")

    # The upstream SFX job writes to output/sfx. Select the newest indexed
    # ambient file deterministically; importing object-specific effects and
    # positioned object instances are separate work.
    audio_dir = project / "output" / "sfx"
    ambient = None
    if audio_dir.is_dir():
        choices = []
        for entry in audio_dir.iterdir():
            if entry.suffix.lower() not in {".mp3", ".wav", ".ogg"} or entry.name.startswith("."):
                continue
            local = _local_file(project, Path("output/sfx") / entry.name)
            if local:
                match = re.match(r"^(\d+)-", entry.name)
                choices.append((int(match.group(1)) if match else -1, entry.name, local))
        if choices:
            ambient = sorted(choices)[-1][2]

    docs = response.get("assets", {})
    splat_semantics = {}
    if isinstance(docs, dict) and isinstance(docs.get("splats"), dict):
        splat_semantics = docs["splats"].get("semantics_metadata") or {}
    if not isinstance(splat_semantics, dict):
        splat_semantics = {}

    entity_list = []
    if mesh:
        entity_list.append({
            "id": "environment-collider",
            "kind": "mesh",
            "role": "collider-preview",
            "position": [0, 0, 0],
            "scale": [1, 1, 1],
            "collidable": False,
            "asset": "assets/" + mesh.name,
        })

    manifest = {
        "schema": SCHEMA, "id": slug, "title": title,
        "units": "meters", "up_axis": "Y", "spawn": [0, 1.7, 5],
        "entities": entity_list,
        "source": {
            "type": "image-blaster",
            "project_slug": slug,
            "world_index": generation,
            "splat_quality": selected_quality,
            "splat_semantics": splat_semantics,
            "notes": "Existing local exports only. World transform, splat and object placement not yet calibrated.",
        },
    }
    if splat:
        manifest["environment_splat"] = "assets/" + splat.name
    if ambient:
        manifest["ambient_audio"] = "assets/" + ambient.name

    output.mkdir(parents=True, exist_ok=True)
    (output / "assets").mkdir(exist_ok=True)
    for source in (mesh, splat, ambient):
        if source is not None:
            shutil.copyfile(source, output / "assets" / source.name)
    manifest_path = output / "world.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    errors = validate_world(output)
    if errors:
        raise ValueError("import produced invalid scene: " + "; ".join(errors))
    return {
        "world": str(manifest_path),
        "world_index": generation,
        "splat_quality": selected_quality,
        "assets_copied": sum(x is not None for x in (mesh, splat, ambient)),
        "has_collider": mesh is not None,
        "has_splat": splat is not None,
        "has_audio": ambient is not None,
    }
