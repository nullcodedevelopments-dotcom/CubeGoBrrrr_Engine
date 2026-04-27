# Vectors

This folder contains `vectors.py`, which provides the foundational 2D, 3D, and 4D vector types used throughout the CubeGoBrrrr Engine. These types underpin virtually every geometric computation in the engine — positions, directions, normals, UV coordinates, homogeneous clip-space coordinates, and more.

---

## File: `vectors.py`

### Overview

The file defines three immutable-style vector classes:

| Class | Dimensions | Primary Use |
|-------|-----------|-------------|
| `Vector2` | (x, y) | 2D positions, UV texture coordinates, screen-space swizzles |
| `Vector3` | (x, y, z) | 3D world positions, directions, normals, surface tangents |
| `Vector4` | (x, y, z, w) | Homogeneous clip-space coordinates, RGBA colours, full affine transforms |

All three classes follow the same design philosophy: they are pure value objects with no mutable side-effects; every operation returns a new instance. Python's dunder (magic) methods are used so that operators (`+`, `-`, `*`, `/`, unary `-`) work naturally in expressions.

---

## Class: `Vector2`

Represents a two-component floating-point vector `(x, y)`.

### Constructor

```python
Vector2(x: float = 0.0, y: float = 0.0)
```

Stores `x` and `y` as plain `float` attributes. Defaults to the origin `(0, 0)`.

---

### Operator Overloads

| Method | Operator | Description |
|--------|----------|-------------|
| `__str__` | `str()` | Human-readable `"Vector2(x, y)"` |
| `__repr__` | `repr()` | Evaluable `"Vector2(x!, y!)"` using `!r` for exact float literals |
| `__eq__` | `==` | Component-wise equality; returns `NotImplemented` for non-`Vector2` objects so Python can try the reverse comparison |
| `__add__` | `+` | Component-wise addition → new `Vector2` |
| `__sub__` | `-` | Component-wise subtraction → new `Vector2` |
| `__mul__` | `*` | Scalar multiplication (vector × scalar) |
| `__rmul__` | `scalar * v` | Reverse scalar multiplication (scalar × vector) delegates to `__mul__` |
| `__truediv__` | `/` | Scalar division; uses the multiply-by-reciprocal trick (`1.0 / scalar`) to avoid repeated divisions |
| `__neg__` | unary `-` | Negates both components |

### Instance Methods

#### `dot(other: Vector2) → float`
Computes the **dot product**: `x·ox + y·oy`.

The dot product of two unit vectors equals the cosine of the angle between them, making it central to lighting equations, projection, and angle measurement.

#### `length_squared() → float`
Returns `x² + y²` without taking a square root. This is much faster than `length()` and is preferred whenever you only need to compare magnitudes or check for near-zero vectors.

#### `length() → float`
Returns the Euclidean magnitude `√(x² + y²)` via `math.sqrt(length_squared())`.

#### `normalized() → Vector2`
Returns a unit vector (length = 1) in the same direction.

**Guard:** if `length < 1e-10` (effectively zero), returns `Vector2(0, 0)` to avoid division by zero. Otherwise multiplies by the precomputed reciprocal `1/length` for efficiency.

---

## Class: `Vector3`

Represents a three-component floating-point vector `(x, y, z)`.

### Constructor

```python
Vector3(x: float = 0.0, y: float = 0.0, z: float = 0.0)
```

### Operator Overloads

Mirrors `Vector2` exactly (add, sub, mul, rmul, div, neg, eq, str, repr), extended to three components.

### Instance Methods

#### `dot(other: Vector3) → float`
Computes `x·ox + y·oy + z·oz`.

Used everywhere — projection onto normals, diffuse lighting (Lambert), specular (Blinn-Phong half-vector), ray-plane intersection denominators, and many more.

#### `cross(other: Vector3) → Vector3`
Computes the **cross product**, returning a vector perpendicular to both inputs:

```
result.x = self.y * other.z - self.z * other.y
result.y = self.z * other.x - self.x * other.z
result.z = self.x * other.y - self.y * other.x
```

The magnitude of the result equals `|self| * |other| * sin(θ)`. This makes `cross` essential for computing surface normals from two edge vectors, constructing orthonormal bases (camera right/up), and the Möller–Trumbore ray-triangle intersection test used in `raytracing.py`.

#### `length_squared() → float`
`x² + y² + z²` — cheaper than `length()`.

#### `length() → float`
`√(x² + y² + z²)`.

#### `normalized() → Vector3`
Unit vector in the same direction; guards against zero-length vectors (returns `Vector3(0,0,0)` if near zero).

#### Swizzle Helpers

| Method | Returns | Purpose |
|--------|---------|---------|
| `xy()` | `Vector2(x, y)` | Drops the z-component; useful for 2D screen projections |
| `xz()` | `Vector2(x, z)` | Horizontal-plane slice (top-down view) |
| `yz()` | `Vector2(y, z)` | Lateral-plane slice |

---

## Class: `Vector4`

Represents a four-component floating-point vector `(x, y, z, w)`.

### Constructor

```python
Vector4(x: float = 0.0, y: float = 0.0, z: float = 0.0, w: float = 0.0)
```

The `w` component is the **homogeneous coordinate**. When `w = 1` the vector behaves like a point in 3D space; when `w = 0` it behaves like a direction (unaffected by translations). After projection, `w` becomes the clip-space depth divisor used in perspective division.

### Operator Overloads

Same pattern as `Vector2` / `Vector3`, extended to four components.

### Instance Methods

#### `dot(other: Vector4) → float`
`x·ox + y·oy + z·oz + w·ow`.

#### `length_squared() → float`
`x² + y² + z² + w²`.

#### `length() → float`
`√(x² + y² + z² + w²)`.

#### `normalized() → Vector4`
Unit vector; guards against zero-length with threshold `1e-10`.

#### Swizzle Helpers

| Method | Returns | Purpose |
|--------|---------|---------|
| `xyz()` | `Vector3(x, y, z)` | Drops the w-component; converts a homogeneous point back to 3D |
| `xy()` | `Vector2(x, y)` | Extracts the 2D part |

---

## Design Notes

- **No external dependencies** — the only import is Python's built-in `math` module.
- **`from __future__ import annotations`** — enables PEP 563 postponed evaluation so forward references work correctly in type hints without runtime cost.
- **Reciprocal multiplication** — division is always implemented as `1.0 / scalar` followed by multiplication. On most hardware this avoids multiple divisions and is a standard micro-optimisation in real-time math libraries.
- **`1e-10` zero guard** — all normalisation methods check `length < 1e-10` rather than `length == 0`. This handles degenerate cases (e.g., a zero-scale object) gracefully without crashing.
- **`NotImplemented` from `__eq__`** — returning `NotImplemented` instead of `False` when types differ is the correct Python protocol; it allows the reflected comparison on the other operand to run.
