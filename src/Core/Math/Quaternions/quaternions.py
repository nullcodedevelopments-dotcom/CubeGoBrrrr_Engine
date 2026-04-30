from __future__ import annotations
from typing import Any, Tuple
from src.Core.Math.Matrices.matrices import Matrix3x3, Matrix4x4

import math

Vector = Any  # expected to have .x, .y, .z attributes


class Quaternion:
    def __init__(self, w: float, x: float, y: float, z: float) -> None:
        self.w: float = w
        self.x: float = x
        self.y: float = y
        self.z: float = z

    def __str__(self) -> str:
        return f"Quaternion(w={self.w}, x={self.x}, y={self.y}, z={self.z})"

    def __repr__(self) -> str:
        return f"Quaternion({self.w!r}, {self.x!r}, {self.y!r}, {self.z!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Quaternion):
            return NotImplemented
        return self.w == other.w and self.x == other.x and self.y == other.y and self.z == other.z

    def __neg__(self) -> Quaternion:
        return Quaternion(-self.w, -self.x, -self.y, -self.z)

    def __add__(self, other: Quaternion) -> Quaternion:
        return Quaternion(self.w + other.w, self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Quaternion) -> Quaternion:
        return Quaternion(self.w - other.w, self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, other: object) -> Quaternion:
        if isinstance(other, Quaternion):
            result_w: float = self.w * other.w - self.x * other.x - self.y * other.y - self.z * other.z
            result_x: float = self.w * other.x + self.x * other.w + self.y * other.z - self.z * other.y
            result_y: float = self.w * other.y - self.x * other.z + self.y * other.w + self.z * other.x
            result_z: float = self.w * other.z + self.x * other.y - self.y * other.x + self.z * other.w
            return Quaternion(result_w, result_x, result_y, result_z)
        
        if isinstance(other, (int, float)):
            return Quaternion(self.w * float(other), self.x * float(other), self.y * float(other), self.z * float(other))
        return NotImplemented

    def __rmul__(self, scalar: float) -> Quaternion:
        return self.__mul__(scalar)

    @staticmethod
    def identity() -> Quaternion:
        return Quaternion(1.0, 0.0, 0.0, 0.0)

    @staticmethod
    def from_axis_angle(axis: Vector, angle_radians: float) -> Quaternion:
        axis_length: float = math.sqrt(axis.x * axis.x + axis.y * axis.y + axis.z * axis.z)
        if axis_length < 1e-10:
            return Quaternion.identity()
        
        inverse_axis_length: float = 1.0 / axis_length
        normalized_x: float = axis.x * inverse_axis_length
        normalized_y: float = axis.y * inverse_axis_length
        normalized_z: float = axis.z * inverse_axis_length

        half_angle: float = angle_radians * 0.5
        sin_half_angle: float = math.sin(half_angle)
        cos_half_angle: float = math.cos(half_angle)

        return Quaternion(
            cos_half_angle,
            normalized_x * sin_half_angle,
            normalized_y * sin_half_angle,
            normalized_z * sin_half_angle,
        )

    @staticmethod
    def from_euler_angles(pitch_radians: float, yaw_radians: float, roll_radians: float) -> Quaternion:
        half_pitch: float = pitch_radians * 0.5
        half_yaw: float = yaw_radians * 0.5
        half_roll: float = roll_radians * 0.5

        cos_half_pitch: float = math.cos(half_pitch)
        sin_half_pitch: float = math.sin(half_pitch)
        cos_half_yaw: float = math.cos(half_yaw)
        sin_half_yaw: float = math.sin(half_yaw)
        cos_half_roll: float = math.cos(half_roll)
        sin_half_roll: float = math.sin(half_roll)

        result_w: float = cos_half_roll * cos_half_pitch * cos_half_yaw + sin_half_roll * sin_half_pitch * sin_half_yaw
        result_x: float = cos_half_roll * sin_half_pitch * cos_half_yaw - sin_half_roll * cos_half_pitch * sin_half_yaw
        result_y: float = cos_half_roll * cos_half_pitch * sin_half_yaw + sin_half_roll * sin_half_pitch * cos_half_yaw
        result_z: float = sin_half_roll * cos_half_pitch * cos_half_yaw - cos_half_roll * sin_half_pitch * sin_half_yaw
        return Quaternion(result_w, result_x, result_y, result_z)

    @staticmethod
    def from_matrix3x3(matrix: Matrix3x3) -> Quaternion:
        trace: float = matrix.get(0, 0) + matrix.get(1, 1) + matrix.get(2, 2)
        if trace > 0.0:
            scale_factor: float = 0.5 / math.sqrt(trace + 1.0)
            return Quaternion(
                0.25 / scale_factor,
                (matrix.get(2, 1) - matrix.get(1, 2)) * scale_factor,
                (matrix.get(0, 2) - matrix.get(2, 0)) * scale_factor,
                (matrix.get(1, 0) - matrix.get(0, 1)) * scale_factor,
            )
        
        if matrix.get(0, 0) > matrix.get(1, 1) and matrix.get(0, 0) > matrix.get(2, 2):
            scale_factor = 2.0 * math.sqrt(1.0 + matrix.get(0, 0) - matrix.get(1, 1) - matrix.get(2, 2))
            return Quaternion(
                (matrix.get(2, 1) - matrix.get(1, 2)) / scale_factor,
                0.25 * scale_factor,
                (matrix.get(0, 1) + matrix.get(1, 0)) / scale_factor,
                (matrix.get(0, 2) + matrix.get(2, 0)) / scale_factor,
            )
        
        if matrix.get(1, 1) > matrix.get(2, 2):
            scale_factor = 2.0 * math.sqrt(1.0 + matrix.get(1, 1) - matrix.get(0, 0) - matrix.get(2, 2))
            return Quaternion(
                (matrix.get(0, 2) - matrix.get(2, 0)) / scale_factor,
                (matrix.get(0, 1) + matrix.get(1, 0)) / scale_factor,
                0.25 * scale_factor,
                (matrix.get(1, 2) + matrix.get(2, 1)) / scale_factor,
            )
        
        scale_factor = 2.0 * math.sqrt(1.0 + matrix.get(2, 2) - matrix.get(0, 0) - matrix.get(1, 1))
        return Quaternion(
            (matrix.get(1, 0) - matrix.get(0, 1)) / scale_factor,
            (matrix.get(0, 2) + matrix.get(2, 0)) / scale_factor,
            (matrix.get(1, 2) + matrix.get(2, 1)) / scale_factor,
            0.25 * scale_factor,
        )

    def dot(self, other: Quaternion) -> float:
        return self.w * other.w + self.x * other.x + self.y * other.y + self.z * other.z

    def length_squared(self) -> float:
        return self.w * self.w + self.x * self.x + self.y * self.y + self.z * self.z

    def length(self) -> float:
        return math.sqrt(self.length_squared())

    def normalized(self) -> Quaternion:
        quaternion_length: float = self.length()
        if quaternion_length < 1e-10:
            return Quaternion.identity()
        
        inverse_length: float = 1.0 / quaternion_length

        return Quaternion(
            self.w * inverse_length,
            self.x * inverse_length,
            self.y * inverse_length,
            self.z * inverse_length,
        )

    def conjugate(self) -> Quaternion:
        return Quaternion(self.w, -self.x, -self.y, -self.z)

    def inverse(self) -> Quaternion | None:
        squared_length: float = self.length_squared()
        if squared_length < 1e-10:
            return None
        inverse_squared_length: float = 1.0 / squared_length

        return Quaternion(
            self.w * inverse_squared_length,
            -self.x * inverse_squared_length,
            -self.y * inverse_squared_length,
            -self.z * inverse_squared_length,
        )

    def rotate_vector(self, vector: Vector) -> Tuple[float, float, float]:
        pure_quaternion: Quaternion = Quaternion(0.0, vector.x, vector.y, vector.z)
        rotated_quaternion: Quaternion = self * pure_quaternion * self.conjugate()
        return (rotated_quaternion.x, rotated_quaternion.y, rotated_quaternion.z)

    def to_matrix3x3(self) -> Matrix3x3:
        normalized_self: Quaternion = self.normalized()
        quaternion_w: float = normalized_self.w
        quaternion_x: float = normalized_self.x
        quaternion_y: float = normalized_self.y
        quaternion_z: float = normalized_self.z

        xx: float = quaternion_x * quaternion_x
        yy: float = quaternion_y * quaternion_y
        zz: float = quaternion_z * quaternion_z
        xy: float = quaternion_x * quaternion_y
        xz: float = quaternion_x * quaternion_z
        yz: float = quaternion_y * quaternion_z
        wx: float = quaternion_w * quaternion_x
        wy: float = quaternion_w * quaternion_y
        wz: float = quaternion_w * quaternion_z

        return Matrix3x3(
            1.0 - 2.0 * (yy + zz), 2.0 * (xy - wz), 2.0 * (xz + wy),
            2.0 * (xy + wz), 1.0 - 2.0 * (xx + zz), 2.0 * (yz - wx),
            2.0 * (xz - wy), 2.0 * (yz + wx), 1.0 - 2.0 * (xx + yy),
        )

    def to_matrix4x4(self) -> Matrix4x4:
        normalized_self: Quaternion = self.normalized()
        quaternion_w: float = normalized_self.w
        quaternion_x: float = normalized_self.x
        quaternion_y: float = normalized_self.y
        quaternion_z: float = normalized_self.z

        xx: float = quaternion_x * quaternion_x
        yy: float = quaternion_y * quaternion_y
        zz: float = quaternion_z * quaternion_z
        xy: float = quaternion_x * quaternion_y
        xz: float = quaternion_x * quaternion_z
        yz: float = quaternion_y * quaternion_z
        wx: float = quaternion_w * quaternion_x
        wy: float = quaternion_w * quaternion_y
        wz: float = quaternion_w * quaternion_z

        return Matrix4x4(
            1.0 - 2.0 * (yy + zz), 2.0 * (xy - wz), 2.0 * (xz + wy), 0.0,
            2.0 * (xy + wz), 1.0 - 2.0 * (xx + zz), 2.0 * (yz - wx), 0.0,
            2.0 * (xz - wy), 2.0 * (yz + wx), 1.0 - 2.0 * (xx + yy), 0.0,
            0.0, 0.0, 0.0, 1.0,
        )

    def to_euler_angles(self) -> Tuple[float, float, float]:
        normalized_self: Quaternion = self.normalized()
        quaternion_w: float = normalized_self.w
        quaternion_x: float = normalized_self.x
        quaternion_y: float = normalized_self.y
        quaternion_z: float = normalized_self.z

        sinr_cosp: float = 2.0 * (quaternion_w * quaternion_x + quaternion_y * quaternion_z)
        cosr_cosp: float = 1.0 - 2.0 * (quaternion_x * quaternion_x + quaternion_y * quaternion_y)
        pitch_radians: float = math.atan2(sinr_cosp, cosr_cosp)
        sinp: float = 2.0 * (quaternion_w * quaternion_y - quaternion_z * quaternion_x)

        if abs(sinp) >= 1.0:
            yaw_radians: float = math.copysign(math.pi / 2.0, sinp)
        else:
            yaw_radians = math.asin(sinp)

        siny_cosp: float = 2.0 * (quaternion_w * quaternion_z + quaternion_x * quaternion_y)
        cosy_cosp: float = 1.0 - 2.0 * (quaternion_y * quaternion_y + quaternion_z * quaternion_z)
        roll_radians: float = math.atan2(siny_cosp, cosy_cosp)
        return (pitch_radians, yaw_radians, roll_radians)

    @staticmethod
    def slerp(start: Quaternion, end: Quaternion, t: float) -> Quaternion:
        dot_product: float = start.dot(end)
        adjusted_end: Quaternion = end

        if dot_product < 0.0:
            adjusted_end = -end
            dot_product = -dot_product

        dot_product = min(1.0, dot_product)
        if dot_product > 0.9995:
            blended: Quaternion = start + (adjusted_end - start) * t
            return blended.normalized()
        
        theta_zero: float = math.acos(dot_product)
        theta: float = theta_zero * t

        sin_theta: float = math.sin(theta)
        sin_theta_zero: float = math.sin(theta_zero)

        scale_start: float = math.cos(theta) - dot_product * sin_theta / sin_theta_zero
        scale_end: float = sin_theta / sin_theta_zero
        return (start * scale_start + adjusted_end * scale_end).normalized()