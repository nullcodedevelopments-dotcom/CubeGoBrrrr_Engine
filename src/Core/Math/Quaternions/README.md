# Quaternions

This folder contains `quaternions.py`, which implements the `Quaternion` class — the primary rotation representation used throughout the CubeGoBrrrr Engine. Quaternions avoid the **gimbal lock** problem inherent in Euler angles and support smooth interpolation (SLERP) that matrix representations cannot provide as elegantly.

---

## File: `quaternions.py`

### Overview

A **quaternion** is a hypercomplex number of the form:

```
q = w + xi + yj + zk
```

where `i`, `j`, `k` are imaginary unit vectors satisfying `i² = j² = k² = ijk = -1`. For 3D rotations, the quaternion is kept **unit-length** (`|q| = 1`), in which case it encodes a rotation of angle `2·arccos(w)` around the axis `(x, y, z) / sin(arccos(w))`.

Quaternions have **half the storage** of a rotation matrix (4 floats vs. 9) and compose with a single 16-multiply multiplication rather than 27, making them the standard choice in game engines.

---

## Class: `Quaternion`

### Constructor

```python
Quaternion(w: float, x: float, y: float, z: float)
```

Stores the four components as plain `float` attributes. The **scalar** (real) part is `w`; the **vector** (imaginary) part is `(x, y, z)`.

---

### String Representations

| Method | Output |
|--------|--------|
| `__str__` | `"Quaternion(w=…, x=…, y=…, z=…)"` — human-readable |
| `__repr__` | `"Quaternion(w!, x!, y!, z!)"` — evaluable Python literal using `!r` |

---

### Comparison and Arithmetic Operators

#### `__eq__(other) → bool`
Exact component-wise equality. Returns `NotImplemented` for non-`Quaternion` operands (proper Python protocol).

#### `__neg__() → Quaternion`
Negates all four components: `-q`. This is the additive inverse, not the same as the conjugate.

#### `__add__(other) → Quaternion`
Component-wise addition: `(w+ow, x+ox, y+oy, z+oz)`. Used in interpolation and accumulation.

#### `__sub__(other) → Quaternion`
Component-wise subtraction.

#### `__mul__(other) → Quaternion`
The most important operation. Handles two cases:

- **Quaternion × Quaternion** — Hamilton product (quaternion composition):
  ```
  w' = w·ow − x·ox − y·oy − z·oz
  x' = w·ox + x·ow + y·oz − z·oy
  y' = w·oy − x·oz + y·ow + z·ox
  z' = w·oz + x·oy − y·ox + z·ow
  ```
  This is the non-commutative quaternion multiplication rule. When both quaternions are unit quaternions, the product represents the **composition** of the two rotations (apply `self` then `other`).

- **Quaternion × scalar** — uniform scaling of all four components. Used in SLERP interpolation.

#### `__rmul__(scalar) → Quaternion`
Handles `scalar * quaternion` by delegating to `__mul__`.

---

### Static Factory Methods

#### `identity() → Quaternion`
Returns `Quaternion(1, 0, 0, 0)` — the multiplicative identity. Represents **no rotation** (0° around any axis). This is analogous to the identity matrix.

#### `from_axis_angle(axis: Vector, angle_radians: float) → Quaternion`
Converts an axis-angle rotation to a quaternion using the standard formula:
```
q = (cos(θ/2), sin(θ/2)·ux, sin(θ/2)·uy, sin(θ/2)·uz)
```
where `(ux, uy, uz)` is the normalised axis. The method:
1. Guards against zero-length axis (returns `identity()`).
2. Normalises the axis by computing and applying `1 / |axis|`.
3. Computes `half_angle = angle / 2` then takes `sin` and `cos`.

The half-angle formulation comes directly from the double-cover property of quaternions: rotating by θ around axis `n` requires `q = cos(θ/2) + sin(θ/2)·n`.

#### `from_euler_angles(pitch, yaw, roll) → Quaternion`
Converts ZYX-order Euler angles to a quaternion. The conversion computes the half-angles `(p/2, y/2, r/2)`, then takes their sines and cosines, and combines them with the quaternion multiplication formula for the **intrinsic ZYX** order (roll applied first, then yaw, then pitch):

```
w = cᵣcₚcy + sᵣsₚsy
x = cᵣsₚcy − sᵣcₚsy
y = cᵣcₚsy + sᵣsₚcy
z = sᵣcₚcy − cᵣsₚsy
```

This avoids three separate `from_axis_angle` calls and one quaternion multiplication.

#### `from_matrix3x3(matrix: Matrix3x3) → Quaternion`
Extracts a quaternion from a 3×3 rotation matrix using **Shepperd's method**, which selects the numerically most stable formula based on the matrix trace and dominant diagonal element. Four cases:

1. **Trace > 0**: `s = 0.5 / √(trace + 1)`, then `w = 0.25/s`, and the imaginary parts are differences of off-diagonal elements scaled by `s`.
2. **`M[0,0]` is dominant**: isolate `x` as the largest component.
3. **`M[1,1]` is dominant**: isolate `y`.
4. **`M[2,2]` is dominant**: isolate `z`.

Selecting the largest component first ensures division by a large number, minimising floating-point error.

