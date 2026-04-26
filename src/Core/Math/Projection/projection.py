from __future__ import annotations

import math
from typing import Optional

from src.Core.Math.Matrices.matrices import Matrix4x4
from src.Core.Math.Vectors.vectors import Vector3

class Projection:
    @staticmethod
    def perspective(fov_radians: float, aspect_ratio: float, near_plane: float, far_plane: float) -> Matrix4x4:
        f: float = 1.0 / math.tan(fov_radians / 2.0)
        depth_range: float = near_plane - far_plane

        return Matrix4x4(
            f / aspect_ratio, 0.0, 0.0, 0.0,
            0.0, f, 0.0, 0.0,
            0.0, 0.0, (far_plane + near_plane) / depth_range, (2 * far_plane * near_plane) / depth_range,
            0.0, 0.0, -1.0, 0.0
        )
    
    @staticmethod
    def orthographic(left: float, right: float, bottom: float, top: float,
        near_plane: float, far_plane: float) -> Matrix4x4:
        width: float = right - left
        height: float = top - bottom
        depth: float = far_plane - near_plane

        if width < 1e-10 or height < 1e-10 or depth < 1e-10:
            return Matrix4x4.identity()
        
        return Matrix4x4(
            2.0 / width, 0.0, 0.0, -(right + left) / width,
            0.0, 2.0 / height, 0.0, -(top + bottom) / height,
            0.0, 0.0, -2.0 / depth, -(far_plane + near_plane) / depth,
            0.0, 0.0, 0.0, 1.0
        )
    
    # NDC (Normalized Device Coordinates): Didn't type this out due to significant length - Null Chan :3
    @staticmethod
    def clip_to_ndc(clip_x: float, clip_y: float, clip_z: float, clip_w: float) -> tuple[float, float, float]:
        if abs(clip_w) < 1e-10:
            return (0.0, 0.0, 0.0)
        
        ndc_x: float = clip_x / clip_w
        ndc_y: float = clip_y / clip_w
        ndc_z: float = clip_z / clip_w
        return (ndc_x, ndc_y, ndc_z)
    
    @staticmethod
    def ndc_to_screen(ndc_x: float, ndc_y: float, screen_width: int, screen_height: int) -> tuple[int, int]:
        screen_x: int = int((ndc_x + 1.0) * 0.5 * screen_width)
        screen_y: int = int((1.0 - (ndc_y + 1.0) * 0.5) * screen_height)
        return (screen_x, screen_y)
    
    @staticmethod
    def projection_point(world_point: Vector3, projection_matrix: Matrix4x4, view_matrix: Matrix4x4,
        viewport_width: int, viewport_height: int) -> Optional[tuple[int, int]]:

        view_x, view_y, view_z = view_matrix.transform_point(world_point)
        clip_x, clip_y, clip_z, clip_w = projection_matrix.transform_vector4(view_x, view_y, view_z, 1.0)

        if clip_w <= 0.0:
            return None

        ndc_x, ndc_y, _ = Projection.clip_to_ndc(clip_x, clip_y, clip_z, clip_w)
        screen_x, screen_y = Projection.ndc_to_screen(ndc_x, ndc_y, viewport_width, viewport_height)
        return (screen_x, screen_y)
    
    @staticmethod
    def unproject_point(screen_x: int, screen_y: int, depth_ndc: float, projection_matrix: Matrix4x4, view_matrix: Matrix4x4,
        viewport_width: int, viewport_height: int) -> Optional[Vector3]:

        ndc_x: float = (screen_x / viewport_width) * 2.0 - 1.0
        ndc_y: float = 1.0 - (screen_y / viewport_height) * 2.0

        inverse_projection_view: Optional[Matrix4x4] = (projection_matrix * view_matrix).inverse()
        if inverse_projection_view is None:
            return None

        world_x, world_y, world_z, world_w = inverse_projection_view.transform_vector4(ndc_x, ndc_y, depth_ndc, 1.0)

        if abs(world_w) < 1e-10:
            return None

        inverse_w: float = 1.0 / world_w
        return Vector3(world_x * inverse_w, world_y * inverse_w, world_z * inverse_w)