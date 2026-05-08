import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { PointerLockControls } from 'three/examples/jsm/controls/PointerLockControls.js';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';

/* ============================================================
 * Dreamwalk — first-person Three.js explorer for the
 * apocalyptic city dream world.
 * ============================================================ */

const CITY_URL = new URL('../public/models/apocalyptic_city.glb', import.meta.url).href;

const PLAYER = {
  eyeHeight: 1.7,
  radius: 0.4,
  walkSpeed: 6.0,
  sprintSpeed: 11.0,
  flySpeed: 18.0,
  jumpSpeed: 6.5,
  gravity: 22.0,
  damping: 10.0,
};

const WORLD = {
  fogColor: 0x1c1410,
  bgColorTop: 0x2a1c14,
  bgColorBottom: 0x0a0708,
  sunColor: 0xffb27a,
  hemiSky: 0xffd9b8,
  hemiGround: 0x231510,
  ambient: 0x33241c,
};

/* ----- DOM ----- */
const canvas = document.getElementById('scene');
const overlayEl = document.getElementById('overlay');
const startBtn = document.getElementById('start-btn');
const startBtnLabel = startBtn.querySelector('.overlay__cta-label');
const loaderFill = document.getElementById('loader-fill');
const loaderText = document.getElementById('loader-text');
const overlayHint = document.getElementById('overlay-hint');
const hudMode = document.getElementById('hud-mode');
const hudSpeed = document.getElementById('hud-speed');
const hudPos = document.getElementById('hud-pos');

/* ----- Renderer ----- */
const renderer = new THREE.WebGLRenderer({
  canvas,
  antialias: true,
  powerPreference: 'high-performance',
});
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

/* ----- Scene ----- */
const scene = new THREE.Scene();
scene.background = makeSkyTexture(WORLD.bgColorTop, WORLD.bgColorBottom);
scene.fog = new THREE.Fog(WORLD.fogColor, 30, 320);

/* ----- Camera ----- */
const camera = new THREE.PerspectiveCamera(
  72,
  window.innerWidth / window.innerHeight,
  0.1,
  1000,
);
camera.position.set(0, 100, 0);

/* ----- Lighting ----- */
const hemi = new THREE.HemisphereLight(WORLD.hemiSky, WORLD.hemiGround, 0.55);
hemi.position.set(0, 200, 0);
scene.add(hemi);

const ambient = new THREE.AmbientLight(WORLD.ambient, 0.35);
scene.add(ambient);

const sun = new THREE.DirectionalLight(WORLD.sunColor, 1.6);
sun.position.set(80, 120, 60);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.near = 1;
sun.shadow.camera.far = 400;
sun.shadow.camera.left = -120;
sun.shadow.camera.right = 120;
sun.shadow.camera.top = 120;
sun.shadow.camera.bottom = -120;
sun.shadow.bias = -0.0005;
scene.add(sun);
scene.add(sun.target);

/* ----- Fallback ground (in case the .glb has gaps) ----- */
const groundGeo = new THREE.PlaneGeometry(2000, 2000);
const groundMat = new THREE.MeshStandardMaterial({
  color: 0x1a120e,
  roughness: 1.0,
  metalness: 0.0,
});
const ground = new THREE.Mesh(groundGeo, groundMat);
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
ground.name = 'fallback_ground';
scene.add(ground);

/* ----- Post-processing (subtle bloom for the apocalyptic glow) ----- */
const composer = new EffectComposer(renderer);
composer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
composer.setSize(window.innerWidth, window.innerHeight);
composer.addPass(new RenderPass(scene, camera));
const bloomPass = new UnrealBloomPass(
  new THREE.Vector2(window.innerWidth, window.innerHeight),
  0.55, // strength
  0.85, // radius
  0.65, // threshold
);
composer.addPass(bloomPass);
composer.addPass(new OutputPass());

/* ----- Atmospheric dust particles ----- */
const dustCount = 1500;
const dustField = makeDustField(dustCount, 80);
scene.add(dustField);

