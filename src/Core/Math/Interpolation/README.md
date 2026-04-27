# Interpolation

This folder contains `interpolation.py`, which provides the `Interpolation` utility class — a collection of **pure static methods** for blending between values. These functions are used for animation curves, smooth camera movement, procedural geometry, texture sampling, and any other system in the engine that requires controlled transitions between states.

---

## File: `interpolation.py`

### Overview

The `Interpolation` class has **no instance state** — every method is `@staticmethod`. This means it acts as a well-organised namespace of interpolation functions rather than an object with mutable data. The methods are grouped conceptually:

| Category | Methods |
|----------|---------|
| Linear | `linear_interpolation_scalar`, `linear_interpolation_vector` |
| Smooth (2nd-order) | `smoothstep_interpolation_scalar`, `smoothstep_interpolation_vector` |
| Smooth (5th-order) | `smootherstep_interpolation_scalar`, `smootherstep_interpolation_vector` |
| Spherical | `slerp_interpolation` |
| Barycentric | `triangular_interpolation` |
| Spline | `cubic_interpolation` |
| 2D grid | `bilinear_interpolation`, `bicubic_interpolation` |

The `Vector = Any` type alias means any object supporting addition and scalar multiplication (including `Vector2`, `Vector3`, `Vector4`, colours, etc.) works with the vector variants.

---

## Class: `Interpolation`

### Linear Interpolation

#### `linear_interpolation_scalar(start, end, t) → float`
The classic lerp formula:
```
result = (1 - t) · start + t · end
```
When `t = 0` the result equals `start`; when `t = 1` it equals `end`. Values outside `[0,1]` extrapolate beyond the range.

This form (rather than `start + t * (end - start)`) avoids catastrophic cancellation when `start` and `end` are large values of similar magnitude.

#### `linear_interpolation_vector(start, end, t) → Vector`
Identical formula applied component-wise to any vector type. Works because the expression `(1.0 - t) * start + t * end` uses Python's `__rmul__` and `__add__` operators defined on all engine vector classes.

---

### Smoothstep Interpolation

#### `smoothstep_interpolation_scalar(start, end, t) → float`
Smoothstep replaces the linear `t` with a smooth S-curve:
```
t_clamped = clamp(t, 0, 1)
t_smooth  = t_clamped² · (3 − 2·t_clamped)
result    = lerp(start, end, t_smooth)
```
The polynomial `3t² − 2t³` has:
- Value 0 and derivative 0 at `t = 0` (smooth start)
- Value 1 and derivative 0 at `t = 1` (smooth end)

This makes transitions feel natural — no abrupt kick at the start or snap at the end. Widely used for fade-ins, camera easing, and procedural textures.

**Note:** The input `t` is clamped to `[0, 1]` before the polynomial is applied, so out-of-range values are safely saturated.

#### `smoothstep_interpolation_vector(start, end, t) → Vector`
Same polynomial applied to a vector lerp.

---

### Smootherstep Interpolation

#### `smootherstep_interpolation_scalar(start, end, t) → float`
Ken Perlin's improved version of smoothstep. The polynomial is 5th-order:
```
t_clamped = clamp(t, 0, 1)
t_smooth  = t_clamped³ · (t_clamped · (6·t_clamped − 15) + 10)
result    = lerp(start, end, t_smooth)
```
The expanded form `6t⁵ − 15t⁴ + 10t³` has:
- Zero first **and second** derivatives at both endpoints

This eliminates any visible acceleration artifact that can be noticed with regular smoothstep in animated contexts, making it better for things like noise gradient blending in Perlin noise.

#### `smootherstep_interpolation_vector(start, end, t) → Vector`
Same 5th-order polynomial applied to vectors.

---

### Spherical Linear Interpolation

#### `slerp_interpolation(start: Vector, end: Vector, t: float) → Vector`
SLERP interpolates along the **great arc** on the unit sphere, rather than through the interior. This preserves the length of the vectors throughout the interpolation and produces constant angular velocity.

Algorithm:
1. Clamp the dot product to `[-1, 1]` to guard against floating-point values slightly outside `acos`'s domain.
2. `theta = acos(dot)` — the angle between the two vectors.
3. **Near-parallel fallback**: if `|sin(theta)| < 1e-6`, the vectors are nearly parallel and the denominator would blow up — fall back to linear interpolation.
4. Otherwise:
   ```
   scale_start = sin((1-t) · θ) / sin(θ)
   scale_end   = sin(t · θ) / sin(θ)
   result      = scale_start · start + scale_end · end
   ```

