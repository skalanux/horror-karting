"""Lectura de controles: volante físico (postura ``steer``), stick y botones.

Sin Panda3D. El volante viene de la postura ``steer`` de la plataforma
(``frame.axis("steer")``, -1..1 con deadzone, saturación y curva), calculada por
el reconocedor de gestos sobre el giro del teléfono. El juego agrega sensibilidad
por jugador y un invertir; el re-centrado del neutro es ``ctx.phone.recenter()``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

SENSITIVITY_GAIN: dict[str, float] = {
    "suave": 0.7,
    "normal": 1.0,
    "agresiva": 1.4,
}
SENSITIVITY_ORDER = ("suave", "normal", "agresiva")


@dataclass(slots=True)
class PlayerInput:
    throttle: float = 0.0
    brake: float = 0.0
    steer: float = 0.0
    throttle_edge: bool = False
    brake_edge: bool = False
    cross_edge: bool = False
    triangle_edge: bool = False
    options_edge: bool = False
    camera_edge: bool = False
    look_back: bool = False
    stick_x: float = 0.0
    stick_y: float = 0.0
    pointer: tuple[float, float] | None = None
    motion: bool = False


class ControlReader:
    """Estado por slot: botones anteriores, sensibilidad y si el volante activó."""

    def __init__(self, slot: int) -> None:
        self.slot = slot
        self.previous: frozenset[str] = frozenset()
        self.motion_seen = False
        self.sensitivity = "normal"
        self.invert = False

    # -- volante ------------------------------------------------------------

    def reset_motion(self) -> None:
        """Volver al stick hasta que el jugador gire el teléfono otra vez."""
        self.motion_seen = False

    def steer_value(self, steer: float) -> float:
        """Aplicar sensibilidad e invertir a la postura ``steer`` (-1..1)."""
        if steer == 0.0:
            return 0.0
        value = max(-1.0, min(1.0, steer * SENSITIVITY_GAIN[self.sensitivity]))
        return -value if self.invert else value

    def cycle_sensitivity(self, direction: int) -> None:
        index = SENSITIVITY_ORDER.index(self.sensitivity)
        self.sensitivity = SENSITIVITY_ORDER[(index + direction) % len(SENSITIVITY_ORDER)]

    # -- frame --------------------------------------------------------------

    def read(self, frame: object | None) -> PlayerInput:
        if frame is None:
            self.previous = frozenset()
            return PlayerInput()
        buttons = frozenset(getattr(frame, "buttons", ()) or ())
        axes = getattr(frame, "axes", {}) or {}
        pointer = getattr(frame, "pointer", None)
        steer_raw = float(axes.get("steer", 0.0) or 0.0)
        if abs(steer_raw) > 0.0:
            self.motion_seen = True
        stick_x = float(axes.get("move_x", 0.0) or 0.0)
        stick_y = float(axes.get("move_y", 0.0) or 0.0)
        if abs(stick_x) < 0.14:
            stick_x = 0.0
        if abs(stick_y) < 0.14:
            stick_y = 0.0
        if self.motion_seen:
            steer = self.steer_value(steer_raw)
        else:
            curve = abs(stick_x) ** 1.25
            steer = -math.copysign(curve, stick_x) if stick_x else 0.0
        input_state = PlayerInput(
            throttle=1.0 if "cross" in buttons else 0.0,
            brake=1.0 if "square" in buttons else 0.0,
            steer=max(-1.0, min(1.0, steer)),
            throttle_edge="cross" in buttons and "cross" not in self.previous,
            brake_edge="square" in buttons and "square" not in self.previous,
            cross_edge="cross" in buttons and "cross" not in self.previous,
            triangle_edge="triangle" in buttons and "triangle" not in self.previous,
            options_edge="options" in buttons and "options" not in self.previous,
            camera_edge="r1" in buttons and "r1" not in self.previous,
            look_back="l1" in buttons,
            stick_x=stick_x,
            stick_y=stick_y,
            pointer=tuple(pointer) if pointer else None,
            motion=self.motion_seen,
        )
        self.previous = buttons
        return input_state