/* ----- Controls ----- */
const controls = new PointerLockControls(camera, renderer.domElement);
scene.add(controls.object);

/* ----- Player state ----- */
const player = {
  velocity: new THREE.Vector3(),
  onGround: false,
  flying: false,
  spawn: new THREE.Vector3(0, 100, 0),
};

/* ----- Input ----- */
const keys = {
  forward: false,
  back: false,
  left: false,
  right: false,
  jump: false,
  sprint: false,
  up: false,
  down: false,
};

document.addEventListener('keydown', (event) => {
  switch (event.code) {
    case 'KeyW':
    case 'ArrowUp':
      keys.forward = true;
      break;
    case 'KeyS':
    case 'ArrowDown':
      keys.back = true;
      break;
    case 'KeyA':
    case 'ArrowLeft':
      keys.left = true;
      break;
    case 'KeyD':
    case 'ArrowRight':
      keys.right = true;
      break;
    case 'Space':
      keys.jump = true;
      keys.up = true;
      event.preventDefault();
      break;
    case 'ShiftLeft':
    case 'ShiftRight':
      keys.sprint = true;
      break;
    case 'ControlLeft':
    case 'ControlRight':
      keys.down = true;
      break;
    case 'KeyF':
      player.flying = !player.flying;
      player.velocity.set(0, 0, 0);
      hudMode.textContent = player.flying ? 'flying' : 'walking';
      break;
    case 'KeyR':
      respawn();
      break;
    default:
      break;
  }
});

document.addEventListener('keyup', (event) => {
  switch (event.code) {
    case 'KeyW':
    case 'ArrowUp':
      keys.forward = false;
      break;
    case 'KeyS':
    case 'ArrowDown':
      keys.back = false;
      break;
    case 'KeyA':
    case 'ArrowLeft':
      keys.left = false;
      break;
    case 'KeyD':
    case 'ArrowRight':
      keys.right = false;
      break;
    case 'Space':
      keys.jump = false;
      keys.up = false;
      break;
    case 'ShiftLeft':
    case 'ShiftRight':
      keys.sprint = false;
      break;
    case 'ControlLeft':
    case 'ControlRight':
      keys.down = false;
      break;
    default:
      break;
  }
});

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  composer.setSize(window.innerWidth, window.innerHeight);
  bloomPass.setSize(window.innerWidth, window.innerHeight);
});

controls.addEventListener('lock', () => {
  document.body.classList.add('is-playing');
  overlayEl.classList.add('is-hidden');
});

controls.addEventListener('unlock', () => {
  document.body.classList.remove('is-playing');
  overlayEl.classList.remove('is-hidden');
  startBtnLabel.textContent = 'Resume Dream';
  overlayHint.innerHTML = 'Cursor released. Click <em>Resume Dream</em> to dive back in.';
});

startBtn.addEventListener('click', () => {
  if (!startBtn.disabled) {
    controls.lock();
  }
});

/* ============================================================
 * Loading the city
 * ============================================================ */

const collidableMeshes = [];
const downRaycaster = new THREE.Raycaster();
downRaycaster.far = 500;
const horizontalRaycaster = new THREE.Raycaster();
horizontalRaycaster.far = PLAYER.radius * 2;

