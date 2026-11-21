"""Horror Karting: orquestación del juego, estados y presentación."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any

from panda3d.core import Vec4

from toxinator.api import GameContext, GameManifest

from .audio import AudioManager
from .characters import BY_KEY, KEYS
from .controls import ControlReader, PlayerInput
from .effects import Effects
from .hud import PlayerHud, StandingsPanel
from .karts import KartModel
from .palette import (
    CREAM,
    CYAN,
    DIFFICULTY_ORDER,
    GOLD,
    PLAYER_COLORS,
    v,
)
from .primitives import Build
from .scenery import World
from .screens import Screens
from .sim import ControlState, Entry, RaceSim
from .track import CONTROL_POINTS, Track
from .view import (
    CameraRig,
    ViewportManager,
    podium_pose,
    select_pose,
    title_pose,
)


@dataclass(slots=True)
class PlayerSlot:
    index: int
    slot: int
    color: tuple[float, float, float]
    label: str
    character: str = ""
    kart_index: int = -1


class HorrorKarting:
    def __init__(self, manifest: GameManifest) -> None:
        self.manifest = manifest
        self.ctx: GameContext | None = None
        self.base: Any = None
        self.root = None
        self.ui_root = None
        self.build: Build | None = None
        self.track: Track | None = None
        self.world: World | None = None
        self.effects: Effects | None = None
        self.viewports: ViewportManager | None = None
        self.screens: Screens | None = None
        self.audio: AudioManager | None = None
        self.karts_root = None
        self.models: dict[str, KartModel] = {}
        self.sim: RaceSim | None = None
        self.huds: list[PlayerHud] = []
        self.standings: StandingsPanel | None = None
        self.rigs: list[CameraRig] = []
        self.players: list[PlayerSlot] = []
        self.readers: dict[int, ControlReader] = {}
        self.inputs: dict[int, PlayerInput] = {}
        self.frames: dict[int, Any] = {}
        self.state = "title"
        self.mode = "race"
        self.difficulty = "normal"
        self.mirror = False
        self.attract = False
        self.elapsed = 0.0
        self.end_timer = 0.0
        self.go_clear = 0.0
        self.last_count = 4
        self.selected: dict[int, str] = {}
        self.taken: set[str] = set()
        self.select_order: list[int] = []
        self.select_index = 0
        self.select_choice = KEYS[0]
        self.select_nav = 0.0
        self.select_repeat = 0.0
        self.diff_cooldown = 0.0
        self.pause_owner = 0
        self.pause_selected = 0
        self.pause_nav = 0.0
        self.pause_adjust = 0.0
        self.resume_timer = 0.0
        self.last_resume = 4
        self.trial_record: float | None = None
        self.trial_new_record = False
        self.title_signature: tuple[Any, ...] | None = None

    # ------------------------------------------------------------------ lifecycle

    def start(self, ctx: GameContext) -> None:
        self.ctx = ctx
        self.base = ctx.base
        self.root = ctx.scene.attach_new_node("horror-karting")
        self.ui_root = ctx.ui.attach_new_node("horror-karting-ui")
        self.build = Build(self.base)
        self.karts_root = self.root.attach_new_node("karts")
        self.models = {
            key: KartModel(self.build, BY_KEY[key], self.karts_root, None) for key in KEYS
        }
        for model in self.models.values():
            model.set_visible(False)
            model.set_marker_visible(False)
        self.viewports = ViewportManager(self.base, self.root)
        self.screens = Screens(self.ui_root)
        self.audio = AudioManager(self.base)
        self.audio.start_music()
        self._build_circuit(False)
        self._enter_title()
        self._dev_override(os.environ.get("HK_DEV_STATE", ""))

    def update(self, dt: float) -> None:
        if self.ctx is None or self.world is None:
            return
        dt = min(max(dt, 0.0), 0.1)
        self.elapsed += dt
        self._read_inputs()
        self.world.update(dt, self.elapsed)
        self.diff_cooldown = max(0.0, self.diff_cooldown - dt)
        if self.state == "title":
            self._update_title(dt)
        elif self.state == "select":
            self._update_select(dt)
        elif self.state == "race":
            self._update_race(dt)
        elif self.state == "attract":
            self._update_attract(dt)
        elif self.state == "paused":
            self._update_paused(dt)
        elif self.state == "resuming":
            self._update_resuming(dt)
        elif self.state == "podium":
            self._update_podium(dt)
        elif self.state == "results":
            self._update_results(dt)

    def stop(self) -> None:
        if self.ctx is not None:
            try:
                self.ctx.phone.stop()
            except Exception:
                pass
        self._destroy_race_ui()
        if self.screens is not None:
            self.screens.destroy()
            self.screens = None
        if self.audio is not None:
            self.audio.destroy()
            self.audio = None
        if self.viewports is not None:
            self.viewports.destroy()
            self.viewports = None
        if self.effects is not None:
            self.effects.destroy()
            self.effects = None
        self.models.clear()
        if self.ui_root is not None:
            self.ui_root.remove_node()
            self.ui_root = None
        if self.root is not None:
            self.root.remove_node()
            self.root = None
        self.world = None
        self.track = None
        self.sim = None
        self.ctx = None
        self.base = None
        self.build = None

    # ------------------------------------------------------------------ setup

    def _build_circuit(self, mirror: bool) -> None:
        if self.world is not None:
            self.world.node.remove_node()
            self.world = None
        if self.effects is not None:
            self.effects.destroy()
            self.effects = None
        self.mirror = mirror
        if mirror:
            control = (CONTROL_POINTS[0],) + tuple(reversed(CONTROL_POINTS[1:]))
        else:
            control = CONTROL_POINTS
        self.track = Track(control)
        assert self.base is not None and self.root is not None
        self.world = World(self.base, self.root, self.track, mirror=mirror)
        self.effects = Effects(self.base, self.root, self.track)

    def _enter_title(self) -> None:
        self.state = "title"
        self.sim = None
        self.attract = False
        self.end_timer = 0.0
        self.go_clear = 0.0
        self.mode = "race"
        self.selected = {}
        self.taken = set()
        self.rigs = []
        self._destroy_race_ui()
        if self.mirror:
            self._build_circuit(False)
        assert self.viewports is not None
        self.viewports.set_count(1)
        self.viewports.set_hud_visible(False)
        self._place_display_grid()
        self._apply_title_camera()
        if self.screens is not None:
            self.screens.show_title(
                [(player.index, player.color) for player in self.players], self.difficulty
            )
        if self.audio is not None:
            self.audio.update_engine(False, 0.0)

    def _place_display_grid(self) -> None:
        for index, key in enumerate(KEYS):
            model = self.models.get(key)
            if model is None:
                continue
            row = index // 2
            side = -1.0 if index % 2 == 0 else 1.0
            s = -(7.0 + row * 4.2)
            point = self.track.point(s, side * 2.35) if self.track else (0, 0, 0)
            model.root.set_pos(point[0], point[1], point[2] + 0.03)
            model.root.set_h(math.degrees(self.track.heading(s)) if self.track else 0.0)
            model.rest()
            model.set_visible(True)
            model.set_marker_visible(False)

    def _apply_title_camera(self) -> None:
        if self.viewports is None or self.track is None or self.world is None:
            return
        position, look, fov = title_pose(self.track, self.world, self.elapsed)
        self.viewports.set_count(1)
        self.viewports.set_hud_visible(False)
        self.viewports.apply_camera(0, position, look, fov)

    # ------------------------------------------------------------------ input

    def _read_inputs(self) -> None:
        if self.ctx is None:
            return
        self.inputs = {}
        self.frames = {}
        input_state = self.ctx.input_state
        for slot in range(5):
            frame = input_state.frame(slot)
            reader = self.readers.get(slot)
            if reader is None:
                reader = ControlReader(slot)
                self.readers[slot] = reader
            self.inputs[slot] = reader.read(frame)
            if frame is not None:
                self.frames[slot] = frame

    def _any_input(self) -> list[tuple[int, PlayerInput]]:
        return list(self.inputs.items())

    def _joined_inputs(self) -> list[tuple[int, PlayerInput]]:
        slots = {player.slot for player in self.players}
        return [(slot, inp) for slot, inp in self.inputs.items() if slot in slots]

    # ------------------------------------------------------------------ title

    def _update_title(self, dt: float) -> None:
        assert self.track is not None and self.world is not None and self.viewports is not None
        self._apply_title_camera()
        for slot, inp in self._any_input():
            if inp.cross_edge and len(self.players) < 4 and not any(p.slot == slot for p in self.players):
                self._join(slot)
        if self.diff_cooldown <= 0.0:
            for slot, inp in self._joined_inputs() or self._any_input():
                if inp.stick_x > 0.6:
                    self._cycle_difficulty(1)
                    self.diff_cooldown = 0.35
                    break
                if inp.stick_x < -0.6:
                    self._cycle_difficulty(-1)
                    self.diff_cooldown = 0.35
                    break
        for slot, inp in self._joined_inputs():
            if inp.options_edge:
                self._begin_select(trial=False)
                return
        for slot, inp in self._any_input():
            if inp.triangle_edge:
                self._begin_select(trial=True, slot=slot)
                return
        signature = (
            tuple((player.index, player.slot) for player in self.players),
            self.difficulty,
        )
        if signature != self.title_signature:
            self.title_signature = signature
            if self.screens is not None:
                self.screens.show_title(
                    [(player.index, player.color) for player in self.players],
                    self.difficulty,
                )

    def _join(self, slot: int) -> None:
        index = len(self.players)
        if index >= 4:
            return
        color = PLAYER_COLORS[index]
        self.players.append(
            PlayerSlot(index=index, slot=slot, color=color, label=f"P{index + 1}")
        )
        self.title_signature = None
        if 0 <= slot < 4:
            try:
                assert self.ctx is not None
                self.ctx.phone.tone(660, 70, volume=0.3, slot=slot)
            except Exception:
                pass

    def _cycle_difficulty(self, direction: int) -> None:
        index = DIFFICULTY_ORDER.index(self.difficulty)
        self.difficulty = DIFFICULTY_ORDER[(index + direction) % len(DIFFICULTY_ORDER)]
        self.title_signature = None

    # ------------------------------------------------------------------ select

    def _begin_select(self, *, trial: bool, slot: int | None = None) -> None:
        if trial:
            player = next((p for p in self.players if p.slot == slot), None)
            if player is None:
                if len(self.players) >= 4:
                    player = self.players[0]
                else:
                    self._join(slot if slot is not None else 4)
                    player = self.players[-1]
            self.players = [player]
            self.mode = "trial"
        else:
            if not self.players:
                return
            self.mode = "race"
        self.selected = {}
        self.taken = set()
        self.select_order = [player.index for player in self.players]
        self.select_index = 0
        self.select_choice = self._first_available()
        self.select_nav = 0.0
        self.select_repeat = 0.0
        self.state = "select"
        self._enter_select()

    def _enter_select(self) -> None:
        self._destroy_race_ui()
        assert self.viewports is not None and self.screens is not None
        self.viewports.set_count(1)
        self.viewports.set_hud_visible(False)
        self.screens.hide_all()
        self._show_stage()
        assert self.audio is not None
        self.audio.update_engine(False, 0.0)

    def _current_select_player(self) -> PlayerSlot | None:
        if not self.select_order:
            return None
        index = self.select_order[min(self.select_index, len(self.select_order) - 1)]
        for player in self.players:
            if player.index == index:
                return player
        return self.players[0] if self.players else None

    def _first_available(self) -> str:
        for key in KEYS:
            if key not in self.taken:
                return key
        return KEYS[0]

    def _show_stage(self) -> None:
        player = self._current_select_player()
        if player is None or self.screens is None or self.viewports is None:
            return
        for model in self.models.values():
            model.set_visible(False)
            model.set_marker_visible(False)
        model = self.models[self.select_choice]
        assert self.world is not None and self.track is not None
        stage = self.world.stage_point
        model.root.set_pos(stage[0], stage[1], 0.68)
        model.root.set_h(0.0)
        model.rest()
        model.set_visible(True)
        model.set_marker_color(player.color)
        model.set_marker_visible(True)
        self.screens.show_select(
            player.index,
            player.color,
            self.select_choice,
            self.taken,
            player.label,
        )
        position, look, fov = select_pose(self.world, self.elapsed)
        self.viewports.apply_camera(0, position, look, fov)

    def _update_select(self, dt: float) -> None:
        player = self._current_select_player()
        if player is None or self.screens is None:
            return
        inp = self.inputs.get(player.slot)
        if inp is None and player.slot not in self.frames:
            inp = self.inputs.get(4)
        self.select_nav = max(0.0, self.select_nav - dt)
        if inp is not None:
            if abs(inp.stick_x) > 0.55 and self.select_nav <= 0.0:
                self._move_choice(1 if inp.stick_x > 0.0 else -1)
                self.select_nav = 0.24
            if inp.triangle_edge:
                available = [key for key in KEYS if key not in self.taken]
                if available:
                    self.select_choice = available[self.select_order[self.select_index] % len(available)]
                    self._show_stage()
            if inp.cross_edge:
                self._confirm_select()
                return
            if inp.options_edge:
                self._enter_title()
                return
            if inp.pointer is not None:
                self._pointer_select(inp.pointer)
        model = self.models.get(self.select_choice)
        if model is not None:
            model.root.set_h(self.elapsed * 26.0)
        assert self.world is not None and self.viewports is not None
        position, look, fov = select_pose(self.world, self.elapsed)
        self.viewports.apply_camera(0, position, look, fov)

    def _pointer_select(self, pointer: tuple[float, float]) -> None:
        if self.screens is None:
            return
        if pointer[1] < 0.70:
            return
        aspect = 1.78
        world_x = pointer[0] * 2.0 * aspect - aspect
        index = int(round((world_x - 0.30) / 0.185))
        if 0 <= index < len(KEYS):
            key = KEYS[index]
            if key not in self.taken and key != self.select_choice:
                self.select_choice = key
                self._show_stage()

    def _move_choice(self, delta: int) -> None:
        available = [key for key in KEYS if key not in self.taken]
        if not available:
            return
        index = available.index(self.select_choice) if self.select_choice in available else 0
        index = (index + delta) % len(available)
        self.select_choice = available[index]
        self._show_stage()

    def _confirm_select(self) -> None:
        player = self._current_select_player()
        if player is None:
            return
        player.character = self.select_choice
        self.selected[player.index] = self.select_choice
        self.taken.add(self.select_choice)
        self.select_index += 1
        if self.select_index >= len(self.select_order):
            self._start_race()
            return
        self.select_choice = self._first_available()
        self._show_stage()

    # ------------------------------------------------------------------ race begin

    def _start_race(self) -> None:
        if self.track is None or self.viewports is None or self.screens is None:
            return
        self._destroy_race_ui()
        entries = [
            Entry(player.slot, player.character or self._first_available(), player.label, player.color)
            for player in self.players
        ]
        self.sim = RaceSim(
            self.track,
            entries=entries,
            difficulty=self.difficulty,
            time_trial=self.mode == "trial",
            seed=int(self.elapsed * 1000) % 99991,
        )
        self.attract = False
        self.end_timer = 0.0
        self.go_clear = 0.0
        self.last_count = 4
        count = max(1, len(self.players))
        self.viewports.set_count(count)
        self.viewports.set_hud_visible(True)
        self.huds = []
        for index, player in enumerate(self.players):
            view = self.viewports.viewport(index)
            if view is None:
                continue
            self.huds.append(
                PlayerHud(
                    self.build,
                    view,
                    self.track,
                    color=player.color,
                    label=player.label,
                )
            )
        self.standings = StandingsPanel(self.ui_root, self.sim) if count == 3 else None
        self.rigs = [CameraRig(index) for index in range(count)]
        self._assign_models()
        assert self.effects is not None
        self.effects.setup(self.sim)
        self.screens.hide_all()
        for player in self.players:
            frame = self.frames.get(player.slot)
            if frame is not None:
                self.readers[player.slot].reset_motion()
                if self.ctx is not None:
                    self.ctx.phone.recenter(player.slot)
        self.state = "race"
        self._apply_visuals(0.0)
        self._update_cameras(0.0)
        if self.audio is not None:
            self.audio.update_engine(False, 0.0)

    def _assign_models(self) -> None:
        for model in self.models.values():
            model.set_visible(False)
            model.set_marker_visible(False)
            model.rest()
        if self.sim is None:
            return
        show_markers = len(self.players) > 1
        for kart in self.sim.karts:
            model = self.models.get(kart.character)
            if model is None:
                continue
            model.set_visible(True)
            if kart.is_human and show_markers:
                model.set_marker_color(kart.color)
                model.set_marker_visible(True)
            else:
                model.set_marker_visible(False)
        for player in self.players:
            match = next(
                (kart for kart in self.sim.karts if kart.is_human and kart.slot == player.slot),
                None,
            )
            player.kart_index = match.index if match is not None else -1

    def _apply_visuals(self, dt: float) -> None:
        if self.sim is None or self.track is None:
            return
        for kart in self.sim.karts:
            model = self.models.get(kart.character)
            if model is None:
                continue
            point = self.track.point(kart.s, kart.t)
            model.root.set_pos(point[0], point[1], kart.air_z + 0.03)
            heading = self.track.heading(kart.s) + kart.slip
            model.root.set_h(math.degrees(heading))
            air = kart.air_z - self.track.height(kart.s)
            model.update(kart, dt, air, self.elapsed)

    # ------------------------------------------------------------------ title/select dev

    def _dev_override(self, value: str) -> None:
        if value == "race":
            self.players = []
            self._start_attract()
        elif value == "select":
            self.players = [PlayerSlot(0, 4, PLAYER_COLORS[0], "P1")]
            self.mode = "race"
            self.selected = {}
            self.taken = set()
            self.select_order = [0]
            self.select_index = 0
            self.select_choice = "milei"
            self.state = "select"
            self._enter_select()
            self._show_stage()
        elif value == "countdown":
            self.players = [PlayerSlot(0, 7, PLAYER_COLORS[0], "P1", "wolf")]
            self.selected = {0: "wolf"}
            self.mode = "race"
            self._start_race()
        elif value == "pause":
            self.players = [PlayerSlot(0, 7, PLAYER_COLORS[0], "P1", "dracula")]
            self.selected = {0: "dracula"}
            self.mode = "race"
            self._start_race()
            assert self.sim is not None
            self.sim.state = "race"
            self.sim.countdown = 0.0
            self.last_count = 0
            self._pause(0)
        elif value == "mirror":
            self.players = [PlayerSlot(0, 7, PLAYER_COLORS[0], "P1", "kuchisake")]
            self.selected = {0: "kuchisake"}
            self.mode = "race"
            self.mirror = True
            self._build_circuit(True)
            self._start_race()
            assert self.sim is not None
            self.sim.state = "race"
            self.sim.countdown = 0.0
            for kart in self.sim.karts:
                kart.ai_controlled = True
            self.last_count = 0
        elif value == "trial_results":
            self.players = [PlayerSlot(0, 7, PLAYER_COLORS[0], "P1", "milei")]
            self.selected = {0: "milei"}
            self.mode = "trial"
            self._start_race()
            assert self.sim is not None
            self.sim.state = "finished"
            kart = self.sim.karts[self.players[0].kart_index]
            kart.finished = True
            kart.finish_time = 171.4
            kart.best_lap = 54.8
            kart.lap_index = 3
            self._show_trial_results()
        elif value in ("race2", "race3", "race4"):
            count = {"race2": 2, "race3": 3, "race4": 4}[value]
            characters = ("wolf", "milei", "dracula", "kuchisake")
            self.players = [
                PlayerSlot(index, 7 + index, PLAYER_COLORS[index], f"P{index + 1}", characters[index])
                for index in range(count)
            ]
            self.selected = {player.index: player.character for player in self.players}
            self.mode = "race"
            self._start_race()
            assert self.sim is not None
            self.sim.state = "race"
            self.sim.countdown = 0.0
            for kart in self.sim.karts:
                kart.ai_controlled = True
            self.last_count = 0
        elif value == "podium":
            self.players = []
            self.attract = True
            assert self.track is not None
            self.sim = RaceSim(self.track, entries=[], difficulty="normal", seed=3)
            for index, kart in enumerate(self.sim.karts):
                kart.finished = True
                kart.finish_time = 88.0 + index * 2.7
                kart.best_lap = 27.0 + index * 0.6
                kart.lap_index = 3
            self.sim.state = "finished"
            self.sim._sort_positions()
            self._show_podium()

    # ------------------------------------------------------------------ race

    def _update_race(self, dt: float) -> None:
        if self.sim is None or self.viewports is None or self.screens is None:
            return
        for player in self.players:
            inp = self.inputs.get(player.slot)
            if inp is not None and inp.options_edge and player.slot in self.frames:
                self._pause(player.index)
                return
        controls = self._race_controls()
        self.sim.update(dt, controls)
        self._handle_events()
        self._apply_visuals(dt)
        self._update_cameras(dt)
        if self.effects is not None:
            self.effects.update(self.sim, dt, self.elapsed)
        self._update_huds(dt)
        if self.standings is not None:
            self.standings.update(self.sim)
        for index, player in enumerate(self.players):
            inp = self.inputs.get(player.slot)
            if inp is not None and inp.camera_edge and index < len(self.rigs):
                name = self.rigs[index].cycle()
                if index < len(self.huds):
                    self.huds[index].banner_message(f"CÁMARA: {name}", v(CYAN), 1.1)
        self._update_engine_audio()
        if self.sim.state == "countdown":
            self._countdown_tick()
        elif self.go_clear > 0.0:
            self.go_clear = max(0.0, self.go_clear - dt)
        if self.sim.state == "finished":
            self.end_timer += dt
            if self.end_timer >= 0.9:
                self._finish()

    def _race_controls(self) -> dict[int, ControlState]:
        controls: dict[int, ControlState] = {}
        if self.sim is None:
            return controls
        for player in self.players:
            if player.kart_index < 0:
                continue
            kart = self.sim.karts[player.kart_index]
            connected = player.slot in self.frames
            kart.ai_controlled = not connected
            if not connected:
                continue
            inp = self.inputs.get(player.slot)
            if inp is None:
                continue
            controls[player.kart_index] = ControlState(
                throttle=inp.throttle,
                brake=inp.brake,
                steer=inp.steer,
                item=inp.triangle_edge,
                throttle_edge=inp.throttle_edge,
            )
        return controls

    def _update_cameras(self, dt: float) -> None:
        if self.sim is None or self.viewports is None:
            return
        cinematic = self.elapsed if self.sim.state == "countdown" else None
        for index, player in enumerate(self.players):
            if index >= len(self.rigs) or player.kart_index < 0:
                continue
            kart = self.sim.karts[player.kart_index]
            inp = self.inputs.get(player.slot)
            look_back = bool(inp and inp.look_back)
            position, look, fov = self.rigs[index].pose(
                kart, self.track, dt, look_back=look_back, cinematic=cinematic, others=self.sim.karts
            )
            self.viewports.apply_camera(index, position, look, fov)

    def _update_huds(self, dt: float, countdown_override: str | None = None) -> None:
        if self.sim is None:
            return
        for index, player in enumerate(self.players):
            if index >= len(self.huds) or player.kart_index < 0:
                continue
            hud = self.huds[index]
            hud.update(self.sim, player.kart_index, dt, time_trial=self.mode == "trial")
            if countdown_override is not None:
                hud.set_countdown(countdown_override)
            elif self.sim.state == "countdown":
                hud.set_countdown(self._countdown_text())
            elif self.go_clear > 0.0:
                hud.set_countdown("¡LARGADA!")
            else:
                hud.set_countdown(None)

    def _countdown_text(self) -> str:
        if self.sim is None:
            return ""
        countdown = self.sim.countdown
        if countdown > 0.6:
            return str(max(1, min(3, int(math.ceil(countdown - 0.6)))))
        return "¡LARGADA!"

    def _countdown_tick(self) -> None:
        if self.sim is None or self.audio is None:
            return
        value = int(math.ceil(self.sim.countdown - 0.6))
        if value != self.last_count and 1 <= value <= 3:
            self.audio.play("countdown", 0.4)
            self.last_count = value

    def _update_engine_audio(self) -> None:
        if self.audio is None:
            return
        if self.attract or len(self.players) != 1 or self.sim is None:
            self.audio.update_engine(False, 0.0)
            return
        player = self.players[0]
        if player.kart_index < 0:
            self.audio.update_engine(False, 0.0)
            return
        kart = self.sim.karts[player.kart_index]
        active = self.sim.state == "race" and not kart.finished
        self.audio.update_engine(active, kart.speed / max(kart.spec.max_speed, 1.0))

    # ------------------------------------------------------------------ attract

    def _start_attract(self) -> None:
        if self.track is None or self.viewports is None or self.screens is None:
            return
        self._destroy_race_ui()
        self.attract = True
        self.players = []
        self.sim = RaceSim(self.track, entries=[], difficulty="normal", seed=11)
        self.sim.state = "race"
        self.sim.countdown = 0.0
        self.viewports.set_count(1)
        self.viewports.set_hud_visible(True)
        self.rigs = [CameraRig(0)]
        kart = self.sim.karts[0]
        accent = BY_KEY[kart.character].accent
        view = self.viewports.viewport(0)
        if view is not None:
            self.huds = [PlayerHud(self.build, view, self.track, color=accent, label="CPU")]
        assert self.effects is not None
        self.effects.setup(self.sim)
        self._assign_models()
        self.screens.hide_all()
        self.state = "attract"
        self.end_timer = 0.0

    def _update_attract(self, dt: float) -> None:
        if self.sim is None or self.viewports is None or self.screens is None:
            return
        self.sim.update(dt, {})
        self._handle_events()
        self._apply_visuals(dt)
        if self.rigs:
            kart = self.sim.karts[0]
            position, look, fov = self.rigs[0].pose(kart, self.track, dt, others=self.sim.karts)
            self.viewports.apply_camera(0, position, look, fov)
        if self.effects is not None:
            self.effects.update(self.sim, dt, self.elapsed)
        if self.huds:
            self.huds[0].update(self.sim, 0, dt)
        if self.audio is not None:
            self.audio.update_engine(False, 0.0)
        if self.sim.state == "finished":
            self.end_timer += dt
            if self.end_timer >= 0.9:
                self._show_podium()

    # ------------------------------------------------------------------ events

    def _handle_events(self) -> None:
        if self.sim is None:
            return
        for event in self.sim.events:
            self._handle_event(event)

    def _handle_event(self, event: Any) -> None:
        if self.sim is None:
            return
        kind = event.kind
        if kind in ("go", "race_end"):
            if kind == "go":
                self.go_clear = 0.6
                self.last_count = 0
                if self.audio is not None:
                    self.audio.play("go", 0.5)
            return
        if event.kart < 0 or event.kart >= len(self.sim.karts):
            return
        kart = self.sim.karts[event.kart]
        point = self.track.point(kart.s, kart.t)
        position = (point[0], point[1], kart.air_z + 0.3)
        heading = self.track.heading(kart.s)
        forward = (-math.sin(heading), math.cos(heading))
        hud = self._hud_for_kart(kart.index)
        if kind == "pickup":
            if self.effects is not None:
                self.effects.burst("pickup", position, 12)
            self._play("pickup", 0.4)
            self._phone(kart, "pickup")
        elif kind in ("nitro", "mini_turbo"):
            if self.effects is not None:
                self.effects.burst("boost", position, 10, forward)
            self._play("boost" if kind == "nitro" else "mini_turbo", 0.4)
            self._shake(kart.index, 0.25)
            self._phone(kart, "boost")
        elif kind == "saw":
            if self.effects is not None:
                self.effects.burst("saw", position, 10, forward)
            self._play("saw", 0.4)
            self._shake(kart.index, 0.3)
            self._phone(kart, "hit")
        elif kind == "saw_push":
            if 0 <= event.other < len(self.sim.karts):
                other = self.sim.karts[event.other]
                other_point = self.track.point(other.s, other.t)
                if self.effects is not None:
                    self.effects.burst("hit", (other_point[0], other_point[1], other.air_z + 0.4), 8)
                self._shake(other.index, 0.2)
        elif kind in ("drop_oil", "throw_bomb", "throw_web"):
            self._play("bump", 0.2)
        elif kind == "shield":
            self._play("shield", 0.4)
            self._phone(kart, "pickup")
        elif kind == "shield_break":
            if self.effects is not None:
                self.effects.burst("hit", position, 12)
            self._play("shield", 0.35)
            self._shake(kart.index, 0.3)
        elif kind == "explosion":
            if self.effects is not None:
                self.effects.burst("explosion", position, 26)
                self.effects.flash(position, Vec4(1.0, 0.55, 0.12, 0.7), 2.2)
            self._play("explosion", 0.55)
            self._shake(kart.index, 0.75)
            self._phone(kart, "hit")
        elif kind == "hit_bomb":
            if self.effects is not None:
                self.effects.burst("hit", position, 14)
            self._play("hit", 0.5)
            self._shake(kart.index, 0.6)
            self._phone(kart, "hit")
        elif kind == "hit_oil":
            if self.effects is not None:
                self.effects.burst("dust", position, 10)
            self._play("oil", 0.4)
            self._shake(kart.index, 0.35)
            self._phone(kart, "hit")
        elif kind == "hit_web":
            if self.effects is not None:
                self.effects.burst("web", position, 12)
            self._play("web", 0.4)
            self._shake(kart.index, 0.35)
            self._phone(kart, "hit")
        elif kind == "wall":
            if self.effects is not None:
                self.effects.burst("dust", position, 6)
            self._play("wall", 0.35)
            self._shake(kart.index, 0.3)
        elif kind == "bump":
            if self.effects is not None:
                self.effects.burst("dust", position, 4)
            self._play("bump", 0.25)
            self._shake(kart.index, 0.15)
        elif kind == "jump":
            self._play("jump", 0.3)
        elif kind == "land":
            if self.effects is not None:
                self.effects.burst("dust", position, 8)
            self._play("land", 0.3)
            self._shake(kart.index, 0.2)
        elif kind == "lap":
            self._play("lap", 0.4)
            self._phone(kart, "lap")
            if hud is not None:
                hud.banner_message(f"VUELTA {kart.lap}/3", v(CREAM), 1.2)
        elif kind == "last_lap":
            self._play("last_lap", 0.45)
            self._phone(kart, "last_lap")
            if hud is not None:
                hud.banner_message("¡ÚLTIMA VUELTA!", v(GOLD), 2.0)
        elif kind == "finish":
            self._play("finish", 0.5)
            self._phone(kart, "finish")
            if hud is not None:
                hud.banner_message(f"¡META! {kart.position}/8", v(GOLD), 2.6)
                hud.set_status("ESPERANDO...")

    def _hud_for_kart(self, kart_index: int) -> PlayerHud | None:
        for index, player in enumerate(self.players):
            if player.kart_index == kart_index and index < len(self.huds):
                return self.huds[index]
        return None

    def _shake(self, kart_index: int, amount: float) -> None:
        for index, player in enumerate(self.players):
            if player.kart_index == kart_index and index < len(self.rigs):
                self.rigs[index].add_shake(amount)

    def _play(self, name: str, volume: float = 0.4) -> None:
        if self.audio is not None:
            self.audio.play(name, volume)

    def _phone(self, kart: Any, kind: str) -> None:
        if self.ctx is None or not kart.is_human or kart.slot is None or kart.slot > 3:
            return
        slot = kart.slot
        try:
            if kind == "pickup":
                self.ctx.phone.tone(880, 60, volume=0.28, slot=slot)
            elif kind == "boost":
                self.ctx.phone.vibrate([18, 24, 18], slot=slot)
            elif kind == "hit":
                self.ctx.phone.vibrate([45, 35, 45], slot=slot)
            elif kind == "lap":
                self.ctx.phone.tone(1046, 70, volume=0.25, slot=slot)
            elif kind == "last_lap":
                self.ctx.phone.tone(1318, 110, volume=0.3, slot=slot)
            elif kind == "finish":
                self.ctx.phone.vibrate([60, 50, 60, 50, 120], slot=slot)
        except Exception:
            pass

    # ------------------------------------------------------------------ finish

    def _finish(self) -> None:
        if self.sim is None:
            return
        if self.mode == "trial":
            self._show_trial_results()
        else:
            self._show_podium()

    def _show_podium(self) -> None:
        if self.sim is None or self.viewports is None or self.screens is None or self.track is None:
            return
        results = self.sim.results()
        if self.track is not None:
            for row in results:
                if row.get("time") is None:
                    kart = self.sim.karts[int(row["kart"])]
                    remaining = max(0.0, self.sim.laps_total * self.track.length - kart.s)
                    row["time"] = self.sim.race_time + remaining / max(kart.speed, 8.0)
                    row["estimated"] = True
        self.state = "podium"
        self.end_timer = 0.0
        self.viewports.set_count(1)
        self.viewports.set_hud_visible(False)
        self._destroy_race_ui()
        for model in self.models.values():
            model.set_visible(False)
            model.set_marker_visible(False)
        if self.world is not None:
            base = self.world.podium_point
            steps = ((0.0, 1.5), (4.2, 0.9), (-4.2, 0.6))
            for index, row in enumerate(results[:3]):
                kart_index = int(row["kart"])
                character = str(row["character"])
                model = self.models.get(character)
                if model is None:
                    continue
                offset, height = steps[index]
                model.root.set_pos(base[0] + offset, base[1], 0.45 + height)
                model.root.set_h(0.0)
                model.rest()
                model.set_visible(True)
                model.set_marker_visible(False)
                _ = kart_index
            if self.effects is not None:
                self.effects.burst("pickup", (base[0], base[1], 3.4), 30)
        self.screens.show_podium(results)
        position, look, fov = podium_pose(self.world, self.elapsed)
        self.viewports.apply_camera(0, position, look, fov)
        if self.audio is not None:
            self.audio.update_engine(False, 0.0)

    def _update_podium(self, dt: float) -> None:
        if self.viewports is None or self.screens is None:
            return
        for slot, inp in self._any_input():
            if inp.cross_edge:
                if self.attract:
                    self._start_attract()
                else:
                    self._start_race()
                return
            if inp.brake_edge:
                self.mirror = not self.mirror
                self._build_circuit(self.mirror)
                if self.attract:
                    self._start_attract()
                else:
                    self._start_race()
                return
            if inp.options_edge:
                self._enter_title()
                return
        assert self.world is not None
        position, look, fov = podium_pose(self.world, self.elapsed)
        self.viewports.apply_camera(0, position, look, fov)
        if self.effects is not None and self.sim is not None:
            self.effects.update(self.sim, dt, self.elapsed)

    def _show_trial_results(self) -> None:
        if self.sim is None or self.viewports is None or self.screens is None:
            return
        player = self.players[0] if self.players else None
        if player is None or player.kart_index < 0:
            return
        kart = self.sim.karts[player.kart_index]
        total = kart.finish_time
        best = kart.best_lap
        new_record = self.trial_record is None or total < self.trial_record
        if new_record:
            self.trial_record = total
        self.trial_new_record = new_record
        self.state = "results"
        self.viewports.set_count(1)
        self.viewports.set_hud_visible(False)
        self._destroy_race_ui()
        self.screens.show_results(total, best, self.trial_record, new_record=new_record)
        if self.rigs:
            rig = self.rigs[0]
            self.viewports.apply_camera(0, rig.position, rig.look, rig.fov)
        if self.audio is not None:
            self.audio.update_engine(False, 0.0)

    def _update_results(self, dt: float) -> None:
        if self.viewports is None:
            return
        for slot, inp in self._any_input():
            if inp.cross_edge:
                self._start_race()
                return
            if inp.options_edge:
                self._enter_title()
                return
        if self.rigs:
            rig = self.rigs[0]
            self.viewports.apply_camera(0, rig.position, rig.look, rig.fov)

    # ------------------------------------------------------------------ pause

    def _pause(self, owner_index: int) -> None:
        if self.sim is None or self.screens is None or self.viewports is None:
            return
        self.pause_owner = owner_index
        self.pause_selected = 0
        self.pause_nav = 0.0
        self.pause_adjust = 0.0
        self.state = "paused"
        self.viewports.set_hud_visible(False)
        if self.audio is not None:
            self.audio.update_engine(False, 0.0)
        owner = self.players[owner_index] if owner_index < len(self.players) else None
        label = owner.label if owner else "PAUSA"
        self.screens.show_pause(label, self._pause_rows(), self.pause_selected)

    def _pause_rows(self) -> list[str]:
        owner = self.players[self.pause_owner] if self.pause_owner < len(self.players) else None
        reader = self.readers.get(owner.slot) if owner else None
        sensitivity = reader.sensitivity.upper() if reader else "NORMAL"
        invert = "SÍ" if reader and reader.invert else "NO"
        sound = "NO" if self.audio and self.audio.muted else "SÍ"
        return [
            "REANUDAR",
            f"SENSIBILIDAD: {sensitivity}",
            f"INVERTIR VOLANTE: {invert}",
            "CENTRAR VOLANTES",
            f"SONIDO: {sound}",
            "REINICIAR",
            "VOLVER AL TÍTULO",
        ]

    def _update_paused(self, dt: float) -> None:
        if self.screens is None or self.sim is None:
            return
        owner = self.players[self.pause_owner] if self.pause_owner < len(self.players) else None
        inp = self.inputs.get(owner.slot) if owner else None
        if inp is None and (owner is None or owner.slot not in self.frames):
            inp = self.inputs.get(4)
        self.pause_nav = max(0.0, self.pause_nav - dt)
        self.pause_adjust = max(0.0, self.pause_adjust - dt)
        if inp is not None:
            if self.pause_nav <= 0.0:
                if inp.stick_y > 0.55:
                    self.pause_selected = (self.pause_selected - 1) % 7
                    self.pause_nav = 0.22
                elif inp.stick_y < -0.55:
                    self.pause_selected = (self.pause_selected + 1) % 7
                    self.pause_nav = 0.22
            if self.pause_adjust <= 0.0:
                if inp.stick_x > 0.55:
                    self._pause_adjust(1)
                    self.pause_adjust = 0.28
                elif inp.stick_x < -0.55:
                    self._pause_adjust(-1)
                    self.pause_adjust = 0.28
            if inp.options_edge:
                self._resume()
                return
            if inp.cross_edge:
                self._pause_activate()
                return
        label = owner.label if owner else "PAUSA"
        self.screens.show_pause(label, self._pause_rows(), self.pause_selected)
        if self.effects is not None:
            self.effects.update(self.sim, dt, self.elapsed)

    def _pause_adjust(self, direction: int) -> None:
        owner = self.players[self.pause_owner] if self.pause_owner < len(self.players) else None
        reader = self.readers.get(owner.slot) if owner else None
        if reader is None:
            return
        if self.pause_selected == 1:
            reader.cycle_sensitivity(direction)
        elif self.pause_selected == 2:
            reader.invert = not reader.invert
        elif self.pause_selected == 4 and self.audio is not None:
            self.audio.set_muted(not self.audio.muted)

    def _pause_activate(self) -> None:
        if self.sim is None or self.audio is None:
            return
        if self.pause_selected == 0:
            self._resume()
        elif self.pause_selected == 1:
            self._pause_adjust(1)
        elif self.pause_selected == 2:
            self._pause_adjust(1)
        elif self.pause_selected == 3:
            for player in self.players:
                frame = self.frames.get(player.slot)
                if frame is not None:
                    self.readers[player.slot].reset_motion()
                    if self.ctx is not None:
                        self.ctx.phone.recenter(player.slot)
            self.audio.play("pickup", 0.4)
        elif self.pause_selected == 4:
            self.audio.set_muted(not self.audio.muted)
        elif self.pause_selected == 5:
            self._start_race()
        elif self.pause_selected == 6:
            self._enter_title()

    def _resume(self) -> None:
        if self.sim is None or self.screens is None or self.viewports is None:
            return
        self.screens.hide_all()
        self.viewports.set_hud_visible(True)
        if self.sim.state == "countdown":
            self.state = "race"
            self.last_count = 4
            return
        self.state = "resuming"
        self.resume_timer = 2.6
        self.last_resume = 4
        if self.audio is not None:
            self.audio.play("countdown", 0.4)

    def _update_resuming(self, dt: float) -> None:
        if self.sim is None or self.viewports is None:
            return
        self.resume_timer = max(0.0, self.resume_timer - dt)
        if self.effects is not None:
            self.effects.update(self.sim, dt, self.elapsed)
        if self.resume_timer <= 0.0:
            self.state = "race"
            self.go_clear = 0.5
            if self.audio is not None:
                self.audio.play("go", 0.5)
            self._update_huds(dt)
            return
        if self.resume_timer > 0.6:
            value = int(math.ceil(self.resume_timer - 0.4))
            text = str(max(1, min(3, value)))
        else:
            text = "¡YA!"
        if self.audio is not None:
            value = int(math.ceil(self.resume_timer - 0.4))
            if value != self.last_resume and 1 <= value <= 3:
                self.audio.play("countdown", 0.4)
                self.last_resume = value
        self._update_huds(dt, countdown_override=text)

    # ------------------------------------------------------------------ helpers

    def _destroy_race_ui(self) -> None:
        for hud in self.huds:
            hud.destroy()
        self.huds = []
        if self.standings is not None:
            self.standings.destroy()
            self.standings = None
