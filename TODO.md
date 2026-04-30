# TODO

## Math module logging

### Math data and events that should be logged

- Vector operations
  - `Vector2`, `Vector3`, `Vector4` input values
  - addition, subtraction, scalar multiplication/division
  - dot product, cross product, length, length squared
  - normalization attempts and zero-length guard behavior
  - conversions between vector dimensions (`xy`, `xz`, `yz`, `xyz`)

- Matrix operations
  - creation of `Matrix3x3` and `Matrix4x4` matrices
  - identity/translation/scale/rotation matrix parameters
  - matrix multiplication, addition, subtraction results
  - transpose, determinant values, inverse success/failure
  - vector transform results and invalid transform conditions

- Quaternion operations
  - quaternion construction, identity, negation
  - conversions from axis-angle, Euler angles, matrix3x3
  - conversions to matrix3x3, matrix4x4, Euler angles
  - dot product, length, length squared, normalization and invalid quaternion handling
  - conjugate/inverse results and failure cases
  - `rotate_vector` input vector and output rotated vector
  - `slerp` start/end/quaternion dot, theta, fallback linear path

- Rotation operations
  - Euler-to-matrix and matrix-to-Euler conversion inputs and outputs
  - axis-angle conversion inputs and results for matrix/quaternion
  - quaternion conversion inputs and outputs
  - compose/invert rotation operations and their matrix/quaternion outputs

- Projection operations
  - perspective and orthographic matrix creation parameters and matrices
  - clip-to-NDC conversion, clip coordinates and NDC output
  - NDC-to-screen conversion and screen coordinate output
  - projection point transforms and `None` cases when clip_w <= 0
  - unprojection inputs, inverse matrix availability, and computed world coordinates

- Raytracing / geometry operations
  - ray origin/direction values
  - triangle/sphere/plane/box/cylinder/cone intersection inputs
  - intersection coefficients, discriminants, barycentric weights, and parameters
  - intersection results and misses, including reason for failure
  - barycentric and normal interpolation input points and output values
  - culling decisions and cull mode results

- Interpolation operations
  - scalar/vector interpolation inputs and outputs
  - clamped parameter values for `smoothstep`/`smootherstep`
  - Slerp dot-product clamping and fallback behavior
  - triangular, cubic, bilinear, bicubic interpolation inputs and outputs

## File I/O module logging

- Path handling and directory operations
  - resolved project root and asset directory paths
  - directory creation via `ensure_directory`
  - invalid path fragments or missing directories

- File read/write operations
  - text and binary file read/write attempts
  - append operations and write results
  - file I/O exceptions and missing file reports

- Asset loading
  - shader load requests and shader pair resolution
  - texture load requests for BMP/TGA/PNG
  - file signature checks and header metadata: width, height, channels, bit depth, compression, origin
  - parse failures and unsupported format errors
  - pixel data parsing steps for BMP/TGA/PNG, including row orientation and filter type handling

## Logging module TODO

- `src/Core/Utils/Logging/logging_handler.py`
  - replace the hard-coded event-type chain with a dispatch/template map
  - define a clear event category config model
  - use `event_type` directly instead of `Log Type` mismatch
  - avoid shared mutable class state for events and log storage
  - add explicit configuration helpers for enabled categories and filters
  - standardize invalid-event handling (return vs exception)

- `src/Core/Utils/Logging/calculations_logger.py`
  - implement per-category calculation event logging
  - capture math/physics/geometry diagnostics and result metadata
  - support event severity and explicit failure logging

- `src/Core/Utils/Logging/input_logger.py`
  - log raw input events, state changes, and input-processing results
  - capture timing / input frame state for debugging

- `src/Core/Utils/Logging/mainstream_logger.py`
  - implement the main logger backend or wrapper for Python `logging`
  - route log events to file, console, and/or in-memory storage
  - support log levels, timestamps, and structured payloads

## Utils module logging and TODO

- `Core/Utils` should have a centralized log strategy
  - unify FileIO logs, calculation logs, and input logs
  - define event categories and payload schemas
  - decide whether to preserve raw dict logs or structured model objects

- Additional Utils areas to log once implemented
  - timing and performance metrics
  - platform-specific initialization and detection
  - user settings load/save events
  - data structure state/debug snapshots

## Project notes

- `src/BUILD.md` currently only contains a placeholder TODO
- `TODO.md` should become the main task list for logging and math telemetry work

## Full audit report

- `src/Core/Math/Transforms/transforms.py`
  - Logic flow is implemented correctly for `Transform` and `TransformPipeline` and the module imports successfully when the repo root is on `PYTHONPATH`.
  - `Transform.to_model_matrix()` uses `translation * rotation * scale`, which is reasonable but should be verified against the engine's column/row matrix convention.
  - `Transform.decompose()` computes scale from column norms and uses `0.0` for inverse scale when a scale component is near zero. This can silently degrade rotation extraction instead of failing safely.
  - `TransformPipeline.world_to_ndc()` correctly guards `clip_w <= 0.0`, but `Projection.clip_to_ndc()` returns `(0.0, 0.0, 0.0)` for near-zero `clip_w`, which may hide invalid projection cases.

- `src/Core/Utils/FileIO/paths.py`
  - Root path detection is brittle: `Path(__file__).resolve().parent[4]` depends on the file staying exactly four levels deep.
  - The helper functions currently resolve asset directories under `Assets/*`, but the repository root does not contain an `Assets` folder.
  - This mismatch means path helpers are not aligned with the current repo layout and should be audited before file I/O is used.

- Typing and style inconsistencies across the codebase
  - `src/Core/Math/Matrices/matrices.py`, `src/Core/Math/Geometry/raytracing.py`, `src/Core/Math/Quaternions/quaternions.py`, `src/Core/Math/Rotations/rotations.py`, and `src/Core/Math/Interpolation/interpolation.py` still use `from typing import Any, List, Tuple` and old-style generic names.
  - `src/Core/Math/Projection/projection.py` and `src/Core/Math/Transforms/transforms.py` use built-in generic syntax like `tuple[int, int]` and `Matrix3x3 | None`.
  - The alias `Vector = Any` in `matrices.py` weakens type safety and should be replaced with concrete vector types or a common vector protocol.
  - Some modules use `__future__ import annotations` while others do not, increasing the chance of inconsistent annotation resolution.

- Files requiring follow-up work
  - `src/Core/Utils/FileIO/paths.py`
  - `src/Core/Math/Transforms/transforms.py`
  - `src/Core/Math/Matrices/matrices.py`
  - `src/Core/Math/Projection/projection.py`
  - `src/Core/Math/Geometry/raytracing.py`
  - `src/Core/Math/Quaternions/quaternions.py`
  - `src/Core/Math/Rotations/rotations.py`
  - `src/Core/Math/Interpolation/interpolation.py`
  - `src/Core/Utils/FileIO/asset_loader.py` (verify asset path assumptions)

- Next Steps
  - Standardize type annotations across modules using either `typing` imports or built-in generics consistently.
  - Replace brittle root path logic in `paths.py` with a package-aware or config-driven project root resolver.
  - Add explicit failure handling for zero-scale decomposition and invalid projection states.
  - Confirm the matrix multiplication order and projection conventions match the rest of the engine.
