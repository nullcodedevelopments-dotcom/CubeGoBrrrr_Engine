from __future__ import annotations

import math

class Vector2:
    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self.x: float = x
        self.y: float = y

    def __str__(self) -> str:
        return f"Vector2({self.x}, {self.y})"

    def __repr__(self) -> str:
        return f"Vector2({self.x!r}, {self.y!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector2):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __add__(self, other: Vector2) -> Vector2:
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vector2) -> Vector2:
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vector2:
        return Vector2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> Vector2:
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Vector2:
        inverse_scalar: float = 1.0 / scalar
        return Vector2(self.x * inverse_scalar, self.y * inverse_scalar)

    def __neg__(self) -> Vector2:
        return Vector2(-self.x, -self.y)

    def dot(self, other: Vector2) -> float:
        return self.x * other.x + self.y * other.y

    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y

    def length(self) -> float:
        return math.sqrt(self.length_squared())

    def normalized(self) -> Vector2:
        vector_length: float = self.length()
        if vector_length < 1e-10:
            return Vector2(0.0, 0.0)
        
        inverse_length: float = 1.0 / vector_length
        return Vector2(self.x * inverse_length, self.y * inverse_length)


class Vector3:
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        self.x: float = x
        self.y: float = y
        self.z: float = z

    def __str__(self) -> str:
        return f"Vector3({self.x}, {self.y}, {self.z})"

    def __repr__(self) -> str:
        return f"Vector3({self.x!r}, {self.y!r}, {self.z!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector3):
            return NotImplemented
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __add__(self, other: Vector3) -> Vector3:
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vector3) -> Vector3:
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vector3:
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> Vector3:
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Vector3:
        inverse_scalar: float = 1.0 / scalar
        return Vector3(self.x * inverse_scalar, self.y * inverse_scalar, self.z * inverse_scalar)

    def __neg__(self) -> Vector3:
        return Vector3(-self.x, -self.y, -self.z)

    def dot(self, other: Vector3) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vector3) -> Vector3:
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y + self.z * self.z

    def length(self) -> float:
        return math.sqrt(self.length_squared())

    def normalized(self) -> Vector3:
        vector_length: float = self.length()
        if vector_length < 1e-10:
            return Vector3(0.0, 0.0, 0.0)
        
        inverse_length: float = 1.0 / vector_length
        return Vector3(self.x * inverse_length, self.y * inverse_length, self.z * inverse_length)

    def xy(self) -> Vector2:
        return Vector2(self.x, self.y)

    def xz(self) -> Vector2:
        return Vector2(self.x, self.z)

    def yz(self) -> Vector2:
        return Vector2(self.y, self.z)


class Vector4:
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0, w: float = 0.0) -> None:
        self.x: float = x
        self.y: float = y
        self.z: float = z
        self.w: float = w

    def __str__(self) -> str:
        return f"Vector4({self.x}, {self.y}, {self.z}, {self.w})"

    def __repr__(self) -> str:
        return f"Vector4({self.x!r}, {self.y!r}, {self.z!r}, {self.w!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector4):
            return NotImplemented
        return self.x == other.x and self.y == other.y and self.z == other.z and self.w == other.w

    def __add__(self, other: Vector4) -> Vector4:
        return Vector4(self.x + other.x, self.y + other.y, self.z + other.z, self.w + other.w)

    def __sub__(self, other: Vector4) -> Vector4:
        return Vector4(self.x - other.x, self.y - other.y, self.z - other.z, self.w - other.w)

    def __mul__(self, scalar: float) -> Vector4:
        return Vector4(self.x * scalar, self.y * scalar, self.z * scalar, self.w * scalar)

    def __rmul__(self, scalar: float) -> Vector4:
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Vector4:
        inverse_scalar: float = 1.0 / scalar
        return Vector4(self.x * inverse_scalar, self.y * inverse_scalar, self.z * inverse_scalar, self.w * inverse_scalar)

    def __neg__(self) -> Vector4:
        return Vector4(-self.x, -self.y, -self.z, -self.w)

    def dot(self, other: Vector4) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z + self.w * other.w

    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y + self.z * self.z + self.w * self.w

    def length(self) -> float:
        return math.sqrt(self.length_squared())

    def normalized(self) -> Vector4:
        vector_length: float = self.length()
        if vector_length < 1e-10:
            return Vector4(0.0, 0.0, 0.0, 0.0)
        inverse_length: float = 1.0 / vector_length
        return Vector4(self.x * inverse_length, self.y * inverse_length, self.z * inverse_length, self.w * inverse_length)

    def xyz(self) -> Vector3:
        return Vector3(self.x, self.y, self.z)

    def xy(self) -> Vector2:
        return Vector2(self.x, self.y)