const loader = new GLTFLoader();
loader.load(
  CITY_URL,
  (gltf) => {
    const cityRoot = gltf.scene;
    cityRoot.name = 'apocalyptic_city';

    // Compute bounds to scale/center if needed.
    const bbox = new THREE.Box3().setFromObject(cityRoot);
    const size = bbox.getSize(new THREE.Vector3());
    const center = bbox.getCenter(new THREE.Vector3());

    // Center the city horizontally on the origin and put its base at y=0.
    cityRoot.position.x -= center.x;
    cityRoot.position.z -= center.z;
    cityRoot.position.y -= bbox.min.y;

    // If the model is very small or huge, normalize a bit so the player feels human-sized.
    const maxHorizontal = Math.max(size.x, size.z);
    if (maxHorizontal > 0) {
      // Aim for the city to span at least ~150 units; cap scaling so we don't blow up tiny meshes.
      const desired = 200;
      let scale = 1;
      if (maxHorizontal < 40) {
        scale = desired / maxHorizontal;
      } else if (maxHorizontal > 800) {
        scale = desired / maxHorizontal;
      }
      if (scale !== 1) {
        cityRoot.scale.setScalar(scale);
        // Recompute placement after scaling.
        const bbox2 = new THREE.Box3().setFromObject(cityRoot);
        const center2 = bbox2.getCenter(new THREE.Vector3());
        cityRoot.position.x -= center2.x;
        cityRoot.position.z -= center2.z;
        cityRoot.position.y -= bbox2.min.y;
      }
    }

    cityRoot.traverse((child) => {
      if (child.isMesh) {
        child.castShadow = true;
        child.receiveShadow = true;
        collidableMeshes.push(child);

        // Improve material look: make sure double-sided surfaces and
        // emissive maps are preserved while sharpening the apocalyptic look.
        const mat = child.material;
        if (mat) {
          if (Array.isArray(mat)) {
            mat.forEach((m) => tweakMaterial(m));
          } else {
            tweakMaterial(mat);
          }
        }
      }
    });

    scene.add(cityRoot);

    // Hide the fallback ground if the city already covers it.
    const finalBounds = new THREE.Box3().setFromObject(cityRoot);
    const finalSize = finalBounds.getSize(new THREE.Vector3());
    if (finalSize.x > 60 && finalSize.z > 60) {
      ground.visible = false;
    } else {
      ground.position.y = finalBounds.min.y;
      collidableMeshes.push(ground);
    }

    // Spawn player above the model and let gravity drop them onto it.
    const spawnY = finalBounds.max.y + 5;
    player.spawn.set(0, spawnY, 0);
    controls.object.position.copy(player.spawn);

    finishLoading();
  },
  (xhr) => {
    if (xhr.lengthComputable) {
      const pct = Math.min(99, Math.round((xhr.loaded / xhr.total) * 100));
      updateLoaderUi(pct);
    } else if (xhr.loaded > 0) {
      const mb = (xhr.loaded / (1024 * 1024)).toFixed(1);
      loaderText.textContent = `Loading the dream… ${mb} MB`;
    }
  },
  (err) => {
    console.error('Failed to load city model', err);
    loaderText.textContent = 'Could not load the city model. Check the console for details.';
    startBtnLabel.textContent = 'Unavailable';
  },
);

function tweakMaterial(material) {
  if ('roughness' in material && material.roughness === undefined) {
    material.roughness = 0.95;
  }
  if (material.map) {
    material.map.anisotropy = 8;
    material.map.colorSpace = THREE.SRGBColorSpace;
  }
  if (material.emissiveMap) {
    material.emissiveMap.anisotropy = 8;
  }
  material.needsUpdate = true;
}

function updateLoaderUi(pct) {
  loaderFill.style.width = `${pct}%`;
  loaderText.textContent = `Loading the dream… ${pct}%`;
}

function finishLoading() {
  updateLoaderUi(100);
  loaderText.textContent = 'Dream ready.';
  startBtn.disabled = false;
  startBtnLabel.textContent = 'Begin Dream';
  overlayHint.innerHTML = 'Click <em>Begin Dream</em> to enter — your cursor will lock to the world.';
}

function respawn() {
  controls.object.position.copy(player.spawn);
  player.velocity.set(0, 0, 0);
}

/* ============================================================
 * Movement & collision
 * ============================================================ */

const tmpForward = new THREE.Vector3();
const tmpRight = new THREE.Vector3();
const tmpMove = new THREE.Vector3();
const tmpDown = new THREE.Vector3(0, -1, 0);

