// 3D anatomy viewer. Rendering only: all logic lives in Python.
// Every element with class "body3d" gets its own viewer. Python writes JSON to
// its data-muscles attribute as {muscle_id: {color, label}} and the meshes recolor.
// Optional data-info="<element id>" shows the tapped muscle's label there.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const UP = new THREE.Vector3(0, 1, 0);
const V = (x, y, z) => new THREE.Vector3(x, y, z);
const DEPTH = 0.62; // torso front-to-back vs side-to-side

// Torso silhouette: [radius, height] from hips to neck.
const TORSO = [
  [0, 0.84], [0.12, 0.845], [0.165, 0.88], [0.168, 0.93], [0.15, 0.99],
  [0.135, 1.05], [0.14, 1.12], [0.155, 1.2], [0.172, 1.3], [0.178, 1.37],
  [0.17, 1.43], [0.13, 1.48], [0.07, 1.51], [0, 1.52],
];
function torsoR(y) {
  for (let i = 1; i < TORSO.length; i++) {
    const [r0, y0] = TORSO[i - 1], [r1, y1] = TORSO[i];
    if (y <= y1) return r0 + ((r1 - r0) * (y - y0)) / (y1 - y0);
  }
  return 0;
}

// Muscle-fiber bump texture shared by all muscles.
const fibers = (() => {
  const c = document.createElement("canvas");
  c.width = 128; c.height = 8;
  const g = c.getContext("2d");
  for (let x = 0; x < 128; x++) {
    const v = 110 + Math.floor(Math.random() * 90);
    g.fillStyle = `rgb(${v},${v},${v})`;
    g.fillRect(x, 0, 1, 8);
  }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(3, 1);
  return t;
})();

const sphereGeo = new THREE.SphereGeometry(1, 32, 24);

// Tapered limb from a to b; radii are sampled evenly along its length.
function limbGeo(len, radii) {
  const n = radii.length, pts = [];
  pts.push(new THREE.Vector2(0, -radii[0] * 0.6));
  pts.push(new THREE.Vector2(radii[0] * 0.75, -radii[0] * 0.35));
  radii.forEach((r, i) => pts.push(new THREE.Vector2(r, (i / (n - 1)) * len)));
  pts.push(new THREE.Vector2(radii[n - 1] * 0.75, len + radii[n - 1] * 0.35));
  pts.push(new THREE.Vector2(0, len + radii[n - 1] * 0.6));
  return new THREE.LatheGeometry(pts, 32);
}

// Spindle-shaped muscle belly (thick middle, tapered tendons).
function spindleGeo(len, r) {
  const pts = [];
  for (let i = 0; i <= 14; i++) {
    const t = i / 14;
    pts.push(new THREE.Vector2(Math.max(0.0005, r * Math.pow(Math.sin(Math.PI * t), 0.7)), t * len - len / 2));
  }
  return new THREE.LatheGeometry(pts, 24);
}

function orient(mesh, a, b) {
  const dir = b.clone().sub(a);
  mesh.quaternion.setFromUnitVectors(UP, dir.normalize());
}

