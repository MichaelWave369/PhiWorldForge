# External integration boundaries

## Image-Blaster

Reference: https://github.com/neilsonnn/image-blaster

Upstream's documented outputs are GLB/OBJ dynamic objects, SPZ static environments and MP3 audio. Genesis copies pre-existing files into a portable scene. It does not vendor Image-Blaster code, invoke World Labs/FAL/ElevenLabs, manage keys or claim automatic layout/collision.

To make this a full provider, inspect upstream file paths and parameters, translate unit/axis/pivot conventions, verify actual scene output, store provenance and obey external API pricing/licensing.

## Unreal Engine

An Unreal importer and MCP automation layer are **planned**. A working importer must translate the portable world manifest into assets, actor placement, collision proxies and scene validation. Gaussian splats may require an engine plugin or dedicated renderer. Epic experimental editor/browser features should not be assumed stable.

## PhiOS and Quest

Three.js currently renders the handcrafted room on supported WebGL browsers. The WebXR button is experimental and has not been benchmarked on Quest 3. Production locomotion, collision and frame budget checks are future work.

## Safety and transparency

Do not commit provider secrets. Treat generated 3D/audio files as untrusted inputs. Restrict paths, budget asset sizes and require human approval for any agent-initiated external writes. The repo's MIT license does not grant rights over third-party generated assets.
