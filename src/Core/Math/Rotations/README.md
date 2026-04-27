# Rotations

This folder contains `rotations.py`, which provides the `Rotation` utility class — a **pure-static conversion and composition layer** that bridges Euler angles, axis-angle pairs, quaternions, and rotation matrices. Rather than implementing rotation math from scratch, it orchestrates the lower-level primitives in `matrices.py` and `quaternions.py` into a single coherent API.

---

## File: `rotations.py`

### Overview

Rotation can be represented in several ways in 3D graphics and physics:

| Representation | Strengths | Weaknesses |
|---------------|-----------|------------|
| **Euler angles** (pitch/yaw/roll) | Intuitive, compact (3 floats) | Gimbal lock, order-dependent |
| **Axis-angle** | Natural for physics, animators | Hard to compose |
| **Quaternion** | No gimbal lock, smooth SLERP, compact (4 floats) | Less intuitive |
| **3×3 Matrix** | Fast vector transform | Large (9 floats), accumulates drift |
| **4×4 Matrix** | Combines rotation + translation + projection | Largest (16 floats) |

`Rotation` provides a clean set of conversion functions between all of these, so other engine systems can work in whatever representation is most convenient without caring about the math underneath.

---

## Class: `Rotation`

All methods are `@staticmethod` — the class is a namespace, not an object with state.

### Imports

```python
from src.Core.Math.Matrices.matrices import Matrix3x3, Matrix4x4
from src.Core.Math.Quaternions.quaternions import Quaternion
```

The `Vector = Any` alias accepts any object with `.x`, `.y`, `.z` attributes (typically `Vector3`).

---

### Euler → Other

#### `euler_to_matrix3x3(pitch, yaw, roll) → Matrix3x3`
Converts ZYX Euler angles to a 3×3 rotation matrix by building three axis-rotation matrices and multiplying them in ZYX order:
```
R = Rz(roll) * Ry(yaw) * Rx(pitch)
```
This order means: first apply pitch (X), then yaw (Y), then roll (Z) — the standard aerospace / game engine convention. The multiplication order is **right-to-left**: pitch is innermost (applied first to the vector).

#### `euler_to_matrix4x4(pitch, yaw, roll) → Matrix4x4`
Same as above but produces a 4×4 matrix embedding the rotation in homogeneous space. Uses `Matrix4x4.rotation_x/y/z` and the same ZYX multiplication order.

#### `euler_to_quaternion(pitch, yaw, roll) → Quaternion`
Delegates directly to `Quaternion.from_euler_angles`, which applies the same ZYX ordering using half-angle trigonometry internally (see `quaternions.py`). This thin wrapper keeps the API symmetric — callers never need to know which module implements the conversion.

---

### Axis-Angle → Other

#### `axis_angle_to_matrix3x3(axis, angle_radians) → Matrix3x3`
Implements the **Rodrigues rotation formula** directly for a 3×3 output:
```
R = cos(θ)·I + (1−cos(θ))·n⊗n + sin(θ)·[n]×
```
Expanded into the 9 explicit matrix elements. The axis is normalised inside the method (zero-length axis returns `Matrix3x3.identity()`). This is the most direct form — no intermediate quaternion or matrix multiplication chain is needed.

#### `axis_angle_to_matrix4x4(axis, angle_radians) → Matrix4x4`
Delegates to `Matrix4x4.rotation_axis_angle`, which implements the same Rodrigues formula embedded in a 4×4 matrix.

#### `axis_angle_to_quaternion(axis, angle_radians) → Quaternion`
Delegates to `Quaternion.from_axis_angle`. Axis-angle and quaternion are closely related — the quaternion IS the half-angle/axis encoding, so this conversion is particularly natural.

---

### Matrix → Euler

#### `matrix3x3_to_euler(matrix) → Tuple[float, float, float]`
Extracts `(pitch, yaw, roll)` from a ZYX rotation matrix using the analytic inverse of the construction formula.

