# Geometry

This folder contains `raytracing.py`, which implements the `RayCast` class — the engine's ray-geometry intersection system. A ray cast is the fundamental primitive behind rendering (ray tracing, shadow testing), physics (collision detection), and editor tools (mouse picking). Every intersection test returns the hit point in 3D world space, or `None` if there is no hit.

---

## File: `raytracing.py`

### Overview

The file defines a single class, `RayCast`, which represents an infinite ray:

```
P(t) = origin + t · direction
```

where `t ≥ 0` traces the ray forward from its origin along its direction. The class implements intersection tests against six primitive shapes, two barycentric-based interpolation helpers, and a face-culling utility.

### Type Alias

```python
Vector = Any  # expected to support .x, .y, .z, +, -, *, dot(), cross(), normalized()
```

Any `Vector3`-compatible object works.

---

## Class: `RayCast`

### Constructor

```python
RayCast(origin: Vector, direction: Vector)
```

| Attribute | Meaning |
|-----------|---------|
| `origin` | The ray's starting point in 3D world space |
| `direction` | The ray's direction vector (not required to be normalised, but must be non-zero) |

`__str__` prints both attributes for debugging.

---

### Intersection Tests

All intersection methods return `Optional[Vector]`:
- **Hit**: the 3D world-space point where the ray first intersects the shape (smallest positive `t`).
- **Miss**: `None`.

The `1e-6` threshold on `t` avoids **self-intersection** ("shadow acne") — when a ray originates from a surface it just hit, the intersection point's floating-point representation may be slightly inside the surface, yielding a spurious `t ≈ 0` hit. Requiring `t > 1e-6` ignores these.

---

#### `triangle_intersection(vertex0, vertex1, vertex2) → Optional[Vector]`
Implements the **Möller–Trumbore algorithm** — the industry-standard ray-triangle intersection test.

**Algorithm:**

1. Compute edge vectors from `vertex0`:
   ```
   edge1 = vertex1 - vertex0
   edge2 = vertex2 - vertex0
   ```

2. Compute `h = direction × edge2` (cross product). The determinant `det = edge1 · h` measures how aligned the ray is with the triangle's plane.

3. **Near-zero determinant** (`|det| < 1e-6`): the ray is parallel (or nearly so) to the triangle — no intersection.

4. Compute barycentric coordinate `u`:
   ```
   origin_to_v0 = origin - vertex0
   u = (1/det) * (origin_to_v0 · h)
   ```
   If `u < 0` or `u > 1`, the hit point is outside the triangle — exit early.

5. Compute barycentric coordinate `v`:
   ```
   q = origin_to_v0 × edge1
   v = (1/det) * (direction · q)
   ```
   If `v < 0` or `u + v > 1`, the hit point is outside the triangle — exit early.

6. Compute distance `t = (1/det) * (edge2 · q)`. If `t > 1e-6`, the hit is in front of the ray: return `origin + direction * t`.

The Möller–Trumbore test is branchless and avoids computing the explicit plane equation, making it highly efficient for mesh intersection.

**Alias:** `traiangle_intersection = triangle_intersection` (note the intentional typo in the alias, kept for backward compatibility).

---

#### `sphere_intersection(center, radius) → Optional[Vector]`
Solves the quadratic equation for `P(t)` on a sphere centred at `center` with the given `radius`.

**Derivation:**
`|P(t) - center|² = radius²` expands to:
```
a·t² + b·t + c = 0
a = direction · direction
b = 2 · (origin - center) · direction
c = (origin - center) · (origin - center) - radius²
```

Discriminant `D = b² - 4ac`:
- `D < 0`: no real solutions → no intersection.
- `D ≥ 0`: two solutions `t0 = (-b - √D) / 2a` and `t1 = (-b + √D) / 2a`.

The method prefers `t0` (the near hit, entry point). If `t0 ≤ 1e-6` (behind or at origin), it tries `t1` (the far hit, exit point — useful when the ray starts inside the sphere). Returns `None` if both are non-positive.

---

#### `plane_intersection(plane_point, plane_normal) → Optional[Vector]`
Intersects the ray with an infinite plane defined by a point on the plane and its normal.

**Derivation:**
For any point `P` on the plane: `(P - plane_point) · plane_normal = 0`. Substituting `P = origin + t·direction`:
```
t = ((plane_point - origin) · plane_normal) / (direction · plane_normal)
```

**Guards:**
- If `|denominator| < 1e-6`, the ray is nearly parallel to the plane — no intersection.
- If `t < 1e-6`, the intersection is behind the ray origin — no valid hit.

---

#### `box_intersection(box_minimum, box_maximum) → Optional[Vector]`
Implements the **slab method** (Kay–Kajiya algorithm) for an axis-aligned bounding box (AABB).

**Concept:** An AABB is the intersection of three infinite "slabs" — one per axis. The ray intersects the box if it enters all three slabs before it exits any of them.

**Per-axis computation:**
```
t_min_x = (box_min.x - origin.x) / direction.x
t_max_x = (box_max.x - origin.x) / direction.x
```
If `direction.x == 0`, the inverse is `math.inf`, which causes the slab to be infinitely thick (always intersected), as intended.

After computing min/max `t` for all three axes:
```
t_enter = max(t_min_x, t_min_y, t_min_z)   # latest entry
t_exit  = min(t_max_x, t_max_y, t_max_z)   # earliest exit
```

The ray hits the box if `t_enter ≤ t_exit` and `t_exit > 1e-6`. The hit point is at `t_enter` (the front face).

---

