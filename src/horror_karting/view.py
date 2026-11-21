"""Cámaras de carrera, pantalla dividida y HUD por jugador."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any

from panda3d.core import (
    Camera,
    DisplayRegion,
    NodePath,
    OrthographicLens,
    PerspectiveLens,
)

from .track import Track

CAMERA_NAMES = ("CERCA", "LEJOS", "CAPÓ", "CENITAL")


@dataclass(slots=True)
class Viewport:
    index: int
    camera: NodePath
    region: DisplayRegion
    lens: PerspectiveLens
    aspect: float
    width: int
    height: int
    ui_scene: NodePath
    ui_camera: NodePath
    ui_region: DisplayRegion
    ui_root: NodePath
    text_scale: float


class CameraRig:
    """Cámara suave por jugador con cuatro modos."""

    def __init__(self, seed: int = 0) -> None:
        self.mode = 0
        self.position = (0.0, 0.0, 0.0)
        self.look = (0.0, 0.0, 0.0)
        self.fov = 74.0
        self.shake = 0.0
        self.rng = random.Random(seed)
        self.initialized = False

    def cycle(self) -> str:
        self.mode = (self.mode + 1) % len(CAMERA_NAMES)
        return CAMERA_NAMES[self.mode]

    def add_shake(self, amount: float) -> None:
        self.shake = min(1.2, self.shake + amount)

    def reset(self) -> None:
        self.initialized = False
        self.shake = 0.0
        self.mode = 0

    def pose(
        self,
        kart: Any,
        track: Track,
        dt: float,
        *,
        look_back: bool = False,
        cinematic: float | None = None,
        others: list[Any] | None = None,
    ) -> tuple[tuple[float, float, float], tuple[float, float, float], float]:
        point = track.point(kart.s, kart.t)
        z = kart.air_z + 0.05
        heading = track.heading(kart.s) + kart.slip
        forward = (-math.sin(heading), math.cos(heading))
        right = (forward[1], -forward[0])
        speed_ratio = min(1.0, max(0.0, kart.speed / max(kart.spec.max_speed, 1.0)))
        mode = self.mode
        if look_back:
            mode = 0
        if cinematic is not None:
            orbit = cinematic * 0.65
            position = (
                point[0] - forward[0] * 6.0 + right[0] * math.sin(orbit) * 6.5,
                point[1] - forward[1] * 6.0 + right[1] * math.sin(orbit) * 6.5,
                z + 3.6 + math.cos(orbit) * 1.4,
            )
            look = (point[0] + forward[0] * 2.0, point[1] + forward[1] * 2.0, z + 1.1)
            fov = 72.0
        elif mode == 0:
            distance = 7.4
            height = 3.4
            if look_back:
                position = (point[0] + forward[0] * distance, point[1] + forward[1] * distance, z + height)
                look = (point[0] - forward[0] * 4.0, point[1] - forward[1] * 4.0, z + 1.5)
            else:
                position = (point[0] - forward[0] * distance, point[1] - forward[1] * distance, z + height)
                look = (point[0] + forward[0] * 7.0, point[1] + forward[1] * 7.0, z + 1.9)
            fov = 76.0 + speed_ratio * 6.0 + (7.0 if kart.boost > 0.0 else 0.0)
        elif mode == 1:
            distance = 10.5
            height = 4.9
            position = (point[0] - forward[0] * distance, point[1] - forward[1] * distance, z + height)
            look = (point[0] + forward[0] * 9.0, point[1] + forward[1] * 9.0, z + 2.0)
            fov = 70.0 + speed_ratio * 5.0
        elif mode == 2:
            position = (point[0] + forward[0] * 0.55, point[1] + forward[1] * 0.55, z + 1.62)
            look = (point[0] + forward[0] * 14.0, point[1] + forward[1] * 14.0, z + 1.45)
            fov = 80.0 + speed_ratio * 6.0
        else:
            position = (point[0] - forward[0] * 8.0, point[1] - forward[1] * 8.0, z + 15.5)
            look = (point[0] + forward[0] * 5.0, point[1] + forward[1] * 5.0, z + 0.8)
            fov = 62.0 + speed_ratio * 4.0
        if others:
            for other in others:
                if other is kart:
                    continue
                other_point = track.point(other.s, other.t)
                if math.hypot(position[0] - other_point[0], position[1] - other_point[1]) < 2.6:
                    if position[2] < other.air_z + 4.8:
                        position = (position[0], position[1], other.air_z + 4.8)
        if self.shake > 0.0:
            amount = self.shake * self.shake
            position = (
                position[0] + self.rng.uniform(-1.0, 1.0) * amount * 0.18,
                position[1] + self.rng.uniform(-1.0, 1.0) * amount * 0.18,
                position[2] + self.rng.uniform(-0.6, 0.6) * amount * 0.12,
            )
        if not self.initialized:
            self.position = position
            self.look = look
            self.fov = fov
            self.initialized = True
        else:
            blend = 1.0 - math.exp(-max(dt, 1e-4) / 0.085)
            self.position = tuple(self.position[i] + (position[i] - self.position[i]) * blend for i in range(3))
            self.look = tuple(self.look[i] + (look[i] - self.look[i]) * blend for i in range(3))
            self.fov += (fov - self.fov) * blend
        self.shake = max(0.0, self.shake - dt * 2.6)
        return self.position, self.look, self.fov


class ViewportManager:
    """Reparte la ventana entre 1 y 4 jugadores y les da un HUD 2D propio."""

    def __init__(self, base: Any, root: NodePath) -> None:
        self.base = base
        self.root = root
        self.win = base.win
        self.main_region = self.win.getDisplayRegion(1)
        self.saved_dims = tuple(self.main_region.getDimensions())
        self.saved_pos = base.cam.get_pos()
        self.saved_hpr = base.cam.get_hpr()
        self.saved_fov = base.camLens.get_fov()
        self.saved_aspect = base.camLens.get_aspect_ratio()
        self.viewports: list[Viewport] = []
        self.count = 0
        self.hud_visible = True
        self.set_count(1)

    # ------------------------------------------------------------------ setup

    def _rects(self, count: int) -> list[tuple[float, float, float, float]]:
        if count <= 1:
            return [(0.0, 1.0, 0.0, 1.0)]
        if count == 2:
            return [(0.0, 1.0, 0.5, 1.0), (0.0, 1.0, 0.0, 0.5)]
        if count == 3:
            return [(0.0, 0.5, 0.5, 1.0), (0.5, 1.0, 0.5, 1.0), (0.0, 0.5, 0.0, 0.5)]
        return [
            (0.0, 0.5, 0.5, 1.0),
            (0.5, 1.0, 0.5, 1.0),
            (0.0, 0.5, 0.0, 0.5),
            (0.5, 1.0, 0.0, 0.5),
        ]

    def _clear(self) -> None:
        for view in self.viewports:
            if view.index > 0:
                try:
                    self.win.remove_display_region(view.region)
                except Exception:
                    pass
                view.camera.remove_node()
            else:
                view.camera = self.base.cam
                self.base.camLens.set_fov(self.saved_fov)
                self.base.camLens.set_aspect_ratio(self.saved_aspect)
            try:
                self.win.remove_display_region(view.ui_region)
            except Exception:
                pass
            view.ui_scene.remove_node()
        self.viewports.clear()

    def set_count(self, count: int) -> None:
        count = max(1, min(4, count))
        if count == self.count and self.viewports:
            return
        self._clear()
        self.count = count
        rects = self._rects(count)
        width_px = self.win.get_x_size()
        height_px = self.win.get_y_size()
        for index, rect in enumerate(rects):
            x0, x1, y0, y1 = rect
            width = max(1, int((x1 - x0) * width_px))
            height = max(1, int((y1 - y0) * height_px))
            aspect = width / height
            if index == 0:
                camera = self.base.cam
                lens = self.base.camLens
                self.main_region.set_dimensions(x0, x1, y0, y1)
                self.main_region.set_active(True)
                region = self.main_region
            else:
                camera = self.base.makeCamera(self.win, sort=2)
                region = camera.node().get_display_region(0)
                region.set_dimensions(x0, x1, y0, y1)
                region.set_sort(2)
                lens = camera.node().get_lens()
                lens.set_aspect_ratio(aspect)
                lens.set_fov(76.0)
            if index == 0:
                lens.set_aspect_ratio(aspect)
            # HUD propio
            ui_scene = NodePath(f"hk-ui-{index}")
            ui_camera_node = Camera(f"hk-ui-cam-{index}")
            ui_lens = OrthographicLens()
            ui_lens.set_film_size(2.0 * aspect, 2.0)
            ui_lens.set_near_far(0.1, 10.0)
            ui_camera_node.set_lens(ui_lens)
            ui_camera = ui_scene.attach_new_node(ui_camera_node)
            ui_root = ui_scene.attach_new_node(f"hk-ui-root-{index}")
            ui_root.set_pos(0, 1, 0)
            ui_region = self.win.make_display_region(x0, x1, y0, y1)
            ui_region.set_camera(ui_camera)
            ui_region.set_sort(30)
            ui_region.set_active(True)
            text_scale = 2.0 * 21.0 / height
            self.viewports.append(
                Viewport(
                    index=index,
                    camera=camera,
                    region=region,
                    lens=lens,
                    aspect=aspect,
                    width=width,
                    height=height,
                    ui_scene=ui_scene,
                    ui_camera=ui_camera,
                    ui_region=ui_region,
                    ui_root=ui_root,
                    text_scale=text_scale,
                )
            )
        self.hud_visible = True

    # ------------------------------------------------------------------ frame

    def apply_camera(self, index: int, position: tuple[float, float, float], look: tuple[float, float, float], fov: float) -> None:
        if index >= len(self.viewports):
            return
        view = self.viewports[index]
        view.camera.set_pos(*position)
        view.camera.look_at(look[0], look[1], look[2])
        try:
            view.lens.set_fov(fov)
            view.lens.set_aspect_ratio(view.aspect)
        except Exception:
            pass

    def set_hud_visible(self, visible: bool) -> None:
        self.hud_visible = visible
        for view in self.viewports:
            view.ui_region.set_active(visible)
            view.ui_scene.show() if visible else view.ui_scene.hide()

    def set_ui_visible(self, index: int, visible: bool) -> None:
        if index < len(self.viewports):
            view = self.viewports[index]
            view.ui_scene.show() if visible else view.ui_scene.hide()

    def viewport(self, index: int) -> Viewport | None:
        if 0 <= index < len(self.viewports):
            return self.viewports[index]
        return None

    def destroy(self) -> None:
        self._clear()
        self.main_region.set_dimensions(*self.saved_dims)
        self.main_region.set_active(True)
        self.base.cam.set_pos(self.saved_pos)
        self.base.cam.set_hpr(self.saved_hpr)
        self.base.camLens.set_fov(self.saved_fov)
        self.base.camLens.set_aspect_ratio(self.saved_aspect)


def title_pose(track: Track, world: Any, elapsed: float) -> tuple[tuple[float, float, float], tuple[float, float, float], float]:
    center = world.start_point
    angle = 0.28 + elapsed * 0.075
    radius = 34.0
    position = (center[0] + math.cos(angle) * radius, center[1] + math.sin(angle) * radius, 10.5)
    look = (center[0], center[1], 11.0)
    return position, look, 92.0


def select_pose(world: Any, elapsed: float) -> tuple[tuple[float, float, float], tuple[float, float, float], float]:
    stage = world.stage_point
    sway = math.sin(elapsed * 0.35) * 0.7
    position = (stage[0] + sway, stage[1] + 9.5, 4.9)
    look = (stage[0] - 2.0, stage[1], 1.55)
    return position, look, 62.0


def podium_pose(world: Any, elapsed: float) -> tuple[tuple[float, float, float], tuple[float, float, float], float]:
    point = world.podium_point
    sway = math.sin(elapsed * 0.25) * 1.2
    position = (point[0] + sway, point[1] + 13.0, 5.8)
    look = (point[0] - 1.5, point[1], 1.6)
    return position, look, 62.0
