from __future__ import annotations
from typing import Any, Tuple
from src.Core.Math.Matrices.matrices import Matrix3x3, Matrix4x4
from src.Core.Math.Quaternions.quaternions import Quaternion

import math

Vector = Any  # expected to have .x, .y, .z attributes


class Rotation:
    @staticmethod
    def euler_to_matrix3x3(pitch_radians: float, yaw_radians: float, roll_radians: float) -> Matrix3x3:
        rotation_x: Matrix3x3 = Matrix3x3.rotation_x(pitch_radians)
        rotation_y: Matrix3x3 = Matrix3x3.rotation_y(yaw_radians)
        rotation_z: Matrix3x3 = Matrix3x3.rotation_z(roll_radians)
        return rotation_z * rotation_y * rotation_x

    @staticmethod
    def euler_to_matrix4x4(pitch_radians: float, yaw_radians: float, roll_radians: float) -> Matrix4x4:
        rotation_x: Matrix4x4 = Matrix4x4.rotation_x(pitch_radians)
        rotation_y: Matrix4x4 = Matrix4x4.rotation_y(yaw_radians)
        rotation_z: Matrix4x4 = Matrix4x4.rotation_z(roll_radians)
        return rotation_z * rotation_y * rotation_x

    @staticmethod
    def euler_to_quaternion(pitch_radians: float, yaw_radians: float, roll_radians: float) -> Quaternion:
        return Quaternion.from_euler_angles(pitch_radians, yaw_radians, roll_radians)

    @staticmethod
    def axis_angle_to_matrix3x3(axis: Vector, angle_radians: float) -> Matrix3x3:
        cos_angle: float = math.cos(angle_radians)
        sin_angle: float = math.sin(angle_radians)
        one_minus_cos: float = 1.0 - cos_angle
        axis_length: float = math.sqrt(axis.x * axis.x + axis.y * axis.y + axis.z * axis.z)
        if axis_length < 1e-10:
            return Matrix3x3.identity()
        
        normalized_x: float = axis.x / axis_length
        normalized_y: float = axis.y / axis_length
        normalized_z: float = axis.z / axis_length

        return Matrix3x3(
            cos_angle + normalized_x * normalized_x * one_minus_cos,
            normalized_x * normalized_y * one_minus_cos - normalized_z * sin_angle,
            normalized_x * normalized_z * one_minus_cos + normalized_y * sin_angle,
            normalized_y * normalized_x * one_minus_cos + normalized_z * sin_angle,
            cos_angle + normalized_y * normalized_y * one_minus_cos,
            normalized_y * normalized_z * one_minus_cos - normalized_x * sin_angle,
            normalized_z * normalized_x * one_minus_cos - normalized_y * sin_angle,
            normalized_z * normalized_y * one_minus_cos + normalized_x * sin_angle,
            cos_angle + normalized_z * normalized_z * one_minus_cos,
        )

    @staticmethod
    def axis_angle_to_matrix4x4(axis: Vector, angle_radians: float) -> Matrix4x4:
        return Matrix4x4.rotation_axis_angle(axis, angle_radians)

    @staticmethod
    def axis_angle_to_quaternion(axis: Vector, angle_radians: float) -> Quaternion:
        return Quaternion.from_axis_angle(axis, angle_radians)

    @staticmethod
    def matrix3x3_to_euler(matrix: Matrix3x3) -> Tuple[float, float, float]:
        # ZYX convention: R = Rz(roll) * Ry(yaw) * Rx(pitch)
        # R[2][0] = -sin(yaw), R[2][1] = cos(yaw)*sin(pitch), R[2][2] = cos(yaw)*cos(pitch)
        # R[1][0] = cos(yaw)*sin(roll), R[0][0] = cos(yaw)*cos(roll)
        sin_yaw: float = -matrix.get(2, 0)

        if abs(sin_yaw) >= 1.0:
            yaw_radians: float = math.copysign(math.pi / 2.0, sin_yaw)
            pitch_radians: float = math.atan2(matrix.get(0, 1), matrix.get(0, 2))
            roll_radians: float = 0.0
        else:
            yaw_radians = math.asin(sin_yaw)
            pitch_radians = math.atan2(matrix.get(2, 1), matrix.get(2, 2))
            roll_radians = math.atan2(matrix.get(1, 0), matrix.get(0, 0))
        return (pitch_radians, yaw_radians, roll_radians)

    @staticmethod
    def matrix4x4_to_euler(matrix: Matrix4x4) -> Tuple[float, float, float]:
        # ZYX convention: R = Rz(roll) * Ry(yaw) * Rx(pitch)
        sin_yaw: float = -matrix.get(2, 0)

        if abs(sin_yaw) >= 1.0:
            yaw_radians: float = math.copysign(math.pi / 2.0, sin_yaw)
            pitch_radians: float = math.atan2(matrix.get(0, 1), matrix.get(0, 2))
            roll_radians: float = 0.0
        else:
            yaw_radians = math.asin(sin_yaw)
            pitch_radians = math.atan2(matrix.get(2, 1), matrix.get(2, 2))
            roll_radians = math.atan2(matrix.get(1, 0), matrix.get(0, 0))
        return (pitch_radians, yaw_radians, roll_radians)

    @staticmethod
    def quaternion_to_matrix3x3(quaternion: Quaternion) -> Matrix3x3:
        return quaternion.to_matrix3x3()

    @staticmethod
    def quaternion_to_matrix4x4(quaternion: Quaternion) -> Matrix4x4:
        return quaternion.to_matrix4x4()

    @staticmethod
    def matrix3x3_to_quaternion(matrix: Matrix3x3) -> Quaternion:
        return Quaternion.from_matrix3x3(matrix)

    @staticmethod
    def compose_rotations_matrix3x3(first: Matrix3x3, second: Matrix3x3) -> Matrix3x3:
        return second * first

    @staticmethod
    def compose_rotations_matrix4x4(first: Matrix4x4, second: Matrix4x4) -> Matrix4x4:
        return second * first

    @staticmethod
    def compose_rotations_quaternion(first: Quaternion, second: Quaternion) -> Quaternion:
        return second * first

    @staticmethod
    def invert_rotation_matrix3x3(matrix: Matrix3x3) -> Matrix3x3:
        return matrix.transpose()

    @staticmethod
    def invert_rotation_matrix4x4(matrix: Matrix4x4) -> Matrix4x4:
        return matrix.transpose()

    @staticmethod
    def invert_rotation_quaternion(quaternion: Quaternion) -> Quaternion:
        return quaternion.conjugate().normalized()
