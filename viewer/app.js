import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OBJLoader } from "three/addons/loaders/OBJLoader.js";
import { VRButton } from "three/addons/webxr/VRButton.js";

// Genesis uses a fixed trusted demo world. External input and untrusted
// model decoding should be sandboxed and given resource limits later.
const status = document.querySelector("#status");
const viewport = document.querySelector("#viewport");
const count = document.querySelector("#entity-count");
const scene = new THREE.Scene();
scene.background = new THREE.Color("#020a18");
const camera = new THREE.PerspectiveCamera(68, innerWidth / innerHeight, .05, 1500);
camera.position.set(8, 4, 10);
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
renderer.setSize(innerWidth, innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.35;
renderer.xr.enabled = true;
viewport.appendChild(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 2, 0);
controls.enableDamping = true;
controls.dampingFactor = .08;
controls.minDistance = 1.5;
controls.maxDistance = 75;
controls.maxPolarAngle = Math.PI - .1;
controls.update();

const hemi = new THREE.HemisphereLight("#a4d7ff", "#0b2341", 3.2);
scene.add(hemi);
const mainLight = new THREE.PointLight("#8defff", 90, 22, 1.5);
mainLight.position.set(0, 4.4, 1);
scene.add(mainLight);
const frontLight = new THREE.PointLight("#477eec", 120, 22, 1.4);
frontLight.position.set(0, 2, -6);
scene.add(frontLight);
const rimLight = new THREE.PointLight("#ffb38a", 80, 30, 1.5);
rimLight.position.set(5, 3, -13);
scene.add(rimLight);

function seededRandom(seed) {
  let state = seed >>> 0;
  return function () {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 4294967296;
  };
}
const random = seededRandom(369);
const starPositions = [];
for (let i = 0; i < 1750; i++) {
  const theta = random() * Math.PI * 2;
  const u = random() * 2 - 1;
  const radius = 180 + random() * 300;
  const k = Math.sqrt(1 - u * u);
  starPositions.push(radius * k * Math.cos(theta), radius * u, radius * k * Math.sin(theta));
}
const starGeometry = new THREE.BufferGeometry();
starGeometry.setAttribute("position", new THREE.Float32BufferAttribute(starPositions, 3));
scene.add(new THREE.Points(starGeometry, new THREE.PointsMaterial({
  color: "#a9d6ff", size: .75, sizeAttenuation: false, transparent: true, opacity: .95
})));
const planet = new THREE.Mesh(
  new THREE.SphereGeometry(18, 48, 24),
  new THREE.MeshStandardMaterial({
    color: "#2c6baf", emissive: "#10326a", emissiveIntensity: .4,
    roughness: .96, metalness: 0
  })
);
planet.position.set(22, 9, -90);
scene.add(planet);
const halo = new THREE.Mesh(
  new THREE.RingGeometry(20, 25, 96),
  new THREE.MeshBasicMaterial({ color: "#407ba0", side: THREE.DoubleSide, transparent: true, opacity: .45 })
);
halo.position.copy(planet.position);
halo.rotation.set(.4, .5, .7);
scene.add(halo);

function transform(object, item) {
  object.position.set(...item.position);
  if (item.rotation) object.rotation.set(...item.rotation);
  if (item.scale) object.scale.set(...item.scale);
}
const glbLoader = new GLTFLoader();
const objLoader = new OBJLoader();

async function showWorld() {
  const url = new URL("../examples/arclight-room/world.json", window.location.href);
  const response = await fetch(url);
  if (!response.ok) throw new Error("Cannot load world.json (HTTP " + response.status + ")");
  const data = await response.json();
  if (data.schema !== "phiworldforge.scene/0.1" || data.units !== "meters" || data.up_axis !== "Y") {
    throw new Error("Unsupported scene schema, units, or up-axis");
  }
  let loaded = 0;
  let failed = 0;
  for (const item of data.entities) {
    try {
      let object;
      if (item.kind === "box") {
        object = new THREE.Mesh(
          new THREE.BoxGeometry(...item.size),
          new THREE.MeshStandardMaterial({
            color: item.color, metalness: .55, roughness: .36,
            opacity: item.opacity ?? 1, transparent: (item.opacity ?? 1) < 1,
            side: THREE.DoubleSide
          })
        );
      } else if (item.kind === "mesh") {
        if (!item.asset.startsWith("assets/") || item.asset.includes("..")) {
          throw new Error("Invalid relative mesh path");
        }
        const assetUrl = new URL(item.asset, url).href;
        if (item.asset.toLowerCase().endsWith(".glb")) {
          object = (await glbLoader.loadAsync(assetUrl)).scene;
        } else if (item.asset.toLowerCase().endsWith(".obj")) {
          object = await objLoader.loadAsync(assetUrl);
        } else {
          throw new Error("Unsupported viewer mesh format");
        }
      } else {
        throw new Error("Unknown entity kind");
      }
      transform(object, item);
      object.name = item.id;
      scene.add(object);
      loaded++;
    } catch (error) {
      failed++;
      console.error("Entity failed:", item.id, error);
    }
  }
  count.textContent = String(loaded) + " / " + data.entities.length;
  status.textContent = failed ? "Scene loaded with " + failed + " asset error(s)" : "Scene loaded · orbit or move to explore";
  if (data.environment_splat) {
    status.textContent += " · SPZ rendering not implemented";
  }
  if (data.ambient_audio && data.ambient_audio.startsWith("assets/") && !data.ambient_audio.includes("..")) {
    const audio = new Audio(new URL(data.ambient_audio, url).href);
    audio.loop = true;
    const toggle = document.querySelector("#audio-toggle");
    toggle.hidden = false;
    toggle.addEventListener("click", async () => {
      if (audio.paused) {
        try {
          await audio.play();
          toggle.textContent = "Pause ambience";
        } catch (error) {
          status.textContent = "Audio playback blocked by browser";
        }
      } else {
        audio.pause();
        toggle.textContent = "Play ambience";
      }
    });
  }
}

const keys = new Set();
window.addEventListener("keydown", event => {
  if (["KeyW", "KeyA", "KeyS", "KeyD", "KeyQ", "KeyE"].includes(event.code)) keys.add(event.code);
});
window.addEventListener("keyup", event => keys.delete(event.code));
window.addEventListener("blur", () => keys.clear());
const clock = new THREE.Clock();
const forward = new THREE.Vector3();
const right = new THREE.Vector3();
const translation = new THREE.Vector3();
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), .06);
  if (!renderer.xr.isPresenting) {
    camera.getWorldDirection(forward);
    forward.y = 0;
    forward.normalize();
    right.crossVectors(forward, camera.up).normalize();
    translation.set(0, 0, 0);
    if (keys.has("KeyW")) translation.add(forward);
    if (keys.has("KeyS")) translation.sub(forward);
    if (keys.has("KeyD")) translation.add(right);
    if (keys.has("KeyA")) translation.sub(right);
    if (keys.has("KeyE")) translation.y++;
    if (keys.has("KeyQ")) translation.y--;
    if (translation.lengthSq() > 0) {
      translation.normalize().multiplyScalar(dt * 5);
      controls.target.add(translation);
      camera.position.add(translation);
    }
    controls.update();
  }
  renderer.render(scene, camera);
});

if ("xr" in navigator && window.isSecureContext) {
  viewport.appendChild(VRButton.createButton(renderer));
}
addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});
showWorld().catch(error => {
  console.error(error);
  status.textContent = "Scene load failed: " + error.message;
});
