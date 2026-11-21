"""Tests puros de controles: volante físico (steer), stick y bordes de botones."""

from __future__ import annotations

import pytest

from horror_karting.controls import ControlReader


class FakeFrame:
    def __init__(
        self,
        *,
        buttons: set[str] | None = None,
        move_x: float = 0.0,
        steer: float = 0.0,
    ) -> None:
        self.buttons = frozenset(buttons or set())
        self.axes = {"move_x": move_x, "move_y": 0.0, "steer": steer}
        self.pointer = None


def test_stick_fallback_steers_right() -> None:
    reader = ControlReader(0)
    state = reader.read(FakeFrame(move_x=0.8))
    assert state.steer < -0.1
    assert not state.motion


def test_button_edges_only_fire_once() -> None:
    reader = ControlReader(0)
    first = reader.read(FakeFrame(buttons={"cross"}))
    second = reader.read(FakeFrame(buttons={"cross"}))
    third = reader.read(FakeFrame())
    assert first.cross_edge
    assert not second.cross_edge
    assert not third.cross_edge


def test_motion_detection_activates_wheel() -> None:
    reader = ControlReader(0)
    state = reader.read(FakeFrame(steer=0.5))
    assert state.motion
    assert state.steer == pytest.approx(0.5)


def test_invert_flips_steer() -> None:
    reader = ControlReader(0)
    reader.invert = True
    state = reader.read(FakeFrame(steer=0.5))
    assert state.steer == pytest.approx(-0.5)


def test_sensitivity_scales_steer() -> None:
    reader = ControlReader(0)
    reader.cycle_sensitivity(1)  # agresiva = 1.4
    state = reader.read(FakeFrame(steer=0.5))
    assert state.steer == pytest.approx(0.5 * 1.4)


def test_sensitivity_order() -> None:
    reader = ControlReader(0)
    assert reader.sensitivity == "normal"
    reader.cycle_sensitivity(1)
    assert reader.sensitivity == "agresiva"
    reader.cycle_sensitivity(1)
    assert reader.sensitivity == "suave"
