from __future__ import annotations

import math
from typing import Any, List, Tuple

Vector = Any

class Matrix3x3:
    def __init__(
        self,
        row0_col0: float = 0.0, row0_col1: float = 0.0, row0_col2: float = 0.0,
        row1_col0: float = 0.0, row1_col1: float = 0.0, row1_col2: float = 0.0,
        row2_col0: float = 0.0, row2_col1: float = 0.0, row2_col2: float = 0.0,
    ) -> None:
        
        self.elements: List[float] = [
            row0_col0, row0_col1, row0_col2,
            row1_col0, row1_col1, row1_col2,
            row2_col0, row2_col1, row2_col2,
        ]

    def __str__(self) -> str:
        row0: List[float] = self.elements[0:3]
        row1: List[float] = self.elements[3:6]
        row2: List[float] = self.elements[6:9]

        return (
            f"Matrix3x3(\n"
            f"  [{row0[0]}, {row0[1]}, {row0[2]}]\n"
            f"  [{row1[0]}, {row1[1]}, {row1[2]}]\n"
            f"  [{row2[0]}, {row2[1]}, {row2[2]}]\n"
            f")"
        )

    def get(self, row: int, column: int) -> float:
        return self.elements[row * 3 + column]

    def set(self, row: int, column: int, value: float) -> None:
        self.elements[row * 3 + column] = value

    @staticmethod
    def identity() -> Matrix3x3:
        return Matrix3x3(
            1.0, 0.0, 0.0,
            0.0, 1.0, 0.0,
            0.0, 0.0, 1.0,
        )

    @staticmethod
    def scale(scale_x: float, scale_y: float, scale_z: float) -> Matrix3x3:
        return Matrix3x3(
            scale_x, 0.0, 0.0,
            0.0, scale_y, 0.0,
            0.0, 0.0, scale_z,
        )

    @staticmethod
    def rotation_x(angle_radians: float) -> Matrix3x3:
        cos_angle: float = math.cos(angle_radians)
        sin_angle: float = math.sin(angle_radians)

        return Matrix3x3(
            1.0, 0.0, 0.0,
            0.0, cos_angle, -sin_angle,
            0.0, sin_angle, cos_angle,
        )

    @staticmethod
    def rotation_y(angle_radians: float) -> Matrix3x3:
        cos_angle: float = math.cos(angle_radians)
        sin_angle: float = math.sin(angle_radians)

        return Matrix3x3(
            cos_angle, 0.0, sin_angle,
            0.0, 1.0, 0.0,
            -sin_angle, 0.0, cos_angle,
        )

    @staticmethod
    def rotation_z(angle_radians: float) -> Matrix3x3:
        cos_angle: float = math.cos(angle_radians)
        sin_angle: float = math.sin(angle_radians)

        return Matrix3x3(
            cos_angle, -sin_angle, 0.0,
            sin_angle, cos_angle, 0.0,
            0.0, 0.0, 1.0,
        )

    def __add__(self, other: Matrix3x3) -> Matrix3x3:
        return Matrix3x3(*[self.elements[index] + other.elements[index] for index in range(9)])

    def __sub__(self, other: Matrix3x3) -> Matrix3x3:
        return Matrix3x3(*[self.elements[index] - other.elements[index] for index in range(9)])

    def __mul__(self, other: object) -> Matrix3x3:
        if isinstance(other, Matrix3x3):
            result: Matrix3x3 = Matrix3x3()
            for row_index in range(3):
                for col_index in range(3):
                    accumulated_sum: float = 0.0
                    for k in range(3):
                        accumulated_sum += self.get(row_index, k) * other.get(k, col_index)
                    result.set(row_index, col_index, accumulated_sum)
            return result
        
        if isinstance(other, (int, float)):
            return Matrix3x3(*[element * float(other) for element in self.elements])
        return NotImplemented

    def __rmul__(self, scalar: float) -> Matrix3x3:
        return self.__mul__(scalar)

    def transpose(self) -> Matrix3x3:
        return Matrix3x3(
            self.get(0, 0), self.get(1, 0), self.get(2, 0),
            self.get(0, 1), self.get(1, 1), self.get(2, 1),
            self.get(0, 2), self.get(1, 2), self.get(2, 2),
        )

    def determinant(self) -> float:
        element_00: float = self.elements[0]
        element_01: float = self.elements[1]
        element_02: float = self.elements[2]
        element_10: float = self.elements[3]
        element_11: float = self.elements[4]
        element_12: float = self.elements[5]
        element_20: float = self.elements[6]
        element_21: float = self.elements[7]
        element_22: float = self.elements[8]

        return (
            element_00 * (element_11 * element_22 - element_12 * element_21)
            - element_01 * (element_10 * element_22 - element_12 * element_20)
            + element_02 * (element_10 * element_21 - element_11 * element_20)
        )

    def inverse(self) -> Matrix3x3 | None:
        matrix_determinant: float = self.determinant()
        if abs(matrix_determinant) < 1e-10:
            return None
        inverse_determinant: float = 1.0 / matrix_determinant

        element_00: float = self.elements[0]
        element_01: float = self.elements[1]
        element_02: float = self.elements[2]
        element_10: float = self.elements[3]
        element_11: float = self.elements[4]
        element_12: float = self.elements[5]
        element_20: float = self.elements[6]
        element_21: float = self.elements[7]
        element_22: float = self.elements[8]

        cofactor_00: float = element_11 * element_22 - element_12 * element_21
        cofactor_01: float = -(element_10 * element_22 - element_12 * element_20)
        cofactor_02: float = element_10 * element_21 - element_11 * element_20
        cofactor_10: float = -(element_01 * element_22 - element_02 * element_21)
        cofactor_11: float = element_00 * element_22 - element_02 * element_20
        cofactor_12: float = -(element_00 * element_21 - element_01 * element_20)
        cofactor_20: float = element_01 * element_12 - element_02 * element_11
        cofactor_21: float = -(element_00 * element_12 - element_02 * element_10)
        cofactor_22: float = element_00 * element_11 - element_01 * element_10

        return Matrix3x3(
            cofactor_00 * inverse_determinant, cofactor_10 * inverse_determinant, cofactor_20 * inverse_determinant,
            cofactor_01 * inverse_determinant, cofactor_11 * inverse_determinant, cofactor_21 * inverse_determinant,
            cofactor_02 * inverse_determinant, cofactor_12 * inverse_determinant, cofactor_22 * inverse_determinant,
        )

    def transform_vector(self, vector: Vector) -> Tuple[float, float, float]:
        result_x: float = self.get(0, 0) * vector.x + self.get(0, 1) * vector.y + self.get(0, 2) * vector.z
        result_y: float = self.get(1, 0) * vector.x + self.get(1, 1) * vector.y + self.get(1, 2) * vector.z
        result_z: float = self.get(2, 0) * vector.x + self.get(2, 1) * vector.y + self.get(2, 2) * vector.z

        return (result_x, result_y, result_z)


