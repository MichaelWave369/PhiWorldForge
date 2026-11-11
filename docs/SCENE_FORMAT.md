# ΦWorldForge scene schema: phiworldforge.scene/0.1

A scene is a directory with world.json and optional files in assets/. Right-handed coordinate system; meters; Y-up; Euler rotations in radians.

```json
{"schema":"phiworldforge.scene/0.1","id":"demo","title":"Demo","units":"meters","up_axis":"Y","spawn":[0,1.7,5],"entities":[
  {"id":"floor","kind":"box","position":[0,-0.1,0],"size":[5,0.2,5],"color":"#18344a","collidable":true},
  {"id":"model","kind":"mesh","position":[0,0,0],"asset":"assets/model.glb","scale":[1,1,1]}
]}
```

Entity kinds: box (positive size, six-digit hex color, optional opacity 0..1), mesh (local GLB or OBJ file). Both accept optional rotation and collidable fields. Optional top-level environment_splat references SPZ and ambient_audio references MP3, WAV or OGG.

All asset names must be relative POSIX paths beneath assets/, without parent traversal or symlink escape. The validator checks metadata and file presence only, **not** file decoding, geometry integrity, licensing, collision fitness, polygon budgets or actual device compatibility.

Prefer self-contained GLB. OBJ linked textures/materials are not collected automatically. The viewer does not display SPZ. Model scale and origins must be calibrated separately after import.
