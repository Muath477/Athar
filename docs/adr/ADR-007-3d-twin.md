# ADR-007: GLB mesh with facade planes; Gaussian splat optional

- Status: Accepted (pending team review)
- Date: 2026-11-16

## Context

The dashboard pins findings on a 3D model of one building. Pins must land on the right facade (>= 90%). Splats look better but are harder to raycast and to keep light on laptops.

## Decision

Phone photogrammetry → Blender cleanup → GLB compressed with gltf-transform (Draco + KTX2), <= 15 MB. Facades are defined by 4 corner points each in `facade_map.json`; pins are computed analytically from facade UV, not by raycasting a noisy mesh. Viewer: three.js via @react-three/fiber and drei. Spark is used only if the scan ends up as a splat.

## Alternatives considered

- **Raycast pins onto the mesh**: precise on clean meshes, fragile on photogrammetry holes.
- **Splat-first**: best visuals, extra library, pins still need facade planes.
- **2D elevation drawings**: easy, loses the "digital twin" story.

## Consequences

- Pin placement is deterministic and testable (facade UV → xyz).
- Facade corners must be placed by hand once per building (about 30 minutes).

## Versions

three 0.187.0, @react-three/fiber 9.8.2, @react-three/drei 10.7.9, @sparkjsdev/spark 2.4.0, @gltf-transform/cli 4.5.1 (npm, 2026-11-16).
