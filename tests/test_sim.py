"""Tests puros de la simulación de carrera."""

from __future__ import annotations

from horror_karting.sim import ControlState, Entry, Oil, RaceSim
from horror_karting.track import Track


def _make_sim(*, seed: int = 11, time_trial: bool = False) -> RaceSim:
    track = Track()
    entries = [Entry(0, "dracula", "P1", (0.9, 0.2, 0.2))]
    return RaceSim(track, entries=entries, difficulty="normal", time_trial=time_trial, seed=seed)


def test_grid_and_countdown() -> None:
    sim = _make_sim()
    assert len(sim.karts) == 8
    human = sim.karts[sim.human_karts[0]]
    assert human.s < 0.0
    assert sim.state == "countdown"
    sim.update(1 / 60, {human.index: ControlState(throttle=1.0)})
    assert sim.state == "countdown"


def test_throttle_moves_kart_after_countdown() -> None:
    sim = _make_sim()
    human = sim.karts[sim.human_karts[0]]
    start = human.s
    while sim.state == "countdown":
        sim.update(1 / 60, {human.index: ControlState(throttle=1.0)})
    for _ in range(120):
        sim.update(1 / 60, {human.index: ControlState(throttle=1.0)})
    assert human.s > start + 8.0
    assert human.speed > 5.0


def test_lap_counting_and_finish() -> None:
    sim = _make_sim()
    sim.state = "race"
    sim.countdown = 0.0
    sim.laps_total = 1
    human = sim.karts[sim.human_karts[0]]
    human.s = sim.track.length - 4.0
    human.speed = 18.0
    for _ in range(240):
        sim.update(1 / 60, {human.index: ControlState(throttle=1.0)})
        if human.finished:
            break
    assert human.finished
    assert human.lap_index >= 1
    for _ in range(150):
        sim.update(1 / 60, {human.index: ControlState(throttle=1.0)})
    assert sim.state == "finished"
    results = sim.results()
    assert results[0]["finished"]


def test_items_activate_effects() -> None:
    sim = _make_sim()
    human = sim.karts[sim.human_karts[0]]
    human.item = "nitro"
    sim.use_item(human)
    assert human.item is None
    assert human.boost > 0.0
    human.item = "oil"
    sim.use_item(human)
    assert len(sim.oils) == 1
    human.item = "shield"
    sim.use_item(human)
    assert human.shield > 0.0
    human.item = "bomb"
    sim.use_item(human)
    assert len(sim.projectiles) == 1


def test_oil_hit_spins_kart() -> None:
    sim = _make_sim()
    sim.state = "race"
    sim.countdown = 0.0
    human = sim.karts[sim.human_karts[0]]
    human.s = 120.0
    human.t = 0.0
    human.speed = 15.0
    sim.oils = [Oil(999, human.s, human.t)]
    sim.update(1 / 60, {human.index: ControlState(throttle=1.0)})
    assert human.spin > 0.0 or human.hit_timer > 0.0


def test_item_box_pickup() -> None:
    sim = _make_sim()
    sim.state = "race"
    sim.countdown = 0.0
    human = sim.karts[sim.human_karts[0]]
    box = sim.item_boxes[0]
    human.s = box.s
    human.t = box.t
    human.speed = 0.0
    sim.update(1 / 60, {human.index: ControlState()})
    assert human.item is not None
    assert not box.active


def test_ai_drives_when_no_input() -> None:
    sim = _make_sim()
    sim.state = "race"
    sim.countdown = 0.0
    for _ in range(120):
        sim.update(1 / 60, {})
    ai_karts = [kart for kart in sim.karts if not kart.is_human]
    assert any(kart.s > 1.0 for kart in ai_karts)


def test_time_trial_has_one_kart() -> None:
    sim = _make_sim(time_trial=True)
    assert len(sim.karts) == 1
    assert not sim.item_boxes