#### `cylinder_intersection(base_center, axis, radius, height) → Optional[Vector]`
Intersects with a **finite open cylinder** (no end caps).

**Approach:**
Decompose the ray and the vector from base_center to the ray origin into components **parallel** and **perpendicular** to the cylinder's axis. The perpendicular components reduce the problem to a 2D circle intersection.

1. Normalise the axis: `n = axis.normalized()`.
2. Project ray direction onto axis: `d_proj = direction · n`. Perpendicular ray component: `d_perp = direction - n * d_proj`.
3. Project `origin - base_center` onto axis: `o_proj`. Perpendicular: `o_perp`.
4. Solve the 2D quadratic `a·t² + b·t + c = 0` where:
   - `a = d_perp · d_perp`
   - `b = 2 · d_perp · o_perp`
   - `c = o_perp · o_perp - radius²`
5. For each positive root `t`, compute the hit point and check `0 ≤ height_at_point ≤ height` (within the finite cylinder's height range). Return the first valid hit.

---

#### `cone_intersection(apex, axis, angle) → Optional[Vector]`
Intersects with an **infinite single-sheeted cone** defined by its apex, axis direction, and half-angle.

**Setup:**
A point `P` is on the cone if `((P - apex) · n)² = |P - apex|² · cos²(angle)`, which is equivalent to requiring `(P-apex) · n = |P-apex| · cos(angle)` (one sheet, positive projection). Using `cot(angle) = cos/sin`:

The equation expands to a quadratic in `t` using perpendicular/parallel decomposition (same technique as the cylinder). For each positive root, the height `h = (P - apex) · n` must be `> 0` to restrict to the forward-pointing cone sheet.

**Degenerate case:** if `|sin(angle)| < 1e-6` (a flat disk or a line), returns `None`.

---

### Barycentric Helpers

These methods enable interpolation of per-vertex attributes (UV coordinates, normals, colours) at an arbitrary point inside a triangle.

#### `_barycentric_weights(vertex0, vertex1, vertex2, point) → Optional[Tuple[float, float, float]]`
**Private method.** Computes barycentric coordinates `(u, v, w)` for `point` within the triangle `(vertex0, vertex1, vertex2)` using the **Cramer's rule / dot-product method**:

1. Edge vectors: `e1 = vertex1 - vertex0`, `e2 = vertex2 - vertex0`, `pv = point - vertex0`.
2. Precompute dot products: `d00 = e1·e1`, `d01 = e1·e2`, `d11 = e2·e2`, `d20 = pv·e1`, `d21 = pv·e2`.
3. Denominator: `denom = d00·d11 - d01²`. If `|denom| < 1e-6` (degenerate triangle), return `None`.
4. Solve:
   ```
   v = (d11·d20 - d01·d21) / denom
   w = (d00·d21 - d01·d20) / denom
   u = 1 - v - w
   ```
5. If any of `u, v, w < 0`, the point is outside the triangle — return `None`.

#### `barycentric_interpolation(vertex0, vertex1, vertex2, uv0, uv1, uv2, point) → Optional[Vector]`
Interpolates UV coordinates (or any per-vertex attribute) at `point`:
```
result = uv0 * u + uv1 * v + uv2 * w
```
Uses `_barycentric_weights` internally. Returns `None` if the point is outside the triangle or the triangle is degenerate. Essential for texture mapping — given a hit point on a triangle, this returns the texture coordinate at that point.

#### `normal_interpolation(normal0, normal1, normal2, vertex0, vertex1, vertex2, point) → Optional[Vector]`
Interpolates vertex normals at `point` using the same barycentric weights:
```
interpolated_normal = normal0 * u + normal1 * v + normal2 * w
return interpolated_normal.normalized()
```
The interpolated normal is renormalised because the weighted sum of unit vectors is generally not unit-length. This produces **smooth shading** (Phong shading) — normals vary continuously across the triangle face, hiding the polygonal silhouette.

---

### Face Culling

#### `culling(normal: Vector, cull_mode: str) → bool`
Determines whether a face should be **culled** (not rendered) based on the relationship between the ray direction and the face normal.

| `cull_mode` | Returns `True` (cull this face) when |
|-------------|--------------------------------------|
| `'back'` | `direction · normal > 0` — the ray hits the back face (normal points away from camera) |
| `'front'` | `direction · normal < 0` — the ray hits the front face |
| anything else | Always `False` (no culling) |

- **Back-face culling** (`'back'`): the most common mode. Discards faces whose normal points away from the viewer, assuming solid objects where the interior is never visible. This halves the rendering work for closed meshes.
- **Front-face culling** (`'front'`): useful for rendering the interior of volumes or certain shadow techniques.

---

## Design Notes

- **No dependency on `Vector3`** — `Vector = Any` is intentional. The class works with any duck-typed vector that implements `.x/.y/.z`, arithmetic operators, `.dot()`, `.cross()`, and `.normalized()`. This avoids coupling the geometry system to a specific vector class.
- **`1e-6` epsilon** — used consistently as the threshold for "zero" distances and denominators. This value balances avoiding self-intersection vs. missing legitimate near-origin hits.
- **Infinite primitives** — the cone is infinite (no height cap) and the plane is infinite. Only the cylinder is explicitly bounded by a height parameter.
- **`traiangle_intersection` alias** — the backward-compatibility alias for the misspelled variant is at the bottom of the file and should be noted when refactoring.
- **No `__init_subclass__` or ABC** — `RayCast` is a concrete class, not an abstract interface. If multiple ray types are needed (e.g., segment vs. infinite ray), the `t > 1e-6` guard could be replaced by a parameterised `t_max`.
