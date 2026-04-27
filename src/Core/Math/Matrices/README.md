# Matrices

This folder contains `matrices.py`, which provides two full-featured matrix classes — `Matrix3x3` and `Matrix4x4` — that are the backbone of every linear transformation in the CubeGoBrrrr Engine. They handle rotation, scaling, translation (4×4 only), projection, the view/camera matrix, and general vector transformation.

---

## File: `matrices.py`

### Overview

| Class | Size | Primary Use |
|-------|------|-------------|
| `Matrix3x3` | 3 × 3 | Pure linear transforms (rotation, scale), normal matrix, upper-left extraction |
| `Matrix4x4` | 4 × 4 | Full affine/projective transforms: model, view, projection, look-at |

Both classes store their elements in a **flat row-major `list[float]`** of length 9 or 16 respectively. Element `(row, col)` is at index `row * N + col` where N is 3 or 4. This layout matches how GPU APIs (OpenGL, Vulkan, DirectX) expect matrix data to be uploaded via uniform buffers.

---

## Class: `Matrix3x3`

### Constructor

```python
Matrix3x3(
    row0_col0, row0_col1, row0_col2,
    row1_col0, row1_col1, row1_col2,
    row2_col0, row2_col1, row2_col2,
)
```

All 9 parameters default to `0.0`, so `Matrix3x3()` produces a zero matrix. Elements are stored in `self.elements: List[float]` as a flat, row-major list.

### `__str__`

Pretty-prints each row on a separate line with bracket notation, useful for debugging.

---

### Element Access

#### `get(row, col) → float`
Returns `self.elements[row * 3 + col]`. This is a direct index calculation with no bounds-checking overhead.

#### `set(row, col, value)`
Writes `value` to `self.elements[row * 3 + col]`.

---

### Static Factory Methods

These are the canonical ways to construct useful matrices.

#### `identity() → Matrix3x3`
Returns the 3×3 identity matrix `I`. Multiplying any matrix by `I` leaves it unchanged. Used as a safe default and neutral element for rotations.

#### `scale(scale_x, scale_y, scale_z) → Matrix3x3`
Returns a **diagonal scaling matrix**. Each axis is independently scaled:
```
[sx,  0,  0]
[ 0, sy,  0]
[ 0,  0, sz]
```
Non-uniform scaling (different values per axis) is valid. When all three values equal the same scalar it produces uniform/isotropic scaling.

#### `rotation_x(angle_radians) → Matrix3x3`
Rotation about the **X-axis** (pitch). Computed from the standard formula:
```
[1,    0,     0  ]
[0, cos θ, -sin θ]
[0, sin θ,  cos θ]
```
`cos` and `sin` are computed once and reused.

#### `rotation_y(angle_radians) → Matrix3x3`
Rotation about the **Y-axis** (yaw):
```
[ cos θ, 0, sin θ]
[   0,   1,   0  ]
[-sin θ, 0, cos θ]
```

#### `rotation_z(angle_radians) → Matrix3x3`
Rotation about the **Z-axis** (roll):
```
[cos θ, -sin θ, 0]
[sin θ,  cos θ, 0]
[  0,      0,   1]
```

---

### Arithmetic Operators

#### `__add__(other) → Matrix3x3`
Component-wise addition via list comprehension over all 9 elements.

#### `__sub__(other) → Matrix3x3`
Component-wise subtraction.

#### `__mul__(other) → Matrix3x3`
Handles two cases:
- **Matrix × Matrix**: Standard 3×3 matrix multiplication using the triple nested loop `Σ_k self[i,k] * other[k,j]`. This implements `(AB)_{ij} = Σ_k A_{ik} B_{kj}`, the fundamental composition of linear transforms.
- **Matrix × scalar (int or float)**: Scales every element by the scalar, returning a new matrix.

#### `__rmul__(scalar) → Matrix3x3`
Handles `scalar * matrix` by delegating to `__mul__`.

---

### Linear Algebra Methods

