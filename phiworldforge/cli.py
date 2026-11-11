"""PhiWorldForge CLI."""
import argparse
import sys
from pathlib import Path
from .core import ingest_exports, pack_world, validate_world
from .catalog import build_catalog
from .image_blaster import import_project

def main(argv=None):
    parser = argparse.ArgumentParser(prog="phiworldforge", description="Portable world tools")
    sub = parser.add_subparsers(dest="action", required=True)
    check = sub.add_parser("validate")
    check.add_argument("world", type=Path)
    pack = sub.add_parser("pack")
    pack.add_argument("world", type=Path)
    pack.add_argument("archive", type=Path)
    ingest = sub.add_parser("ingest")
    ingest.add_argument("--output", type=Path, required=True)
    ingest.add_argument("--title", required=True)
    ingest.add_argument("--mesh", type=Path)
    ingest.add_argument("--splat", type=Path)
    ingest.add_argument("--audio", type=Path)
    ib = sub.add_parser("import-image-blaster", help="convert local Image-Blaster worlds/<slug> exports")
    ib.add_argument("--project", type=Path, required=True)
    ib.add_argument("--output", type=Path, required=True)
    ib.add_argument("--world-index", type=int)
    ib.add_argument("--quality", default="auto", choices=["auto", "full_res", "500k", "150k", "100k"])
    catalog = sub.add_parser("catalog", help="build or verify browser gallery index")
    catalog.add_argument("--worlds", type=Path, default=Path("examples"))
    catalog.add_argument("--output", type=Path, default=Path("viewer/worlds.json"))
    catalog.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.action == "validate":
            errors = validate_world(args.world)
            for error in errors:
                print("ERROR: " + error, file=sys.stderr)
            if errors:
                return 1
            print("VALID:", args.world)
        elif args.action == "pack":
            paths = pack_world(args.world, args.archive)
            print("PACKED:", args.archive, "files:", len(paths))
        elif args.action == "import-image-blaster":
            summary = import_project(args.project, args.output, world_index=args.world_index, quality=args.quality)
            print("IMPORTED LOCAL IMAGE-BLASTER:", summary)
        elif args.action == "catalog":
            gallery = build_catalog(args.worlds, args.output, check=args.check)
            print("GALLERY:", len(gallery["worlds"]), "worlds")
        else:
            path = ingest_exports(args.output, args.title, args.mesh, args.splat, args.audio)
            print("IMPORTED:", path)
    except (ValueError, OSError) as error:
        print("ERROR:", error, file=sys.stderr)
        return 1
    return 0
