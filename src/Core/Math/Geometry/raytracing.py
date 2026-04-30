from __future__ import annotations

import math
from typing import Any, Tuple

Vector = Any

class RayCast:
    def __init__(self, origin: Vector, direction: Vector) -> None:
        self.origin: Vector = origin
        self.direction: Vector = direction

    def __str__(self) -> str:
        return f"RayCast(origin={self.origin}, direction={self.direction})"

    def triangle_intersection(self, vertex0: Vector, vertex1: Vector, vertex2: Vector) -> Vector | None:
        edge_one: Vector = vertex1 - vertex0
        edge_two: Vector = vertex2 - vertex0
        cross_direction_edge_two: Vector = self.direction.cross(edge_two)
        determinant: float = edge_one.dot(cross_direction_edge_two)

        if abs(determinant) < 1e-6:
            return None

        inverse_determinant: float = 1.0 / determinant
        origin_to_vertex: Vector = self.origin - vertex0
        u_parameter: float = inverse_determinant * origin_to_vertex.dot(cross_direction_edge_two)

        if u_parameter < 0.0 or u_parameter > 1.0:
            return None

        cross_origin_edge_one: Vector = origin_to_vertex.cross(edge_one)
        v_parameter: float = inverse_determinant * self.direction.dot(cross_origin_edge_one)

        if v_parameter < 0.0 or u_parameter + v_parameter > 1.0:
            return None

        ray_distance: float = inverse_determinant * edge_two.dot(cross_origin_edge_one)

        if ray_distance > 1e-6:
            return self.origin + self.direction * ray_distance

        return None

    def sphere_intersection(self, center: Vector, radius: float) -> Vector | None:
        origin_to_center: Vector = self.origin - center
        coefficient_a: float = self.direction.dot(self.direction)
        coefficient_b: float = 2.0 * origin_to_center.dot(self.direction)
        coefficient_c: float = origin_to_center.dot(origin_to_center) - radius * radius
        discriminant: float = coefficient_b * coefficient_b - 4.0 * coefficient_a * coefficient_c

        if discriminant < 0.0:
            return None

        sqrt_discriminant: float = math.sqrt(discriminant)
        distance_t0: float = (-coefficient_b - sqrt_discriminant) / (2.0 * coefficient_a)
        distance_t1: float = (-coefficient_b + sqrt_discriminant) / (2.0 * coefficient_a)

        if distance_t0 > 1e-6:
            return self.origin + self.direction * distance_t0

        if distance_t1 > 1e-6:
            return self.origin + self.direction * distance_t1

        return None

    def plane_intersection(self, plane_point: Vector, plane_normal: Vector) -> Vector | None:
        denominator: float = plane_normal.dot(self.direction)

        if abs(denominator) < 1e-6:
            return None

        ray_distance: float = (plane_point - self.origin).dot(plane_normal) / denominator

        if ray_distance >= 1e-6:
            return self.origin + self.direction * ray_distance

        return None

    def box_intersection(self, box_minimum: Vector, box_maximum: Vector) -> Vector | None:
        inverse_direction_x: float = (1.0 / self.direction.x) if self.direction.x != 0.0 else math.inf
        inverse_direction_y: float = (1.0 / self.direction.y) if self.direction.y != 0.0 else math.inf
        inverse_direction_z: float = (1.0 / self.direction.z) if self.direction.z != 0.0 else math.inf

        slab_x_min: float = (box_minimum.x - self.origin.x) * inverse_direction_x
        slab_x_max: float = (box_maximum.x - self.origin.x) * inverse_direction_x
        slab_y_min: float = (box_minimum.y - self.origin.y) * inverse_direction_y
        slab_y_max: float = (box_maximum.y - self.origin.y) * inverse_direction_y
        slab_z_min: float = (box_minimum.z - self.origin.z) * inverse_direction_z
        slab_z_max: float = (box_maximum.z - self.origin.z) * inverse_direction_z

        t_min_x: float = min(slab_x_min, slab_x_max)
        t_max_x: float = max(slab_x_min, slab_x_max)
        t_min_y: float = min(slab_y_min, slab_y_max)
        t_max_y: float = max(slab_y_min, slab_y_max)
        t_min_z: float = min(slab_z_min, slab_z_max)
        t_max_z: float = max(slab_z_min, slab_z_max)

        t_enter: float = max(t_min_x, max(t_min_y, t_min_z))
        t_exit: float = min(t_max_x, min(t_max_y, t_max_z))

        if t_enter > t_exit or t_exit < 1e-6:
            return None

        return self.origin + self.direction * t_enter

    def cylinder_intersection(self, base_center: Vector, axis: Vector, radius: float, height: float) -> Vector | None:
        normalized_axis: Vector = axis.normalized()
        direction_projection: float = self.direction.dot(normalized_axis)
        perpendicular_direction: Vector = self.direction - normalized_axis * direction_projection
        origin_to_base: Vector = self.origin - base_center
        origin_projection: float = origin_to_base.dot(normalized_axis)
        perpendicular_origin: Vector = origin_to_base - normalized_axis * origin_projection

        coefficient_a: float = perpendicular_direction.dot(perpendicular_direction)
        coefficient_b: float = 2.0 * perpendicular_direction.dot(perpendicular_origin)
        coefficient_c: float = perpendicular_origin.dot(perpendicular_origin) - radius * radius
        discriminant: float = coefficient_b * coefficient_b - 4.0 * coefficient_a * coefficient_c

        if discriminant < 0.0:
            return None

        sqrt_discriminant: float = math.sqrt(discriminant)
        distance_t0: float = (-coefficient_b - sqrt_discriminant) / (2.0 * coefficient_a)
        distance_t1: float = (-coefficient_b + sqrt_discriminant) / (2.0 * coefficient_a)

        for ray_distance in (distance_t0, distance_t1):
            if ray_distance > 1e-6:
                intersection_point: Vector = self.origin + self.direction * ray_distance
                height_at_point: float = (intersection_point - base_center).dot(normalized_axis)
                if 0.0 <= height_at_point <= height:
                    return intersection_point

        return None

    def cone_intersection(self, apex: Vector, axis: Vector, angle: float) -> Vector | None:
        normalized_axis: Vector = axis.normalized()
        cos_angle: float = math.cos(angle)
        sin_angle: float = math.sin(angle)

        if abs(sin_angle) < 1e-6:
            return None

        cotangent_angle: float = cos_angle / sin_angle
        direction_projection: float = self.direction.dot(normalized_axis)
        perpendicular_direction: Vector = self.direction - normalized_axis * direction_projection
        origin_to_apex: Vector = self.origin - apex
        origin_projection: float = origin_to_apex.dot(normalized_axis)
        perpendicular_origin: Vector = origin_to_apex - normalized_axis * origin_projection

        coefficient_a: float = (
            perpendicular_direction.dot(perpendicular_direction)
            - (cotangent_angle * cotangent_angle) * (direction_projection * direction_projection)
        )
        coefficient_b: float = 2.0 * (
            perpendicular_direction.dot(perpendicular_origin)
            - (cotangent_angle * cotangent_angle) * direction_projection * origin_projection
        )
        coefficient_c: float = (
            perpendicular_origin.dot(perpendicular_origin)
            - (cotangent_angle * cotangent_angle) * (origin_projection * origin_projection)
        )
        discriminant: float = coefficient_b * coefficient_b - 4.0 * coefficient_a * coefficient_c

        if discriminant < 0.0:
            return None

        sqrt_discriminant: float = math.sqrt(discriminant)
        distance_t0: float = (-coefficient_b - sqrt_discriminant) / (2.0 * coefficient_a)
        distance_t1: float = (-coefficient_b + sqrt_discriminant) / (2.0 * coefficient_a)

        for ray_distance in (distance_t0, distance_t1):
            if ray_distance > 1e-6:
                intersection_point: Vector = self.origin + self.direction * ray_distance
                height_at_point: float = (intersection_point - apex).dot(normalized_axis)
                if height_at_point > 0.0:
                    return intersection_point

        return None

    def _barycentric_weights(self, vertex0: Vector, vertex1: Vector, vertex2: Vector, point: Vector) -> Tuple[float, float, float] | None:
        edge_one: Vector = vertex1 - vertex0
        edge_two: Vector = vertex2 - vertex0
        point_vector: Vector = point - vertex0

        dot00: float = edge_one.dot(edge_one)
        dot01: float = edge_one.dot(edge_two)
        dot11: float = edge_two.dot(edge_two)
        dot20: float = point_vector.dot(edge_one)
        dot21: float = point_vector.dot(edge_two)

        denominator: float = dot00 * dot11 - dot01 * dot01

        if abs(denominator) < 1e-6:
            return None

        inverse_denominator: float = 1.0 / denominator
        v_parameter: float = (dot11 * dot20 - dot01 * dot21) * inverse_denominator
        w_parameter: float = (dot00 * dot21 - dot01 * dot20) * inverse_denominator
        u_parameter: float = 1.0 - v_parameter - w_parameter

        if v_parameter < 0.0 or w_parameter < 0.0 or u_parameter < 0.0:
            return None

        return u_parameter, v_parameter, w_parameter

    def barycentric_interpolation(self, vertex0: Vector, vertex1: Vector, vertex2: Vector, uv0: Vector, uv1: Vector, uv2: Vector, point: Vector) -> Vector | None:
        barycentric_weights = self._barycentric_weights(vertex0, vertex1, vertex2, point)

        if barycentric_weights is None:
            return None

        u_parameter, v_parameter, w_parameter = barycentric_weights
        return uv0 * u_parameter + uv1 * v_parameter + uv2 * w_parameter

    def normal_interpolation(self, normal0: Vector, normal1: Vector, normal2: Vector, vertex0: Vector, vertex1: Vector, vertex2: Vector, point: Vector) -> Vector | None:
        barycentric_weights = self._barycentric_weights(vertex0, vertex1, vertex2, point)

        if barycentric_weights is None:
            return None

        u_parameter, v_parameter, w_parameter = barycentric_weights
        interpolated_normal: Vector = normal0 * u_parameter + normal1 * v_parameter + normal2 * w_parameter
        return interpolated_normal.normalized()

    def culling(self, normal: Vector, cull_mode: str) -> bool:
        if cull_mode == 'back' and self.direction.dot(normal) > 0.0:
            return True

        if cull_mode == 'front' and self.direction.dot(normal) < 0.0:
            return True

        return False

    traiangle_intersection = triangle_intersection