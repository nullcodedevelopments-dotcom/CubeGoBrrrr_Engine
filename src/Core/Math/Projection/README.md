# Projection

This folder contains `projection.py`, which implements the `Projection` utility class — a set of static methods that handle the full **world-to-screen pipeline**: building projection matrices, converting between coordinate spaces, and mapping 3D world points to 2D screen pixels (and back).

---

## File: `projection.py`

### Overview

The journey from a 3D world position to a pixel on screen passes through several coordinate spaces:

```
World Space
    ↓  (view matrix)
View / Camera Space
    ↓  (projection matrix)
Clip Space
    ↓  (perspective division ÷w)
NDC  (Normalized Device Coordinates, range [-1,1]³)
    ↓  (viewport transform)
Screen / Pixel Space
```

`Projection` encapsulates each step of this pipeline as a named, reusable static method, as well as the reverse path (screen → world) for picking and ray casting.

### Dependencies

```python
from src.Core.Math.Matrices.matrices import Matrix4x4
from src.Core.Math.Vectors.vectors import Vector3
```

---

## Class: `Projection`

### Projection Matrix Builders

#### `perspective(fov_radians, aspect_ratio, near_plane, far_plane) → Matrix4x4`
Constructs an **OpenGL-style perspective projection matrix**.

**Derivation:**
- `f = 1 / tan(fov_y / 2)` — the focal length. A smaller FOV (zoomed in) gives a larger `f`, compressing the image.
- `f / aspect_ratio` — corrects the x-scale for non-square viewports (e.g., a 16:9 screen).
- The z column maps `[near, far]` to `[-1, 1]` in NDC:
  ```
  M[2,2] = (far + near) / (near - far)
  M[2,3] = 2·far·near / (near - far)
  ```
- `M[3,2] = -1` causes the `w` component of a clip-space point to equal `-z_view`, enabling perspective division.

The resulting matrix:
```
[f/a,  0,         0,              0    ]
[ 0,   f,         0,              0    ]
[ 0,   0,  (n+f)/(n-f),  2nf/(n-f)   ]
[ 0,   0,        -1,              0    ]
```

#### `orthographic(left, right, bottom, top, near_plane, far_plane) → Matrix4x4`
Constructs an **orthographic (parallel) projection matrix**.

Unlike perspective, there is no foreshortening — distant objects appear the same size as nearby ones. Used for UIs, 2D games, technical drawings, and shadow maps.

The matrix maps the view frustum box `[left,right] × [bottom,top] × [near,far]` uniformly to the NDC cube `[-1,1]³`:
```
M[0,0] = 2/width,    M[0,3] = -(right+left)/width
M[1,1] = 2/height,   M[1,3] = -(top+bottom)/height
M[2,2] = -2/depth,   M[2,3] = -(far+near)/depth
M[3,3] = 1
```

**Guard:** if any dimension (`width`, `height`, or `depth`) is less than `1e-10`, the matrix is degenerate (zero-area viewport or zero-length depth range), so `Matrix4x4.identity()` is returned as a safe fallback.

---

### Coordinate Space Conversions

#### `clip_to_ndc(clip_x, clip_y, clip_z, clip_w) → tuple[float, float, float]`
Performs **perspective division**: divides the clip-space coordinates by `w` to obtain Normalized Device Coordinates in the range `[-1, 1]³`:
```
ndc_x = clip_x / clip_w
ndc_y = clip_y / clip_w
ndc_z = clip_z / clip_w
```
**Guard:** if `|clip_w| < 1e-10` (degenerate — the point is at or behind the camera), returns `(0, 0, 0)` to avoid division by zero. The comment in the source notes this function is for NDC conversion; the `clip_w ≤ 0` early-out in `projection_point` provides an upstream guard.

NDC coordinates are hardware-independent: `(-1,-1,-1)` is the back-bottom-left corner of the view frustum and `(1,1,1)` is the front-top-right corner.

