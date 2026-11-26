import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import InfoTooltip from "./InfoTooltip";

function makeTextSprite(text, color, fontSize = 26) {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  ctx.font = `600 ${fontSize}px system-ui, -apple-system, sans-serif`;
  const textWidth = Math.ceil(ctx.measureText(text).width);
  canvas.width = textWidth + 24;
  canvas.height = fontSize + 18;
  ctx.font = `600 ${fontSize}px system-ui, -apple-system, sans-serif`;
  ctx.fillStyle = color;
  ctx.textBaseline = "middle";
  ctx.textAlign = "center";
  ctx.fillText(text, canvas.width / 2, canvas.height / 2);

  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;
  const material = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: false,
  });
  const sprite = new THREE.Sprite(material);
  const aspect = canvas.width / canvas.height;
  const scaleY = 0.32;
  sprite.scale.set(scaleY * aspect, scaleY, 1);
  return sprite;
}

/** Interactive 3D trajectory of (Epoch/Step, Accuracy, Loss) using Three.js. */
export default function TrainingTrajectory3D({
  metrics = [],
  liveSamples = [],
}) {
  const containerRef = useRef(null);
  const [webglError, setWebglError] = useState(false);
  const [hovered, setHovered] = useState(null);

  const pointsData = React.useMemo(() => {
    if (metrics.length >= 2) {
      return metrics
        .filter(
          (m) =>
            Number.isFinite(Number(m.train_loss)) &&
            Number.isFinite(Number(m.val_acc ?? m.train_acc)),
        )
        .map((m, idx) => ({
          label: `Epoch ${m.epoch ?? idx + 1}`,
          short: `E${m.epoch ?? idx + 1}`,
          x: Number(m.epoch ?? idx + 1),
          y: Number(m.val_acc ?? m.train_acc),
          z: Number(m.val_loss ?? m.train_loss),
        }));
    }
    if (liveSamples.length >= 3) {
      const stride = Math.max(1, Math.floor(liveSamples.length / 40));
      return liveSamples
        .filter(
          (_, idx) => idx % stride === 0 || idx === liveSamples.length - 1,
        )
        .filter(
          (s) =>
            Number.isFinite(Number(s.batch_loss)) &&
            Number.isFinite(Number(s.running_acc)),
        )
        .map((s, idx) => ({
          label: `Step ${s.batch_idx ?? idx + 1}`,
          short: `S${s.batch_idx ?? idx + 1}`,
          x: idx + 1,
          y: Number(s.running_acc),
          z: Number(s.batch_loss),
        }));
    }
    return [];
  }, [metrics, liveSamples]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || pointsData.length < 2) return undefined;

    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      setWebglError(true);
      return undefined;
    }

    const width = container.clientWidth || 640;
    const height = 290;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height);
    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    const isDark = Boolean(
      document.querySelector(".app-shell")?.classList.contains("theme-dark"),
    );

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 100);
    camera.position.set(5.4, 3.8, 6.2);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.06;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.55;
    controls.minDistance = 3.8;
    controls.maxDistance = 14;

    const floorY = -1.2;
    const gridColor = isDark ? 0x2a3646 : 0xd6e0eb;
    const gridCenter = isDark ? 0x3b4d63 : 0xb0c0d0;
    const grid = new THREE.GridHelper(5.6, 10, gridCenter, gridColor);
    grid.position.y = floorY;
    scene.add(grid);

    scene.add(new THREE.AmbientLight(0xffffff, 0.9));
    const keyLight = new THREE.DirectionalLight(0xffffff, 0.95);
    keyLight.position.set(5, 8, 6);
    scene.add(keyLight);

    const xs = pointsData.map((p) => p.x);
    const ys = pointsData.map((p) => p.y);
    const zs = pointsData.map((p) => p.z);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const minZ = Math.min(...zs);
    const maxZ = Math.max(...zs);

    const norm = (val, lo, hi, outLo, outHi) =>
      hi - lo < 1e-6
        ? (outLo + outHi) / 2
        : outLo + ((val - lo) / (hi - lo)) * (outHi - outLo);

    // Draw labeled 3D axes anchored at (-2.4, floorY, -2.0)
    const origin = new THREE.Vector3(-2.4, floorY, -2.0);
    const addAxis = (dir, length, hex, labelText, offset) => {
      const end = origin.clone().addScaledVector(dir, length);
      const geo = new THREE.BufferGeometry().setFromPoints([origin, end]);
      const mat = new THREE.LineBasicMaterial({ color: hex });
      scene.add(new THREE.Line(geo, mat));
      const sprite = makeTextSprite(
        labelText,
        `#${hex.toString(16).padStart(6, "0")}`,
      );
      sprite.position.copy(end).add(offset);
      scene.add(sprite);
    };

    addAxis(
      new THREE.Vector3(1, 0, 0),
      4.8,
      isDark ? 0x6cb6ff : 0x2272b4,
      `X: ${pointsData[0].short} → ${pointsData.at(-1).short}`,
      new THREE.Vector3(0, -0.22, 0.25),
    );
    addAxis(
      new THREE.Vector3(0, 1, 0),
      3.0,
      isDark ? 0x56d364 : 0x1a7f37,
      `Y: Acc (${minY.toFixed(1)}%–${maxY.toFixed(1)}%)`,
      new THREE.Vector3(0.1, 0.25, 0),
    );
    addAxis(
      new THREE.Vector3(0, 0, 1),
      4.0,
      isDark ? 0xf59e0b : 0xb45309,
      `Z: Loss (${minZ.toFixed(3)}–${maxZ.toFixed(3)})`,
      new THREE.Vector3(-0.15, -0.22, 0.35),
    );

    const vectors = pointsData.map(
      (p) =>
        new THREE.Vector3(
          norm(p.x, minX, maxX, -2.1, 2.1),
          norm(p.y, minY, maxY, -0.75, 1.5),
          norm(p.z, minZ, maxZ, -1.7, 1.7),
        ),
    );

    const curve = new THREE.CatmullRomCurve3(vectors);
    const tubeGeo = new THREE.TubeGeometry(curve, 64, 0.045, 10, false);
    const tubeMat = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      emissive: 0x0ea5e9,
      emissiveIntensity: 0.35,
      roughness: 0.3,
      metalness: 0.2,
    });
    scene.add(new THREE.Mesh(tubeGeo, tubeMat));

    let bestIdx = 0;
    pointsData.forEach((p, i) => {
      if (p.y > pointsData[bestIdx].y) bestIdx = i;
    });

    const sphereGeo = new THREE.SphereGeometry(0.11, 20, 20);
    const interactiveMeshes = [];
    const labelColor = isDark ? "#e6edf3" : "#1f2328";

    vectors.forEach((vec, idx) => {
      const isBest = idx === bestIdx;
      const mat = new THREE.MeshStandardMaterial({
        color: isBest ? 0x2da44e : idx === 0 ? 0xf59e0b : 0x38bdf8,
        emissive: isBest ? 0x2da44e : 0x0284c7,
        emissiveIntensity: isBest ? 0.55 : 0.2,
        roughness: 0.25,
      });
      const mesh = new THREE.Mesh(sphereGeo, mat);
      mesh.position.copy(vec);
      if (isBest) mesh.scale.setScalar(1.35);
      mesh.userData = { point: pointsData[idx], isBest };
      scene.add(mesh);
      interactiveMeshes.push(mesh);

      if (pointsData.length <= 12 || isBest || idx === 0) {
        const tag = isBest
          ? `${pointsData[idx].short} · ${pointsData[idx].y.toFixed(1)}%`
          : pointsData[idx].short;
        const nodeSprite = makeTextSprite(
          tag,
          isBest ? "#56d364" : labelColor,
          22,
        );
        nodeSprite.position.set(vec.x, vec.y + 0.28, vec.z);
        scene.add(nodeSprite);
      }

      const stemGeo = new THREE.BufferGeometry().setFromPoints([
        vec,
        new THREE.Vector3(vec.x, floorY, vec.z),
      ]);
      const stemMat = new THREE.LineBasicMaterial({
        color: isDark ? 0x4b6078 : 0x94a3b8,
        transparent: true,
        opacity: 0.4,
      });
      scene.add(new THREE.Line(stemGeo, stemMat));
    });

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const onPointerMove = (e) => {
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hits = raycaster.intersectObjects(interactiveMeshes, false);
      if (hits.length > 0) {
        const { point, isBest } = hits[0].object.userData;
        setHovered({ ...point, isBest });
        renderer.domElement.style.cursor = "pointer";
      } else {
        setHovered(null);
        renderer.domElement.style.cursor = "grab";
      }
    };
    const onPointerLeave = () => setHovered(null);
    renderer.domElement.addEventListener("pointermove", onPointerMove);
    renderer.domElement.addEventListener("pointerleave", onPointerLeave);

    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth || 640;
      camera.aspect = w / height;
      camera.updateProjectionMatrix();
      renderer.setSize(w, height);
    };
    window.addEventListener("resize", handleResize);

    let frameId = 0;
    const animate = () => {
      frameId = window.requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      window.cancelAnimationFrame(frameId);
      window.removeEventListener("resize", handleResize);
      renderer.domElement.removeEventListener("pointermove", onPointerMove);
      renderer.domElement.removeEventListener("pointerleave", onPointerLeave);
      controls.dispose();
      tubeGeo.dispose();
      tubeMat.dispose();
      sphereGeo.dispose();
      renderer.dispose();
    };
  }, [pointsData]);

  if (pointsData.length < 2 || webglError) return null;

  return (
    <div className="trajectory-3d-wrap">
      <div className="trajectory-3d-header">
        <div className="trajectory-3d-title-row">
          <strong>3D Optimization Trajectory</strong>
          <InfoTooltip label="About 3D Optimization Trajectory">
            Plots Epoch (X), Accuracy (Y), and Loss (Z) together in 3D space. A
            healthy run climbs upward (higher accuracy) while sweeping toward
            lower loss; flat clusters or reversals highlight plateaus and
            overfitting.
          </InfoTooltip>
          <span className="trajectory-3d-legend">
            <i style={{ background: "#f59e0b" }} /> Start
            <i style={{ background: "#38bdf8" }} /> Progress
            <i style={{ background: "#2da44e" }} /> Best
          </span>
        </div>
        <span className="trajectory-3d-hint">
          {hovered
            ? `${hovered.label} · Acc ${hovered.y.toFixed(2)}% · Loss ${hovered.z.toFixed(4)}${hovered.isBest ? " (Best)" : ""}`
            : "Hover a point · Drag to orbit · Scroll to zoom"}
        </span>
      </div>
      <div
        ref={containerRef}
        className="trajectory-3d-canvas"
        role="img"
        aria-label="3D training optimization trajectory across epochs"
      />
    </div>
  );
}
