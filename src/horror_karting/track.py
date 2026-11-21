"""Pista de Horror Karting: spline cerrada, muestreo por longitud de arco.

Todo el módulo es puro Python (sin Panda3D) para poder testear la simulación.
La pista se recorre en coordenadas (s, t):

* ``s`` es la distancia recorrida sobre la línea central (puede ser negativa
  en la grilla de largada y crece sin límite durante la carrera).
* ``t`` es el desplazamiento lateral en metros, positivo a la derecha del
  sentido de avance.
* ``z`` sale del perfil de altura de la spline.

La malla 3D se construye en ``scenery.py`` a partir de ``samples``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

Vec3 = tuple[float, float, float]

# Puntos de control (x, y, z). La pista sale de (0, -120) rumbo al oeste,
# recorre el cementerio y vuelve por la recta inferior.
CONTROL_POINTS: tuple[Vec3, ...] = (
    (0.0, -120.0, 0.0),
    (-50.0, -120.0, 0.0),
    (-85.0, -112.0, 0.0),
    (-110.0, -122.0, 0.0),
    (-135.0, -115.0, 0.0),
    (-150.0, -90.0, 0.4),
    (-152.0, -60.0, 1.4),
    (-150.0, -40.0, 2.8),
    (-146.0, -20.0, 2.8),
    (-152.0, 0.0, 0.4),
    (-150.0, 30.0, 0.0),
    (-142.0, 65.0, 0.4),
    (-122.0, 95.0, 0.8),
    (-95.0, 118.0, 0.8),
    (-65.0, 135.0, 0.6),
    (-30.0, 142.0, 0.4),
    (10.0, 142.0, 0.4),
    (50.0, 138.0, 0.4),
    (85.0, 125.0, 0.3),
    (112.0, 102.0, 0.2),
    (132.0, 70.0, 0.2),
    (142.0, 30.0, 0.2),
    (150.0, -10.0, 0.0),
    (154.0, -45.0, 0.0),
    (150.0, -78.0, 0.0),
    (136.0, -104.0, 0.0),
    (112.0, -118.0, 0.0),
    (88.0, -122.0, 0.0),
    (66.0, -120.0, 1.9),
    (44.0, -120.0, 0.0),
    (20.0, -120.0, 0.0),
)

TARGET_LENGTH = 1600.0
HALF_WIDTH = 6.0


@dataclass(frozen=True, slots=True)
class TrackSample:
    pos: Vec3
    tangent: Vec3
    lateral: Vec3
    curvature: float
    bank: float
    s: float


def _lerp(a: float, b: float, f: float) -> float:
    return a + (b - a) * f


def _catmull(p0: Vec3, p1: Vec3, p2: Vec3, p3: Vec3, t: float) -> Vec3:
    t2 = t * t
    t3 = t2 * t
    values: list[float] = []
    for a, b, c, d in zip(p0, p1, p2, p3, strict=True):
        values.append(
            0.5
            * (
                2.0 * b
                + (-a + c) * t
                + (2.0 * a - 5.0 * b + 4.0 * c - d) * t2
                + (-a + 3.0 * b - 3.0 * c + d) * t3
            )
        )
    return (values[0], values[1], values[2])


def _distance(a: Vec3, b: Vec3) -> float:
    return math.dist(a, b)


def _normalize(vector: Vec3) -> Vec3:
    length = math.sqrt(vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2)
    if length < 1e-9:
        return (0.0, 1.0, 0.0)
    return (vector[0] / length, vector[1] / length, vector[2] / length)


class Track:
    """Circuito cerrado con muestras equidistantes en longitud de arco."""

    def __init__(
        self,
        control: tuple[Vec3, ...] = CONTROL_POINTS,
        *,
        target_length: float = TARGET_LENGTH,
        half_width: float = HALF_WIDTH,
        step: float = 0.72,
    ) -> None:
        if len(control) < 4:
            raise ValueError("la pista necesita al menos 4 puntos de control")
        dense = self._dense_points(control)
        raw_length = self._polyline_length(dense)
        scale = target_length / max(raw_length, 1e-6)
        scaled = [(x * scale, y * scale, z) for x, y, z in dense]
        self.length = target_length
        self.half_width = half_width
        self.scale = scale
        self.step = step
        self.samples = self._resample(scaled, target_length, step)
        self._compute_frames()
        self.sample_count = len(self.samples)

    # -- construccion -------------------------------------------------------

    @staticmethod
    def _dense_points(control: tuple[Vec3, ...], subdivisions: int = 16) -> list[Vec3]:
        count = len(control)
        points: list[Vec3] = []
        for index in range(count):
            p0 = control[(index - 1) % count]
            p1 = control[index]
            p2 = control[(index + 1) % count]
            p3 = control[(index + 2) % count]
            for sub in range(subdivisions):
                points.append(_catmull(p0, p1, p2, p3, sub / subdivisions))
        points.append(points[0])
        return points

    @staticmethod
    def _polyline_length(points: list[Vec3]) -> float:
        total = 0.0
        for a, b in zip(points, points[1:], strict=False):
            total += _distance(a, b)
        return total

    @staticmethod
    def _resample(points: list[Vec3], target_length: float, step: float) -> list[TrackSample]:
        count = max(8, int(round(target_length / step)))
        actual_step = target_length / count
        result: list[TrackSample] = []
        target = 0.0
        index = 0
        walked = 0.0
        while len(result) < count:
            while index < len(points) - 2:
                seg = _distance(points[index], points[index + 1])
                if walked + seg >= target:
                    break
                walked += seg
                index += 1
            if index >= len(points) - 1:
                break
            seg = _distance(points[index], points[index + 1])
            fraction = 0.0 if seg < 1e-9 else (target - walked) / seg
            fraction = max(0.0, min(1.0, fraction))
            a = points[index]
            b = points[index + 1]
            pos = (
                _lerp(a[0], b[0], fraction),
                _lerp(a[1], b[1], fraction),
                _lerp(a[2], b[2], fraction),
            )
            result.append(TrackSample(pos, (0.0, 1.0, 0.0), (1.0, 0.0, 0.0), 0.0, 0.0, target))
            target += actual_step
        while len(result) < count:
            result.append(result[-1])
        return result

    def _compute_frames(self) -> None:
        count = len(self.samples)
        tangents: list[Vec3] = []
        for index in range(count):
            previous = self.samples[(index - 1) % count].pos
            following = self.samples[(index + 1) % count].pos
            tangents.append(_normalize((following[0] - previous[0], following[1] - previous[1], following[2] - previous[2])))
        frames: list[TrackSample] = []
        for index in range(count):
            tangent = tangents[index]
            horizontal = math.hypot(tangent[0], tangent[1])
            if horizontal < 1e-6:
                horizontal = 1.0
            lateral = (tangent[1] / horizontal, -tangent[0] / horizontal, 0.0)
            nxt = tangents[(index + 1) % count]
            cross = tangent[0] * nxt[1] - tangent[1] * nxt[0]
            curvature = cross / max(self.step, 1e-6)
            bank = max(-0.10, min(0.10, -curvature * 26.0))
            old = self.samples[index]
            frames.append(
                TrackSample(old.pos, tangent, lateral, curvature, bank, old.s)
            )
        self.samples = frames

    # -- consultas ----------------------------------------------------------

    def _at(self, s: float) -> tuple[int, int, float]:
        wrapped = s % self.length
        position = wrapped / self.length * self.sample_count
        index = int(position)
        fraction = position - index
        return index % self.sample_count, (index + 1) % self.sample_count, fraction

    def sample(self, s: float) -> TrackSample:
        i, j, f = self._at(s)
        a = self.samples[i]
        b = self.samples[j]
        pos = (
            _lerp(a.pos[0], b.pos[0], f),
            _lerp(a.pos[1], b.pos[1], f),
            _lerp(a.pos[2], b.pos[2], f),
        )
        tangent = _normalize(
            (
                _lerp(a.tangent[0], b.tangent[0], f),
                _lerp(a.tangent[1], b.tangent[1], f),
                _lerp(a.tangent[2], b.tangent[2], f),
            )
        )
        lateral = _normalize(
            (
                _lerp(a.lateral[0], b.lateral[0], f),
                _lerp(a.lateral[1], b.lateral[1], f),
                0.0,
            )
        )
        return TrackSample(
            pos,
            tangent,
            lateral,
            _lerp(a.curvature, b.curvature, f),
            _lerp(a.bank, b.bank, f),
            s,
        )

    def point(self, s: float, lateral: float = 0.0) -> Vec3:
        sample = self.sample(s)
        return (
            sample.pos[0] + sample.lateral[0] * lateral,
            sample.pos[1] + sample.lateral[1] * lateral,
            sample.pos[2],
        )

    def height(self, s: float) -> float:
        return self.sample(s).pos[2]

    def tangent(self, s: float) -> Vec3:
        return self.sample(s).tangent

    def curvature(self, s: float) -> float:
        return self.sample(s).curvature

    def heading(self, s: float) -> float:
        """Heading de Panda3D (radianes) para el sentido de avance."""
        tangent = self.tangent(s)
        return math.atan2(-tangent[0], tangent[1])

    def slope(self, s: float, delta: float = 1.0) -> float:
        return (self.height(s + delta) - self.height(s - delta)) / (2.0 * delta)

    def lateral_at(self, s: float) -> Vec3:
        return self.sample(s).lateral

    def point_ahead(self, s: float, distance: float) -> tuple[float, float, float]:
        return self.point(s + distance)

    def nearest_s(self, x: float, y: float) -> float:
        best = 0.0
        best_distance = float("inf")
        for sample in self.samples:
            dx = sample.pos[0] - x
            dy = sample.pos[1] - y
            distance = dx * dx + dy * dy
            if distance < best_distance:
                best_distance = distance
                best = sample.s
        return best
