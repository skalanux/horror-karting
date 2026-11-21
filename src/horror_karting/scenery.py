"""Mundo estático: cielo, pista, cementerio, puente, túnel, salto y escenarios."""

from __future__ import annotations

import math
import random

from panda3d.core import (
    Fog,
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    NodePath,
    Vec4,
)

from .palette import (
    CREAM,
    EDGE,
    FIREFLY,
    FOG,
    GOLD,
    GRASS,
    GRASS_2,
    GROUND,
    INK,
    MOON,
    PUMPKIN,
    ROAD,
    ROAD_2,
    SKY_GLOW,
    SKY_HORIZON,
    SKY_MID,
    SKY_ZENITH,
    STAR,
    STEM,
    STONE,
    STONE_DARK,
    STONE_LIGHT,
    TREE,
    TREE_2,
    WALL,
    WATER,
    WOOD,
    WOOD_2,
    v,
)
from .primitives import Build
from .track import Track


def _mix(a: Vec4, b: Vec4, factor: float) -> Vec4:
    return Vec4(
        a[0] + (b[0] - a[0]) * factor,
        a[1] + (b[1] - a[1]) * factor,
        a[2] + (b[2] - a[2]) * factor,
        a[3] + (b[3] - a[3]) * factor,
    )


class World:
    """Todo lo que no se mueve. Se puede reconstruir para la pista espejada."""

    def __init__(self, base: object, root: NodePath, track: Track, *, mirror: bool = False) -> None:
        self.base = base
        self.root = root
        self.track = track
        self.mirror = mirror
        self.node = root.attach_new_node("world")
        self.build = Build(base)
        self.rng = random.Random(23 if mirror else 17)
        self.fireflies: list[tuple[NodePath, tuple[float, float, float], float]] = []
        self.bats: list[tuple[NodePath, NodePath, list[NodePath], float]] = []
        self.torches: list[NodePath] = []
        self.clouds: list[tuple[NodePath, float, float]] = []
        self.fog = Fog("horror-fog")
        self.fog.set_color(v(FOG))
        self.fog.set_exp_density(0.00125)
        self.node.set_fog(self.fog)
        self.start_point = track.point(0)
        self.crypt_point = track.point(0, -20)
        self.stage_point = track.point(30, 15)
        self.podium_point = track.point(-35, 15)
        self.moon_point = (-260.0, -600.0, 120.0)
        self._sky()
        self._ground()
        self._road()
        self._walls()
        self._start_area()
        self._crypt()
        self._bridge()
        self._tunnel()
        self._jump()
        self._cemetery()
        self._landmarks()
        self._stage()
        self._podium()
        self._fireflies()
        self._bats()
        self._clouds()

    # ------------------------------------------------------------------ mesh

    def _pool(self, parent: NodePath, center: tuple[float, float, float], radius: float, color: Vec4) -> NodePath:
        pool = self.build.ball(parent, center, (radius, radius, 0.02), color, alpha=True)
        pool.set_depth_write(False)
        pool.set_bin("fixed", 2)
        return pool

    def _mesh(self, name: str, verts: list[tuple[float, float, float]], colors: list[Vec4], triangles: list[tuple[int, int, int]], *, two_sided: bool = True, bin_name: str | None = None, sort: int = 0, fog: bool = True) -> NodePath:
        data = GeomVertexData(name, GeomVertexFormat.getV3c4(), Geom.UHStatic)
        writer = GeomVertexWriter(data, "vertex")
        color = GeomVertexWriter(data, "color")
        for (x, y, z), rgba in zip(verts, colors, strict=True):
            writer.add_data3(x, y, z)
            color.add_data4(rgba)
        prim = GeomTriangles(Geom.UHStatic)
        for a, b, c in triangles:
            prim.add_vertices(a, b, c)
        geom = Geom(data)
        geom.add_primitive(prim)
        node = GeomNode(name)
        node.add_geom(geom)
        holder = self.node.attach_new_node(node)
        holder.set_light_off(1)
        holder.set_two_sided(two_sided)
        if bin_name:
            holder.set_bin(bin_name, sort)
        if not fog:
            holder.set_fog_off(1)
        return holder

    def _ribbon(self, name: str, off_a: float, off_b: float, z_a: float, z_b: float, color_a: Vec4, color_b: Vec4 | None = None, variation: float = 0.0) -> NodePath:
        samples = self.track.samples
        verts: list[tuple[float, float, float]] = []
        colors: list[Vec4] = []
        for index, sample in enumerate(samples):
            base = color_a if color_b is None or (index // 4) % 2 == 0 else color_b
            factor = 1.0 + variation * math.sin(index * 0.19)
            color = Vec4(base[0] * factor, base[1] * factor, base[2] * factor, base[3])
            for off, zoff in ((off_a, z_a), (off_b, z_b)):
                verts.append(
                    (
                        sample.pos[0] + sample.lateral[0] * off,
                        sample.pos[1] + sample.lateral[1] * off,
                        sample.pos[2] + zoff,
                    )
                )
                colors.append(color)
        count = len(samples)
        tris: list[tuple[int, int, int]] = []
        for index in range(count):
            nxt = (index + 1) % count
            a = index * 2
            b = a + 1
            c = nxt * 2
            d = c + 1
            tris.append((a, b, c))
            tris.append((b, d, c))
        return self._mesh(name, verts, colors, tris)

    # ------------------------------------------------------------------- sky

    def _sky(self) -> None:
        radius = 880.0
        lat_steps = 12
        lon_steps = 32
        verts: list[tuple[float, float, float]] = []
        colors: list[Vec4] = []
        moon_az = math.atan2(self.moon_point[1], self.moon_point[0])
        zenith = v(SKY_ZENITH)
        mid = v(SKY_MID)
        horizon = v(SKY_HORIZON)
        glow = v(SKY_GLOW)
        for lat in range(lat_steps + 1):
            phi = math.pi / 2.0 * lat / lat_steps
            height = math.sin(phi) * radius
            ring = math.cos(phi) * radius
            for lon in range(lon_steps):
                theta = math.tau * lon / lon_steps
                x = math.cos(theta) * ring
                y = math.sin(theta) * ring
                t = height / radius
                if t > 0.55:
                    color = _mix(mid, zenith, (t - 0.55) / 0.45)
                else:
                    color = _mix(horizon, mid, t / 0.55)
                warm = max(0.0, math.cos(theta - moon_az)) ** 8 * (1.0 - t) ** 3 * 0.70
                color = Vec4(
                    min(1.0, color[0] + glow[0] * warm),
                    min(1.0, color[1] + glow[1] * warm),
                    min(1.0, color[2] + glow[2] * warm),
                    1.0,
                )
                verts.append((x, y, height))
                colors.append(color)
        tris: list[tuple[int, int, int]] = []
        for lat in range(lat_steps):
            for lon in range(lon_steps):
                nxt = (lon + 1) % lon_steps
                a = lat * lon_steps + lon
                b = lat * lon_steps + nxt
                c = (lat + 1) * lon_steps + lon
                d = (lat + 1) * lon_steps + nxt
                tris.append((a, b, c))
                tris.append((b, d, c))
        self._mesh("sky", verts, colors, tris, two_sided=True, bin_name="background", sort=0, fog=False)
        # luna
        moon = self.build.ball(self.node, self.moon_point, 24.0, v(MOON))
        moon.set_fog_off(1)
        moon.set_depth_write(False)
        moon.set_bin("background", 1)
        center = (0.0, 0.0, 0.0)
        direction = (center[0] - self.moon_point[0], center[1] - self.moon_point[1], center[2] - self.moon_point[2])
        length = math.sqrt(direction[0] ** 2 + direction[1] ** 2 + direction[2] ** 2) or 1.0
        dx, dy, dz = direction[0] / length, direction[1] / length, direction[2] / length
        for index, (ox, oy, radius) in enumerate(((-0.22, 0.18, 4.2), (0.26, -0.12, 3.1), (0.05, 0.35, 2.4))):
            _ = index
            crater = self.build.ball(
                self.node,
                (
                    self.moon_point[0] + dx * 18.0 + ox * 12.0,
                    self.moon_point[1] + dy * 18.0 + oy * 12.0,
                    self.moon_point[2] + dz * 18.0 + 0.5,
                ),
                radius,
                Vec4(0.82, 0.80, 0.72, 1.0),
            )
            crater.set_fog_off(1)
            crater.set_depth_write(False)
            crater.set_bin("background", 1)
        for index, (scale, alpha) in enumerate(((1.35, 0.10), (1.9, 0.05), (2.6, 0.025))):
            halo = self.build.ball(self.node, self.moon_point, 24.0 * scale, Vec4(MOON[0], MOON[1], MOON[2], alpha), alpha=True)
            halo.set_fog_off(1)
            halo.set_depth_write(False)
            halo.set_bin("background", 1)
            _ = index
        # estrellas
        rng = random.Random(91)
        for _ in range(110):
            theta = rng.uniform(0, math.tau)
            sigma = rng.uniform(0.06, 1.35)
            r = 790.0
            x = math.cos(theta) * math.cos(sigma) * r
            y = math.sin(theta) * math.cos(sigma) * r
            z = math.sin(sigma) * r
            if z < 40.0:
                continue
            star = self.build.ball(self.node, (x, y, z), rng.uniform(0.6, 1.5), v(STAR))
            star.set_fog_off(1)
            star.set_depth_write(False)
            star.set_bin("background", 0)

    # ---------------------------------------------------------------- ground

    def _ground(self) -> None:
        self.build.box(self.node, (0, 0, -0.35), (1500, 1500, 0.7), v(GROUND))
        rng = random.Random(5)
        for _ in range(55):
            x = rng.uniform(-500, 500)
            y = rng.uniform(-500, 500)
            size = rng.uniform(30, 110)
            color = v(GRASS if rng.random() < 0.5 else GRASS_2)
            self.build.box(self.node, (x, y, 0.015), (size, size * rng.uniform(0.5, 1.4), 0.02), color)

    def _road(self) -> None:
        samples = self.track.samples
        half = self.track.half_width
        verts: list[tuple[float, float, float]] = []
        colors: list[Vec4] = []
        for index, sample in enumerate(samples):
            factor = 0.88 + 0.16 * math.sin(index * 0.21)
            base = ROAD_2 if (index // 9) % 2 == 0 else ROAD
            color = Vec4(base[0] * factor, base[1] * factor, base[2] * factor, 1.0)
            for off in (-half, half):
                z = sample.pos[2] - math.sin(sample.bank) * off
                verts.append(
                    (
                        sample.pos[0] + sample.lateral[0] * off,
                        sample.pos[1] + sample.lateral[1] * off,
                        z + 0.045,
                    )
                )
                colors.append(color)
        count = len(samples)
        tris: list[tuple[int, int, int]] = []
        for index in range(count):
            nxt = (index + 1) % count
            a = index * 2
            b = a + 1
            c = nxt * 2
            d = c + 1
            tris.append((a, b, c))
            tris.append((b, d, c))
        self._mesh("road", verts, colors, tris)
        # banquinas
        self._ribbon("grass-left", -10.5, -half, 0.01, 0.01, v(GRASS), variation=0.15)
        self._ribbon("grass-right", half, 10.5, 0.01, 0.01, v(GRASS), variation=0.15)
        # lineas
        for side in (-1.0, 1.0):
            self._ribbon(
                f"edge-{side}",
                side * 5.55,
                side * 5.72,
                0.06,
                0.06,
                v(EDGE),
            )
        # dashes del centro
        for index in range(int(self.track.length / 10.0)):
            s = index * 10.0
            if abs((s % self.track.length) - 0.0) < 3.0:
                continue
            point = self.track.point(s)
            self.build.box(
                self.node,
                (point[0], point[1], point[2] + 0.07),
                (0.16, 3.4, 0.03),
                v(EDGE),
                hpr=(math.degrees(self.track.heading(s)), 0, 0),
            )
        # linea de largada
        for index in range(12):
            lateral = -5.5 + index
            point = self.track.point(0, lateral)
            color = v(CREAM) if index % 2 == 0 else v(INK)
            self.build.box(
                self.node,
                (point[0], point[1], point[2] + 0.08),
                (0.92, 1.35, 0.03),
                color,
                hpr=(math.degrees(self.track.heading(0)), 0, 0),
            )

    def _walls(self) -> None:
        for side in (-1.0, 1.0):
            off = side * 6.35
            self._ribbon(f"wall-{side}", off, off, 0.03, 0.80, v(WALL), v(STONE), variation=0.10)
            self._ribbon(f"wall-top-{side}", side * 6.12, side * 6.58, 0.80, 0.80, v(STONE_LIGHT), v(STONE))

    # --------------------------------------------------------------- start area

    def _start_area(self) -> None:
        heading = math.degrees(self.track.heading(0))
        base = self.start_point
        for side in (-1.0, 1.0):
            point = self.track.point(0, side * 7.7)
            self.build.box(
                self.node,
                (point[0], point[1], point[2] + 3.0),
                (0.95, 0.95, 6.0),
                v(STONE_LIGHT),
                hpr=(heading, 0, 0),
            )
            self.build.box(
                self.node,
                (point[0], point[1], point[2] + 6.0),
                (1.25, 1.25, 0.35),
                v(STONE),
                hpr=(heading, 0, 0),
            )
            torch = self.build.glow(self.node, (point[0], point[1], point[2] + 6.65), 0.42, v((1.0, 0.62, 0.20, 0.85)), layers=2)
            self.torches.append(torch)
        self.build.box(
            self.node,
            (base[0], base[1], base[2] + 6.15),
            (16.0, 0.65, 0.55),
            v(STONE),
            hpr=(heading, 0, 0),
        )
        self.build.box(
            self.node,
            (base[0], base[1], base[2] + 6.95),
            (15.4, 0.18, 1.25),
            v((0.24, 0.035, 0.06)),
            hpr=(heading, 0, 0),
        )
        self.build.text(
            self.node,
            "HORROR KARTING",
            (base[0], base[1] - 0.2, base[2] + 6.95),
            0.95,
            v(CREAM),
            billboard=True,
        )
        # banderines
        for index in range(8):
            lateral = -5.4 + index * 1.55
            point = self.track.point(-2.0, lateral)
            color = v((0.55, 0.04, 0.07)) if index % 2 == 0 else v(CREAM)
            self.build.card(
                self.node,
                (point[0], point[1], point[2] + 5.55),
                0.55,
                0.8,
                color,
                billboard=False,
                hpr=(heading, 0, 0),
            )
        # rejas laterales
        for side in (-1.0, 1.0):
            for index in range(26):
                s = -35.0 + index * 3.4
                point = self.track.point(s, side * 9.4)
                self.build.box(
                    self.node,
                    (point[0], point[1], 0.55),
                    (0.11, 0.11, 1.1),
                    v(WOOD_2),
                )
            for index in range(25):
                s = -35.0 + index * 3.4
                point = self.track.point(s + 1.7, side * 9.4)
                self.build.box(
                    self.node,
                    (point[0], point[1], 0.85),
                    (0.08, 3.5, 0.08),
                    v(WOOD_2),
                    hpr=(math.degrees(self.track.heading(s)), 0, 0),
                )

    def _crypt(self) -> None:
        point = self.crypt_point
        heading = math.degrees(self.track.heading(0))
        pivot = self.node.attach_new_node("crypt")
        pivot.set_pos(point[0], point[1], 0.0)
        pivot.set_hpr(heading, 0, 0)
        b = self.build
        b.box(pivot, (0, 0, 0.35), (12.0, 16.0, 0.7), v(STONE_DARK))
        b.box(pivot, (0, 0, 3.0), (9.0, 13.0, 5.4), v(STONE))
        b.box(pivot, (0, 0, 6.0), (11.0, 15.0, 0.9), v(STONE_DARK))
        b.box(pivot, (0, 0, 6.9), (8.0, 11.5, 1.0), v(STONE))
        b.box(pivot, (0, 0, 6.0), (9.6, 13.6, 0.35), v(STONE_LIGHT))
        for side in (-1.0, 1.0):
            b.box(pivot, (4.3, side * 5.4, 2.7), (0.8, 0.8, 5.4), v(STONE_LIGHT))
            b.box(pivot, (4.3, side * 5.4, 5.5), (1.1, 1.1, 0.35), v(STONE_DARK))
        b.box(pivot, (4.45, 0, 1.7), (0.22, 2.5, 3.3), v((0.55, 0.28, 0.10)))
        b.box(pivot, (4.62, 0, 1.7), (0.08, 1.9, 2.8), v((1.0, 0.62, 0.20)))
        for side in (-1.0, 1.0):
            b.box(pivot, (4.45, side * 4.0, 3.4), (0.2, 1.0, 1.2), v((1.0, 0.58, 0.18)))
            b.box(pivot, (4.45, side * 4.0, 3.4), (0.1, 0.55, 0.8), v((1.0, 0.80, 0.35)))
        b.glow(pivot, (4.75, 0, 1.8), 1.1, v((1.0, 0.55, 0.18, 0.35)), layers=2)
        self._pool(pivot, (7.0, 0, 0.05), 4.2, Vec4(1.0, 0.52, 0.16, 0.10))
        # escalones
        for index in range(3):
            b.box(pivot, (5.4 + index * 0.8, 0, 0.18 + index * 0.12), (1.6, 4.0, 0.36), v(STONE_LIGHT))
        # lápida grande
        b.box(pivot, (7.8, -4.4, 1.2), (0.4, 2.4, 2.4), v(STONE_DARK), hpr=(0, 0, 12))
        b.ball(pivot, (7.8, -4.4, 2.5), 0.8, v(STONE))

    # ----------------------------------------------------------------- bridge

    def _bridge(self) -> None:
        samples = self.track.samples
        peak = max(samples, key=lambda sample: sample.pos[2])
        center_s = peak.s
        start = center_s - 28.0
        for index in range(23):
            s = start + index * 2.5
            point = self.track.point(s)
            heading = math.degrees(self.track.heading(s))
            self.build.box(
                self.node,
                (point[0], point[1], point[2] + 0.10),
                (12.1, 1.35, 0.10),
                v(WOOD),
                hpr=(heading, 0, 0),
            )
        for side in (-1.0, 1.0):
            for index in range(13):
                s = start + index * 4.4
                point = self.track.point(s, side * 6.05)
                self.build.box(
                    self.node,
                    (point[0], point[1], point[2] + 0.65),
                    (0.15, 0.15, 1.25),
                    v(WOOD_2),
                )
            for index in range(12):
                s = start + 2.2 + index * 4.4
                point = self.track.point(s, side * 6.05)
                self.build.box(
                    self.node,
                    (point[0], point[1], point[2] + 1.22),
                    (0.13, 4.5, 0.14),
                    v(WOOD),
                    hpr=(math.degrees(self.track.heading(s)), 0, 0),
                )
        # río
        point = self.track.point(center_s)
        heading = math.degrees(self.track.heading(center_s))
        self.build.box(
            self.node,
            (point[0], point[1], 0.25),
            (280.0, 19.0, 0.45),
            v(WATER),
            hpr=(heading, 0, 0),
        )
        for index in range(4):
            width = 16.0 + index * 9.0
            self.build.card(
                self.node,
                (point[0], point[1], 0.85 + index * 0.12),
                width,
                3.0,
                Vec4(0.35, 0.75, 0.65, 0.055),
                billboard=True,
                alpha=True,
                depth_write=False,
            )
        for side in (-1.0, 1.0):
            self.build.box(
                self.node,
                (point[0] + side * 4.2, point[1] - 1.5, 1.2),
                (1.1, 1.1, 2.6),
                v(STONE_DARK),
            )

    # ---------------------------------------------------------------- tunnel

    def _tunnel(self) -> None:
        target = self.track.nearest_s(self.track.scale * -98.0, self.track.scale * 116.0)
        start = target - 22.0
        mid = start + 22.0
        point = self.track.point(mid)
        heading = math.degrees(self.track.heading(mid))
        self.build.box(
            self.node,
            (point[0], point[1], point[2] + 4.9),
            (15.5, 46.0, 0.9),
            v(STONE_DARK),
            hpr=(heading, 0, 0),
        )
        self.build.box(
            self.node,
            (point[0], point[1], point[2] + 5.55),
            (16.4, 47.0, 0.45),
            v(STONE),
            hpr=(heading, 0, 0),
        )
        for side in (-1.0, 1.0):
            wall_point = self.track.point(mid, side * 7.25)
            self.build.box(
                self.node,
                (wall_point[0], wall_point[1], wall_point[2] + 2.45),
                (0.95, 46.0, 4.9),
                v(STONE),
                hpr=(heading, 0, 0),
            )
            for index in range(5):
                s = start + 4.5 + index * 9.0
                candle = self.track.point(s, side * 6.75)
                self.build.box(
                    self.node,
                    (candle[0], candle[1], candle[2] + 2.0),
                    (0.12, 0.12, 0.5),
                    v(CREAM),
                )
                glow = self.build.glow(self.node, (candle[0], candle[1], candle[2] + 2.35), 0.24, v((1.0, 0.68, 0.28, 0.9)), layers=1)
                self.torches.append(glow)
        for offset in (start, start + 44.0):
            point = self.track.point(offset)
            for side in (-1.0, 1.0):
                point = self.track.point(offset, side * 7.25)
                self.build.box(
                    self.node,
                    (point[0], point[1], point[2] + 2.45),
                    (1.3, 1.3, 4.9),
                    v(STONE_LIGHT),
                )

    # ------------------------------------------------------------------ jump

    def _jump(self) -> None:
        target = self.track.nearest_s(self.track.scale * 66.0, self.track.scale * -120.0)
        point = self.track.point(target)
        heading = math.degrees(self.track.heading(target))
        self.build.box(
            self.node,
            (point[0], point[1], point[2] + 0.10),
            (12.2, 1.0, 0.16),
            v(WOOD),
            hpr=(heading, 0, 0),
        )
        for side in (-1.0, 1.0):
            p = self.track.point(target, side * 7.0)
            self.build.box(self.node, (p[0], p[1], p[2] + 1.1), (0.3, 0.3, 2.2), v(WOOD_2))
            glow = self.build.glow(self.node, (p[0], p[1], p[2] + 2.4), 0.35, v((1.0, 0.45, 0.12, 0.85)), layers=2)
            self.torches.append(glow)
        sign_point = self.track.point(target - 8.0, -8.0)
        self.build.text(
            self.node,
            "SALTO",
            (sign_point[0], sign_point[1], 3.2),
            0.55,
            v((1.0, 0.72, 0.25)),
            billboard=True,
        )
        for index in range(5):
            s = target + 8.0 + index * 3.0
            p = self.track.point(s, -4.0 + index * 2.0)
            self.build.ball(self.node, (p[0], p[1], 0.35), (0.5, 0.5, 0.2), Vec4(0.18, 0.32, 0.25, 0.35), alpha=True)

    # -------------------------------------------------------------- cemetery

    def _blocked(self, s: float, t: float) -> bool:
        if abs(s) < 22.0 and t < -8.0:
            return True
        if abs(s - 30.0) < 20.0 and t > 8.0:
            return True
        if abs(s + 35.0) < 20.0 and t > 8.0:
            return True
        return False

    def _cemetery(self) -> None:
        rng = self.rng
        length = self.track.length
        stone_colors = (v(STONE), v(STONE_LIGHT), v(STONE_DARK))
        for index in range(190):
            s = rng.uniform(0.0, length)
            side = -1.0 if rng.random() < 0.5 else 1.0
            t = side * rng.uniform(11.0, 35.0)
            if self._blocked(s % length, t):
                continue
            point = self.track.point(s, t)
            heading = math.degrees(self.track.heading(s)) + rng.uniform(-28.0, 28.0)
            tilt = rng.uniform(-6.0, 6.0)
            color = stone_colors[index % 3]
            variant = index % 4
            if variant == 0:
                self.build.box(self.node, (point[0], point[1], 0.55), (0.75, 0.16, 1.1), color, hpr=(heading, 0, tilt))
            elif variant == 1:
                self.build.box(self.node, (point[0], point[1], 0.75), (0.22, 0.2, 1.5), color, hpr=(heading, 0, tilt))
                self.build.box(self.node, (point[0], point[1], 1.05), (0.9, 0.2, 0.2), color, hpr=(heading, 0, tilt))
            elif variant == 2:
                self.build.box(self.node, (point[0], point[1], 0.45), (1.2, 0.18, 0.9), color, hpr=(heading, 0, tilt))
                self.build.ball(self.node, (point[0], point[1], 0.9), (0.55, 0.16, 0.42), color)
            else:
                self.build.box(self.node, (point[0], point[1], 0.35), (0.55, 0.55, 0.7), color, hpr=(heading, 0, tilt))
        # árboles muertos
        for index in range(46):
            s = rng.uniform(0.0, length)
            side = -1.0 if rng.random() < 0.5 else 1.0
            t = side * rng.uniform(13.0, 42.0)
            if self._blocked(s % length, t):
                continue
            point = self.track.point(s, t)
            heading = math.degrees(self.track.heading(s))
            color = v(TREE) if index % 2 == 0 else v(TREE_2)
            self.build.box(self.node, (point[0], point[1], 2.1), (0.55, 0.55, 4.2), color, hpr=(heading, 0, rng.uniform(-5, 5)))
            for branch in range(3):
                angle = heading + branch * 42.0 - 40.0
                branch_z = 2.8 + branch * 0.55
                offset = (branch - 1) * 0.45
                self.build.box(
                    self.node,
                    (point[0] + offset, point[1] + offset * 0.4, branch_z),
                    (0.18, 0.18, 2.1),
                    color,
                    hpr=(0, 0, angle),
                )
            if index % 5 == 0:
                self.build.glow(self.node, (point[0], point[1], 3.7), 0.25, v((1.0, 0.58, 0.22, 0.6)), layers=1)
        # faroles
        for index in range(31):
            s = 24.0 + index * 51.0
            if s > length - 10.0:
                break
            side = -1.0 if index % 2 == 0 else 1.0
            point = self.track.point(s, side * 8.3)
            z = self.track.height(s)
            self.build.box(self.node, (point[0], point[1], z + 1.7), (0.17, 0.17, 3.4), v(STONE_DARK))
            self.build.box(self.node, (point[0], point[1], z + 3.5), (0.6, 0.6, 0.18), v(STONE_DARK))
            self.build.glow(self.node, (point[0], point[1], z + 3.35), 0.34, v((1.0, 0.68, 0.28, 0.85)), layers=2)
            self._pool(self.node, (point[0], point[1], 0.055), 2.6, Vec4(1.0, 0.60, 0.24, 0.10))
        # calabazas
        for index in range(76):
            if index < 44:
                s = length - 250.0 + index * 5.4
                t = (1.0 if index % 2 == 0 else -1.0) * (8.4 + (index % 5) * 1.4)
            else:
                s = rng.uniform(0.0, length)
                t = (-1.0 if rng.random() < 0.5 else 1.0) * rng.uniform(9.0, 27.0)
            if self._blocked(s % length, t):
                continue
            point = self.track.point(s, t)
            self.build.ball(self.node, (point[0], point[1], 0.34), (0.46, 0.46, 0.34), v(PUMPKIN))
            self.build.box(self.node, (point[0], point[1], 0.71), (0.1, 0.1, 0.2), v(STEM))
            if index % 3 == 0:
                glow = self.build.glow(self.node, (point[0], point[1], 0.38), 0.55, v((1.0, 0.62, 0.16, 0.32)), layers=1)
                _ = glow
                self._pool(self.node, (point[0], point[1], 0.045), 1.4, Vec4(1.0, 0.55, 0.14, 0.07))
                for eye in (-1.0, 1.0):
                    self.build.ball(self.node, (point[0] + eye * 0.14, point[1] + 0.40, 0.43), 0.055, v(INK))
        # mausoleos chicos
        for index in range(6):
            s = rng.uniform(40.0, length - 60.0)
            side = -1.0 if rng.random() < 0.5 else 1.0
            t = side * rng.uniform(17.0, 30.0)
            if self._blocked(s % length, t):
                continue
            point = self.track.point(s, t)
            heading = math.degrees(self.track.heading(s))
            pivot = self.node.attach_new_node("mausoleum")
            pivot.set_pos(point[0], point[1], 0.0)
            pivot.set_hpr(heading, 0, 0)
            self.build.box(pivot, (0, 0, 1.4), (5.0, 4.2, 2.8), v(STONE_DARK))
            self.build.box(pivot, (0, 0, 3.0), (5.8, 5.0, 0.45), v(STONE))
            self.build.box(pivot, (0, 2.15, 1.0), (1.2, 0.18, 1.8), v((1.0, 0.55, 0.16)))
            self.build.glow(pivot, (0, 2.24, 1.0), 0.55, v((1.0, 0.55, 0.16, 0.35)), layers=1)

    # ------------------------------------------------------------- landmarks

    def _landmarks(self) -> None:
        # mansión en la colina
        hill = self.build.ball(self.node, (-290, 300, -12), (120, 90, 34), v((0.035, 0.045, 0.045)))
        _ = hill
        pivot = self.node.attach_new_node("mansion")
        pivot.set_pos(-290, 300, 0.0)
        pivot.set_hpr(18, 0, 0)
        self.build.box(pivot, (0, 0, 20), (34, 26, 20), v((0.055, 0.045, 0.07)))
        self.build.box(pivot, (0, 0, 32), (37, 29, 1.2), v((0.03, 0.03, 0.045)))
        for x, y, h in ((-12, -6, 16), (12, -6, 16), (0, 6, 12)):
            self.build.box(pivot, (x, y, 32 + h / 2), (7, 7, h), v((0.045, 0.04, 0.06)))
            self.build.box(pivot, (x, y, 32 + h + 1), (8, 8, 1), v((0.02, 0.02, 0.03)))
        for index in range(7):
            x = -10.0 + index * 3.4
            self.build.box(pivot, (x, -13.15, 19.0), (1.1, 0.15, 1.8), v((1.0, 0.62, 0.22)))
            self.build.glow(pivot, (x, -13.3, 19.0), 0.5, v((1.0, 0.62, 0.22, 0.28)), layers=1)
        # castillo lejano
        castle = self.node.attach_new_node("castle")
        castle.set_pos(330, 280, 0.0)
        for index, (x, y, w, h) in enumerate(((-14, 0, 10, 34), (0, 4, 12, 46), (15, -2, 9, 30), (-3, -12, 8, 26))):
            self.build.box(castle, (x, y, h / 2), (w, w, h), v((0.035, 0.03, 0.055)))
            self.build.box(castle, (x, y, h + 2), (w + 1.2, w + 1.2, 2), v((0.02, 0.02, 0.035)))
            for win in range(2):
                self.build.box(castle, (x, y - w / 2 - 0.1, 12 + win * 9), (1.2, 0.2, 2.4), v((0.95, 0.58, 0.18)))
        # capilla en el centro del circuito
        chapel = self.node.attach_new_node("chapel")
        chapel.set_pos(0, 45, 0.0)
        self.build.box(chapel, (0, 0, 5), (12, 8, 10), v(STONE_DARK))
        self.build.box(chapel, (0, 0, 10.2), (13, 9, 0.8), v(STONE))
        self.build.box(chapel, (0, 0, 14), (4, 4, 8), v(STONE_DARK))
        self.build.box(chapel, (0, 0, 18), (5, 5, 1), v(STONE))
        for x in (-3.0, 3.0):
            self.build.box(chapel, (x, -4.1, 5.0), (1.0, 0.2, 2.4), v((1.0, 0.62, 0.22)))
            self.build.glow(chapel, (x, -4.3, 5.0), 0.7, v((1.0, 0.62, 0.22, 0.25)), layers=1)

    # ----------------------------------------------------------- stage/podium

    def _stage(self) -> None:
        point = self.stage_point
        pivot = self.node.attach_new_node("stage")
        pivot.set_pos(point[0], point[1], 0.0)
        self.build.box(pivot, (0, 0, 0.22), (10.0, 10.0, 0.44), v(STONE_DARK))
        self.build.box(pivot, (0, 0, 0.52), (8.0, 8.0, 0.18), v(STONE))
        self.build.box(pivot, (0, 0, 0.63), (6.4, 6.4, 0.05), v((0.32, 0.03, 0.06)))
        for side in (-1.0, 1.0):
            self.build.box(pivot, (side * 4.4, -3.2, 1.9), (0.4, 0.4, 3.8), v(STONE_LIGHT))
            torch = self.build.glow(pivot, (side * 4.4, -3.2, 4.05), 0.45, v((1.0, 0.58, 0.18, 0.85)), layers=2)
            self.torches.append(torch)
        self._pool(pivot, (0, 0, 0.68), 6.0, Vec4(1.0, 0.55, 0.18, 0.08))

    def _podium(self) -> None:
        point = self.podium_point
        pivot = self.node.attach_new_node("podium")
        pivot.set_pos(point[0], point[1], 0.0)
        self.build.box(pivot, (0, 0, 0.25), (14.0, 8.0, 0.5), v(STONE_DARK))
        for x, height in ((-4.2, 0.9), (0.0, 1.5), (4.2, 0.6)):
            self.build.box(pivot, (x, 0, height / 2 + 0.45), (4.0, 5.0, height), v(STONE))
            self.build.box(pivot, (x, 0, height + 0.48), (4.1, 5.1, 0.06), v((0.36, 0.035, 0.07)))
        for side in (-1.0, 1.0):
            self.build.box(pivot, (side * 6.6, 0, 2.6), (0.4, 0.4, 5.2), v(STONE_LIGHT))
            torch = self.build.glow(pivot, (side * 6.6, 0, 5.4), 0.5, v((1.0, 0.58, 0.18, 0.85)), layers=2)
            self.torches.append(torch)
        self.build.text(pivot, "PODIO", (0, 0, 6.2), 0.62, v(GOLD), billboard=True)

    # ---------------------------------------------------------- ambientación

    def _fireflies(self) -> None:
        rng = random.Random(41)
        for index in range(36):
            s = rng.uniform(0.0, self.track.length)
            t = (-1.0 if rng.random() < 0.5 else 1.0) * rng.uniform(9.0, 26.0)
            point = self.track.point(s, t)
            base = (point[0], point[1], rng.uniform(1.0, 3.2))
            holder = self.node.attach_new_node("firefly")
            holder.set_pos(*base)
            self.build.ball(holder, (0, 0, 0), 0.055, v(FIREFLY))
            self.build.glow(holder, (0, 0, 0), 0.16, v((0.65, 1.0, 0.35, 0.55)), layers=1, sort=7)
            self.fireflies.append((holder, base, index * 0.7))

    def _bats(self) -> None:
        rng = random.Random(77)
        center = (self.crypt_point[0], self.crypt_point[1], 15.0)
        for index in range(9):
            pivot = self.node.attach_new_node("bat-pivot")
            pivot.set_pos(*center)
            pivot.set_h(rng.uniform(0, 360))
            bat = pivot.attach_new_node("bat")
            bat.set_pos(rng.uniform(16.0, 30.0), 0.0, rng.uniform(-2.0, 7.0))
            self.build.ball(bat, (0, 0, 0), (0.34, 0.20, 0.18), v((0.04, 0.03, 0.05)))
            wings: list[NodePath] = []
            for side in (-1.0, 1.0):
                wing = self.build.box(bat, (side * 0.48, 0, 0), (0.9, 0.6, 0.06), v((0.06, 0.04, 0.07)), hpr=(0, 0, 0))
                wings.append(wing)
            self.bats.append((pivot, bat, wings, rng.uniform(0.35, 0.7)))

    def _clouds(self) -> None:
        rng = random.Random(63)
        for index in range(4):
            angle = rng.uniform(0, math.tau)
            radius = rng.uniform(400, 620)
            z = rng.uniform(150, 220)
            x = math.cos(angle) * radius
            y = math.sin(angle) * radius
            card = self.build.card(
                self.node,
                (x, y, z),
                rng.uniform(80, 150),
                rng.uniform(16, 26),
                Vec4(0.55, 0.45, 0.75, 0.05),
                billboard=True,
                alpha=True,
                depth_write=False,
            )
            card.set_bin("background", 2)
            card.set_fog_off(1)
            self.clouds.append((card, angle, rng.uniform(0.4, 1.2)))

    # ------------------------------------------------------------------ frame

    def update(self, dt: float, elapsed: float) -> None:
        for holder, base, phase in self.fireflies:
            holder.set_pos(
                base[0] + math.sin(elapsed * 0.7 + phase) * 0.9,
                base[1] + math.cos(elapsed * 0.6 + phase) * 0.9,
                base[2] + math.sin(elapsed * 1.4 + phase) * 0.35,
            )
        for pivot, bat, wings, speed in self.bats:
            pivot.set_h(pivot.get_h() + dt * speed * 22.0)
            bat.set_p(math.sin(elapsed * 6.0 + speed) * 8.0)
            for index, wing in enumerate(wings):
                wing.set_r(math.sin(elapsed * 9.0 + index) * 42.0)
        for torch in self.torches:
            scale = 1.0 + math.sin(elapsed * 7.0 + torch.get_x()) * 0.08
            torch.set_scale(scale)
        for card, angle, speed in self.clouds:
            angle += dt * speed * 0.01
            radius = math.hypot(card.get_x(), card.get_y())
            card.set_x(math.cos(angle) * radius)
            card.set_y(math.sin(angle) * radius)
