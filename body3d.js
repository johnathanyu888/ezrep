// 3D anatomy viewer. Rendering only: all logic lives in Python.
//
// Model: models/muscles.glb, adapted from Z-Anatomy (Gauthier Kervyn), based on
// BodyParts3D (© The Database Center for Life Science), CC BY-SA 4.0.
// See CREDITS.md.
//
// Every element with class "body3d" gets its own viewer. Python writes JSON to
// its data-muscles attribute as {muscle_id: {color, label, glow?}}.
// Optional data-info="<element id>" shows the tapped muscle's label there.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

// Model region (node name) -> EZRep muscle id (see muscles.py).
const REGION_TO_MUSCLE = {
  pec_major_upper: "chest", pec_major_lower: "chest",
  anterior_delt: "front_delts", lateral_delt: "side_delts", posterior_delt: "rear_delts",
  biceps: "biceps", brachialis: "biceps",
  triceps_long: "triceps", triceps_lateral: "triceps", triceps_medial: "triceps",
  brachioradialis: "forearms", forearm_flexors: "forearms", forearm_extensors: "forearms",
  upper_traps: "traps", mid_traps: "traps", lower_traps: "traps", rhomboids: "traps",
  upper_lats: "lats", lower_lats: "lats", teres_major: "lats",
  erector_spinae: "lower_back",
  rectus_abdominis: "abs", transverse_abdominis: "abs",
  obliques: "obliques",
  glute_max: "glutes", glute_med: "glutes",
  rectus_femoris: "quads", vastus_group: "quads",
  lateral_hamstrings: "hamstrings", medial_hamstrings: "hamstrings",
  gastrocnemius: "calves", soleus: "calves",
};
// Non-muscle parts (head, bones, tendons, hand/foot skin) keep their own look.
const CONTEXT = new Set(["body_context", "context_bone", "context_skin", "context_tendon"]);
const UNTRAINED = "#5c5c5c";

let modelPromise = null;
function loadModel() {
  if (!modelPromise) {
    modelPromise = new GLTFLoader().loadAsync("models/muscles.glb").then((g) => g.scene);
  }
  return modelPromise;
}

function makeViewer(host) {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(28, 1, 0.05, 30);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  host.appendChild(renderer.domElement);

  scene.add(new THREE.HemisphereLight(0xffffff, 0x2a2a2a, 2.2));
  const key = new THREE.DirectionalLight(0xffffff, 2.0);
  key.position.set(2, 3, 4);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0xffffff, 1.1);
  rim.position.set(-2, 2, -4);
  scene.add(rim);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 0, 0);
  controls.enablePan = false;
  controls.enableZoom = false;
  controls.minPolarAngle = Math.PI * 0.3;
  controls.maxPolarAngle = Math.PI * 0.7;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 1.4;
  controls.addEventListener("start", () => (controls.autoRotate = false));

  // One material per EZRep muscle id, plus one for muscles we don't track.
  // vertexColors keeps the model's baked ambient occlusion.
  const muscleMats = {};
  const matFor = (id) => {
    if (!muscleMats[id]) {
      muscleMats[id] = new THREE.MeshStandardMaterial({ color: UNTRAINED, roughness: 0.55, vertexColors: true });
    }
    return muscleMats[id];
  };
  const otherMat = new THREE.MeshStandardMaterial({ color: 0x404040, roughness: 0.6, vertexColors: true });
  const pickable = [];

  loadModel().then((src) => {
    const body = src.clone(true);
    body.traverse((obj) => {
      if (!obj.isMesh) return;
      let node = obj;
      while (node.parent && node.parent !== body) node = node.parent;
      const region = node.name;
      if (CONTEXT.has(region)) {
        // Dim the head/bones/skin so the muscles stay the focus.
        obj.material = obj.material.clone();
        if (obj.material.color) obj.material.color.set(region === "body_context" ? 0x555555 : 0x333333);
        if (obj.material.emissive) obj.material.emissive.set(0x000000);
        return;
      }
      const id = REGION_TO_MUSCLE[region];
      obj.material = id ? matFor(id) : otherMat;
      if (id) {
        obj.userData.id = id;
        pickable.push(obj);
      }
    });
    scene.add(body);
    apply();
  });

  let labels = {};
  function apply() {
    let data = {};
    try { data = JSON.parse(host.dataset.muscles || "{}"); } catch (e) {}
    labels = {};
    for (const id in muscleMats) {
      const d = data[id];
      muscleMats[id].color.set(d ? d.color : UNTRAINED);
      muscleMats[id].emissive.set(d && d.glow ? d.color : "#000000");
      muscleMats[id].emissiveIntensity = d && d.glow ? 0.3 : 0;
      if (d) labels[id] = d.label;
    }
  }
  new MutationObserver(apply).observe(host, { attributes: true, attributeFilter: ["data-muscles"] });

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

  // Fit the whole body (1.8 tall, ~0.75 wide incl. arms) in view with a margin,
  // whatever the box's aspect ratio.
  const BODY_H = 1.8 * 1.12, BODY_W = 0.8 * 1.12;
  const resize = () => {
    const w = host.clientWidth, h = host.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    const tanHalf = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
    const distH = BODY_H / 2 / tanHalf;
    const distW = BODY_W / 2 / (tanHalf * camera.aspect);
    const dist = Math.max(distH, distW);
    const dir = camera.position.clone().sub(controls.target);
    if (dir.lengthSq() < 1e-6) dir.set(0, 0, 1);
    camera.position.copy(controls.target).add(dir.normalize().multiplyScalar(dist));
    camera.updateProjectionMatrix();
  };
  camera.position.set(0, 0, 4);
  new ResizeObserver(resize).observe(host);
  resize();
  renderer.setAnimationLoop(() => {
    if (!host.clientWidth) return; // hidden: skip work
    controls.update();
    renderer.render(scene, camera);
  });
}

document.querySelectorAll(".body3d").forEach(makeViewer);