function updateMovement(dt) {
  if (!controls.isLocked) {
    return;
  }

  controls.getDirection(tmpForward);
  if (!player.flying) {
    tmpForward.y = 0;
  }
  tmpForward.normalize();

  tmpRight.copy(tmpForward).cross(camera.up).normalize();

  let moveX = 0;
  let moveZ = 0;
  if (keys.forward) moveZ += 1;
  if (keys.back) moveZ -= 1;
  if (keys.right) moveX += 1;
  if (keys.left) moveX -= 1;

  const inputLen = Math.hypot(moveX, moveZ);
  if (inputLen > 0) {
    moveX /= inputLen;
    moveZ /= inputLen;
  }

  const baseSpeed = player.flying
    ? PLAYER.flySpeed
    : keys.sprint
      ? PLAYER.sprintSpeed
      : PLAYER.walkSpeed;

  tmpMove.set(0, 0, 0);
  tmpMove.addScaledVector(tmpForward, moveZ * baseSpeed);
  tmpMove.addScaledVector(tmpRight, moveX * baseSpeed);

  if (player.flying) {
    let vy = 0;
    if (keys.up) vy += 1;
    if (keys.down) vy -= 1;
    tmpMove.y = vy * baseSpeed;

    // Smooth velocity in fly mode (no gravity).
    player.velocity.x = THREE.MathUtils.damp(player.velocity.x, tmpMove.x, PLAYER.damping, dt);
    player.velocity.y = THREE.MathUtils.damp(player.velocity.y, tmpMove.y, PLAYER.damping, dt);
    player.velocity.z = THREE.MathUtils.damp(player.velocity.z, tmpMove.z, PLAYER.damping, dt);
  } else {
    // Smooth horizontal velocity, gravity for vertical.
    player.velocity.x = THREE.MathUtils.damp(player.velocity.x, tmpMove.x, PLAYER.damping, dt);
    player.velocity.z = THREE.MathUtils.damp(player.velocity.z, tmpMove.z, PLAYER.damping, dt);

    if (keys.jump && player.onGround) {
      player.velocity.y = PLAYER.jumpSpeed;
      player.onGround = false;
    }

    player.velocity.y -= PLAYER.gravity * dt;
  }

  // Step horizontal collision: prevent walking through walls.
  const nextPos = controls.object.position.clone();
  nextPos.x += player.velocity.x * dt;
  nextPos.z += player.velocity.z * dt;
  resolveHorizontalCollisions(nextPos, controls.object.position);

  // Apply vertical velocity (we'll resolve ground after).
  nextPos.y += player.velocity.y * dt;

  controls.object.position.copy(nextPos);

  if (!player.flying) {
    resolveGround();
  }

  // Prevent falling forever — respawn if we drop too far.
  if (controls.object.position.y < -200) {
    respawn();
  }
}

function resolveHorizontalCollisions(nextPos, currentPos) {
  if (collidableMeshes.length === 0) return;
  const dx = nextPos.x - currentPos.x;
  const dz = nextPos.z - currentPos.z;
  const dist = Math.hypot(dx, dz);
  if (dist < 1e-5) return;

  const dir = new THREE.Vector3(dx, 0, dz).normalize();
  const origin = new THREE.Vector3(currentPos.x, currentPos.y - PLAYER.eyeHeight * 0.5, currentPos.z);
  horizontalRaycaster.set(origin, dir);
  horizontalRaycaster.far = PLAYER.radius + dist;
  const hits = horizontalRaycaster.intersectObjects(collidableMeshes, false);
  if (hits.length > 0) {
    const hit = hits[0];
    if (hit.distance < PLAYER.radius + 0.05) {
      // Cancel motion into the wall.
      nextPos.x = currentPos.x;
      nextPos.z = currentPos.z;
      player.velocity.x = 0;
      player.velocity.z = 0;
    }
  }
}

function resolveGround() {
  if (collidableMeshes.length === 0) return;
  const origin = controls.object.position.clone();
  origin.y += 0.5; // start a bit above the camera position to avoid origin-inside-mesh
  downRaycaster.set(origin, tmpDown);
  const hits = downRaycaster.intersectObjects(collidableMeshes, false);
  if (hits.length === 0) {
    player.onGround = false;
    return;
  }
  const hit = hits[0];
  const groundY = hit.point.y;
  const desiredY = groundY + PLAYER.eyeHeight;

  if (controls.object.position.y <= desiredY) {
    controls.object.position.y = desiredY;
    if (player.velocity.y < 0) player.velocity.y = 0;
    player.onGround = true;
  } else {
    player.onGround = false;
  }
}