#### `ndc_to_screen(ndc_x, ndc_y, screen_width, screen_height) → tuple[int, int]`
Maps an NDC point to integer **pixel coordinates**:
```
screen_x = int( (ndc_x + 1.0) * 0.5 * screen_width  )
screen_y = int( (1.0 - (ndc_y + 1.0) * 0.5) * screen_height )
```
- `(ndc_x + 1) * 0.5` remaps `[-1, 1] → [0, 1]`, then multiply by width to get pixel x.
- The y-axis is **flipped** (`1.0 - …`) because NDC y-up conflicts with screen y-down (pixel (0,0) is the top-left in most screen APIs).

The result is truncated to `int` (floor). No clamping is applied — callers are expected to clip against the viewport bounds if needed.

---

### High-Level Pipeline Methods

#### `projection_point(world_point, projection_matrix, view_matrix, viewport_width, viewport_height) → Optional[tuple[int, int]]`
The complete **3D → 2D screen pixel** pipeline for a single point:

1. **World → View**: `view_x, view_y, view_z = view_matrix.transform_point(world_point)` — moves the point into camera space using the view matrix.
2. **View → Clip**: `clip_x, clip_y, clip_z, clip_w = projection_matrix.transform_vector4(view_x, view_y, view_z, 1.0)` — applies the projection matrix (returns 4 clip-space components).
3. **Behind-camera check**: if `clip_w ≤ 0`, the point is behind or at the near plane; return `None` to signal "not visible."
4. **Clip → NDC**: `Projection.clip_to_ndc(…)` — perspective division.
5. **NDC → Screen**: `Projection.ndc_to_screen(…)` — remaps to pixel coordinates.

Returns `Optional[tuple[int, int]]` — callers must handle the `None` case (point is behind the camera or outside the clip region).

#### `unproject_point(screen_x, screen_y, depth_ndc, projection_matrix, view_matrix, viewport_width, viewport_height) → Optional[Vector3]`
The **reverse pipeline** — converts a screen pixel coordinate + depth back to a 3D world position. Used for mouse picking, ray generation, and depth buffer reconstruction.

Steps:
1. **Screen → NDC**:
   ```
   ndc_x = (screen_x / width)  * 2.0 - 1.0
   ndc_y = 1.0 - (screen_y / height) * 2.0
   ```
   (The y-axis is flipped again to go from screen y-down back to NDC y-up.)

2. **Invert the combined projection-view matrix**: `(projection_matrix * view_matrix).inverse()`. Returns `None` if the combined matrix is singular (degenerate camera setup).

3. **NDC → World (homogeneous)**: Apply the inverse matrix to the NDC point `(ndc_x, ndc_y, depth_ndc, 1.0)` via `transform_vector4`. The result has a `w` component due to the projective nature of the matrix.

4. **Perspective un-divide**: if `|world_w| < 1e-10` return `None`; otherwise divide all components by `world_w` to recover the true 3D position:
   ```
   return Vector3(world_x / world_w, world_y / world_w, world_z / world_w)
   ```

---

## Design Notes

- **Two separate `perspective` implementations** — there is also `Matrix4x4.perspective` in `matrices.py`. The `Projection.perspective` method here uses the same OpenGL convention but is expressed slightly differently (computes `depth_range = near - far` explicitly). Both are equivalent; `Projection` is the higher-level, pipeline-oriented API while `Matrix4x4` exposes the raw matrix.
- **`Optional` return types** — `projection_point` and `unproject_point` return `None` rather than raising exceptions for out-of-view or degenerate inputs. This is the correct design for real-time rendering where many points will routinely be off-screen.
- **Integer screen coordinates** — `ndc_to_screen` truncates to `int`, which matches rasteriser conventions. Sub-pixel accuracy (for anti-aliasing or smooth animation) would require keeping `float` coordinates.
- **`depth_ndc` parameter in `unproject_point`** — the caller supplies the depth in NDC space (typically read from the depth buffer). A value of `-1.0` corresponds to the near plane; `+1.0` corresponds to the far plane.
