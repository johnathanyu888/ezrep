// 3D muscle map. Rendering only: all logic lives in Python (main.py / muscles.py).
// Python writes JSON to <div id="body3d" data-muscles="..."> as
// {muscle_id: {color, label}}, and this file recolors the meshes to match.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const host = document.getElementById("body3d");
const info = document.getElementById("muscleInfo");

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 20);
camera.position.set(0, 1.0, 3.5);

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
host.appendChild(renderer.domElement);

scene.add(new THREE.HemisphereLight(0xffffff, 0x333333, 2.2));
const key = new THREE.DirectionalLight(0xffffff, 1.6);
key.position.set(2, 3, 4);
scene.add(key);
const rim = new THREE.DirectionalLight(0xffffff, 0.9);
rim.position.set(-2, 2, -4);
scene.add(rim);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0.95, 0);
controls.enablePan = false;
controls.enableZoom = false;
controls.minPolarAngle = Math.PI * 0.3;
controls.maxPolarAngle = Math.PI * 0.7;
controls.autoRotate = true;
controls.autoRotateSpeed = 1.2;
controls.addEventListener("start", () => (controls.autoRotate = false));

// ---------- body ----------
const skin = new THREE.MeshStandardMaterial({ color: 0x3a3a3a, roughness: 0.8 });
const body = new THREE.Group();
scene.add(body);

function part(geo, x, y, z, sx = 1, sy = 1, sz = 1) {
  const m = new THREE.Mesh(geo, skin);
  m.position.set(x, y, z);
  m.scale.set(sx, sy, sz);
  body.add(m);
}
const sphere = new THREE.SphereGeometry(1, 32, 20);
const capsule = (r, len) => new THREE.CapsuleGeometry(r, len, 8, 20);

part(sphere, 0, 1.66, 0, 0.1, 0.12, 0.11);              // head
part(capsule(0.05, 0.08), 0, 1.52, 0);                  // neck
part(capsule(0.16, 0.34), 0, 1.24, 0, 1.3, 1, 0.72);    // torso
part(sphere, 0, 0.95, 0, 0.18, 0.12, 0.12);             // pelvis
for (const s of [-1, 1]) {
  part(sphere, s * 0.22, 1.42, 0, 0.075, 0.07, 0.075);  // shoulder
  part(capsule(0.048, 0.24), s * 0.275, 1.23, 0);       // upper arm
  part(capsule(0.04, 0.24), s * 0.285, 0.95, 0);        // forearm
  part(sphere, s * 0.285, 0.77, 0, 0.04, 0.05, 0.03);   // hand
  part(capsule(0.08, 0.32), s * 0.1, 0.67, 0);          // thigh
  part(capsule(0.055, 0.32), s * 0.1, 0.29, 0);         // shin
  part(sphere, s * 0.1, 0.06, 0.04, 0.05, 0.035, 0.1);  // foot
}

// ---------- muscles ----------
// [id, x, y, z, sx, sy, sz]: each is mirrored to both sides unless x === 0.
const MUSCLES = [
  ["chest",       0.085, 1.34, 0.095, 0.09, 0.065, 0.045],
  ["abs",         0,     1.12, 0.105, 0.07, 0.13,  0.03],
  ["obliques",    0.135, 1.1,  0.07,  0.04, 0.1,   0.04],
  ["front_delts", 0.22,  1.42, 0.04,  0.05, 0.062, 0.045],
  ["side_delts",  0.265, 1.42, 0,     0.035,0.062, 0.05],
  ["rear_delts",  0.22,  1.42, -0.04, 0.05, 0.062, 0.045],
  ["biceps",      0.275, 1.25, 0.03,  0.036,0.09,  0.032],
  ["triceps",     0.275, 1.25, -0.03, 0.036,0.1,   0.032],
  ["forearms",    0.285, 0.97, 0.005, 0.042,0.1,   0.04],
  ["traps",       0.075, 1.47, -0.055,0.09, 0.06,  0.04],
  ["lats",        0.12,  1.25, -0.085,0.075,0.14,  0.04],
  ["lower_back",  0.05,  1.05, -0.095,0.04, 0.09,  0.03],
  ["glutes",      0.08,  0.92, -0.085,0.085,0.08,  0.05],
  ["quads",       0.1,   0.7,  0.045, 0.065,0.15,  0.05],
  ["hamstrings",  0.1,   0.7,  -0.045,0.06, 0.15,  0.045],
  ["calves",      0.1,   0.33, -0.035,0.045,0.1,   0.04],
];

const meshes = {};   // id -> [mesh, ...]
const pickable = [];
for (const [id, x, y, z, sx, sy, sz] of MUSCLES) {
  const mat = new THREE.MeshStandardMaterial({ color: 0x4a4a4a, roughness: 0.55 });
  meshes[id] = [];
  for (const s of x === 0 ? [1] : [-1, 1]) {
    const m = new THREE.Mesh(sphere, mat);
    m.position.set(s * x, y, z);
    m.scale.set(sx, sy, sz);
    m.userData.id = id;
    body.add(m);
    meshes[id].push(m);
    pickable.push(m);
  }
}

let labels = {};
function apply() {
  let data = {};
  try { data = JSON.parse(host.dataset.muscles || "{}"); } catch (e) {}
  labels = {};
  for (const id in meshes) {
    const d = data[id];
    if (!d) continue;
    meshes[id][0].material.color.set(d.color);
    labels[id] = d.label;
  }
}
new MutationObserver(apply).observe(host, { attributes: true, attributeFilter: ["data-muscles"] });
apply();

// Tap a muscle to see its set count.
const ray = new THREE.Raycaster();
const ptr = new THREE.Vector2();
let downAt = null;
renderer.domElement.addEventListener("pointerdown", (e) => (downAt = [e.clientX, e.clientY]));
renderer.domElement.addEventListener("pointerup", (e) => {
  if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 6) return;
  const r = renderer.domElement.getBoundingClientRect();
  ptr.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ptr, camera);
  const hit = ray.intersectObjects(pickable)[0];
  info.textContent = hit ? labels[hit.object.userData.id] || "" : "Tap a muscle to see its sets.";
});

// ---------- loop ----------
function resize() {
  const w = host.clientWidth, h = host.clientHeight;
  if (!w || !h) return;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(host);
resize();
renderer.setAnimationLoop(() => {
  controls.update();
  renderer.render(scene, camera);
});
