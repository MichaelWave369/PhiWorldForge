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

const worldLayer = new THREE.Group();
scene.add(worldLayer);
const selector = document.querySelector("#world-selector");
const audioToggle = document.querySelector("#audio-toggle");
let playingAudio = null;

function validAsset(path) {
  return typeof path === "string" && path.startsWith("assets/") &&
    !path.includes("\\") && !path.includes(":") &&
    path.split("/").every(p => p !== "" && p !== "." && p !== "..");
}

function clearWorld() {
  if (playingAudio) {
    playingAudio.pause();
    playingAudio.src = "";
    playingAudio = null;
  }
  audioToggle.hidden = true;
  audioToggle.textContent = "Play ambience";
  worldLayer.traverse(object => {
    if (object.geometry) object.geometry.dispose();
    const list = object.material ? (Array.isArray(object.material) ? object.material : [object.material]) : [];
    list.forEach(material => {
      for (const value of Object.values(material)) if (value && value.isTexture) value.dispose();
      material.dispose();
    });
  });
  worldLayer.clear();
}

function showCollider(object) {
  object.traverse(mesh => {
    if (!mesh.isMesh) return;
    const old = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    old.filter(Boolean).forEach(material => material.dispose());
    mesh.material = new THREE.MeshBasicMaterial({
      color: "#63e9ef", wireframe: true, transparent: true, opacity: 0.35,
      depthWrite: false, side: THREE.DoubleSide
    });
  });
}

async function showWorld(entry) {
  selector.disabled = true;
  status.textContent = "Loading " + entry.title + "…";
  count.textContent = "--";
  clearWorld();
  try {
    if (!/^\.\.\/examples\/[a-z][a-z0-9-]{0,63}\/world\.json$/.test(entry.manifest)) {
      throw new Error("Invalid manifest route");
    }
    const url = new URL(entry.manifest, import.meta.url);
    if (url.origin !== window.location.origin) throw new Error("Cross-origin world denied");
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error("World fetch HTTP " + response.status);
    const data = await response.json();
    if (data.schema !== "phiworldforge.scene/0.1" || data.units !== "meters" ||
        data.up_axis !== "Y" || !Array.isArray(data.entities)) {
      throw new Error("Invalid scene schema");
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
          if (!validAsset(item.asset)) throw new Error("Invalid local asset path");
          const assetUrl = new URL(item.asset, url).href;
          if (item.asset.toLowerCase().endsWith(".glb")) {
            object = (await glbLoader.loadAsync(assetUrl)).scene;
          } else if (item.asset.toLowerCase().endsWith(".obj")) {
            object = await objLoader.loadAsync(assetUrl);
          } else throw new Error("Unsupported mesh extension");
          if (item.role === "collider-preview") showCollider(object);
        } else throw new Error("Unknown entity type");
        transform(object, item);
        object.name = item.id;
        worldLayer.add(object);
        loaded++;
      } catch (error) {
        console.error("Asset load error:", item.id, error);
        failed++;
      }
    }
    count.textContent = String(loaded) + " / " + data.entities.length;
    document.querySelector("#current-title").textContent = data.title;
    if (entry.id !== "arclight-genesis" && loaded) {
      const bounds = new THREE.Box3().setFromObject(worldLayer);
      if (!bounds.isEmpty()) {
        const center = bounds.getCenter(new THREE.Vector3());
        const radius = Math.max(3, bounds.getSize(new THREE.Vector3()).length());
        controls.target.copy(center);
        camera.position.copy(center).add(new THREE.Vector3(radius * .65, radius * .35, radius * .85));
        controls.update();
      }
    } else {
      controls.target.set(0, 2, 0);
      camera.position.set(8, 4, 10);
      controls.update();
    }
    let message = failed ? String(failed) + " entities failed" : "Scene loaded";
    if (data.source?.type === "image-blaster") message += " · collider preview only";
    if (data.environment_splat) message += " · SPZ rendering not implemented";
    status.textContent = message;
    if (validAsset(data.ambient_audio) && /\.(mp3|wav|ogg)$/i.test(data.ambient_audio)) {
      playingAudio = new Audio(new URL(data.ambient_audio, url).href);
      playingAudio.loop = true;
      audioToggle.hidden = false;
    }
    const address = new URL(window.location.href);
    address.searchParams.set("world", entry.id);
    history.replaceState(null, "", address.href);
  } finally {
    selector.disabled = false;
  }
}

audioToggle.addEventListener("click", async () => {
  if (!playingAudio) return;
  if (playingAudio.paused) {
    try {
      await playingAudio.play();
      audioToggle.textContent = "Pause ambience";
    } catch (error) {
      status.textContent = "Audio unavailable: " + error.message;
    }
  } else {
    playingAudio.pause();
    audioToggle.textContent = "Play ambience";
  }
});

async function loadGallery() {
  const response = await fetch(new URL("./worlds.json", import.meta.url), { cache: "no-store" });
  if (!response.ok) throw new Error("Catalog fetch HTTP " + response.status);
  const gallery = await response.json();
  if (gallery.schema !== "phiworldforge.catalog/0.1" || !Array.isArray(gallery.worlds) || !gallery.worlds.length) {
    throw new Error("Invalid world catalog");
  }
  selector.replaceChildren();
  gallery.worlds.forEach(entry => {
    const option = document.createElement("option");
    option.value = entry.id;
    option.textContent = entry.title;
    selector.appendChild(option);
  });
  const requestedId = new URL(location.href).searchParams.get("world");
  const first = gallery.worlds.find(entry => entry.id === requestedId) || gallery.worlds[0];
  selector.value = first.id;
  selector.addEventListener("change", () => {
    const next = gallery.worlds.find(entry => entry.id === selector.value);
    if (next) showWorld(next).catch(error => {
      console.error(error);
      status.textContent = "Scene load failed: " + error.message;
    });
  });
  await showWorld(first);
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
loadGallery().catch(error => {
  console.error(error);
  status.textContent = "Gallery failed: " + error.message;
});