function buildBody(group) {
  const skin = new THREE.MeshStandardMaterial({ color: 0x343434, roughness: 0.75, metalness: 0.05 });
  const muscleMats = {};
  const pickable = [];

  const add = (geo, mat, pos, scale, rot) => {
    const m = new THREE.Mesh(geo, mat);
    m.position.copy(pos);
    if (scale) m.scale.copy(scale);
    if (rot) m.rotation.set(rot[0], rot[1], rot[2]);
    group.add(m);
    return m;
  };
  const limb = (a, b, radii) => {
    const m = new THREE.Mesh(limbGeo(a.distanceTo(b), radii), skin);
    m.position.copy(a);
    orient(m, a, b);
    group.add(m);
  };
  const mat = (id) => {
    if (!muscleMats[id]) {
      muscleMats[id] = new THREE.MeshStandardMaterial({
        color: 0x5c5c5c, roughness: 0.5, bumpMap: fibers, bumpScale: 0.9,
      });
    }
    return muscleMats[id];
  };
  const tag = (m, id) => { m.userData.id = id; pickable.push(m); return m; };
  const blob = (id, pos, scale, rot) => tag(add(sphereGeo, mat(id), pos, scale, rot), id);
  // Muscle along segment [a, b] from t0 to t1, pushed out by `off`.
  const belly = (id, a, b, t0, t1, off, r, sx = 1, sz = 1) => {
    const p0 = a.clone().lerp(b, t0).add(off), p1 = a.clone().lerp(b, t1).add(off);
    const m = new THREE.Mesh(spindleGeo(p0.distanceTo(p1), r), mat(id));
    m.position.copy(p0.clone().add(p1).multiplyScalar(0.5));
    orient(m, p0, p1);
    m.scale.set(sx, 1, sz);
    group.add(m);
    return tag(m, id);
  };

  // ----- skeleton / skin -----
  const torso = new THREE.Mesh(new THREE.LatheGeometry(TORSO.map(([r, y]) => new THREE.Vector2(r, y)), 48), skin);
  torso.scale.z = DEPTH;
  group.add(torso);
  add(sphereGeo, skin, V(0, 0.9, 0), V(0.16, 0.1, 0.105));        // pelvis
  limb(V(0, 1.47, -0.005), V(0, 1.6, 0), [0.058, 0.052, 0.05]);    // neck
  add(sphereGeo, skin, V(0, 1.67, 0.01), V(0.092, 0.115, 0.102));  // skull
  add(sphereGeo, skin, V(0, 1.605, 0.03), V(0.07, 0.06, 0.075));   // jaw

  for (const s of [-1, 1]) {
    const UA = [V(s * 0.205, 1.43, 0), V(s * 0.25, 1.13, -0.005)];
    const FA = [V(s * 0.25, 1.13, -0.005), V(s * 0.27, 0.87, 0.03)];
    const TH = [V(s * 0.09, 0.92, 0), V(s * 0.1, 0.5, 0.01)];
    const SH = [V(s * 0.1, 0.5, 0.01), V(s * 0.105, 0.09, -0.005)];

    add(sphereGeo, skin, V(s * 0.2, 1.42, 0), V(0.06, 0.06, 0.06));       // shoulder joint
    limb(UA[0], UA[1], [0.05, 0.046, 0.04, 0.037]);
    add(sphereGeo, skin, UA[1], V(0.036, 0.036, 0.036));                  // elbow
    limb(FA[0], FA[1], [0.04, 0.042, 0.034, 0.026]);
    add(sphereGeo, skin, V(s * 0.275, 0.8, 0.035), V(0.026, 0.065, 0.045)); // hand
    limb(TH[0], TH[1], [0.088, 0.082, 0.07, 0.056, 0.05]);
    add(sphereGeo, skin, TH[1], V(0.05, 0.05, 0.05));                     // knee
    limb(SH[0], SH[1], [0.05, 0.054, 0.046, 0.036, 0.03]);
    add(sphereGeo, skin, V(s * 0.105, 0.035, 0.045), V(0.042, 0.03, 0.11)); // foot

    // ----- muscles -----
    const zf = (y) => torsoR(y) * DEPTH; // torso surface depth at height y
    blob("chest", V(s * 0.085, 1.335, zf(1.335) - 0.016), V(0.092, 0.066, 0.04), [0, 0, s * -0.2]);
    for (const [y, h] of [[1.225, 0.031], [1.155, 0.031], [1.085, 0.031], [1.015, 0.036]]) {
      blob("abs", V(s * 0.03, y, zf(y) - 0.006), V(0.027, h, 0.016));
    }
    blob("obliques", V(s * torsoR(1.08) * 0.82, 1.08, zf(1.08) * 0.45), V(0.03, 0.085, 0.035), [0, s * -0.6, 0]);

    blob("front_delts", V(s * 0.2, 1.405, 0.04), V(0.042, 0.07, 0.04));
    blob("side_delts", V(s * 0.236, 1.41, 0), V(0.035, 0.072, 0.05));
    blob("rear_delts", V(s * 0.2, 1.405, -0.04), V(0.042, 0.07, 0.04));

    belly("biceps", UA[0], UA[1], 0.25, 0.85, V(0, 0, 0.03), 0.033, 1, 0.9);
    belly("triceps", UA[0], UA[1], 0.1, 0.8, V(0, 0, -0.03), 0.036, 1, 0.85);
    belly("forearms", FA[0], FA[1], 0.02, 0.65, V(0, 0, 0.012), 0.036, 1.1, 0.8);
    belly("forearms", FA[0], FA[1], 0.05, 0.6, V(s * 0.012, 0, -0.012), 0.03, 1, 0.8);

    blob("traps", V(s * 0.065, 1.465, -0.05), V(0.085, 0.045, 0.035), [0, 0, s * -0.3]);
    belly("traps", V(s * 0.03, 1.56, -0.03), V(s * 0.17, 1.45, -0.02), 0, 1, V(0, 0, 0), 0.028, 1, 0.7);
    blob("lats", V(s * 0.11, 1.26, -(zf(1.26) - 0.02)), V(0.07, 0.15, 0.03), [0, 0, s * 0.28]);
    belly("lower_back", V(s * 0.035, 0.96, -(zf(1.08) - 0.005)), V(s * 0.035, 1.2, -(zf(1.08) - 0.005)), 0, 1, V(0, 0, 0), 0.028, 1, 0.6);
    blob("glutes", V(s * 0.075, 0.9, -0.075), V(0.085, 0.09, 0.06));

    belly("quads", TH[0], TH[1], 0.08, 0.88, V(0, 0, 0.045), 0.04, 1, 0.8);            // rectus femoris
    belly("quads", TH[0], TH[1], 0.2, 0.9, V(s * 0.04, 0, 0.015), 0.038);             // vastus lateralis
    belly("quads", TH[0], TH[1], 0.5, 0.97, V(-s * 0.035, 0, 0.028), 0.032);          // vastus medialis
    belly("hamstrings", TH[0], TH[1], 0.1, 0.88, V(s * 0.022, 0, -0.045), 0.034);
    belly("hamstrings", TH[0], TH[1], 0.1, 0.88, V(-s * 0.022, 0, -0.045), 0.032);
    belly("calves", SH[0], SH[1], 0.05, 0.55, V(s * 0.02, 0, -0.035), 0.034);
    belly("calves", SH[0], SH[1], 0.05, 0.55, V(-s * 0.018, 0, -0.033), 0.036);
  }
  return { muscleMats, pickable };
}

