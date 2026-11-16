# ADR-005: Classical alignment + difference map + LLM judgment with a deterministic label rule

- Status: Accepted (pending team review)
- Date: 2026-11-16

## Context

Visitor photos differ from baselines in angle, lens and light; shadows can look like cracks. We cannot train a damage model in 3 days. Every finding must carry evidence.

## Decision

Pipeline in 03-architecture §9: quality gate → SIFT + MAGSAC homography alignment → LAB/CLAHE normalization → SSIM + gradient difference map with a lighting flag → Sonnet judgment restricted to numbered difference regions → optional pretrained YOLO segmentation → pure-function label rule (`verification/domain/labels.py`). `Confirmed` only after >= 2 independent confirmations or expert approval. Thresholds in §9 are starting values; final values are recorded here after tuning on the 50-image set.

## Alternatives considered

- **LLM-only comparison** (send both photos, ask "what changed"): fastest to build but no pixel evidence and more hallucinated changes.
- **Pretrained crack segmentation only**: finds cracks that already existed; does not detect change or encroachments.
- **Deep feature matchers** (learned matchers): more robust alignment, heavier dependencies; revisit if SIFT fails on the test set.

## Consequences

- The model cannot report a change where pixels did not change, which directly supports "0 unverified reports".
- Real changes hidden by poor alignment are missed (lower recall); mitigated by the overlay and retake loop.
- Ultralytics YOLO is AGPL-3.0: kept optional and off by default; license review before commercial use.

## Versions

opencv-python-headless 5.0.0.93, scikit-image 0.26.0, numpy 2.5.5, ultralytics 8.4.215 (optional) (PyPI, 2026-11-16). YuNet model: `face_detection_yunet_2023mar.onnx` from opencv_zoo (OpenCV 5.0 docs via Context7). Tuned thresholds: TBD after Nov 18.
