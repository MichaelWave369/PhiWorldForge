# ΦWorldForge

**From image assets to portable explorable worlds.** Local-first scene tools designed for Three.js/WebXR today and future Unreal/PhiOS integrations.

> **Genesis v0.1 is a foundation, not a finished AI game generator.** It validates scenes, ingests already-created 3D/audio exports, packs deterministic archives and displays an original procedural demo. AI generation APIs, Unreal MCP, SPZ rendering and production VR collisions are not implemented.

## Quick start

Requires Python 3.11+; the browser viewer loads pinned Three.js ES modules from a CDN and needs an internet connection.

```bash
git clone https://github.com/MichaelWave369/PhiWorldForge.git
cd PhiWorldForge
python -m unittest discover -s tests -v
python -m phiworldforge validate examples/arclight-room
python -m phiworldforge pack examples/arclight-room dist/arclight-genesis.zip
python -m http.server 8000
```

Open **http://localhost:8000/viewer/**. Drag to orbit, scroll to zoom, use WASD and Q/E to translate the camera. If the browser and secure context support immersive VR, an experimental Enter VR button is provided; Quest 3 performance and interaction have not yet been verified.

## Import Image-Blaster-compatible exports

The upstream [image-blaster](https://github.com/neilsonnn/image-blaster) describes GLB/OBJ dynamic meshes, SPZ environment splats and MP3 audio. Export generation is external to ΦWorldForge; **no external API is called here**.

```bash
python -m phiworldforge ingest --output examples/imported-room --title 'Imported Room' --mesh /path/to/object.glb --splat /path/to/environment.spz --audio /path/to/ambience.mp3
python -m phiworldforge validate examples/imported-room
python -m phiworldforge pack examples/imported-room dist/imported-room.zip
```

The importer copies local assets into a new, empty world folder. It refuses to overwrite an existing project. GLB and OBJ may be rendered by the viewer loader **once a scene is explicitly selected/configured**; Genesis currently displays the ARCLight demo by default. SPZ is packaged but not displayed, while audio playback requires a user gesture.

## What works

- Portable, versioned JSON scene format with meter-scale Y-up coordinates and transform declarations.
- Strict relative file validation, duplicate-ID checks, finite numeric data and path-traversal/symlink escape checks.
- Reproducible ZIP export containing only the manifest and explicitly referenced local files.
- A browser-rendered ARCLight room with procedural lighting, space backdrop, orbital navigation and experimental WebXR entry.
- An existing-asset importer, eight standard-library tests and GitHub Actions validation.

## What's next

- Engine-specific mesh and splat registration; transforms, collision proxies and asset budgets.
- Image-Blaster provider orchestration after verifying its actual output interfaces and service terms.
- Unreal asset/actor importer and optional MCP automation, with exact version and permission requirements.
- PhiStream/Agentora job specs, provenance, approvals and per-platform QA.
- Quest 3 and browser performance benchmarks, locomotion, robust error recovery and tests.

See [scene format](docs/SCENE_FORMAT.md), [architecture](docs/ARCHITECTURE.md) and [integrations](docs/INTEGRATIONS.md).

MIT © 2026 Michael Hughes. This independent project is not affiliated with Epic Games or the Image-Blaster developers. External service terms, content rights and API charges remain separate.
