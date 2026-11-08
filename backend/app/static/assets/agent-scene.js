import * as THREE from "./vendor/three.js";

const canvas = document.getElementById("agentCanvas");
const viewport = document.getElementById("sceneViewport");
const labelsRoot = document.getElementById("sceneLabels");
const status = document.getElementById("renderStatus");
const metadata = window.AegisStages || [];
const motionPreference = matchMedia("(prefers-reduced-motion: reduce)");
let renderer;
try {
  renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: true,
    powerPreference: "low-power",
  });
} catch {
  document.getElementById("sceneFallback").hidden = false;
  canvas.hidden = true;
  status.textContent = "ACCESSIBLE STAGE VIEW";
}
if (renderer) {
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
  renderer.setClearColor(0x0a101b, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.3;
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x0a101b, 0.025);
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 70);
  camera.position.set(0, 7.8, 12.6);
  camera.lookAt(0, 0.3, 0);
  scene.add(new THREE.AmbientLight(0x8e9acb, 1.5));
  const key = new THREE.DirectionalLight(0xb4c9ff, 4);
  key.position.set(3, 8, 5);
  scene.add(key);
  const rim = new THREE.PointLight(0x8f65ee, 32, 20);
  rim.position.set(-4, 3, -3);
  scene.add(rim);
  const cold = new THREE.PointLight(0x719fff, 25, 18);
  cold.position.set(4, 3, 1);
  scene.add(cold);
  const rig = new THREE.Group();
  scene.add(rig);
  const material = (color, roughness = 0.3, metalness = 0.7) =>
    new THREE.MeshStandardMaterial({ color, roughness, metalness });
  const baseMaterial = material(0x1d273b, 0.45, 0.75);
  const coreMaterial = material(0x5d5a8b, 0.27, 0.85);
  const positions = [
    [-3.8, 0, 0.1],
    [-2.05, 0, -2.7],
    [2.05, 0, -2.7],
    [3.8, 0, 0.1],
    [1.85, 0, 2.65],
    [-1.85, 0, 2.65],
  ];
  const colors = [0xb9a0fa, 0x87a8f4, 0x9b94e4, 0xbd9de1, 0x8ba9ec, 0x84b4d0];
  const modules = [],
    hitMeshes = [],
    raycaster = new THREE.Raycaster(),
    mouse = new THREE.Vector2();
  const reduced = () => motionPreference.matches;
  let paused = reduced(),
    active = false,
    selected = 0,
    angle = 0,
    targetAngle = 0,
    last = 0,
    drag = null;
  const circle = (radius, color, opacity) => {
    const points = [];
    for (let n = 0; n <= 160; n++) {
      const a = (n / 160) * Math.PI * 2;
      points.push(
        new THREE.Vector3(Math.cos(a) * radius, 0.025, Math.sin(a) * radius),
      );
    }
    return new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(points),
      new THREE.LineBasicMaterial({ color, transparent: true, opacity }),
    );
  };
  for (const radius of [1.15, 1.42, 3.3, 4.45, 4.58])
    rig.add(circle(radius, 0x6c76ae, radius > 4 ? 0.14 : 0.09));
  const grid = new THREE.GridHelper(15, 30, 0x27324a, 0x1a2439);
  grid.material.transparent = true;
  grid.material.opacity = 0.22;
  grid.position.y = -0.08;
  rig.add(grid);
  const plate = new THREE.Mesh(
    new THREE.CylinderGeometry(1.05, 1.15, 0.12, 64),
    baseMaterial,
  );
  plate.position.y = 0.03;
  rig.add(plate);
  const pedestal = new THREE.Mesh(
    new THREE.CylinderGeometry(0.72, 0.86, 0.26, 6),
    material(0x272d47, 0.35, 0.85),
  );
  pedestal.position.y = 0.2;
  rig.add(pedestal);
  const halo = new THREE.Mesh(
    new THREE.TorusGeometry(0.78, 0.009, 6, 100),
    new THREE.MeshBasicMaterial({
      color: 0x8e82cd,
      transparent: true,
      opacity: 0.6,
    }),
  );
  halo.rotation.x = Math.PI / 2;
  halo.position.y = 0.36;
  rig.add(halo);
  const core = new THREE.Group();
  core.position.y = 1;
  rig.add(core);
  const shape = new THREE.Shape();
  shape.moveTo(0, 0.65);
  shape.lineTo(0.48, 0.38);
  shape.lineTo(0.38, -0.25);
  shape.lineTo(0, -0.58);
  shape.lineTo(-0.38, -0.25);
  shape.lineTo(-0.48, 0.38);
  shape.closePath();
  const shield = new THREE.Mesh(
    new THREE.ExtrudeGeometry(shape, {
      depth: 0.13,
      bevelEnabled: true,
      bevelSize: 0.045,
      bevelThickness: 0.035,
      bevelSegments: 2,
      steps: 1,
    }),
    coreMaterial,
  );
  shield.position.z = -0.07;
  core.add(shield);
  const outline = new THREE.LineSegments(
    new THREE.EdgesGeometry(shield.geometry),
    new THREE.LineBasicMaterial({
      color: 0xc4adff,
      transparent: true,
      opacity: 0.7,
    }),
  );
  outline.position.copy(shield.position);
  core.add(outline);
  const markPoints = [
    [-0.2, -0.12, 0.12],
    [0, 0.32, 0.12],
    [0.2, -0.12, 0.12],
    [-0.11, 0.04, 0.12],
    [0.11, 0.04, 0.12],
  ];
  const markGeometry = new THREE.BufferGeometry().setFromPoints(
    markPoints.map((p) => new THREE.Vector3(...p)),
  );
  const mark = new THREE.Line(
    markGeometry,
    new THREE.LineBasicMaterial({ color: 0xe1d6ff }),
  );
  core.add(mark);
  const orbital = new THREE.Mesh(
    new THREE.TorusGeometry(1.05, 0.012, 6, 90),
    new THREE.MeshBasicMaterial({
      color: 0x6a82b5,
      transparent: true,
      opacity: 0.32,
    }),
  );
  orbital.rotation.x = 1.2;
  orbital.rotation.z = 0.3;
  core.add(orbital);
  const stateColor = (state) =>
    state === "complete"
      ? 0x81c2e0
      : state === "waiting"
        ? 0xe4b876
        : ["blocked", "error"].includes(state)
          ? 0xe88097
          : 0xb9a0fa;
  positions.forEach((position, index) => {
    const group = new THREE.Group();
    group.position.set(...position);
    rig.add(group);
    const base = new THREE.Mesh(
      new THREE.CylinderGeometry(0.53, 0.66, 0.11, 6),
      baseMaterial,
    );
    base.rotation.y = Math.PI / 6;
    base.position.y = 0.09;
    group.add(base);
    base.userData.agent = index;
    hitMeshes.push(base);
    const lowerRing = new THREE.Mesh(
      new THREE.TorusGeometry(0.52, 0.012, 6, 60),
      new THREE.MeshBasicMaterial({
        color: colors[index],
        transparent: true,
        opacity: 0.3,
      }),
    );
    lowerRing.rotation.x = Math.PI / 2;
    lowerRing.position.y = 0.16;
    group.add(lowerRing);
    const body = new THREE.Group();
    body.position.y = 0.62;
    group.add(body);
    const shell = new THREE.MeshStandardMaterial({
      color: colors[index],
      metalness: 0.75,
      roughness: 0.23,
      emissive: colors[index],
      emissiveIntensity: 0.09,
    });
    let geometry;
    if (index === 0)
      geometry = new THREE.TorusKnotGeometry(0.27, 0.075, 70, 10, 2, 3);
    else if (index === 1) geometry = new THREE.OctahedronGeometry(0.4, 0);
    else if (index === 2) geometry = new THREE.BoxGeometry(0.48, 0.13, 0.48);
    else if (index === 3) geometry = new THREE.DodecahedronGeometry(0.37, 0);
    else if (index === 4) geometry = new THREE.IcosahedronGeometry(0.37, 0);
    else geometry = new THREE.TorusGeometry(0.31, 0.07, 10, 60);
    const mesh = new THREE.Mesh(geometry, shell);
    mesh.userData.agent = index;
    body.add(mesh);
    hitMeshes.push(mesh);
    if (index === 2) {
      for (const height of [-0.23, 0.23]) {
        const layer = new THREE.Mesh(geometry, shell);
        layer.position.y = height;
        layer.userData.agent = index;
        body.add(layer);
        hitMeshes.push(layer);
      }
      body.rotation.y = 0.5;
    }
    if (index === 5) {
      mesh.rotation.x = 0.6;
      const ring2 = new THREE.Mesh(
        new THREE.TorusGeometry(0.38, 0.012, 5, 60),
        new THREE.MeshBasicMaterial({
          color: colors[index],
          transparent: true,
          opacity: 0.65,
        }),
      );
      ring2.rotation.y = 1.4;
      body.add(ring2);
      body.add(new THREE.Mesh(new THREE.OctahedronGeometry(0.16), shell));
    } else {
      const wire = new THREE.LineSegments(
        new THREE.EdgesGeometry(geometry),
        new THREE.LineBasicMaterial({
          color: 0xc6cbfa,
          transparent: true,
          opacity: 0.24,
        }),
      );
      body.add(wire);
    }
    const pillar = new THREE.Mesh(
      new THREE.CylinderGeometry(0.012, 0.035, 0.32, 6),
      new THREE.MeshBasicMaterial({
        color: colors[index],
        transparent: true,
        opacity: 0.3,
      }),
    );
    pillar.position.y = 0.29;
    group.add(pillar);
    const curve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(0, 0.11, 0),
      new THREE.Vector3(position[0] * 0.43, 0.11, position[2] * 0.43),
      new THREE.Vector3(position[0], 0.11, position[2]),
    ]);
    const path = new THREE.Mesh(
      new THREE.TubeGeometry(curve, 32, 0.008, 4, false),
      new THREE.MeshBasicMaterial({
        color: colors[index],
        transparent: true,
        opacity: 0.15,
      }),
    );
    rig.add(path);
    const packet = new THREE.Mesh(
      new THREE.SphereGeometry(0.025, 8, 6),
      new THREE.MeshBasicMaterial({ color: colors[index] }),
    );
    rig.add(packet);
    packet.visible = false;
    const label = document.createElement("div");
    label.className = "scene-label" + (index === 0 ? " selected" : "");
    label.dataset.stage = metadata[index]?.id;
    label.append(
      document.createElement("i"),
      document.createTextNode(metadata[index]?.name.toUpperCase() || ""),
    );
    labelsRoot.append(label);
    modules.push({
      group,
      body,
      shell,
      ring: lowerRing,
      path,
      packet,
      curve,
      label,
      state: "idle",
      pulse: 0,
    });
  });
  const particlePositions = [];
  for (let i = 0; i < 45; i++) {
    particlePositions.push(
      Math.sin(i * 17.2) * 6,
      Math.abs(Math.cos(i * 4.4)) * 3.5 + 0.25,
      Math.cos(i * 9.7) * 5,
    );
  }
  const particleGeo = new THREE.BufferGeometry();
  particleGeo.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(particlePositions, 3),
  );
  rig.add(
    new THREE.Points(
      particleGeo,
      new THREE.PointsMaterial({
        color: 0x6777a2,
        size: 0.018,
        transparent: true,
        opacity: 0.45,
        sizeAttenuation: true,
      }),
    ),
  );
  const labelPosition = new THREE.Vector3();
  function resize() {
    const width = viewport.clientWidth,
      height = viewport.clientHeight;
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.position.set(
      0,
      camera.aspect < 1.8 ? 6.4 : 4.8,
      camera.aspect < 1.8 ? 10.2 : 7.8,
    );
    camera.lookAt(0, 0.25, 0);
    camera.updateProjectionMatrix();
  }
  const observer = new ResizeObserver(resize);
  observer.observe(viewport);
  window.addEventListener("aegis:resize", () => requestAnimationFrame(resize));
  resize();
  function choose(index) {
    selected = index;
    modules[index].pulse = 1;
    targetAngle = -0.035 * (index - 2);
  }
  window.addEventListener("aegis:select-agent", (event) =>
    choose(event.detail.index),
  );
  window.addEventListener("aegis:run-start", () => {
    active = true;
    modules.forEach((module) => {
      module.state = "idle";
      module.pulse = 0;
    });
  });
  window.addEventListener("aegis:stage", (event) => {
    const index = metadata.findIndex(
      (stage) => stage.id === event.detail.stage,
    );
    if (index < 0) return;
    const module = modules[index];
    module.state = event.detail.state;
    module.pulse = 1;
  });
  window.addEventListener("aegis:run-end", () => {
    active = false;
  });
  document.getElementById("resetScene").onclick = () => {
    targetAngle = 0;
    window.AegisSelectAgent?.(0);
  };
  function motionButton() {
    const button = document.getElementById("toggleMotion");
    button.textContent = paused ? "▷" : "Ⅱ";
    button.setAttribute(
      "aria-label",
      paused ? "Resume ambient motion" : "Pause ambient motion",
    );
    button.title = button.getAttribute("aria-label");
  }
  motionButton();
  document.getElementById("toggleMotion").onclick = () => {
    paused = !paused;
    motionButton();
  };
  function hit(event) {
    const rect = canvas.getBoundingClientRect();
    mouse.set(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      (-(event.clientY - rect.top) / rect.height) * 2 + 1,
    );
    raycaster.setFromCamera(mouse, camera);
    return raycaster.intersectObjects(hitMeshes, false)[0]?.object.userData
      .agent;
  }
  canvas.addEventListener("pointerdown", (event) => {
    drag = {
      x: event.clientX,
      y: event.clientY,
      angle: targetAngle,
      moved: false,
    };
  });
  window.addEventListener("pointermove", (event) => {
    if (drag) {
      const delta = event.clientX - drag.x;
      if (Math.abs(delta) > 4) drag.moved = true;
      targetAngle = drag.angle + delta * 0.004;
    } else if (event.target === canvas) {
      canvas.style.cursor = hit(event) !== undefined ? "pointer" : "grab";
    }
  });
  window.addEventListener("pointerup", (event) => {
    if (drag && !drag.moved && event.target === canvas) {
      const index = hit(event);
      if (index !== undefined) window.AegisSelectAgent?.(index);
    }
    drag = null;
  });
  let sceneVisible = true;
  new IntersectionObserver((entries) => {
    sceneVisible = entries[0].isIntersecting;
  }).observe(viewport);
  function frame(milliseconds) {
    requestAnimationFrame(frame);
    if (document.hidden || !sceneVisible || milliseconds - last < 1000 / 35)
      return;
    last = milliseconds;
    const time = milliseconds * 0.001;
    angle += (targetAngle - angle) * 0.07;
    rig.rotation.y = angle;
    coreMaterial.emissive.set(0x7b68c5);
    coreMaterial.emissiveIntensity = active ? 0.13 : 0.02;
    if (!paused) {
      core.position.y = 1 + Math.sin(time * 0.7) * 0.035;
      orbital.rotation.z = time * 0.045;
    }
    modules.forEach((module, index) => {
      module.pulse *= 0.965;
      const running = module.state === "running";
      const color = new THREE.Color(
        module.state === "idle" ? colors[index] : stateColor(module.state),
      );
      module.shell.emissive.copy(color);
      module.shell.emissiveIntensity =
        (selected === index ? 0.3 : 0.08) +
        (running ? 0.35 : module.pulse * 0.22);
      module.ring.material.color.copy(color);
      module.ring.material.opacity =
        (selected === index ? 0.7 : 0.25) +
        (running && !paused ? Math.sin(time * 4) * 0.15 : 0);
      module.path.material.opacity = running ? 0.55 : 0.1 + module.pulse * 0.2;
      if (!paused) {
        module.body.rotation.y += running ? 0.016 : 0.002;
        module.body.position.y = 0.62 + Math.sin(time * 0.8 + index) * 0.025;
      }
      module.group.position.y = THREE.MathUtils.lerp(
        module.group.position.y,
        selected === index ? 0.14 : 0,
        0.08,
      );
      const selectedScale = selected === index ? 1.18 : 1;
      module.group.scale.setScalar(
        THREE.MathUtils.lerp(module.group.scale.x, selectedScale, 0.08),
      );
      module.packet.visible = running || module.pulse > 0.2;
      if (module.packet.visible)
        module.packet.position.copy(
          module.curve.getPoint(
            ((paused ? 0 : time) * (running ? 0.65 : 0.3) + index * 0.15) % 1,
          ),
        );
      labelPosition.set(0, 1.2, 0);
      module.group.localToWorld(labelPosition);
      labelPosition.project(camera);
      const width = viewport.clientWidth,
        height = viewport.clientHeight;
      module.label.style.left = (labelPosition.x * 0.5 + 0.5) * width + "px";
      module.label.style.top = (-labelPosition.y * 0.5 + 0.5) * height + "px";
      module.label.style.opacity = labelPosition.z < 1 ? "1" : "0";
    });
    renderer.render(scene, camera);
  }
  status.textContent = "WEBGL · INTERACTIVE 3D";
  canvas.dataset.renderer = "webgl";
  requestAnimationFrame(frame);
  canvas.addEventListener("webglcontextlost", (event) => {
    event.preventDefault();
    status.textContent = "3D CONTEXT LOST · STAGE CONTROLS AVAILABLE";
    document.getElementById("sceneFallback").hidden = false;
  });
}
