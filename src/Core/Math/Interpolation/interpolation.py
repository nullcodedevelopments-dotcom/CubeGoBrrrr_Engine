from __future__ import annotations

import math
from typing import Any

Vector = Any

class Interpolation:
    @staticmethod
    def linear_interpolation_scalar(start: float, end: float, t: float) -> float:
        return (1.0 - t) * start + t * end

    @staticmethod
    def linear_interpolation_vector(start: Vector, end: Vector, t: float) -> Vector:
        return (1.0 - t) * start + t * end

    @staticmethod
    def smoothstep_interpolation_scalar(start: float, end: float, t: float) -> float:
        clamped_t: float = max(0.0, min(1.0, t))
        smoothed_t: float = clamped_t * clamped_t * (3.0 - 2.0 * clamped_t)
        return (1.0 - smoothed_t) * start + smoothed_t * end

    @staticmethod
    def smoothstep_interpolation_vector(start: Vector, end: Vector, t: float) -> Vector:
        clamped_t: float = max(0.0, min(1.0, t))
        smoothed_t: float = clamped_t * clamped_t * (3.0 - 2.0 * clamped_t)
        return (1.0 - smoothed_t) * start + smoothed_t * end

    @staticmethod
    def smootherstep_interpolation_scalar(start: float, end: float, t: float) -> float:
        clamped_t: float = max(0.0, min(1.0, t))
        smoothed_t: float = clamped_t * clamped_t * clamped_t * (clamped_t * (6.0 * clamped_t - 15.0) + 10.0)
        return (1.0 - smoothed_t) * start + smoothed_t * end

    @staticmethod
    def smootherstep_interpolation_vector(start: Vector, end: Vector, t: float) -> Vector:
        clamped_t: float = max(0.0, min(1.0, t))
        smoothed_t: float = clamped_t * clamped_t * clamped_t * (clamped_t * (6.0 * clamped_t - 15.0) + 10.0)
        return (1.0 - smoothed_t) * start + smoothed_t * end

    @staticmethod
    def slerp_interpolation(start: Vector, end: Vector, t: float) -> Vector:
        dot_product: float = max(-1.0, min(1.0, start.dot(end)))
        theta: float = math.acos(dot_product)

        if abs(math.sin(theta)) < 1e-6:
            return Interpolation.linear_interpolation_vector(start, end, t)

        scale_start: float = math.sin((1.0 - t) * theta) / math.sin(theta)
        scale_end: float = math.sin(t * theta) / math.sin(theta)
        return scale_start * start + scale_end * end

    @staticmethod
    def triangular_interpolation(v0: Vector, v1: Vector, v2: Vector, w0: float, w1: float, w2: float) -> Vector:
        return w0 * v0 + w1 * v1 + w2 * v2

    @staticmethod
    def cubic_interpolation(p0: Vector, p1: Vector, p2: Vector, p3: Vector, t: float) -> Vector:
        t_squared: float = t * t
        t_cubed: float = t_squared * t
        return 0.5 * (2.0 * p1 + (p2 - p0) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t_squared + (3.0 * p1 - p0 - 3.0 * p2 + p3) * t_cubed)

    @staticmethod
    def bilinear_interpolation(bottom_left: Vector, bottom_right: Vector, top_left: Vector, top_right: Vector, u: float, v: float) -> Vector:
        bottom_edge: Vector = Interpolation.linear_interpolation_vector(bottom_left, bottom_right, u)
        top_edge: Vector = Interpolation.linear_interpolation_vector(top_left, top_right, u)
        return Interpolation.linear_interpolation_vector(bottom_edge, top_edge, v)

    @staticmethod
    def bicubic_interpolation(p00: Vector, p10: Vector, p20: Vector, p30: Vector,
        p01: Vector, p11: Vector, p21: Vector, p31: Vector,
        p02: Vector, p12: Vector, p22: Vector, p32: Vector,
        p03: Vector, p13: Vector, p23: Vector, p33: Vector,
        u: float,
        v: float) -> Vector:
        
        row_zero: Vector = Interpolation.cubic_interpolation(p00, p10, p20, p30, u)
        row_one: Vector = Interpolation.cubic_interpolation(p01, p11, p21, p31, u)
        row_two: Vector = Interpolation.cubic_interpolation(p02, p12, p22, p32, u)
        row_three: Vector = Interpolation.cubic_interpolation(p03, p13, p23, p33, u)
        return Interpolation.cubic_interpolation(row_zero, row_one, row_two, row_three, v)