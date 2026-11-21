"""Simulación pura de la carrera: karts, IA, ítems, vueltas y posiciones.

No importa Panda3D. La vista lee ``RaceSim.karts`` y ``RaceSim.events``.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .characters import BY_KEY, KEYS, Character
from .track import Track

RGB = tuple[float, float, float]

STEP = 1.0 / 120.0
LAPS = 3
GRID_SIZE = 8


@dataclass(frozen=True, slots=True)
class PhysicsSpec:
    max_speed: float
    accel: float
    grip: float

    @classmethod
    def from_character(cls, character: Character) -> PhysicsSpec:
        return cls(
            max_speed=23.0 + (character.speed - 3) * 2.6,
            accel=8.8 + (character.accel - 3) * 1.9,
            grip=0.88 + (character.grip - 3) * 0.13,
        )


@dataclass(slots=True)
class ControlState:
    throttle: float = 0.0
    brake: float = 0.0
    steer: float = 0.0
    item: bool = False
    throttle_edge: bool = False


@dataclass(slots=True)
class KartState:
    index: int
    character: str
    is_human: bool
    slot: int | None
    player_name: str
    color: RGB
    grid_index: int
    spec: PhysicsSpec
    s: float = 0.0
    t: float = 0.0
    speed: float = 0.0
    slip: float = 0.0
    steer: float = 0.0
    air_z: float = 0.0
    vz: float = 0.0
    boost: float = 0.0
    spin: float = 0.0
    slow: float = 0.0
    shield: float = 0.0
    drift: float = 0.0
    charge: float = 0.0
    item: str | None = None
    item_timer: float = 0.0
    ai_controlled: bool = False
    lane: float = 0.0
    ai_timer: float = 0.0
    finished: bool = False
    finish_time: float = 0.0
    lap_index: int = 0
    lap_start: float = 0.0
    best_lap: float = 0.0
    last_lap: float = 0.0
    position: int = 1
    off_road: bool = False
    wall_timer: float = 0.0
    hit_timer: float = 0.0
    rocket: bool = False
    prev_slope: float = 0.0
    airborne: bool = False
    jumps: int = 0

    @property
    def lap(self) -> int:
        return max(1, min(LAPS, self.lap_index + 1))

    @property
    def progress(self) -> float:
        return self.s

    @property
    def speed_kmh(self) -> float:
        return max(0.0, self.speed) * 3.6

    @property
    def boost_ratio(self) -> float:
        return min(1.0, self.charge / 2.0)


@dataclass(slots=True)
class ItemBox:
    uid: int
    s: float
    t: float
    active: bool = True
    cooldown: float = 0.0


@dataclass(slots=True)
class Oil:
    uid: int
    s: float
    t: float
    life: float = 24.0


@dataclass(slots=True)
class Projectile:
    uid: int
    kind: str
    s: float
    t: float
    speed: float
    owner: int
    life: float
    target: int = -1


@dataclass(slots=True)
class SimEvent:
    kind: str
    kart: int
    other: int = -1
    text: str = ""
    value: float = 0.0


@dataclass(frozen=True, slots=True)
class Entry:
    slot: int
    character: str
    name: str
    color: RGB


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


DIFFICULTY = {
    "facil": (0.90, 0.90, 0.26, 0.55),
    "normal": (1.00, 1.00, 0.13, 0.45),
    "dificil": (1.05, 1.05, 0.05, 0.30),
}


class RaceSim:
    """Carrera completa de 8 karts (o contrarreloj de uno)."""

    def __init__(
        self,
        track: Track,
        *,
        entries: list[Entry],
        difficulty: str = "normal",
        time_trial: bool = False,
        seed: int | None = None,
    ) -> None:
        self.track = track
        self.time_trial = time_trial
        self.difficulty = difficulty if difficulty in DIFFICULTY else "normal"
        self.rng = random.Random(seed)
        self.events: list[SimEvent] = []
        self.uid = 1
        self.state = "countdown"
        self.countdown = 3.6
        self.race_time = 0.0
        self.end_timer = 0.0
        self.human_deadline: float | None = None
        self.finish_order: list[int] = []
        self.laps_total = LAPS
        self._accum = 0.0
        self.item_boxes: list[ItemBox] = []
        self.oils: list[Oil] = []
        self.projectiles: list[Projectile] = []
        self.karts: list[KartState] = []
        self._build_karts(entries)
        if not time_trial:
            self._build_item_boxes()
        self._place_grid()
        if not time_trial:
            self._sort_positions()

    # ------------------------------------------------------------------ setup

    def _build_karts(self, entries: list[Entry]) -> None:
        used = {entry.character for entry in entries}
        humans = list(entries)
        ais: list[tuple[str, str, RGB]] = []
        if not self.time_trial:
            pool = [key for key in KEYS if key not in used]
            self.rng.shuffle(pool)
            ai_total = max(0, GRID_SIZE - len(humans))
            for index in range(ai_total):
                key = pool[index % len(pool)] if pool else KEYS[index % len(KEYS)]
                character = BY_KEY[key]
                ais.append((key, f"CPU {index + 1}", character.body))
        # La IA ocupa las filas de adelante; los humanos largan atrás.
        ordered: list[tuple[str, str, RGB, bool, int | None]] = []
        for key, name, color in ais:
            ordered.append((key, name, color, False, None))
        for entry in humans:
            character = BY_KEY[entry.character]
            ordered.append((entry.character, entry.name, entry.color, True, entry.slot))
        for grid_index, (key, name, color, is_human, slot) in enumerate(ordered):
            character = BY_KEY[key]
            kart = KartState(
                index=len(self.karts),
                character=key,
                is_human=is_human,
                slot=slot,
                player_name=name,
                color=color,
                grid_index=grid_index,
                spec=PhysicsSpec.from_character(character),
                ai_controlled=not is_human,
                lane=self.rng.uniform(-1.1, 1.1),
                ai_timer=self.rng.uniform(1.2, 2.6),
            )
            self.karts.append(kart)
        self.human_karts = [kart.index for kart in self.karts if kart.is_human]

    def _place_grid(self) -> None:
        if self.time_trial:
            for kart in self.karts:
                kart.s = -6.0
                kart.t = 0.0
                kart.air_z = self.track.height(kart.s)
                kart.prev_slope = self.track.slope(kart.s)
            return
        for kart in self.karts:
            row = kart.grid_index // 2
            side = -1.0 if kart.grid_index % 2 == 0 else 1.0
            kart.s = -(7.0 + row * 4.2)
            kart.t = side * 2.35
            kart.air_z = self.track.height(kart.s)
            kart.prev_slope = self.track.slope(kart.s)
            kart.lap_start = 0.0

    def _build_item_boxes(self) -> None:
        jump_s = self.track.length - 72.0
        s = 62.0
        while s < self.track.length - 24.0:
            if abs(s - jump_s) > 34.0:
                for lateral in (-3.4, 0.0, 3.4):
                    self.item_boxes.append(ItemBox(self._next_uid(), s, lateral))
            s += 92.0

    def _next_uid(self) -> int:
        value = self.uid
        self.uid += 1
        return value

    # ------------------------------------------------------------------ input

    def update(self, dt: float, controls: dict[int, ControlState] | None = None) -> None:
        self.events.clear()
        controls = controls or {}
        if dt <= 0.0:
            return
        self._accum += min(dt, 0.12)
        first = True
        while self._accum >= STEP:
            self._accum -= STEP
            frame_controls: dict[int, ControlState] = {}
            for index, control in controls.items():
                if first:
                    frame_controls[index] = control
                else:
                    frame_controls[index] = ControlState(
                        throttle=control.throttle,
                        brake=control.brake,
                        steer=control.steer,
                    )
            self._step(STEP, frame_controls)
            first = False

    def _step(self, dt: float, controls: dict[int, ControlState]) -> None:
        if self.state == "countdown":
            previous = self.countdown
            self.countdown -= dt
            for kart in self.karts:
                control = controls.get(kart.index)
                if control is not None and control.throttle_edge:
                    if self.countdown <= 0.45:
                        kart.rocket = True
            if self.countdown <= 0.0 < previous:
                self.state = "race"
                self.race_time = 0.0
                for kart in self.karts:
                    if kart.rocket:
                        kart.boost = max(kart.boost, 1.25)
                    elif not kart.is_human and self.rng.random() < DIFFICULTY[self.difficulty][3]:
                        kart.boost = max(kart.boost, 1.0)
                self.events.append(SimEvent("go", 0))
            return
        if self.state != "race":
            return
        self.race_time += dt
        for kart in self.karts:
            if kart.finished:
                self._coast(kart, dt)
                continue
            control = controls.get(kart.index)
            if kart.ai_controlled or control is None:
                control = self._ai_control(kart, dt)
            self._drive(kart, control, dt)
        self._update_boxes(dt)
        self._update_oils(dt)
        self._update_projectiles(dt)
        self._collide_karts()
        self._update_laps()
        self._sort_positions()
        self._check_end(dt)

    # ------------------------------------------------------------- physics/IA

    def _drive(self, kart: KartState, control: ControlState, dt: float) -> None:
        if control.item:
            self.use_item(kart)
        if kart.spin > 0.0:
            kart.spin = max(0.0, kart.spin - dt)
            kart.speed *= max(0.0, 1.0 - 2.4 * dt)
            kart.slip = math.sin(self.race_time * 18.0) * 0.45
            self._advance(kart, dt)
            self._timers(kart, dt)
            return
        kart.boost = max(0.0, kart.boost - dt)
        kart.slow = max(0.0, kart.slow - dt)
        kart.shield = max(0.0, kart.shield - dt)
        kart.hit_timer = max(0.0, kart.hit_timer - dt)

        limit = kart.spec.max_speed
        if kart.boost > 0.0:
            limit *= 1.36
        if kart.slow > 0.0:
            limit *= 0.5
        if kart.off_road:
            limit *= 0.56

        throttle = _clamp(control.throttle, 0.0, 1.0)
        brake = _clamp(control.brake, 0.0, 1.0)
        if brake > 0.0 and kart.speed <= 0.6:
            kart.speed = max(-7.0, kart.speed - 7.5 * dt)
        elif brake > 0.0:
            kart.speed = max(0.0, kart.speed - 31.0 * dt)
        elif throttle > 0.0:
            ratio = 1.0 - 0.62 * _clamp(kart.speed / max(limit, 1.0), 0.0, 1.0)
            force = kart.spec.accel * (1.55 if kart.boost > 0.0 else 1.0)
            kart.speed += force * throttle * ratio * dt
        else:
            kart.speed = max(0.0, kart.speed - (1.1 + 0.16 * kart.speed) * dt)
        if kart.speed > limit:
            kart.speed -= (kart.speed - limit) * 1.6 * dt
        kart.speed = max(kart.speed, -7.0)

        # derrape
        drifting = (
            brake > 0.0
            and abs(control.steer) > 0.32
            and kart.speed > 9.0
            and not kart.off_road
        )
        if drifting:
            kart.drift = min(2.6, kart.drift + dt)
            kart.charge = min(2.4, kart.charge + dt)
            kart.speed *= max(0.0, 1.0 - 0.05 * dt)
        else:
            if kart.drift > 0.65 and kart.charge > 0.55:
                kart.boost = max(kart.boost, min(1.9, 0.45 + kart.charge * 0.55))
                self.events.append(SimEvent("mini_turbo", kart.index, value=kart.charge))
            kart.drift = 0.0
            kart.charge = max(0.0, kart.charge - dt * 2.5)

        # Modelo de volante: steer > 0 gira a la izquierda (como el heading de
        # Panda3D). La pista también gira debajo del kart, así que sin volante
        # el kart se va hacia afuera de la curva.
        steer_target = _clamp(control.steer, -1.0, 1.0)
        kart.steer += (steer_target - kart.steer) * min(1.0, 13.0 * dt)
        speed_abs = max(abs(kart.speed), 1.0)
        max_curv = min(0.085 * kart.spec.grip, 16.0 / (speed_abs * speed_abs + 4.0))
        if drifting:
            max_curv *= 1.45
        curvature = self.track.curvature(kart.s)
        kart.slip += (kart.steer * max_curv - curvature) * kart.speed * dt
        kart.slip = _clamp(kart.slip, -0.95, 0.95)
        self._advance(kart, dt)
        self._timers(kart, dt)

    def _advance(self, kart: KartState, dt: float) -> None:
        kart.s += kart.speed * math.cos(kart.slip) * dt
        kart.t += -kart.speed * math.sin(kart.slip) * dt
        half = self.track.half_width
        kart.off_road = abs(kart.t) > half - 0.9
        wall = half - 0.55
        if abs(kart.t) > wall:
            kart.t = math.copysign(wall, kart.t)
            if kart.wall_timer <= 0.0:
                kart.speed *= 0.86
                kart.slip *= -0.45
                kart.wall_timer = 0.35
                self.events.append(SimEvent("wall", kart.index))
            else:
                kart.speed *= max(0.0, 1.0 - 0.9 * dt)
        kart.wall_timer = max(0.0, kart.wall_timer - dt)

        ground = self.track.height(kart.s)
        slope = self.track.slope(kart.s)
        if not kart.airborne:
            if kart.prev_slope > 0.018 and slope <= 0.006 and kart.speed > 9.0:
                kart.airborne = True
                kart.vz = kart.prev_slope * kart.speed * 0.95
                kart.air_z = ground
                kart.jumps += 1
                self.events.append(SimEvent("jump", kart.index))
            else:
                kart.air_z = ground
                kart.vz = 0.0
        if kart.airborne:
            kart.vz -= 21.0 * dt
            kart.air_z += kart.vz * dt
            if kart.air_z <= ground:
                kart.air_z = ground
                kart.vz = 0.0
                kart.airborne = False
                self.events.append(SimEvent("land", kart.index))
        kart.prev_slope = slope

    def _coast(self, kart: KartState, dt: float) -> None:
        kart.speed = max(0.0, kart.speed - 6.0 * dt)
        kart.s += kart.speed * math.cos(kart.slip) * dt
        kart.t += -kart.speed * math.sin(kart.slip) * dt
        half = self.track.half_width - 0.55
        kart.t = _clamp(kart.t, -half, half)
        kart.air_z = self.track.height(kart.s)

    def _timers(self, kart: KartState, dt: float) -> None:
        kart.ai_timer = max(0.0, kart.ai_timer - dt)

    def _ai_control(self, kart: KartState, dt: float) -> ControlState:
        speed, _accel, noise, _rocket = DIFFICULTY[self.difficulty]
        lane = kart.lane
        look = kart.s + 13.0 + kart.speed * 0.55
        curvature = self.track.curvature(look)
        target_t = _clamp(-curvature * 82.0, -3.9, 3.9) + lane * 0.55
        desired_phi = -_clamp((target_t - kart.t) * 0.065, -0.52, 0.52)
        speed_abs = max(kart.speed, 1.0)
        max_curv = min(0.085 * kart.spec.grip, 16.0 / (speed_abs * speed_abs + 4.0))
        steer = (curvature + (desired_phi - kart.slip) * 2.4) / max(max_curv, 0.02)
        steer += self.rng.uniform(-noise, noise)
        steer = _clamp(steer, -1.0, 1.0)
        target_speed = kart.spec.max_speed * speed * (1.0 - min(0.56, abs(curvature) * 7.6))
        # no chocar al de adelante
        for other in self.karts:
            if other.index == kart.index:
                continue
            if 0.0 < other.s - kart.s < 6.5 and abs(other.t - kart.t) < 1.7:
                if other.speed < kart.speed + 1.0:
                    target_speed = min(target_speed, max(6.0, other.speed - 1.5))
                    break
        # catch-up suave contra el mejor humano
        humans = [k for k in self.karts if k.is_human and not k.finished]
        if humans:
            leader = max(humans, key=lambda k: k.s)
            gap = leader.s - kart.s
            if gap > 45.0:
                target_speed *= 1.07
            elif gap < -45.0:
                target_speed *= 0.95
        if kart.off_road:
            target_speed = min(target_speed, kart.spec.max_speed * 0.5)
        throttle = 1.0 if kart.speed < target_speed else 0.0
        brake = 1.0 if kart.speed > target_speed + 3.4 else 0.0
        if self.rng.random() < noise * 0.004:
            throttle = 0.0
        self._ai_items(kart)
        return ControlState(throttle=throttle, brake=brake, steer=steer)

    def _ai_items(self, kart: KartState) -> None:
        if kart.item is None or kart.ai_timer > 0.0:
            return
        kind = kart.item
        ahead = self._nearest_ahead(kart, 34.0)
        behind = self._nearest_behind(kart, 16.0)
        use = False
        if kind in ("nitro", "motosierra"):
            use = ahead is None or abs(self.track.curvature(kart.s + 12.0)) < 0.012
        elif kind == "bomb":
            use = ahead is not None and ahead[0] < 20.0
        elif kind == "web":
            use = ahead is not None and ahead[0] < 30.0
        elif kind == "oil":
            use = behind is not None and behind[0] < 14.0
        elif kind == "shield":
            use = True
        if use:
            self.use_item(kart)
            kart.ai_timer = self.rng.uniform(1.8, 3.4)

    def _nearest_ahead(self, kart: KartState, limit: float) -> tuple[float, int] | None:
        best: tuple[float, int] | None = None
        for other in self.karts:
            if other.index == kart.index:
                continue
            gap = other.s - kart.s
            if 0.0 < gap < limit and abs(other.t - kart.t) < 2.4:
                if best is None or gap < best[0]:
                    best = (gap, other.index)
        return best

    def _nearest_behind(self, kart: KartState, limit: float) -> tuple[float, int] | None:
        best: tuple[float, int] | None = None
        for other in self.karts:
            if other.index == kart.index:
                continue
            gap = kart.s - other.s
            if 0.0 < gap < limit and abs(other.t - kart.t) < 2.4:
                if best is None or gap < best[0]:
                    best = (gap, other.index)
        return best

    # ------------------------------------------------------------------ items

    def _update_boxes(self, dt: float) -> None:
        for box in self.item_boxes:
            if not box.active:
                box.cooldown -= dt
                if box.cooldown <= 0.0:
                    box.active = True
                    box.cooldown = 0.0
                continue
            for kart in self.karts:
                if kart.finished or kart.item is not None:
                    continue
                if abs(kart.s - box.s) < 2.1 and abs(kart.t - box.t) < 1.7:
                    box.active = False
                    box.cooldown = 3.6
                    kart.item = self._roll_item(kart)
                    self.events.append(
                        SimEvent("pickup", kart.index, text=kart.item, value=box.s)
                    )
                    break

    def _roll_item(self, kart: KartState) -> str:
        weights: dict[str, float] = {
            "nitro": 18.0,
            "oil": 16.0,
            "bomb": 18.0,
            "shield": 16.0,
            "web": 14.0,
        }
        total = len(self.karts)
        if kart.position >= total - 1:
            weights["nitro"] += 15.0
            weights["bomb"] += 9.0
            weights["web"] += 4.0
        elif kart.position >= total - 3:
            weights["nitro"] += 7.0
        if kart.position <= 2:
            weights["oil"] += 11.0
            weights["shield"] += 8.0
        bias = BY_KEY[kart.character].item_bias
        weights[bias] = weights.get(bias, 0.0) + 9.0
        if kart.character == "milei":
            weights["motosierra"] = weights.get("motosierra", 0.0) + 12.0
        keys = list(weights)
        return self.rng.choices(keys, weights=[weights[key] for key in keys], k=1)[0]

    def use_item(self, kart: KartState) -> None:
        kind = kart.item
        if kind is None or kart.finished:
            return
        kart.item = None
        if kind == "nitro":
            kart.boost = max(kart.boost, 1.7)
            self.events.append(SimEvent("nitro", kart.index))
        elif kind == "oil":
            self.oils.append(Oil(self._next_uid(), kart.s - 3.0, kart.t))
            self.events.append(SimEvent("drop_oil", kart.index))
        elif kind == "bomb":
            self.projectiles.append(
                Projectile(self._next_uid(), "bomb", kart.s + 2.0, kart.t, 32.0, kart.index, 1.6)
            )
            self.events.append(SimEvent("throw_bomb", kart.index))
        elif kind == "shield":
            kart.shield = 8.0
            self.events.append(SimEvent("shield", kart.index))
        elif kind == "web":
            target = self._nearest_ahead(kart, 40.0)
            target_index = target[1] if target else -1
            self.projectiles.append(
                Projectile(
                    self._next_uid(),
                    "web",
                    kart.s + 1.5,
                    kart.t,
                    38.0,
                    kart.index,
                    2.6,
                    target_index,
                )
            )
            self.events.append(SimEvent("throw_web", kart.index))
        elif kind == "motosierra":
            kart.boost = max(kart.boost, 1.45)
            self.oils = [oil for oil in self.oils if not (kart.s - 2.0 < oil.s < kart.s + 12.0)]
            target = self._nearest_ahead(kart, 4.0)
            if target is not None:
                other = self.karts[target[1]]
                other.t += math.copysign(1.2, other.t - kart.t if other.t != kart.t else 1.0)
                other.speed *= 0.88
                self.events.append(SimEvent("saw_push", kart.index, other.index))
            self.events.append(SimEvent("saw", kart.index))

    def _update_oils(self, dt: float) -> None:
        for oil in self.oils:
            oil.life -= dt
        self.oils = [oil for oil in self.oils if oil.life > 0.0]
        for oil in self.oils:
            for kart in self.karts:
                if kart.finished or kart.hit_timer > 0.0:
                    continue
                if abs(kart.s - oil.s) < 1.25 and abs(kart.t - oil.t) < 1.3:
                    self._hit(kart, "oil", strength=0.5)

    def _update_projectiles(self, dt: float) -> None:
        alive: list[Projectile] = []
        for shot in self.projectiles:
            shot.life -= dt
            if shot.kind == "bomb":
                shot.s += shot.speed * dt
                hit = None
                for kart in self.karts:
                    if kart.index == shot.owner or kart.finished:
                        continue
                    if abs(kart.s - shot.s) < 2.0 and abs(kart.t - shot.t) < 1.8:
                        hit = kart
                        break
                if hit is not None or shot.life <= 0.0:
                    for kart in self.karts:
                        if kart.index == shot.owner or kart.finished:
                            continue
                        if abs(kart.s - shot.s) < 3.4 and abs(kart.t - shot.t) < 3.2:
                            self._hit(kart, "bomb", strength=0.45)
                    self.events.append(SimEvent("explosion", shot.owner, value=shot.s))
                    continue
            else:
                target_index = shot.target
                target = self.karts[target_index] if 0 <= target_index < len(self.karts) else None
                if target is None or target.finished or target.s < shot.s - 4.0:
                    found = self._nearest_ahead(self.karts[shot.owner], 45.0)
                    target = self.karts[found[1]] if found else None
                    shot.target = target.index if target else -1
                if target is not None:
                    shot.s += shot.speed * dt
                    shot.t += _clamp(target.t - shot.t, -1.0, 1.0) * dt * 3.0
                    if abs(target.s - shot.s) < 2.2 and abs(target.t - shot.t) < 1.8:
                        self._hit(target, "web", strength=0.45)
                        self.events.append(SimEvent("web_hit", shot.owner, target.index))
                        continue
                else:
                    shot.s += shot.speed * dt
            if shot.life > 0.0:
                alive.append(shot)
        self.projectiles = alive

    def _hit(self, kart: KartState, kind: str, *, strength: float) -> None:
        if kart.shield > 0.0:
            kart.shield = 0.0
            self.events.append(SimEvent("shield_break", kart.index))
            return
        if kart.hit_timer > 0.0:
            return
        kart.hit_timer = 1.2
        kart.speed *= strength
        if kind == "web":
            kart.slow = max(kart.slow, 2.8)
            self.events.append(SimEvent("hit_web", kart.index))
        else:
            kart.spin = 1.05
            self.events.append(SimEvent(f"hit_{kind}", kart.index))

    # -------------------------------------------------------------- collisions

    def _collide_karts(self) -> None:
        count = len(self.karts)
        for i in range(count):
            a = self.karts[i]
            if a.finished:
                continue
            for j in range(i + 1, count):
                b = self.karts[j]
                if b.finished:
                    continue
                ds = a.s - b.s
                dt = a.t - b.t
                if abs(ds) < 2.5 and abs(dt) < 1.65:
                    push = 0.55 if dt >= 0.0 else -0.55
                    a.t += push
                    b.t -= push
                    rear = a if ds < 0.0 else b
                    rear.speed *= 0.94
                    if rear.wall_timer <= 0.0:
                        rear.wall_timer = 0.2
                        self.events.append(SimEvent("bump", rear.index))

    # ---------------------------------------------------------------- laps/end

    def _update_laps(self) -> None:
        for kart in self.karts:
            if kart.finished:
                continue
            completed = int(max(0.0, kart.s) // self.track.length)
            if completed > kart.lap_index:
                kart.lap_index = completed
                lap_time = self.race_time - kart.lap_start
                kart.last_lap = lap_time
                if kart.best_lap <= 0.0 or lap_time < kart.best_lap:
                    kart.best_lap = lap_time
                kart.lap_start = self.race_time
                if completed >= self.laps_total:
                    kart.finished = True
                    kart.finish_time = self.race_time
                    self.finish_order.append(kart.index)
                    self.events.append(SimEvent("finish", kart.index))
                else:
                    kind = "last_lap" if completed == self.laps_total - 1 else "lap"
                    self.events.append(SimEvent(kind, kart.index, value=completed))

    def _sort_positions(self) -> None:
        ranked = sorted(
            self.karts,
            key=lambda kart: (
                0 if kart.finished else 1,
                kart.finish_time if kart.finished else -kart.s,
            ),
        )
        for position, kart in enumerate(ranked, start=1):
            kart.position = position

    def _check_end(self, dt: float) -> None:
        humans = [kart for kart in self.karts if kart.is_human]
        if humans:
            if all(kart.finished for kart in humans):
                self.end_timer += dt
                if self.end_timer >= 1.6:
                    self.state = "finished"
                    self.events.append(SimEvent("race_end", 0))
            elif any(kart.finished for kart in humans) and self.human_deadline is None:
                first = next(kart for kart in humans if kart.finished)
                self.human_deadline = first.finish_time + 30.0
            if self.human_deadline is not None and self.race_time >= self.human_deadline:
                self.state = "finished"
                self.events.append(SimEvent("race_end", 0))
        else:
            if all(kart.finished for kart in self.karts) or self.race_time >= 220.0:
                self.state = "finished"
                self.events.append(SimEvent("race_end", 0))

    # ------------------------------------------------------------------ helpers

    def karts_ahead(self, kart: KartState) -> list[KartState]:
        return [other for other in self.karts if other.s > kart.s]

    def results(self) -> list[dict[str, object]]:
        ranked = sorted(self.karts, key=lambda kart: kart.position)
        rows: list[dict[str, object]] = []
        for kart in ranked:
            character = BY_KEY[kart.character]
            rows.append(
                {
                    "position": kart.position,
                    "kart": kart.index,
                    "character": character.key,
                    "name": character.name,
                    "player": kart.player_name,
                    "human": kart.is_human,
                    "color": kart.color,
                    "time": kart.finish_time if kart.finished else None,
                    "best_lap": kart.best_lap,
                    "finished": kart.finished,
                }
            )
        return rows
