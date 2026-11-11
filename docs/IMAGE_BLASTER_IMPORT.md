# Image-Blaster local project import contract

Based on the upstream `project-state.mjs`, `generate-world.mjs`, `WorldViewer.tsx`, `worldLoader.ts`, and its documented indexed-file layout.

| Existing upstream file | PhiWorldForge result |
| --- | --- |
| `project.json` | scene `id` and `title` |
| `output/world/N-world.json` | generation number and splat semantic metadata |
| `output/world/N-world.glb` | `collider-preview` mesh entity |
| `output/world/N-world-full_res.spz` | `environment_splat` (copy only) |
| `output/world/N-world-500k.spz` etc. | lower-resolution alternatives |
| `output/sfx/*.mp3`, `.wav`, `.ogg` | deterministically chosen local ambient audio |

Run:

```bash
python -m phiworldforge import-image-blaster --project /path/to/image-blaster/worlds/<slug> --output examples/<slug>
python -m phiworldforge catalog
python -m phiworldforge validate examples/<slug>
python -m http.server 8000
```

Visit `http://localhost:8000/viewer/` and select the imported world. All world assets must exist locally in the upstream project. No provider URLs are requested; if files are missing, use upstream local-asset repair in the Image-Blaster checkout.

Important limitations:

- Image-Blaster's downloaded collider GLB is collision geometry, not a textured complete world. The viewer deliberately shows it in **wireframe**.
- The renderer does not yet display SPZ, handle World Labs `flip_y`, apply `metric_scale_factor` or `ground_plane_offset`, or combine splats and mesh in one calibrated view.
- Image-Blaster `scene.json` object placement and generated `output/<object>/` assets are not imported yet. No object position is invented.
- The manifest validator checks local references, not asset decoding, performance, geometry integrity or licensing.
- Avoid committing gigabytes of generated binary assets to Git. Serve them locally or establish a content-addressed external asset store.

Upstream code is not copied into this adapter. PhiWorldForge's MIT license does not change third-party asset/service terms.
