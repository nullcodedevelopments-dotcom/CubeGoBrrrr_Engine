from __future__ import annotations

import math
from typing import Optional, Tuple

from src.Core.Math.Matrices.matrices import Matrix3x3, Matrix4x4
from src.Core.Math.Quaternions.quaternions import Quaternion
from src.Core.Math.Vectors.vectors import Vector3

class Transform:
    def __init__(
        self,
        position: Optional[Vector3] = None,
        rotation: Optional[Quaternion] = None,
        scale: Optional[Vector3] = None,
    ) -> None:
        
        self.position: Vector3 = position if position is not None else Vector3(0.0, 0.0, 0.0)
        self.rotation: Quaternion = rotation if rotation is not None else Quaternion.identity()
        self.scale: Vector3 = scale if scale is not None else Vector3(1.0, 1.0, 1.0)

    def __str__(self) -> str:
        return (
            f"Transform(\n"
            f"  position={self.position},\n"
            f"  rotation={self.rotation},\n"
            f"  scale={self.scale}\n"
            f")"
        )

    def translate(self, offset: Vector3) -> None:
        self.position = self.position + offset

    def rotate(self, quaternion: Quaternion) -> None:
        self.rotation = (quaternion * self.rotation).normalized()

    def scale_by(self, scale_factor: Vector3) -> None:
        self.scale = Vector3(
            self.scale.x * scale_factor.x,
            self.scale.y * scale_factor.y,
            self.scale.z * scale_factor.z,
        )

    def to_model_matrix(self) -> Matrix4x4:
        scale_matrix: Matrix4x4 = Matrix4x4.scale(self.scale.x, self.scale.y, self.scale.z)
        rotation_matrix: Matrix4x4 = self.rotation.to_matrix4x4()
        translation_matrix: Matrix4x4 = Matrix4x4.translation(self.position.x, self.position.y, self.position.z)
        return translation_matrix * rotation_matrix * scale_matrix

    def to_normal_matrix(self) -> Optional[Matrix3x3]:
        model_matrix: Matrix4x4 = self.to_model_matrix()
        upper_left: Matrix3x3 = Matrix3x3(
            model_matrix.get(0, 0), model_matrix.get(0, 1), model_matrix.get(0, 2),
            model_matrix.get(1, 0), model_matrix.get(1, 1), model_matrix.get(1, 2),
            model_matrix.get(2, 0), model_matrix.get(2, 1), model_matrix.get(2, 2),
        )

        inverse_upper_left: Optional[Matrix3x3] = upper_left.inverse()
        if inverse_upper_left is None:
            return None
        return inverse_upper_left.transpose()

    @staticmethod
    def look_at(eye: Vector3, target: Vector3, world_up: Vector3) -> Matrix4x4:
        return Matrix4x4.look_at(eye, target, world_up)

    @staticmethod
    def decompose(matrix: Matrix4x4) -> Tuple[Vector3, Quaternion, Vector3]:
        translation_x: float = matrix.get(0, 3)
        translation_y: float = matrix.get(1, 3)
        translation_z: float = matrix.get(2, 3)
        position: Vector3 = Vector3(translation_x, translation_y, translation_z)

        scale_x: float = math.sqrt(
            matrix.get(0, 0) ** 2 + matrix.get(1, 0) ** 2 + matrix.get(2, 0) ** 2
        )
        scale_y: float = math.sqrt(
            matrix.get(0, 1) ** 2 + matrix.get(1, 1) ** 2 + matrix.get(2, 1) ** 2
        )
        scale_z: float = math.sqrt(
            matrix.get(0, 2) ** 2 + matrix.get(1, 2) ** 2 + matrix.get(2, 2) ** 2
        )
        extracted_scale: Vector3 = Vector3(scale_x, scale_y, scale_z)

        inverse_scale_x: float = 1.0 / scale_x if scale_x > 1e-10 else 0.0
        inverse_scale_y: float = 1.0 / scale_y if scale_y > 1e-10 else 0.0
        inverse_scale_z: float = 1.0 / scale_z if scale_z > 1e-10 else 0.0

        rotation_matrix: Matrix3x3 = Matrix3x3(
            matrix.get(0, 0) * inverse_scale_x, matrix.get(0, 1) * inverse_scale_y, matrix.get(0, 2) * inverse_scale_z,
            matrix.get(1, 0) * inverse_scale_x, matrix.get(1, 1) * inverse_scale_y, matrix.get(1, 2) * inverse_scale_z,
            matrix.get(2, 0) * inverse_scale_x, matrix.get(2, 1) * inverse_scale_y, matrix.get(2, 2) * inverse_scale_z,
        )
        extracted_rotation: Quaternion = Quaternion.from_matrix3x3(rotation_matrix)

        return (position, extracted_rotation, extracted_scale)


class TransformPipeline:
    @staticmethod
    def model_view_projection(model_matrix: Matrix4x4, view_matrix: Matrix4x4, projection_matrix: Matrix4x4) -> Matrix4x4:
        return projection_matrix * view_matrix * model_matrix

    @staticmethod
    def world_to_view(world_point: Vector3, view_matrix: Matrix4x4) -> Vector3:
        view_x, view_y, view_z = view_matrix.transform_point(world_point)
        return Vector3(view_x, view_y, view_z)

    @staticmethod
    def world_to_clip(
        world_point: Vector3,
        view_matrix: Matrix4x4,
        projection_matrix: Matrix4x4,
    ) -> Tuple[float, float, float, float]:
        
        view_x, view_y, view_z = view_matrix.transform_point(world_point)
        clip_x, clip_y, clip_z, clip_w = projection_matrix.transform_vector4(view_x, view_y, view_z, 1.0)
        return (clip_x, clip_y, clip_z, clip_w)

    @staticmethod
    def world_to_ndc(world_point: Vector3, view_matrix: Matrix4x4, projection_matrix: Matrix4x4) -> Optional[Tuple[float, float, float]]:
        clip_x, clip_y, clip_z, clip_w = TransformPipeline.world_to_clip(world_point, view_matrix, projection_matrix)
        if clip_w <= 0.0:
            return None
        
        inverse_clip_w: float = 1.0 / clip_w
        return (clip_x * inverse_clip_w, clip_y * inverse_clip_w, clip_z * inverse_clip_w)