class Matrix4x4:
    def __init__(
        self,
        row0_col0: float = 0.0, row0_col1: float = 0.0, row0_col2: float = 0.0, row0_col3: float = 0.0,
        row1_col0: float = 0.0, row1_col1: float = 0.0, row1_col2: float = 0.0, row1_col3: float = 0.0,
        row2_col0: float = 0.0, row2_col1: float = 0.0, row2_col2: float = 0.0, row2_col3: float = 0.0,
        row3_col0: float = 0.0, row3_col1: float = 0.0, row3_col2: float = 0.0, row3_col3: float = 0.0,
    ) -> None:
        
        self.elements: List[float] = [
            row0_col0, row0_col1, row0_col2, row0_col3,
            row1_col0, row1_col1, row1_col2, row1_col3,
            row2_col0, row2_col1, row2_col2, row2_col3,
            row3_col0, row3_col1, row3_col2, row3_col3,
        ]

    def __str__(self) -> str:
        row0: List[float] = self.elements[0:4]
        row1: List[float] = self.elements[4:8]
        row2: List[float] = self.elements[8:12]
        row3: List[float] = self.elements[12:16]

        return (
            f"Matrix4x4(\n"
            f"  [{row0[0]}, {row0[1]}, {row0[2]}, {row0[3]}]\n"
            f"  [{row1[0]}, {row1[1]}, {row1[2]}, {row1[3]}]\n"
            f"  [{row2[0]}, {row2[1]}, {row2[2]}, {row2[3]}]\n"
            f"  [{row3[0]}, {row3[1]}, {row3[2]}, {row3[3]}]\n"
            f")"
        )

    def get(self, row: int, column: int) -> float:
        return self.elements[row * 4 + column]

    def set(self, row: int, column: int, value: float) -> None:
        self.elements[row * 4 + column] = value

    @staticmethod
    def identity() -> Matrix4x4:
        return Matrix4x4(
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0,
        )

    @staticmethod
    def translation(translate_x: float, translate_y: float, translate_z: float) -> Matrix4x4:
        return Matrix4x4(
            1.0, 0.0, 0.0, translate_x,
            0.0, 1.0, 0.0, translate_y,
            0.0, 0.0, 1.0, translate_z,
            0.0, 0.0, 0.0, 1.0,
        )

    @staticmethod
    def scale(scale_x: float, scale_y: float, scale_z: float) -> Matrix4x4:
        return Matrix4x4(
            scale_x, 0.0, 0.0, 0.0,
            0.0, scale_y, 0.0, 0.0,
            0.0, 0.0, scale_z, 0.0,
            0.0, 0.0, 0.0, 1.0,
        )

    @staticmethod
    def rotation_x(angle_radians: float) -> Matrix4x4:
        cos_angle: float = math.cos(angle_radians)
        sin_angle: float = math.sin(angle_radians)

        return Matrix4x4(
            1.0, 0.0, 0.0, 0.0,
            0.0, cos_angle, -sin_angle, 0.0,
            0.0, sin_angle, cos_angle, 0.0,
            0.0, 0.0, 0.0, 1.0,
        )

    @staticmethod
    def rotation_y(angle_radians: float) -> Matrix4x4:
        cos_angle: float = math.cos(angle_radians)
        sin_angle: float = math.sin(angle_radians)

        return Matrix4x4(
            cos_angle, 0.0, sin_angle, 0.0,
            0.0, 1.0, 0.0, 0.0,
            -sin_angle, 0.0, cos_angle, 0.0,
            0.0, 0.0, 0.0, 1.0,
        )

    @staticmethod
    def rotation_z(angle_radians: float) -> Matrix4x4:
        cos_angle: float = math.cos(angle_radians)
        sin_angle: float = math.sin(angle_radians)

        return Matrix4x4(
            cos_angle, -sin_angle, 0.0, 0.0,
            sin_angle, cos_angle, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0,
        )

    @staticmethod
    def rotation_axis_angle(axis: Vector, angle_radians: float) -> Matrix4x4:
        cos_angle: float = math.cos(angle_radians)
        sin_angle: float = math.sin(angle_radians)
        one_minus_cos: float = 1.0 - cos_angle
        axis_length: float = math.sqrt(axis.x * axis.x + axis.y * axis.y + axis.z * axis.z)
        if axis_length < 1e-10:
            return Matrix4x4.identity()
        
        normalized_x: float = axis.x / axis_length
        normalized_y: float = axis.y / axis_length
        normalized_z: float = axis.z / axis_length

        return Matrix4x4(
            cos_angle + normalized_x * normalized_x * one_minus_cos,
            normalized_x * normalized_y * one_minus_cos - normalized_z * sin_angle,
            normalized_x * normalized_z * one_minus_cos + normalized_y * sin_angle, 0.0,

            normalized_y * normalized_x * one_minus_cos + normalized_z * sin_angle,
            cos_angle + normalized_y * normalized_y * one_minus_cos,
            normalized_y * normalized_z * one_minus_cos - normalized_x * sin_angle, 0.0,

            normalized_z * normalized_x * one_minus_cos - normalized_y * sin_angle,
            normalized_z * normalized_y * one_minus_cos + normalized_x * sin_angle,
            cos_angle + normalized_z * normalized_z * one_minus_cos,
            0.0, 0.0, 0.0, 0.0, 1.0,
        )

    @staticmethod
    def perspective(
        field_of_view_y_radians: float,
        aspect_ratio: float,
        near_plane: float,
        far_plane: float,
    ) -> Matrix4x4:
        
        tan_half_fov: float = math.tan(field_of_view_y_radians / 2.0)
        depth_range_inverse: float = 1.0 / (near_plane - far_plane)

        return Matrix4x4(
            1.0 / (aspect_ratio * tan_half_fov), 0.0, 0.0, 0.0,
            0.0, 1.0 / tan_half_fov, 0.0, 0.0,
            0.0, 0.0, (near_plane + far_plane) * depth_range_inverse, 2.0 * near_plane * far_plane * depth_range_inverse,
            0.0, 0.0, -1.0, 0.0,
        )

    @staticmethod
    def orthographic(
        left_plane: float,
        right_plane: float,
        bottom_plane: float,
        top_plane: float,
        near_plane: float,
        far_plane: float,
    ) -> Matrix4x4:
        
        right_minus_left: float = right_plane - left_plane
        top_minus_bottom: float = top_plane - bottom_plane
        far_minus_near: float = far_plane - near_plane

        return Matrix4x4(
            2.0 / right_minus_left, 0.0, 0.0, -(right_plane + left_plane) / right_minus_left,
            0.0, 2.0 / top_minus_bottom, 0.0, -(top_plane + bottom_plane) / top_minus_bottom,
            0.0, 0.0, -2.0 / far_minus_near, -(far_plane + near_plane) / far_minus_near,
            0.0, 0.0, 0.0, 1.0,
        )

    @staticmethod
    def look_at(eye: Vector, target: Vector, world_up: Vector) -> Matrix4x4:
        forward_x: float = eye.x - target.x
        forward_y: float = eye.y - target.y
        forward_z: float = eye.z - target.z
        forward_length: float = math.sqrt(forward_x * forward_x + forward_y * forward_y + forward_z * forward_z)
        if forward_length < 1e-10:
            return Matrix4x4.identity()
        
        forward_x /= forward_length
        forward_y /= forward_length
        forward_z /= forward_length

        right_x: float = world_up.y * forward_z - world_up.z * forward_y
        right_y: float = world_up.z * forward_x - world_up.x * forward_z
        right_z: float = world_up.x * forward_y - world_up.y * forward_x
        right_length: float = math.sqrt(right_x * right_x + right_y * right_y + right_z * right_z)
        if right_length < 1e-10:
            return Matrix4x4.identity()
        
        right_x /= right_length
        right_y /= right_length
        right_z /= right_length

        up_x: float = forward_y * right_z - forward_z * right_y
        up_y: float = forward_z * right_x - forward_x * right_z
        up_z: float = forward_x * right_y - forward_y * right_x

        return Matrix4x4(
            right_x, right_y, right_z, -(right_x * eye.x + right_y * eye.y + right_z * eye.z),
            up_x, up_y, up_z, -(up_x * eye.x + up_y * eye.y + up_z * eye.z),
            forward_x, forward_y, forward_z, -(forward_x * eye.x + forward_y * eye.y + forward_z * eye.z),
            0.0, 0.0, 0.0, 1.0,
        )

    def __add__(self, other: Matrix4x4) -> Matrix4x4:
        return Matrix4x4(*[self.elements[index] + other.elements[index] for index in range(16)])

    def __sub__(self, other: Matrix4x4) -> Matrix4x4:
        return Matrix4x4(*[self.elements[index] - other.elements[index] for index in range(16)])

    def __mul__(self, other: object) -> Matrix4x4:
        if isinstance(other, Matrix4x4):
            result: Matrix4x4 = Matrix4x4()
            for row_index in range(4):
                for col_index in range(4):
                    accumulated_sum: float = 0.0
                    for k in range(4):
                        accumulated_sum += self.get(row_index, k) * other.get(k, col_index)
                    result.set(row_index, col_index, accumulated_sum)
            return result
        
        if isinstance(other, (int, float)):
            return Matrix4x4(*[element * float(other) for element in self.elements])
        return NotImplemented

    def __rmul__(self, scalar: float) -> Matrix4x4:
        return self.__mul__(scalar)

    def transpose(self) -> Matrix4x4:
        return Matrix4x4(
            self.get(0, 0), self.get(1, 0), self.get(2, 0), self.get(3, 0),
            self.get(0, 1), self.get(1, 1), self.get(2, 1), self.get(3, 1),
            self.get(0, 2), self.get(1, 2), self.get(2, 2), self.get(3, 2),
            self.get(0, 3), self.get(1, 3), self.get(2, 3), self.get(3, 3),
        )

    def _minor_determinant(self, skip_row: int, skip_column: int) -> float:
        minor_elements: List[float] = [
            self.elements[row * 4 + col]
            for row in range(4) if row != skip_row
            for col in range(4) if col != skip_column
        ]

        element_00: float = minor_elements[0]
        element_01: float = minor_elements[1]
        element_02: float = minor_elements[2]
        element_10: float = minor_elements[3]
        element_11: float = minor_elements[4]
        element_12: float = minor_elements[5]
        element_20: float = minor_elements[6]
        element_21: float = minor_elements[7]
        element_22: float = minor_elements[8]

        return (
            element_00 * (element_11 * element_22 - element_12 * element_21)
            - element_01 * (element_10 * element_22 - element_12 * element_20)
            + element_02 * (element_10 * element_21 - element_11 * element_20)
        )

    def determinant(self) -> float:
        cofactor_sum: float = 0.0

        for col_index in range(4):
            sign: float = 1.0 if col_index % 2 == 0 else -1.0
            cofactor_sum += sign * self.elements[col_index] * self._minor_determinant(0, col_index)
        return cofactor_sum

    def inverse(self) -> Matrix4x4 | None:
        matrix_determinant: float = self.determinant()
        if abs(matrix_determinant) < 1e-10:
            return None
        
        inverse_determinant: float = 1.0 / matrix_determinant
        result: Matrix4x4 = Matrix4x4()

        for row_index in range(4):
            for col_index in range(4):
                sign: float = 1.0 if (row_index + col_index) % 2 == 0 else -1.0
                cofactor_value: float = sign * self._minor_determinant(row_index, col_index)
                result.set(col_index, row_index, cofactor_value * inverse_determinant)
        return result

    def transform_point(self, vector: Vector) -> Tuple[float, float, float]:
        result_x: float = self.get(0, 0) * vector.x + self.get(0, 1) * vector.y + self.get(0, 2) * vector.z + self.get(0, 3)
        result_y: float = self.get(1, 0) * vector.x + self.get(1, 1) * vector.y + self.get(1, 2) * vector.z + self.get(1, 3)
        result_z: float = self.get(2, 0) * vector.x + self.get(2, 1) * vector.y + self.get(2, 2) * vector.z + self.get(2, 3)
        return (result_x, result_y, result_z)

    def transform_direction(self, vector: Vector) -> Tuple[float, float, float]:
        result_x: float = self.get(0, 0) * vector.x + self.get(0, 1) * vector.y + self.get(0, 2) * vector.z
        result_y: float = self.get(1, 0) * vector.x + self.get(1, 1) * vector.y + self.get(1, 2) * vector.z
        result_z: float = self.get(2, 0) * vector.x + self.get(2, 1) * vector.y + self.get(2, 2) * vector.z
        return (result_x, result_y, result_z)

    def transform_vector4(self, x: float, y: float, z: float, w: float) -> Tuple[float, float, float, float]:
        result_x: float = self.get(0, 0) * x + self.get(0, 1) * y + self.get(0, 2) * z + self.get(0, 3) * w
        result_y: float = self.get(1, 0) * x + self.get(1, 1) * y + self.get(1, 2) * z + self.get(1, 3) * w
        result_z: float = self.get(2, 0) * x + self.get(2, 1) * y + self.get(2, 2) * z + self.get(2, 3) * w
        result_w: float = self.get(3, 0) * x + self.get(3, 1) * y + self.get(3, 2) * z + self.get(3, 3) * w
        return (result_x, result_y, result_z, result_w)