function makeViewer(host) {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 20);
  camera.position.set(0, 0.95, 2.75);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  host.appendChild(renderer.domElement);

  scene.add(new THREE.HemisphereLight(0xffffff, 0x333333, 2.0));
  const key = new THREE.DirectionalLight(0xffffff, 1.8);
  key.position.set(2, 3, 4);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0xffffff, 1.0);
  rim.position.set(-2, 2, -4);
  scene.add(rim);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 0.93, 0);
  controls.enablePan = false;
  controls.enableZoom = false;
  controls.minPolarAngle = Math.PI * 0.3;
  controls.maxPolarAngle = Math.PI * 0.7;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 1.4;
  controls.addEventListener("start", () => (controls.autoRotate = false));

  const body = new THREE.Group();
  scene.add(body);
  const { muscleMats, pickable } = buildBody(body);

  let labels = {};
  const apply = () => {
    let data = {};
    try { data = JSON.parse(host.dataset.muscles || "{}"); } catch (e) {}
    labels = {};
    for (const id in muscleMats) {
      const d = data[id];
      muscleMats[id].color.set(d ? d.color : "#5c5c5c");
      muscleMats[id].emissive.set(d && d.glow ? d.color : "#000000");
      muscleMats[id].emissiveIntensity = d && d.glow ? 0.35 : 0;
      if (d) labels[id] = d.label;
    }
  };
  new MutationObserver(apply).observe(host, { attributes: true, attributeFilter: ["data-muscles"] });
  apply();

  const info = host.dataset.info ? document.getElementById(host.dataset.info) : null;
  const ray = new THREE.Raycaster();
  const ptr = new THREE.Vector2();
  let downAt = null;
  renderer.domElement.addEventListener("pointerdown", (e) => (downAt = [e.clientX, e.clientY]));
  renderer.domElement.addEventListener("pointerup", (e) => {
    if (!info || !downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 6) return;
    const r = renderer.domElement.getBoundingClientRect();
    ptr.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ptr, camera);
    const hit = ray.intersectObjects(pickable)[0];
    info.textContent = hit ? labels[hit.object.userData.id] || "" : "Tap a muscle to see its sets.";
  });

  const resize = () => {
    const w = host.clientWidth, h = host.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };
  new ResizeObserver(resize).observe(host);
  resize();
  renderer.setAnimationLoop(() => {
    if (!host.clientWidth) return; // hidden: skip work
    controls.update();
    renderer.render(scene, camera);
  });
}

document.querySelectorAll(".body3d").forEach(makeViewer);