/* ============================================================
 * Helpers
 * ============================================================ */

function makeDustField(count, radius) {
  const positions = new Float32Array(count * 3);
  const seeds = new Float32Array(count);
  for (let i = 0; i < count; i++) {
    const r = Math.cbrt(Math.random()) * radius;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    positions[i * 3 + 0] = r * Math.sin(phi) * Math.cos(theta);
    positions[i * 3 + 1] = r * Math.cos(phi) * 0.5 + 4;
    positions[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta);
    seeds[i] = Math.random();
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geo.setAttribute('seed', new THREE.BufferAttribute(seeds, 1));
  geo.userData.radius = radius;

  const mat = new THREE.PointsMaterial({
    color: 0xffd9b8,
    size: 0.08,
    sizeAttenuation: true,
    transparent: true,
    opacity: 0.55,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const points = new THREE.Points(geo, mat);
  points.frustumCulled = false;
  points.name = 'dust_field';
  return points;
}

function updateDustField(dt, t) {
  const positions = dustField.geometry.attributes.position;
  const seeds = dustField.geometry.attributes.seed;
  const radius = dustField.geometry.userData.radius;
  const player = controls.object.position;
  for (let i = 0; i < positions.count; i++) {
    const idx = i * 3;
    let x = positions.array[idx];
    let y = positions.array[idx + 1];
    let z = positions.array[idx + 2];
    const seed = seeds.array[i];

    // Slow drift + tiny vertical bob.
    x += dt * (0.3 + seed * 0.4);
    y += Math.sin(t * 0.3 + seed * 6.28) * 0.0025;

    // Wrap relative to the player so dust always surrounds them.
    const dx = x - player.x;
    const dz = z - player.z;
    if (dx > radius) x -= radius * 2;
    if (dx < -radius) x += radius * 2;
    if (dz > radius) z -= radius * 2;
    if (dz < -radius) z += radius * 2;
    if (y - player.y > radius * 0.6) y -= radius * 0.8;
    if (y - player.y < -radius * 0.4) y += radius * 0.8;

    positions.array[idx] = x;
    positions.array[idx + 1] = y;
    positions.array[idx + 2] = z;
  }
  positions.needsUpdate = true;
}

function makeSkyTexture(topHex, bottomHex) {
  const size = 256;
  const canvasEl = document.createElement('canvas');
  canvasEl.width = 2;
  canvasEl.height = size;
  const ctx = canvasEl.getContext('2d');
  const gradient = ctx.createLinearGradient(0, 0, 0, size);
  gradient.addColorStop(0, '#' + topHex.toString(16).padStart(6, '0'));
  gradient.addColorStop(1, '#' + bottomHex.toString(16).padStart(6, '0'));
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 2, size);
  const tex = new THREE.CanvasTexture(canvasEl);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.mapping = THREE.EquirectangularReflectionMapping;
  tex.needsUpdate = true;
  return tex;
}

/* ============================================================
 * Render loop
 * ============================================================ */

const clock = new THREE.Clock();

function tick() {
  const dt = Math.min(clock.getDelta(), 1 / 30);
  const t = clock.elapsedTime;
  updateMovement(dt);
  updateDustField(dt, t);

  // Track sun with player so shadows stay near the camera.
  sun.position.set(
    controls.object.position.x + 80,
    controls.object.position.y + 120,
    controls.object.position.z + 60,
  );
  sun.target.position.copy(controls.object.position);

  // HUD
  if (controls.isLocked) {
    const speed = Math.hypot(player.velocity.x, player.velocity.z);
    hudSpeed.textContent = `${speed.toFixed(1)} m/s`;
    const p = controls.object.position;
    hudPos.textContent = `${p.x.toFixed(0)}, ${p.y.toFixed(0)}, ${p.z.toFixed(0)}`;
  }

  composer.render();
  requestAnimationFrame(tick);
}

tick();