For the ZYX convention `R = Rz · Ry · Rx`, the elements relate to angles as:
```
R[2,0] = -sin(yaw)
R[2,1] = cos(yaw)·sin(pitch)
R[2,2] = cos(yaw)·cos(pitch)
R[1,0] = cos(yaw)·sin(roll)
R[0,0] = cos(yaw)·cos(roll)
```

The extraction:
- `yaw  = asin(-R[2,0])`
- `pitch = atan2(R[2,1], R[2,2])`
- `roll  = atan2(R[1,0], R[0,0])`

**Gimbal lock case**: when `|sin(yaw)| ≥ 1` (yaw = ±90°), pitch and roll are degenerate (any combination of them produces the same rotation). The code handles this by clamping yaw to ±π/2 and extracting pitch from `atan2(R[0,1], R[0,2])`, setting roll to 0 as the canonical choice.

#### `matrix4x4_to_euler(matrix) → Tuple[float, float, float]`
Identical algorithm applied to the upper-left 3×3 block of a 4×4 matrix. The translation and projection rows/columns are ignored because Euler angles are a pure rotation concept.

---

### Quaternion ↔ Matrix

#### `quaternion_to_matrix3x3(quaternion) → Matrix3x3`
Thin wrapper for `quaternion.to_matrix3x3()`. Converts the quaternion's four components into the 9-element rotation matrix using the standard formula (see `quaternions.py`).

#### `quaternion_to_matrix4x4(quaternion) → Matrix4x4`
Thin wrapper for `quaternion.to_matrix4x4()`.

#### `matrix3x3_to_quaternion(matrix) → Quaternion`
Thin wrapper for `Quaternion.from_matrix3x3(matrix)` — Shepperd's method (see `quaternions.py`).

---

### Composition

#### `compose_rotations_matrix3x3(first, second) → Matrix3x3`
Returns `second * first`. Matrix multiplication order is right-to-left: `first` is applied to the vector first, then `second`. This is the mathematical standard (column vectors on the right).

#### `compose_rotations_matrix4x4(first, second) → Matrix4x4`
Same right-to-left composition for 4×4 matrices.

#### `compose_rotations_quaternion(first, second) → Quaternion`
Returns `second * first`. Quaternion multiplication is also right-to-left for the same reason: the rightmost quaternion acts on the vector first. This is consistent with the matrix convention.

---

### Inversion

#### `invert_rotation_matrix3x3(matrix) → Matrix3x3`
Returns `matrix.transpose()`. For a **pure rotation matrix** (orthonormal columns, determinant = +1), the inverse equals the transpose. This is much faster than computing the full matrix inverse (9 reads vs. full cofactor expansion) and is numerically more stable.

#### `invert_rotation_matrix4x4(matrix) → Matrix4x4`
Same — transpose the 4×4 rotation matrix. Note: this is only valid for the rotation portion; if the matrix contains translation, the full `inverse()` should be used.

#### `invert_rotation_quaternion(quaternion) → Quaternion`
Returns `quaternion.conjugate().normalized()`. The conjugate flips the rotation direction (negates the imaginary part), and normalising ensures the result is a valid unit quaternion. For a unit quaternion the conjugate already equals the inverse without needing to normalise, but normalising handles any accumulated floating-point drift.

---

## Design Notes

- **Thin wrappers vs. direct implementations** — some methods implement the math directly (e.g., `axis_angle_to_matrix3x3`) while others delegate to `Matrix4x4` or `Quaternion` methods. The direct 3×3 implementation avoids the overhead of constructing an intermediate 4×4 matrix just to discard the extra row/column.
- **Consistent ZYX convention** — all Euler-based methods use the ZYX intrinsic convention. This is documented in inline comments and must be maintained if additional conversion methods are added.
- **No state** — `Rotation` is a pure namespace. There is no `Rotation` object to construct or dispose of.
- **Separation of concerns** — this module is the "glue layer". The actual math lives in `matrices.py` and `quaternions.py`. `rotations.py` is responsible only for wiring the right conversion in the right direction.
