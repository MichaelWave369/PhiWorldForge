"""PhiWorldForge CLI."""
import argparse
import sys
from pathlib import Path
from .core import ingest_exports, pack_world, validate_world

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
        else:
            path = ingest_exports(args.output, args.title, args.mesh, args.splat, args.audio)
            print("IMPORTED:", path)
    except (ValueError, OSError) as error:
        print("ERROR:", error, file=sys.stderr)
        return 1
    return 0
