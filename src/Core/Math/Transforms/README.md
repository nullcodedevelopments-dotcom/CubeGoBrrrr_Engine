# Transforms

This folder contains `transforms.py`, which provides two classes — `Transform` and `TransformPipeline` — that sit at the top of the engine's spatial hierarchy. `Transform` represents a single object's position/rotation/scale in 3D space; `TransformPipeline` provides the full MVP (Model-View-Projection) pipeline for turning a world-space point into clip-space or NDC coordinates.

---

## File: `transforms.py`

### Overview

| Class | Purpose |
|-------|---------|
| `Transform` | Encapsulates an object's TRS (Translation, Rotation, Scale) state and builds model matrices |
| `TransformPipeline` | Static helpers for the MVP transform chain (model → view → clip → NDC) |

### Dependencies

```python
from src.Core.Math.Matrices.matrices import Matrix3x3, Matrix4x4
from src.Core.Math.Quaternions.quaternions import Quaternion
from src.Core.Math.Vectors.vectors import Vector3
```

---

## Class: `Transform`

A `Transform` holds three values that fully describe an object's placement in its parent coordinate space:

| Attribute | Type | Default | Meaning |
|-----------|------|---------|---------|
| `position` | `Vector3` | `(0, 0, 0)` | World/local position (translation) |
| `rotation` | `Quaternion` | `identity` | Orientation as a unit quaternion |
| `scale` | `Vector3` | `(1, 1, 1)` | Non-uniform scale per axis |

### Constructor

```python
Transform(
    position: Optional[Vector3] = None,
    rotation: Optional[Quaternion] = None,
    scale: Optional[Vector3] = None,
)
```

All three parameters are optional. `None` is replaced by safe defaults (origin, identity rotation, unit scale). Using `None` as a sentinel rather than mutable default arguments avoids the classic Python mutable-default-argument bug.

### `__str__`

Multi-line representation showing all three components on separate indented lines. Useful for debug logging.

---

### Mutation Methods

These methods modify the transform in-place (they change `self`) rather than returning a new `Transform`.

#### `translate(offset: Vector3) → None`
Adds `offset` to `self.position`:
```python
self.position = self.position + offset
```
Equivalent to moving the object in world space. The new position is a new `Vector3` instance (vectors are value objects).

#### `rotate(quaternion: Quaternion) → None`
Pre-multiplies the current rotation by the given quaternion:
```python
self.rotation = (quaternion * self.rotation).normalized()
```
Pre-multiplication applies the new rotation in the **world frame** (the new rotation is "outside" the existing one). Normalisation after each composition prevents floating-point drift from accumulating over many frames, which would otherwise cause the rotation quaternion to slowly lose unit-length and produce distorted transforms.

#### `scale_by(scale_factor: Vector3) → None`
Multiplies each scale component independently:
```python
self.scale = Vector3(
    self.scale.x * scale_factor.x,
    self.scale.y * scale_factor.y,
    self.scale.z * scale_factor.z,
)
```
This is a **component-wise** (Hadamard) product, not a dot product. Allows independent scaling of each axis.

---

### Matrix Construction

#### `to_model_matrix() → Matrix4x4`
Builds the object's **model matrix** — the matrix that transforms a vertex from local object space to world space. Constructed as the product of three matrices in the standard TRS order:

```
M_model = T · R · S
```

Where:
- `S = Matrix4x4.scale(scale.x, scale.y, scale.z)` — applied first (innermost)
- `R = rotation.to_matrix4x4()` — applied second
- `T = Matrix4x4.translation(position.x, position.y, position.z)` — applied last (outermost)

This order is significant: scaling happens in local space, rotation happens around the local origin, and translation moves the scaled+rotated object to its world position. Reversing the order would produce completely different (incorrect) results.

#### `to_normal_matrix() → Optional[Matrix3x3]`
Builds the **normal matrix** — the matrix used to transform surface normals alongside the model matrix.

**Why not just use the model matrix for normals?** Normals must remain perpendicular to the surface after transformation. When non-uniform scaling is applied, the model matrix distorts normals incorrectly. The correct transform for normals is the **inverse transpose of the upper-left 3×3 of the model matrix**.

Steps:
1. `model_matrix = self.to_model_matrix()`
2. Extract the upper-left 3×3 (the rotation+scale portion, without translation).
3. Compute `inverse(upper_left)` — returns `None` if singular (e.g., scale is zero on any axis).
4. Return `inverse.transpose()`.

Returns `None` if the object has a zero scale on any axis (the normal matrix would be undefined).

---

### Static Utility Methods

#### `look_at(eye, target, world_up) → Matrix4x4`
A static convenience method that delegates to `Matrix4x4.look_at(eye, target, world_up)`. Constructs a **view matrix** (camera transform) that positions the camera at `eye` looking toward `target`, with `world_up` defining which way is "up."

