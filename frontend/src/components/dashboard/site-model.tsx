"use client";

import { Bounds, OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { useMemo } from "react";
import * as THREE from "three";
import type { Facade, Finding } from "@/lib/api";

const SEVERITY_COLOR: Record<Finding["severity"], string> = {
  watch: "#c9a227",
  moderate: "#d06a1f",
  urgent: "#b3261e",
};

type Props = {
  facades: Facade[];
  findings: Finding[];
  selectedId: string | null;
  onSelect: (findingId: string) => void;
};

/** The site as its facade planes from the facade map, with one pin per published finding. */
export function SiteModel({ facades, findings, selectedId, onSelect }: Props) {
  return (
    <Canvas camera={{ position: [14, 9, 14], fov: 45 }} className="rounded-xl bg-[#d9c7aa]">
      <ambientLight intensity={0.7} />
      <directionalLight position={[10, 15, 5]} intensity={1.2} />
      <Bounds fit clip observe margin={1.3}>
        {facades.map((facade) => (
          <FacadePlane key={facade.id} corners={facade.corners} />
        ))}
      </Bounds>
      {findings.map((finding) => (
        <mesh
          key={finding.id}
          position={finding.pin_xyz as [number, number, number]}
          onClick={(event) => {
            event.stopPropagation();
            onSelect(finding.id);
          }}
        >
          <sphereGeometry args={[finding.id === selectedId ? 0.32 : 0.22, 24, 24]} />
          <meshStandardMaterial
            color={SEVERITY_COLOR[finding.severity]}
            emissive={SEVERITY_COLOR[finding.severity]}
            emissiveIntensity={finding.label === "confirmed" ? 0.6 : 0.2}
          />
        </mesh>
      ))}
      <mesh rotation-x={-Math.PI / 2} position-y={-0.01}>
        <planeGeometry args={[40, 40]} />
        <meshStandardMaterial color="#cdb38c" />
      </mesh>
      <OrbitControls makeDefault maxPolarAngle={Math.PI / 2.05} />
    </Canvas>
  );
}

function FacadePlane({ corners }: { corners: number[][] }) {
  const geometry = useMemo(() => {
    // Corners are bottom-left, bottom-right, top-right, top-left: two triangles make the wall.
    const positions = new Float32Array(corners.flat());
    const shape = new THREE.BufferGeometry();
    shape.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    shape.setIndex([0, 1, 2, 0, 2, 3]);
    shape.computeVertexNormals();
    return shape;
  }, [corners]);

  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial color="#b3804f" side={THREE.DoubleSide} roughness={0.95} />
    </mesh>
  );
}