Unlike the quaternion `Quaternion.slerp`, this method works on general vectors (direction interpolation, colour interpolation on the unit sphere, etc.) and does not handle the sign-flip issue for quaternion rotations.

---

### Barycentric Interpolation

#### `triangular_interpolation(v0, v1, v2, w0, w1, w2) → Vector`
Weighted blend of three values using **barycentric coordinates** `(w0, w1, w2)`:
```
result = w0·v0 + w1·v1 + w2·v2
```
For a point inside a triangle, `w0 + w1 + w2 = 1`. The weights are typically pre-computed from the point's position relative to the triangle's vertices (see `RayCast._barycentric_weights` in `raytracing.py`). Used to interpolate vertex colours, normals, UV coordinates, and any per-vertex attribute across a triangle's surface.

---

### Cubic (Catmull-Rom) Interpolation

#### `cubic_interpolation(p0, p1, p2, p3, t) → Vector`
Catmull-Rom spline interpolation between `p1` and `p2`, using `p0` and `p3` as **tangent controls**:
```
result = 0.5 · (
     2·p1
  + (p2 − p0)·t
  + (2·p0 − 5·p1 + 4·p2 − p3)·t²
  + (−p0 + 3·p1 − 3·p2 + p3)·t³
)
```
Derivation: The Catmull-Rom formula is the cubic Hermite spline where the tangent at `p1` is `(p2 − p0)/2` and the tangent at `p2` is `(p3 − p1)/2`. This produces C¹ continuity (smooth first derivative) automatically when chaining multiple segments.

`t_squared` and `t_cubed` are computed once and reused to avoid redundant multiplications.

Applications: smooth camera paths, spline-based animations, procedural terrain curves, character movement paths.

---

### Bilinear Interpolation

#### `bilinear_interpolation(bottom_left, bottom_right, top_left, top_right, u, v) → Vector`
Interpolates across a **quad** (four-corner patch) using two linear sweeps:

1. **Horizontal sweep** (u-axis):
   - `bottom_edge = lerp(bottom_left, bottom_right, u)`
   - `top_edge    = lerp(top_left, top_right, u)`
2. **Vertical sweep** (v-axis):
   - `result = lerp(bottom_edge, top_edge, v)`

This is the standard algorithm for **texture magnification filtering**, grid-based surface patches, and 2D lookup table interpolation. The two-pass lerp is mathematically equivalent to the one-pass bilinear formula but more readable and makes the separability explicit.

---

### Bicubic Interpolation

#### `bicubic_interpolation(p00…p33, u, v) → Vector`
Interpolates across a **4×4 grid of control points** using two passes of Catmull-Rom:

1. **Horizontal pass** — interpolate each of the four rows at parameter `u`:
   ```
   row_0 = cubic(p00, p10, p20, p30, u)
   row_1 = cubic(p01, p11, p21, p31, u)
   row_2 = cubic(p02, p12, p22, p32, u)
   row_3 = cubic(p03, p13, p23, p33, u)
   ```
2. **Vertical pass** — interpolate the four row results at parameter `v`:
   ```
   result = cubic(row_0, row_1, row_2, row_3, v)
   ```

The naming convention is **column-major** for the first index and **row-major** for the second: `p{col}{row}`, so `p10` is column 1, row 0.

Bicubic produces **smoother** results than bilinear with much less visible blocky artefacts — it is the standard algorithm for high-quality texture upsampling, procedural surface patches (e.g. Bézier patches via conversion), and smooth terrain height maps.

---

## Design Notes

- **All methods are `@staticmethod`** — no instantiation needed. Use as `Interpolation.linear_interpolation_scalar(a, b, t)` directly.
- **Duck-typed vectors** — the `Vector = Any` alias means any object supporting `+` and scalar `*` / `*` with a float works. This gives the class wide applicability without coupling it to specific types.
- **No external dependencies** — only `math` is imported. `math.acos`, `math.sin`, `math.cos` are used for SLERP.
- **Clamping in smoothstep / smootherstep** — `max(0.0, min(1.0, t))` is used instead of a separate clamp function to avoid overhead. This ensures the polynomial is only evaluated on `[0, 1]` where it is well-behaved.
- **`t_squared` / `t_cubed` precomputation** in `cubic_interpolation` — avoids three separate multiplications and makes the polynomial structure clear at a glance.