#### `transpose() → Matrix3x3`
Swaps rows and columns: `result[i][j] = self[j][i]`. For pure rotation matrices (orthogonal matrices), the transpose equals the inverse — this is exploited in `rotations.py` as a fast rotation inversion.

#### `determinant() → float`
Computes the 3×3 determinant via **Sarrus's rule** (cofactor expansion along the first row):
```
det = a(ei − fh) − b(di − fg) + c(dh − eg)
```
where the matrix is:
```
[a b c]
[d e f]
[g h i]
```
The determinant tells you the signed volume scaling factor of the transformation. A determinant of 0 means the matrix is singular (no inverse exists); negative means the transformation includes a reflection.

#### `inverse() → Optional[Matrix3x3]`
Returns the inverse matrix or `None` if the determinant is below `1e-10` (near-singular). Uses the **adjugate (classical adjoint) method**:
1. Compute the 9 cofactors (each is a signed 2×2 minor determinant).
2. Arrange them transposed (adjugate).
3. Multiply by `1 / det`.

The cofactors are computed explicitly and named clearly (`cofactor_00` … `cofactor_22`) for readability.

#### `transform_vector(vector) → Tuple[float, float, float]`
Multiplies the matrix by a `Vector`-like object (must have `.x`, `.y`, `.z`), implementing `result = M * v`:
```
result_x = m[0,0]*v.x + m[0,1]*v.y + m[0,2]*v.z
result_y = m[1,0]*v.x + m[1,1]*v.y + m[1,2]*v.z
result_z = m[2,0]*v.x + m[2,1]*v.y + m[2,2]*v.z
```
Returns a tuple rather than a `Vector3` to avoid circular imports.

---

## Class: `Matrix4x4`

Extends the 3×3 logic to 4×4, adding support for translation and projection.

### Constructor

```python
Matrix4x4(
    row0_col0 … row0_col3,
    row1_col0 … row1_col3,
    row2_col0 … row2_col3,
    row3_col0 … row3_col3,
)
```

All 16 parameters default to `0.0`. Elements stored in `self.elements: List[float]` (flat row-major, length 16).

### Element Access

#### `get(row, col) → float`
`self.elements[row * 4 + col]`.

#### `set(row, col, value)`
`self.elements[row * 4 + col] = value`.

---

### Static Factory Methods

#### `identity() → Matrix4x4`
The 4×4 identity. Neutral element for matrix multiplication.

#### `translation(tx, ty, tz) → Matrix4x4`
Affine translation matrix in homogeneous coordinates:
```
[1, 0, 0, tx]
[0, 1, 0, ty]
[0, 0, 1, tz]
[0, 0, 0,  1]
```
When multiplied by a column vector `(x,y,z,1)^T`, adds `(tx,ty,tz)` to the point. Directions with `w=0` are unaffected.

#### `scale(sx, sy, sz) → Matrix4x4`
4×4 diagonal scale matrix (same as `Matrix3x3.scale` but embedded in a 4×4 matrix with `1.0` in the bottom-right corner).

#### `rotation_x / rotation_y / rotation_z`
4×4 versions of the same axis-aligned rotation matrices from `Matrix3x3`, with the fourth row/column forming an identity extension.

#### `rotation_axis_angle(axis, angle_radians) → Matrix4x4`
Implements the **Rodrigues rotation formula** for an arbitrary unit axis `(ux, uy, uz)`:
```
R = cos(θ)·I + (1−cos(θ))·u⊗u + sin(θ)·[u]×
```
Where `u⊗u` is the outer product and `[u]×` is the skew-symmetric cross-product matrix. The axis is normalised inside the method (guarded against zero-length). This is the most general single-rotation matrix and the form most GPUs use internally.

#### `perspective(fov_y_radians, aspect_ratio, near, far) → Matrix4x4`
Constructs an OpenGL-style **perspective projection matrix**. Key derivation:

- `tan_half_fov = tan(fov_y / 2)` maps the vertical field of view to a scale factor.
- `f_x = 1 / (aspect * tan_half_fov)` corrects for the screen's width-to-height ratio.
- `f_y = 1 / tan_half_fov` scales the y-axis.
- The `[2,2]` and `[2,3]` elements remap z from `[near, far]` into `[-1, 1]` (NDC depth).
- The `[3,2] = -1` entry performs perspective division (writes `-z` into `w`, so dividing by `w` later yields `1/z` depth).

#### `orthographic(left, right, bottom, top, near, far) → Matrix4x4`
Constructs an **orthographic (parallel) projection matrix**. Unlike perspective, there is no perspective division — distant objects appear the same size as close objects. Used for UI, 2D games, and technical/engineering views. Maps the axis-aligned box `[left,right] × [bottom,top] × [near,far]` to the NDC cube `[-1,1]³`.

#### `look_at(eye, target, world_up) → Matrix4x4`
Constructs a **view matrix** (camera matrix) that transforms world coordinates into camera/eye space.

1. **Forward vector**: `(eye − target)` normalised → points from target toward the camera.
2. **Right vector**: `world_up × forward` normalised → the camera's rightward axis.
3. **Up vector**: `forward × right` → the camera's true upward axis (orthogonalised).
4. The resulting matrix is an orthonormal frame change + translation (dot products with `eye` for translation component).

Guards against degenerate cases (zero-length forward or right) by returning identity.

---

### Arithmetic Operators

Same pattern as `Matrix3x3`:
- `__add__`, `__sub__` — component-wise over 16 elements.
- `__mul__` — matrix-matrix multiplication (4×4 triple loop) or scalar multiplication.
- `__rmul__` — reverse scalar.
- `transpose()` — swap rows and columns.

---

### Linear Algebra Methods

#### `_minor_determinant(skip_row, skip_col) → float`
**Private helper.** Builds the 3×3 sub-matrix obtained by deleting `skip_row` and `skip_col`, then evaluates its determinant using the same Sarrus rule as `Matrix3x3.determinant()`. This is the **minor** of element `(skip_row, skip_col)`.

#### `determinant() → float`
Cofactor expansion along the **first row** of the 4×4 matrix:
```
det = Σ_{j=0}^{3} (-1)^j · M[0,j] · minor(0, j)
```
The sign alternates (+, -, +, -) for columns 0–3.

#### `inverse() → Optional[Matrix4x4]`
Returns the inverse or `None` if `|det| < 1e-10`. Uses the **cofactor / adjugate method** generalised to 4×4:
- Iterates all 16 `(row, col)` positions.
- Computes the signed cofactor: `(-1)^(row+col) * minor(row, col)`.
- Stores in the **transposed** position (`result.set(col, row, …)`) — this is the adjugate.
- Multiplies through by `1 / det`.

#### `transform_point(vector) → Tuple[float, float, float]`
Applies the full affine transform `M * (x,y,z,1)^T`, using the first three rows including the translation column (`col 3`). Returns `(x', y', z')` as a tuple, which is correct for points (the `w=1` input absorbs the translation).

#### `transform_direction(vector) → Tuple[float, float, float]`
Applies only the linear (rotation/scale) part of the matrix — equivalent to `M * (x,y,z,0)^T`. The translation column is ignored, which is correct for directions and normals (directions should not be translated).

#### `transform_vector4(x, y, z, w) → Tuple[float, float, float, float]`
Full 4-component matrix-vector multiplication. The `w` parameter lets the caller explicitly control the homogeneous coordinate. Returns the full 4-tuple `(x', y', z', w')`, which is needed for projection (the resulting `w'` is used for perspective division).

---

## Design Notes

- **Row-major flat storage** — all elements are in a single `List[float]`. This is cache-friendly for row-iteration and straightforward to pass to graphics APIs.
- **Static factory methods** — constructors are kept generic; specific matrices are produced by well-named static methods (`identity`, `translation`, `look_at`, etc.), which serves as both documentation and discoverability.
- **`1e-10` singularity guard** — both `inverse()` methods check `|det| < 1e-10` rather than exact zero to handle floating-point rounding gracefully.
- **No NumPy dependency** — all operations are implemented in pure Python, keeping the engine dependency-free and portable.