---

### Instance Methods

#### `dot(other: Quaternion) → float`
4D dot product: `w·ow + x·ox + y·oy + z·oz`.

Used to measure the cosine of the "angle" between two quaternions in 4D space. A value close to ±1 means the quaternions represent nearly identical rotations; values near 0 mean they are 90° apart.

#### `length_squared() → float`
`w² + x² + y² + z²`. For a unit quaternion this should equal `1.0`.

#### `length() → float`
`√(w² + x² + y² + z²)`.

#### `normalized() → Quaternion`
Returns a unit quaternion. If `length < 1e-10`, returns `identity()` to avoid division by zero. All rotation operations assume a unit quaternion, so normalisation should be called after accumulating many multiplications to prevent drift.

#### `conjugate() → Quaternion`
Returns `Quaternion(w, -x, -y, -z)`. For a unit quaternion, the conjugate equals the inverse, representing the **opposite rotation**. Conjugate is used in `rotate_vector` (the sandwich product).

#### `inverse() → Optional[Quaternion]`
Returns the true quaternion inverse: `q* / |q|²` (conjugate divided by squared length). Returns `None` if near-zero. For unit quaternions this equals the conjugate, but the general inverse is needed for non-unit quaternions.

#### `rotate_vector(vector: Vector) → Tuple[float, float, float]`
Applies the quaternion rotation to a 3D vector using the **sandwich product**:
```
v' = q · (0, v) · q*
```
1. Wraps `vector` as a pure quaternion `p = Quaternion(0, v.x, v.y, v.z)`.
2. Computes `q * p * conjugate(q)`.
3. Returns the imaginary part `(x', y', z')` of the result.

This is the most direct quaternion-based rotation of a vector, but for rotating many vectors it is more efficient to first convert to a matrix.

#### `to_matrix3x3() → Matrix3x3`
Converts a unit quaternion to the equivalent 3×3 rotation matrix. Precomputes the cross-products of components (`xx, yy, zz, xy, xz, yz, wx, wy, wz`) and fills the matrix:
```
[1-2(yy+zz),  2(xy-wz),   2(xz+wy) ]
[ 2(xy+wz),  1-2(xx+zz),  2(yz-wx) ]
[ 2(xz-wy),   2(yz+wx),  1-2(xx+yy)]
```
The quaternion is normalised first to guarantee a proper rotation matrix (orthonormal columns, determinant = 1).

#### `to_matrix4x4() → Matrix4x4`
Same conversion as `to_matrix3x3` but embeds the result in a 4×4 matrix (translation/projection row/column set to identity values). This is the form required by `Transform.to_model_matrix()`.

#### `to_euler_angles() → Tuple[float, float, float]`
Converts a unit quaternion back to **ZYX Euler angles** `(pitch, yaw, roll)`:

- `pitch` (x-rotation): `atan2(2(wy + xz), 1 − 2(x² + y²))`
- `yaw` (y-rotation): derived via `asin(2(wy − zx))`; clamped to ±π/2 at the gimbal singularity (`|sinp| >= 1`)
- `roll` (z-rotation): `atan2(2(wz + xy), 1 − 2(y² + z²))`

The gimbal-lock singularity when `|sinp| ≥ 1` (pitch = ±90°) is handled by clamping with `math.copysign`.

---

### Static Interpolation

#### `slerp(start, end, t) → Quaternion`
**Spherical Linear Interpolation** between two quaternions at parameter `t ∈ [0,1]`.

1. **Flip check**: If `dot(start, end) < 0`, negate `end` to ensure the shortest arc is taken (quaternions `q` and `-q` represent the same rotation, but SLERP would go the long way around without this).
2. **Near-parallel fallback**: If `dot > 0.9995`, the angle is tiny and numerical instability in `acos` is a risk, so linear interpolation (`lerp`) + normalise is used instead.
3. **Full SLERP formula**:
   ```
   θ₀ = acos(dot)
   θ  = θ₀ · t
   scale_start = cos(θ) − dot · sin(θ)/sin(θ₀)
   scale_end   = sin(θ) / sin(θ₀)
   result = (start · scale_start + end · scale_end).normalized()
   ```
   This traces the great arc on the 4D unit sphere between `start` and `end`, producing constant-speed rotation with no artificial acceleration.

---

## Design Notes

- **Imports**: Depends on `Matrix3x3` and `Matrix4x4` from `matrices.py` for the conversion methods; avoids circular imports by using `from __future__ import annotations` and the `Vector = Any` type alias.
- **Unit quaternion assumption**: All rotation-semantic methods (`rotate_vector`, `to_matrix*`, `to_euler_angles`, `slerp`) call `normalized()` internally or assume normalised input. Always normalise after accumulating multiplications.
- **Shepperd's method** in `from_matrix3x3`: The four-case branching is deliberate and essential — it avoids dividing by a near-zero number, which would amplify floating-point error and produce garbage quaternions.
- **Hamilton convention**: The `w` component is placed first in the constructor (`w, x, y, z`), which is the Hamilton convention used by most game engines and physics libraries. Some libraries (e.g. XMVECTOR) use `(x, y, z, w)` order — be aware of this when interoperating.
