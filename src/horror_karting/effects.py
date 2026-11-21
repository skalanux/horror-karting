"""Efectos dinámicos: cajas de ítems, aceite, proyectiles y partículas."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any

from panda3d.core import NodePath, Vec4

from .palette import CREAM, INK, PUMPKIN, v
from .primitives import Build


@dataclass(slots=True)
class Particle:
    node: NodePath
    pos: tuple[float, float, float]
    vel: tuple[float, float, float]
    life: float
    max_life: float
    size: float
    color: Vec4
    gravity: float
    drag: float
    alive: bool = False


class Effects:
    def __init__(self, base: Any, root: NodePath, track: Any) -> None:
        self.base = base
        self.track = track
        self.build = Build(base)
        self.root = root.attach_new_node("effects")
        self.rng = random.Random(31)
        self.particles: list[Particle] = []
        self.pool_index = 0
        self.box_nodes: dict[int, tuple[NodePath, Any]] = {}
        self.oil_nodes: dict[int, NodePath] = {}
        self.projectile_nodes: dict[int, NodePath] = {}
        self.spark_timers: dict[int, float] = {}
        self._build_pool(150)

    def _build_pool(self, count: int) -> None:
        for _ in range(count):
            card = self.build.card(
                self.root,
                (0, 0, 0),
                1.0,
                1.0,
                Vec4(1, 1, 1, 0),
                billboard=True,
                alpha=True,
                depth_write=False,
            )
            card.set_bin("fixed", 8)
            card.hide()
            self.particles.append(Particle(card, (0, 0, 0), (0, 0, 0), 0.0, 1.0, 0.1, Vec4(1, 1, 1, 1), 0.0, 0.92))

    # ------------------------------------------------------------------ setup

    def setup(self, sim: Any) -> None:
        for holder, _box in self.box_nodes.values():
            holder.remove_node()
        self.box_nodes.clear()
        for node in self.oil_nodes.values():
            node.remove_node()
        self.oil_nodes.clear()
        for node in self.projectile_nodes.values():
            node.remove_node()
        self.projectile_nodes.clear()
        self.spark_timers.clear()
        for box in sim.item_boxes:
            point = self.track.point(box.s, box.t)
            holder = self.root.attach_new_node(f"itembox-{box.uid}")
            holder.set_pos(point[0], point[1], point[2] + 1.25)
            core = self.build.ball(holder, (0, 0, 0), 0.30, Vec4(0.92, 0.90, 0.82, 1.0))
            _ = core
            for side in (-1.0, 1.0):
                self.build.ball(holder, (side * 0.11, 0.24, 0.04), 0.062, v(INK))
                self.build.ball(holder, (side * 0.11, -0.24, 0.04), 0.062, v(INK))
            self.build.box(holder, (0, 0.245, -0.15), (0.20, 0.05, 0.08), v(INK))
            self.build.box(holder, (0, -0.245, -0.15), (0.20, 0.05, 0.08), v(INK))
            self.build.glow(holder, (0, 0, 0), 0.48, Vec4(0.55, 1.0, 0.75, 0.30), layers=2, sort=6)
            self.box_nodes[box.uid] = (holder, box)

    # ------------------------------------------------------------------ bursts

    def _spawn(self, pos: tuple[float, float, float], vel: tuple[float, float, float], life: float, size: float, color: Vec4, gravity: float = 0.0, drag: float = 0.94) -> None:
        particle = self.particles[self.pool_index]
        self.pool_index = (self.pool_index + 1) % len(self.particles)
        particle.pos = pos
        particle.vel = vel
        particle.life = life
        particle.max_life = life
        particle.size = size
        particle.color = color
        particle.gravity = gravity
        particle.drag = drag
        particle.alive = True
        particle.node.show()
        particle.node.set_pos(*pos)
        particle.node.set_scale(size)
        particle.node.set_color(color)

    def burst(self, kind: str, pos: tuple[float, float, float], count: int = 10, direction: tuple[float, float] | None = None) -> None:
        rng = self.rng
        dx, dy = direction or (0.0, 0.0)
        for index in range(count):
            spread = rng.uniform(-1.6, 1.6)
            forward = rng.uniform(-1.0, 1.5)
            speed = rng.uniform(0.8, 4.5)
            velocity = (
                (-dx * forward + -dy * spread) * speed,
                (-dy * forward + dx * spread) * speed,
                rng.uniform(0.4, 3.2),
            )
            if kind == "boost":
                color = Vec4(1.0, 0.62, 0.16, 0.9) if index % 2 == 0 else Vec4(0.45, 0.95, 1.0, 0.85)
                life = rng.uniform(0.24, 0.45)
                size = rng.uniform(0.08, 0.18)
                gravity = 2.0
            elif kind == "drift":
                color = Vec4(1.0, 0.58, 0.12, 0.95) if index % 3 else Vec4(1.0, 0.92, 0.6, 0.95)
                life = rng.uniform(0.18, 0.34)
                size = rng.uniform(0.06, 0.13)
                gravity = 3.0
            elif kind == "dust":
                color = Vec4(0.20, 0.18, 0.16, 0.5)
                life = rng.uniform(0.3, 0.7)
                size = rng.uniform(0.16, 0.36)
                gravity = 0.6
            elif kind == "explosion":
                color = Vec4(1.0, 0.45, 0.08, 0.95) if index % 3 else Vec4(0.12, 0.08, 0.06, 0.9)
                life = rng.uniform(0.4, 0.9)
                size = rng.uniform(0.24, 0.62)
                gravity = 1.2
            elif kind == "pickup":
                color = Vec4(0.55, 1.0, 0.55, 0.9) if index % 2 else Vec4(1.0, 0.88, 0.30, 0.9)
                life = rng.uniform(0.25, 0.5)
                size = rng.uniform(0.08, 0.16)
                gravity = 2.2
            elif kind == "web":
                color = Vec4(0.95, 0.95, 1.0, 0.9)
                life = rng.uniform(0.2, 0.4)
                size = rng.uniform(0.07, 0.14)
                gravity = 1.0
            elif kind == "hit":
                color = Vec4(0.95, 0.35, 0.85, 0.9)
                life = rng.uniform(0.25, 0.5)
                size = rng.uniform(0.08, 0.18)
                gravity = 2.0
            elif kind == "saw":
                color = Vec4(1.0, 0.85, 0.25, 0.95)
                life = rng.uniform(0.2, 0.35)
                size = rng.uniform(0.07, 0.14)
                gravity = 2.0
            else:
                color = Vec4(0.8, 0.8, 0.9, 0.8)
                life = 0.3
                size = 0.1
                gravity = 1.0
            self._spawn((pos[0], pos[1], pos[2]), velocity, life, size, color, gravity, 0.93)

    def flash(self, pos: tuple[float, float, float], color: Vec4, size: float = 1.6) -> None:
        self._spawn(pos, (0, 0, 0), 0.18, size, color, 0.0, 1.0)

    def skid(self, pos: tuple[float, float, float]) -> None:
        self._spawn(pos, (0, 0, 0), 0.6, 0.22, Vec4(0.05, 0.04, 0.05, 0.35), 0.0, 1.0)

    # ------------------------------------------------------------------ update

    def update(self, sim: Any, dt: float, elapsed: float) -> None:
        for uid, (holder, box) in self.box_nodes.items():
            if box.active:
                holder.show()
                holder.set_z(self.track.height(box.s) + 1.25 + math.sin(elapsed * 2.4 + uid) * 0.12)
                holder.set_h(elapsed * 55.0 + uid)
            else:
                holder.hide()
        oils = {oil.uid: oil for oil in sim.oils}
        for uid in list(self.oil_nodes):
            if uid not in oils:
                self.oil_nodes.pop(uid).remove_node()
        for uid, oil in oils.items():
            if uid not in self.oil_nodes:
                point = self.track.point(oil.s, oil.t)
                holder = self.root.attach_new_node(f"oil-{uid}")
                holder.set_pos(point[0], point[1], point[2] + 0.07)
                self.build.ball(holder, (0, 0, 0), (0.95, 1.15, 0.02), Vec4(0.035, 0.030, 0.045, 0.92), alpha=True)
                self.build.ball(holder, (0, 0, 0.02), (0.60, 0.80, 0.015), Vec4(0.30, 0.10, 0.36, 0.30), alpha=True)
                self.oil_nodes[uid] = holder
        shots = {shot.uid: shot for shot in sim.projectiles}
        for uid in list(self.projectile_nodes):
            if uid not in shots:
                self.projectile_nodes.pop(uid).remove_node()
        for uid, shot in shots.items():
            if uid not in self.projectile_nodes:
                point = self.track.point(shot.s, shot.t)
                holder = self.root.attach_new_node(f"shot-{uid}")
                if shot.kind == "bomb":
                    self.build.ball(holder, (0, 0, 0), 0.28, v(PUMPKIN))
                    self.build.box(holder, (0, 0, 0.34), (0.07, 0.07, 0.16), v(INK))
                    self.build.glow(holder, (0, 0, 0.42), 0.22, Vec4(1.0, 0.55, 0.12, 0.9), layers=1)
                else:
                    self.build.ball(holder, (0, 0, 0), 0.16, Vec4(0.92, 0.92, 1.0, 0.9), alpha=True)
                    for angle in (0, 45, 90, 135):
                        self.build.box(holder, (0, 0, 0), (0.04, 0.52, 0.04), v(CREAM), hpr=(0, 0, angle))
                self.projectile_nodes[uid] = holder
            point = self.track.point(shot.s, shot.t)
            self.projectile_nodes[uid].set_pos(point[0], point[1], point[2] + 0.85)
        for kart in sim.karts:
            timer = self.spark_timers.get(kart.index, 0.0) - dt
            if kart.boost > 0.0 and timer <= 0.0:
                point = self.track.point(kart.s, kart.t)
                heading = self.track.heading(kart.s)
                forward = (-math.sin(heading), math.cos(heading))
                rear = (point[0] - forward[0] * 1.0, point[1] - forward[1] * 1.0, point[2] + 0.45)
                self.burst("boost", rear, 2, forward)
                timer = 0.035
            elif kart.drift > 0.2 and abs(kart.speed) > 8.0 and timer <= 0.0:
                point = self.track.point(kart.s, kart.t)
                heading = self.track.heading(kart.s)
                forward = (-math.sin(heading), math.cos(heading))
                rear = (point[0] - forward[0] * 0.9, point[1] - forward[1] * 0.9, point[2] + 0.15)
                self.burst("drift", rear, 2, forward)
                timer = 0.045
            elif kart.off_road and kart.speed > 6.0 and timer <= 0.0:
                point = self.track.point(kart.s, kart.t)
                heading = self.track.heading(kart.s)
                forward = (-math.sin(heading), math.cos(heading))
                rear = (point[0] - forward[0] * 1.0, point[1] - forward[1] * 1.0, point[2] + 0.10)
                self.burst("dust", rear, 2, forward)
                timer = 0.075
            self.spark_timers[kart.index] = max(0.0, timer)
        for particle in self.particles:
            if not particle.alive:
                continue
            particle.life -= dt
            if particle.life <= 0.0:
                particle.alive = False
                particle.node.hide()
                continue
            vx = particle.vel[0] * particle.drag
            vy = particle.vel[1] * particle.drag
            vz = particle.vel[2] - particle.gravity * dt
            particle.vel = (vx, vy, vz)
            particle.pos = (
                particle.pos[0] + vx * dt,
                particle.pos[1] + vy * dt,
                particle.pos[2] + vz * dt,
            )
            ratio = max(0.0, particle.life / max(particle.max_life, 1e-4))
            color = particle.color
            particle.node.set_pos(*particle.pos)
            particle.node.set_scale(particle.size * (0.45 + 0.55 * ratio))
            particle.node.set_color(Vec4(color[0], color[1], color[2], color[3] * ratio))

    def destroy(self) -> None:
        self.root.remove_node()
