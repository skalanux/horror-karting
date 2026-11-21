"""Modelos de kart y personajes, construidos con primitivas."""

from __future__ import annotations

import math
from typing import Any

from panda3d.core import NodePath, Vec4

from .characters import Character
from .palette import (
    BLOOD,
    CREAM,
    GOLD,
    INK,
    SILVER,
    STONE_LIGHT,
    STONE_DARK,
    v,
)
from .primitives import Build

SKIN = {
    "dracula": (0.86, 0.82, 0.80),
    "frank": (0.52, 0.72, 0.44),
    "mummy": (0.76, 0.66, 0.46),
    "wolf": (0.38, 0.25, 0.16),
    "phantom": (0.88, 0.82, 0.76),
    "llorona": (0.82, 0.84, 0.82),
    "milei": (0.78, 0.62, 0.48),
    "kuchisake": (0.92, 0.88, 0.84),
}


class KartModel:
    """Un kart con su piloto. El forward local es +Y."""

    def __init__(self, build: Build, character: Character, parent: NodePath, player_color: tuple[float, float, float] | None = None) -> None:
        self.build = build
        self.character = character
        self.player_color = player_color
        self.root = parent.attach_new_node(f"kart-{character.key}")
        self.root.set_light_off(1)
        self.lean = self.root.attach_new_node("lean")
        self.wheels: list[NodePath] = []
        self.steer_groups: list[NodePath] = []
        self.wheel_spin = 0.0
        self.bills: list[NodePath] = []
        self.flames: list[NodePath] = []
        self.marker: NodePath | None = None
        self.marker_glow: NodePath | None = None
        self.head: NodePath | None = None
        self.shield: NodePath | None = None
        self.body_color = v(character.body)
        self.accent = v(character.accent)
        self.dark = Vec4(0.035, 0.030, 0.045, 1.0)
        self._build_chassis()
        self._build_driver()
        self._build_signature()
        self._build_shadow()
        self._build_effects()
        self._build_marker(player_color or (0.95, 0.92, 0.85))
        self.marker_visible = player_color is not None
        if not self.marker_visible:
            self.set_marker_visible(False)

    # ------------------------------------------------------------------ base

    def _build_chassis(self) -> None:
        b = self.build
        accent = self.accent
        body = self.body_color
        b.box(self.lean, (0, 0, 0.30), (1.34, 2.10, 0.30), body)
        b.box(self.lean, (0, 0.52, 0.47), (0.92, 0.95, 0.18), body)
        b.box(self.lean, (0, 1.00, 0.34), (0.72, 0.34, 0.20), accent)
        b.box(self.lean, (0, -0.74, 0.52), (0.86, 0.42, 0.32), self.dark)
        b.box(self.lean, (0, -0.99, 0.83), (1.44, 0.12, 0.09), accent)
        for side in (-1.0, 1.0):
            b.box(self.lean, (side * 0.55, -0.95, 0.64), (0.08, 0.08, 0.38), self.dark)
            b.box(self.lean, (side * 0.70, 0.05, 0.40), (0.05, 1.55, 0.09), accent)
        b.box(self.lean, (0, -0.48, 0.72), (0.62, 0.20, 0.52), self.dark)
        b.box(self.lean, (0, 0.18, 0.94), (0.52, 0.10, 0.08), self.dark)
        for side in (-1.0, 1.0):
            b.ball(self.lean, (side * 0.38, 1.02, 0.55), 0.075, Vec4(accent[0], accent[1], accent[2], 1.0))
            b.box(self.lean, (side * 0.36, -1.04, 0.36), (0.16, 0.16, 0.12), v(STONE_DARK))
        # ruedas
        for x, y, front in ((0.80, 0.70, True), (-0.80, 0.70, True), (0.80, -0.70, False), (-0.80, -0.70, False)):
            steer = self.lean.attach_new_node("steer")
            steer.set_pos(x, y, 0.31)
            spin = steer.attach_new_node("spin")
            b.ball(spin, (0, 0, 0), (0.15, 0.34, 0.34), v(INK))
            b.box(spin, (0, 0.0, 0.0), (0.30, 0.42, 0.06), Vec4(0.10, 0.10, 0.13, 1.0))
            b.ball(spin, (math.copysign(0.15, x), 0, 0), 0.075, accent)
            self.wheels.append(spin)
            if front:
                self.steer_groups.append(steer)

    def _build_driver(self) -> None:
        b = self.build
        skin = v(SKIN.get(self.character.key, (0.8, 0.7, 0.6)))
        self.head = self.lean.attach_new_node("head")
        self.head.set_pos(0, -0.34, 1.24)
        b.box(self.lean, (0, -0.34, 0.82), (0.40, 0.34, 0.50), self.dark)
        b.box(self.lean, (0, -0.17, 0.92), (0.44, 0.12, 0.16), v(self.character.accent))
        for side in (-1.0, 1.0):
            b.box(self.lean, (side * 0.27, -0.12, 0.80), (0.10, 0.55, 0.10), skin)
            b.box(self.lean, (side * 0.18, 0.02, 0.88), (0.09, 0.10, 0.16), self.dark)
        b.ball(self.head, (0, 0, 0), 0.225, skin)
        self._build_head(skin)

    def _build_head(self, skin: Vec4) -> None:
        b = self.build
        key = self.character.key
        head = self.head
        assert head is not None
        if key == "dracula":
            b.ball(head, (0, -0.03, 0.06), (0.24, 0.20, 0.16), Vec4(0.06, 0.035, 0.06, 1.0))
            b.box(head, (0, 0.17, -0.06), (0.16, 0.08, 0.06), Vec4(0.92, 0.90, 0.88, 1.0))
            for side in (-1.0, 1.0):
                b.ball(head, (side * 0.085, 0.17, 0.02), 0.028, v(BLOOD))
                b.box(head, (side * 0.10, 0.20, -0.10), (0.025, 0.03, 0.06), v(CREAM))
            for side in (-1.0, 1.0):
                b.box(head, (side * 0.22, -0.03, -0.03), (0.12, 0.22, 0.30), Vec4(0.05, 0.03, 0.05, 1.0))
        elif key == "frank":
            b.box(head, (0, -0.03, 0.07), (0.42, 0.34, 0.20), Vec4(0.05, 0.05, 0.06, 1.0))
            b.box(head, (0, 0.0, 0.0), (0.40, 0.34, 0.22), skin)
            for side in (-1.0, 1.0):
                b.ball(head, (side * 0.23, 0.0, 0.02), 0.055, v(GOLD))
                b.ball(head, (side * 0.08, 0.17, 0.02), 0.03, v((0.1, 0.08, 0.06)))
            b.box(head, (0, 0.17, -0.09), (0.18, 0.03, 0.02), Vec4(0.12, 0.08, 0.08, 1.0))
            b.box(head, (0.06, 0.17, 0.10), (0.12, 0.02, 0.02), Vec4(0.12, 0.08, 0.08, 1.0))
        elif key == "mummy":
            b.box(head, (0, -0.08, 0.02), (0.44, 0.34, 0.46), v((0.58, 0.48, 0.30)))
            for offset in (-0.10, 0.02, 0.13):
                b.box(head, (0, -0.02, offset), (0.46, 0.36, 0.035), v((0.72, 0.62, 0.40)))
            for side in (-1.0, 1.0):
                b.ball(head, (side * 0.08, 0.16, 0.04), 0.032, v((1.0, 0.85, 0.35)))
        elif key == "wolf":
            b.ball(head, (0, 0.01, 0.01), (0.26, 0.24, 0.22), skin)
            b.box(head, (0, 0.24, -0.05), (0.20, 0.20, 0.15), v((0.30, 0.20, 0.13)))
            for side in (-1.0, 1.0):
                b.box(head, (side * 0.17, -0.01, 0.20), (0.07, 0.10, 0.20), v((0.30, 0.20, 0.13)))
                b.ball(head, (side * 0.09, 0.19, 0.04), 0.033, v((1.0, 0.80, 0.15)))
            b.box(head, (0, 0.30, -0.09), (0.10, 0.03, 0.03), v((0.08, 0.06, 0.06)))
            b.ball(self.lean, (0, -0.38, 0.95), (0.30, 0.22, 0.16), v((0.34, 0.22, 0.14)))
        elif key == "phantom":
            b.ball(head, (0, 0.0, 0.06), (0.24, 0.20, 0.16), Vec4(0.04, 0.03, 0.05, 1.0))
            b.box(head, (0, -0.02, 0.22), (0.42, 0.30, 0.06), Vec4(0.04, 0.03, 0.05, 1.0))
            b.box(head, (0, -0.02, 0.28), (0.28, 0.22, 0.12), Vec4(0.04, 0.03, 0.05, 1.0))
            b.box(head, (0.07, 0.19, 0.0), (0.16, 0.035, 0.20), v(CREAM))
            b.ball(head, (-0.09, 0.17, 0.03), 0.03, Vec4(0.15, 0.08, 0.10, 1.0))
            b.ball(self.lean, (0.19, -0.22, 0.97), 0.055, v(BLOOD))
        elif key == "llorona":
            b.ball(head, (0, -0.05, 0.02), (0.30, 0.24, 0.42), Vec4(0.03, 0.025, 0.04, 1.0))
            b.box(head, (0, -0.20, -0.30), (0.42, 0.12, 0.70), Vec4(0.03, 0.025, 0.04, 1.0))
            for side in (-1.0, 1.0):
                b.ball(head, (side * 0.075, 0.18, 0.02), 0.032, Vec4(0.55, 0.95, 0.95, 1.0))
            b.box(head, (0, 0.18, -0.09), (0.14, 0.02, 0.02), Vec4(0.15, 0.08, 0.10, 1.0))
            self.build.card(self.lean, (0, -0.52, 0.95), 0.9, 1.05, Vec4(0.75, 0.80, 0.80, 0.20), alpha=True, two_sided=True)
            b.box(self.lean, (0.42, 0.18, 0.90), (0.08, 0.08, 0.32), v(CREAM))
            self.build.glow(self.lean, (0.42, 0.18, 1.10), 0.12, v((1.0, 0.75, 0.35, 0.9)), layers=1)
        elif key == "milei":
            for index in range(9):
                angle = index / 9.0 * math.tau
                x = math.cos(angle) * 0.22
                y = math.sin(angle) * 0.17 - 0.03
                z = 0.12 + (0.06 if index % 2 == 0 else 0.0)
                b.ball(head, (x, y, z), (0.13, 0.13, 0.20), v((0.42, 0.40, 0.42)) if index % 2 else v((0.30, 0.29, 0.32)))
            for side in (-1.0, 1.0):
                b.box(head, (side * 0.20, 0.10, -0.06), (0.06, 0.10, 0.24), v((0.30, 0.29, 0.32)))
                b.ball(head, (side * 0.085, 0.19, 0.03), 0.032, Vec4(0.75, 0.80, 1.0, 1.0))
                # orejas de gatito
                b.box(head, (side * 0.14, 0.02, 0.26), (0.10, 0.05, 0.14), v((0.36, 0.34, 0.37)), hpr=(0, 0, 18 * side))
            b.ball(head, (0, 0.19, -0.10), 0.05, Vec4(0.90, 0.70, 0.55, 1.0))
            b.ball(self.lean, (0, -0.17, 0.94), 0.045, v(GOLD))
            b.box(self.lean, (0, -0.19, 0.91), (0.06, 0.04, 0.14), Vec4(0.75, 0.10, 0.12, 1.0))
            # motosierra
            b.box(self.lean, (0.80, -0.15, 0.62), (0.22, 0.55, 0.30), Vec4(0.20, 0.20, 0.22, 1.0))
            b.box(self.lean, (0.80, 0.55, 0.62), (0.10, 0.75, 0.10), v(SILVER))
            for tooth in range(5):
                b.box(self.lean, (0.80, 0.92 + tooth * 0.10, 0.62), (0.10, 0.06, 0.05), v(STONE_LIGHT))
            for index in range(3):
                bill = b.card(
                    self.lean,
                    (-0.35 - index * 0.18, -1.18, 1.05 + index * 0.10),
                    0.34,
                    0.16,
                    Vec4(0.30, 0.62, 0.32, 0.95),
                    hpr=(0, 0, -20 + index * 18),
                )
                self.bills.append(bill)
        elif key == "kuchisake":
            b.ball(head, (0, -0.10, 0.02), (0.31, 0.27, 0.42), Vec4(0.025, 0.02, 0.03, 1.0))
            b.box(head, (0, -0.24, -0.28), (0.42, 0.10, 0.72), Vec4(0.025, 0.02, 0.03, 1.0))
            b.box(head, (0, 0.17, -0.08), (0.22, 0.04, 0.12), v(CREAM))
            for side in (-1.0, 1.0):
                b.box(head, (side * 0.10, 0.18, -0.02), (0.025, 0.03, 0.16), v(BLOOD), hpr=(0, 0, 18 * side))
                b.ball(head, (side * 0.075, 0.18, 0.06), 0.031, Vec4(0.20, 0.05, 0.07, 1.0))
            b.box(self.lean, (0, -0.17, 0.94), (0.44, 0.12, 0.14), v(BLOOD))
            # tijeras
            for side in (-1.0, 1.0):
                b.box(self.lean, (0.82, 0.30, 0.66), (0.06, 0.85, 0.07), v(SILVER), hpr=(0, 0, 24 * side))
            b.ball(self.lean, (0.82, 0.30, 0.66), 0.09, v(STONE_DARK))

    def _build_signature(self) -> None:
        key = self.character.key
        b = self.build
        if key == "dracula":
            self.build.card(self.lean, (0, -0.55, 0.95), 1.00, 1.20, Vec4(0.03, 0.02, 0.04, 0.96), hpr=(-12, 0, 0))
            self.build.card(self.lean, (0, -0.50, 0.95), 0.80, 0.90, Vec4(0.35, 0.02, 0.05, 0.65), hpr=(-12, 0, 0))
        elif key == "frank":
            b.box(self.lean, (0, -0.48, 0.78), (0.72, 0.26, 0.62), v((0.14, 0.24, 0.16)))
        elif key == "mummy":
            for side in (-1.0, 1.0):
                b.box(self.lean, (side * 0.48, 0.05, 0.52), (0.12, 1.4, 0.12), v((0.62, 0.52, 0.32)))
        elif key == "wolf":
            b.ball(self.lean, (0, -0.55, 0.86), (0.36, 0.26, 0.40), v((0.32, 0.20, 0.13)))
        elif key == "phantom":
            self.build.card(self.lean, (0, -0.52, 0.98), 1.05, 1.10, Vec4(0.04, 0.025, 0.07, 0.95), hpr=(-10, 0, 0))
        elif key == "llorona":
            for index in range(3):
                b.box(self.lean, (-0.35 + index * 0.35, -0.92, 0.55), (0.10, 0.10, 0.26), v(CREAM))
                self.build.glow(self.lean, (-0.35 + index * 0.35, -0.92, 0.74), 0.10, v((1.0, 0.70, 0.30, 0.85)), layers=1)
        elif key == "milei":
            b.box(self.lean, (0, 0.55, 0.56), (0.36, 0.20, 0.10), v(GOLD))
            b.box(self.lean, (0, -0.85, 0.62), (0.60, 0.10, 0.34), Vec4(0.25, 0.25, 0.28, 1.0))
        elif key == "kuchisake":
            b.box(self.lean, (0, 0.90, 0.56), (0.52, 0.12, 0.20), v(BLOOD))

    def _build_shadow(self) -> None:
        self.shadow = self.build.ball(
            self.root,
            (0, 0, 0.035),
            (1.10, 1.55, 0.02),
            Vec4(0.0, 0.0, 0.0, 0.45),
            alpha=True,
        )
        self.shadow.set_depth_write(False)
        self.shadow.set_bin("fixed", 2)

    def _build_effects(self) -> None:
        b = self.build
        for side in (-1.0, 1.0):
            flame = b.ball(self.lean, (side * 0.25, -1.15, 0.52), (0.14, 0.22, 0.14), Vec4(1.0, 0.65, 0.15, 0.85), alpha=True)
            flame.set_depth_write(False)
            flame.hide()
            self.flames.append(flame)
        self.shield = b.ball(self.lean, (0, 0, 0.85), 1.55, Vec4(0.55, 0.95, 1.0, 0.13), alpha=True)
        self.shield.set_depth_write(False)
        self.shield.set_bin("fixed", 3)
        self.shield.hide()

    def _build_marker(self, rgb: tuple[float, float, float]) -> None:
        color = v(rgb)
        self.marker = self.build.ball(self.root, (0, 0, 2.05), 0.15, color)
        self.marker.set_depth_write(False)
        self.marker.set_bin("fixed", 4)
        self.marker_glow = self.build.glow(self.root, (0, 0, 2.05), 0.26, v(rgb, 0.65), layers=1, sort=4)

    # ------------------------------------------------------------------ update

    def update(self, kart: Any, dt: float, air_offset: float, elapsed: float) -> None:
        self.wheel_spin += kart.speed * dt / 0.34
        angle = math.degrees(self.wheel_spin) % 360.0
        for wheel in self.wheels:
            wheel.setP(-angle)
        for group in self.steer_groups:
            group.setH(kart.steer * 26.0)
        lean = -kart.steer * 7.0
        pitch = -min(6.0, max(-4.0, (kart.speed - 16.0) * 0.15))
        if kart.airborne:
            pitch = 8.0
        self.lean.setR(lean)
        self.lean.setP(pitch + math.sin(elapsed * 13.0) * 0.5 * min(1.0, kart.speed / 20.0))
        self.lean.setZ(math.sin(elapsed * 16.0) * 0.010 + (0.03 if kart.boost > 0.0 else 0.0))
        if self.head is not None:
            self.head.setH(-kart.steer * 9.0)
        boosting = kart.boost > 0.0
        for index, flame in enumerate(self.flames):
            flame.show() if boosting else flame.hide()
            if boosting:
                scale = 1.0 + math.sin(elapsed * 40.0 + index) * 0.25
                flame.setScale(scale, scale * 1.4, scale)
        if self.shield is not None:
            visible = kart.shield > 0.0
            self.shield.show() if visible else self.shield.hide()
            if visible:
                pulse = 0.10 + 0.05 * (1.0 + math.sin(elapsed * 6.0))
                self.shield.set_color(Vec4(0.55, 0.95, 1.0, pulse))
        if self.shadow is not None:
            self.shadow.setZ(-air_offset + 0.035)
            shrink = max(0.55, 1.0 - air_offset * 0.10)
            self.shadow.setScale(1.10 * shrink, 1.55 * shrink, 0.02)
        if self.marker is not None:
            self.marker.setZ(2.05 + math.sin(elapsed * 3.4) * 0.10)
            self.marker.setH(elapsed * 120.0)
        if self.marker_glow is not None:
            self.marker_glow.setZ(2.05 + math.sin(elapsed * 3.4) * 0.10)
        for index, bill in enumerate(self.bills):
            bill.setR(math.sin(elapsed * 3.0 + index) * 16.0)
            bill.setP(math.cos(elapsed * 2.2 + index) * 10.0)

    def rest(self) -> None:
        self.lean.setR(0.0)
        self.lean.setP(0.0)
        self.lean.setZ(0.0)
        self.wheel_spin = 0.0
        for wheel in self.wheels:
            wheel.setP(0.0)
        for group in self.steer_groups:
            group.setH(0.0)
        if self.head is not None:
            self.head.setH(0.0)
        for flame in self.flames:
            flame.hide()
        if self.shield is not None:
            self.shield.hide()
        if self.shadow is not None:
            self.shadow.setZ(0.035)
            self.shadow.set_scale(1.10, 1.55, 0.02)

    def set_marker_visible(self, value: bool) -> None:
        self.marker_visible = value
        if self.marker is not None:
            (self.marker.show() if value else self.marker.hide())
        if self.marker_glow is not None:
            (self.marker_glow.show() if value else self.marker_glow.hide())

    def set_marker_color(self, rgb: tuple[float, float, float]) -> None:
        if self.marker is not None:
            self.marker.set_color(Vec4(rgb[0], rgb[1], rgb[2], 1.0))
        if self.marker_glow is not None:
            for child in self.marker_glow.get_children():
                color = child.get_color()
                child.set_color(Vec4(rgb[0], rgb[1], rgb[2], color[3]))

    def set_visible(self, value: bool) -> None:
        (self.root.show() if value else self.root.hide())

    def destroy(self) -> None:
        self.root.remove_node()