This is a pass-through to the lower-level implementation but lives on `Transform` so camera objects can call it without importing `Matrix4x4` directly.

#### `decompose(matrix: Matrix4x4) → Tuple[Vector3, Quaternion, Vector3]`
Extracts `(position, rotation, scale)` from an arbitrary 4×4 model matrix. This is the inverse of `to_model_matrix()`. Useful when receiving transform data from external sources (file formats, physics engines, animation systems).

**Algorithm:**

1. **Position** — read directly from the translation column (column 3, rows 0–2):
   ```
   position = Vector3(M[0,3], M[1,3], M[2,3])
   ```

2. **Scale** — compute the **Euclidean length of each column vector** (columns 0, 1, 2 of the upper-left 3×3 block):
   ```
   scale_x = √(M[0,0]² + M[1,0]² + M[2,0]²)
   scale_y = √(M[0,1]² + M[1,1]² + M[2,1]²)
   scale_z = √(M[0,2]² + M[1,2]² + M[2,2]²)
   ```
   Each column of the rotation+scale block is a basis vector whose length equals the corresponding scale factor.

3. **Rotation** — divide each column by its scale to produce a normalised rotation matrix, then convert to quaternion using `Quaternion.from_matrix3x3` (Shepperd's method):
   ```
   rotation_matrix[col] /= scale[col]
   rotation = Quaternion.from_matrix3x3(rotation_matrix)
   ```
   Guard: if `scale_x`, `scale_y`, or `scale_z` is less than `1e-10`, the inverse scale is treated as 0 to prevent division by near-zero.

Returns all three components as a tuple `(position, rotation, scale)`.

---

## Class: `TransformPipeline`

A collection of **static methods** for chaining the MVP transform sequence. These are the building blocks of vertex processing in the rendering pipeline.

### `model_view_projection(model, view, projection) → Matrix4x4`
Computes the combined MVP matrix in the correct order:
```
MVP = projection * view * model
```
When this matrix is applied to a vertex in local object space, the result is a clip-space point ready for perspective division. Precomputing this product once per draw call and uploading it to the GPU as a uniform is the standard approach.

### `world_to_view(world_point, view_matrix) → Vector3`
Transforms a single point from world space to camera/view space using the view matrix:
```
(view_x, view_y, view_z) = view_matrix.transform_point(world_point)
return Vector3(view_x, view_y, view_z)
```
View-space coordinates are in the camera's local frame: the camera is at the origin, looking down -Z (in OpenGL convention), with +Y up and +X right.

### `world_to_clip(world_point, view_matrix, projection_matrix) → Tuple[float, float, float, float]`
Applies both view and projection transforms in sequence, returning a 4-component clip-space point `(x, y, z, w)`:

1. `view_x, view_y, view_z = view_matrix.transform_point(world_point)`
2. `clip_x, clip_y, clip_z, clip_w = projection_matrix.transform_vector4(view_x, view_y, view_z, 1.0)`

The `w` component is crucial — it carries the depth information needed for perspective division and is non-trivially 1 only after the projection matrix has been applied.

### `world_to_ndc(world_point, view_matrix, projection_matrix) → Optional[Tuple[float, float, float]]`
Extends `world_to_clip` with perspective division to produce **Normalized Device Coordinates**:

1. Call `world_to_clip` to get clip-space `(x, y, z, w)`.
2. Guard: if `clip_w ≤ 0` (point is behind or at the near plane), return `None`.
3. Divide: `(x/w, y/w, z/w)`.

The `None` return signals that the point should be clipped and not rendered.

---

## Design Notes

- **TRS composition order** — `to_model_matrix()` uses `T * R * S`. This is the standard game-engine order (scale in local space, rotate, then translate). Changing this order would require corresponding changes wherever the model matrix is consumed.
- **In-place mutation** — `translate`, `rotate`, and `scale_by` mutate `self` rather than returning new `Transform` objects. This is the typical game-engine pattern (transforms are mutable state associated with scene entities). Consider adding functional variants (`translated`, `rotated`, `scaled_by`) returning new objects if immutability is needed.
- **`to_normal_matrix` may return `None`** — callers must handle this. A common pattern is to fall back to using the model matrix's rotation-only portion (discarding scale) when the normal matrix is unavailable, or to simply avoid zero-scale transforms.
- **`TransformPipeline` duplication with `Projection`** — `TransformPipeline.world_to_ndc` and `Projection.projection_point` overlap in functionality. `TransformPipeline` returns raw tuples (lower-level, no screen conversion), while `Projection.projection_point` continues all the way to screen pixel integers.
