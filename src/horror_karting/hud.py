"""HUD por jugador: posición, vuelta, ítem, velocidad, derrape y minimapa."""

from __future__ import annotations

from typing import Any

from direct.gui.OnscreenText import OnscreenText
from panda3d.core import CardMaker, LineSegs, NodePath, TextNode, Vec4

from .characters import BY_KEY, ITEM_COLORS, ITEM_LABELS
from .view import Viewport
from .palette import CREAM as _CREAM_RGB, CYAN as _CYAN_RGB, GOLD as _GOLD_RGB, SILVER as _SILVER_RGB, v

CREAM = v(_CREAM_RGB)
CYAN = v(_CYAN_RGB)
GOLD = v(_GOLD_RGB)
SILVER = v(_SILVER_RGB)

MUTED = Vec4(0.62, 0.66, 0.78, 1.0)


class PlayerHud:
    def __init__(self, build: Any, view: Viewport, track: Any, *, color: tuple[float, float, float], label: str) -> None:
        self.build = build
        self.view = view
        self.track = track
        self.color = Vec4(color[0], color[1], color[2], 1.0)
        self.root = view.ui_root
        self.aspect = view.aspect
        self.s = view.text_scale
        self.label = label
        self.banner_timer = 0.0
        self.banner_alpha = 1.0
        self.banner_color = GOLD
        self.dots: list[NodePath] = []
        self.minimap_box = (-self.aspect + 0.06, -self.aspect + 0.62, -0.99, -0.43)
        self._build()
        self._build_minimap()

    # ------------------------------------------------------------------ utils

    def _card(self, x0: float, x1: float, z0: float, z1: float, color: Vec4, sort: int = 90) -> NodePath:
        maker = CardMaker("hud-card")
        maker.set_frame(x0, x1, z0, z1)
        card = self.root.attach_new_node(maker.generate())
        card.set_color(color)
        card.set_transparency(1)
        card.set_bin("fixed", sort)
        card.set_depth_test(False)
        card.set_depth_write(False)
        card.set_light_off(1)
        return card

    def _text(self, pos: tuple[float, float], scale: float, color: Vec4, align: int = TextNode.ALeft, sort: int = 110) -> OnscreenText:
        text = OnscreenText(
            text="",
            parent=self.root,
            pos=pos,
            scale=scale,
            fg=color,
            align=align,
            mayChange=True,
            shadow=Vec4(0.0, 0.0, 0.0, 0.8),
        )
        text.set_bin("fixed", sort)
        text.set_depth_test(False)
        text.set_depth_write(False)
        return text

    # ------------------------------------------------------------------ build

    def _build(self) -> None:
        aspect = self.aspect
        s = self.s
        left = -aspect + 0.06
        right = aspect - 0.06
        self._card(left, left + 0.68, 0.75, 0.99, Vec4(0.02, 0.02, 0.05, 0.72))
        self._card(left, left + 0.035, 0.75, 0.99, self.color, sort=92)
        self.position_text = self._text((left + 0.08, 0.91), s, CREAM)
        self.lap_text = self._text((left + 0.08, 0.845), s * 0.68, GOLD)
        self.time_text = self._text((left + 0.08, 0.785), s * 0.52, MUTED)
        self.time_text.hide()

        self._card(right - 0.56, right, 0.82, 0.99, Vec4(0.02, 0.02, 0.05, 0.72))
        self.item_bar = self._card(right - 0.545, right - 0.02, 0.955, 0.985, Vec4(0.4, 0.4, 0.4, 0.9), sort=92)
        self.item_text = self._text((right - 0.04, 0.88), s * 0.62, CREAM, TextNode.ARight)

        self._card(right - 0.62, right, -0.99, -0.81, Vec4(0.02, 0.02, 0.05, 0.68))
        self.speed_text = self._text((right - 0.04, -0.875), s * 1.0, CREAM, TextNode.ARight)
        self.drift_bg = self._card(right - 0.58, right - 0.04, -0.965, -0.935, Vec4(0.18, 0.18, 0.24, 0.9), sort=92)
        self.drift_fill = self._card(0.0, 1.0, 0.0, 1.0, self.color, sort=93)
        self.drift_fill.hide()
        self.drift_text = self._text((right - 0.04, -0.91), s * 0.42, MUTED, TextNode.ARight)

        self._card(-0.70, 0.70, 0.22, 0.42, Vec4(0.02, 0.02, 0.05, 0.0), sort=90)
        self.banner = self._text((0.0, 0.31), s * 1.05, GOLD, TextNode.ACenter, 120)
        self.banner.hide()
        self.countdown = self._text((0.0, -0.02), s * 3.2, CREAM, TextNode.ACenter, 120)
        self.countdown.hide()
        self.status = self._text((0.0, -0.20), s * 0.9, CREAM, TextNode.ACenter, 120)
        self.status.hide()
        self.badge = self._text((0.0, 0.74), s * 0.62, CYAN, TextNode.ACenter, 120)
        self.badge.hide()
        self.lap_time = 0.0

    def _build_minimap(self) -> None:
        x0, x1, z0, z1 = self.minimap_box
        self._card(x0, x1, z0, z1, Vec4(0.02, 0.02, 0.05, 0.65))
        self._card(x0, x1, z1 - 0.018, z1, Vec4(0.22, 0.22, 0.30, 0.9), sort=91)
        points = []
        samples = self.track.samples
        step = max(1, len(samples) // 120)
        xs = [sample.pos[0] for sample in samples]
        ys = [sample.pos[1] for sample in samples]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span = max(max_x - min_x, max_y - min_y, 1.0)
        pad = 0.09
        for sample in samples[::step]:
            nx = x0 + pad + (sample.pos[0] - min_x) / span * (x1 - x0 - pad * 2)
            nz = z0 + pad + (sample.pos[1] - min_y) / span * (z1 - z0 - pad * 2)
            points.append((nx, nz))
        segs = LineSegs("minimap")
        segs.set_color(Vec4(0.55, 0.58, 0.70, 0.85))
        segs.set_thickness(1.6)
        if points:
            segs.move_to(points[0][0], 0, points[0][1])
            for x, z in points[1:]:
                segs.draw_to(x, 0, z)
            segs.draw_to(points[0][0], 0, points[0][1])
        line = self.root.attach_new_node(segs.create())
        line.set_light_off(1)
        line.set_depth_test(False)
        line.set_bin("fixed", 94)
        self.map_x0, self.map_x1 = x0 + pad, x1 - pad
        self.map_z0, self.map_z1 = z0 + pad, z1 - pad
        self.map_min_x, self.map_min_y, self.map_span = min_x, min_y, span
        marker = CardMaker("start-marker")
        marker.set_frame(-0.012, 0.012, -0.012, 0.012)
        start = self.root.attach_new_node(marker.generate())
        sx, sz = self._map_point(self.track.point(0)[0], self.track.point(0)[1])
        start.set_pos(sx, 0, sz)
        start.set_color(CREAM)
        start.set_bin("fixed", 97)
        start.set_depth_test(False)
        self.dots = []
        for _ in range(8):
            maker = CardMaker("dot")
            maker.set_frame(-0.016, 0.016, -0.016, 0.016)
            dot = self.root.attach_new_node(maker.generate())
            dot.set_bin("fixed", 98)
            dot.set_depth_test(False)
            dot.set_color(SILVER)
            self.dots.append(dot)

    def _map_point(self, x: float, y: float) -> tuple[float, float]:
        nx = self.map_x0 + (x - self.map_min_x) / self.map_span * (self.map_x1 - self.map_x0)
        nz = self.map_z0 + (y - self.map_min_y) / self.map_span * (self.map_z1 - self.map_z0)
        return nx, nz

    # ------------------------------------------------------------------ frame

    def banner_message(self, text: str, color: Vec4 = GOLD, duration: float = 1.8) -> None:
        self.banner.setText(text)
        self.banner.setFg(color)
        self.banner_color = color
        self.banner.show()
        self.banner_timer = duration
        self.banner_alpha = 1.0

    def set_countdown(self, text: str | None, color: Vec4 = CREAM) -> None:
        if text is None:
            self.countdown.hide()
        else:
            self.countdown.setText(text)
            self.countdown.setFg(color)
            self.countdown.show()

    def set_status(self, text: str | None, color: Vec4 = CREAM) -> None:
        if text is None:
            self.status.hide()
        else:
            self.status.setText(text)
            self.status.setFg(color)
            self.status.show()

    def set_badge(self, text: str | None) -> None:
        if text is None:
            self.badge.hide()
        else:
            self.badge.setText(text)
            self.badge.show()

    def update(self, sim: Any, kart_index: int, dt: float, *, time_trial: bool = False) -> None:
        if kart_index >= len(sim.karts):
            return
        kart = sim.karts[kart_index]
        self.position_text.setText(f"{self.label} | {kart.position}/8")
        if time_trial:
            self.lap_text.setText(f"VUELTA {kart.lap}/3")
            best = kart.best_lap
            self.time_text.show()
            self.time_text.setText(
                f"MEJOR {_fmt(best)}" if best > 0.0 else "MEJOR —"
            )
        else:
            self.lap_text.setText(f"VUELTA {kart.lap}/3")
            self.time_text.hide()
        item = kart.item
        if item:
            color = ITEM_COLORS.get(item, (0.8, 0.8, 0.8))
            self.item_bar.set_color(Vec4(color[0], color[1], color[2], 0.95))
            self.item_text.setText(ITEM_LABELS.get(item, item.upper()))
        else:
            self.item_bar.set_color(Vec4(0.22, 0.22, 0.28, 0.9))
            self.item_text.setText("SIN ÍTEM")
        self.speed_text.setText(f"{int(kart.speed_kmh)} KM/H")
        if kart.drift > 0.05 and kart.charge > 0.1:
            ratio = min(1.0, kart.charge / 2.0)
            x0 = self.view.aspect - 0.58
            width = max(0.01, 0.54 * ratio)
            self.drift_fill.show()
            self.drift_fill.set_pos(x0, 0, -0.965)
            self.drift_fill.set_scale(width, 1.0, 0.03)
            color = GOLD if kart.charge > 1.0 else CYAN
            self.drift_fill.set_color(color)
            self.drift_text.setText("DERRAPE")
        else:
            self.drift_fill.hide()
            self.drift_text.setText("")
        if kart.ai_controlled and kart.is_human:
            self.set_badge("IA | RECONECTANDO")
        else:
            self.badge.hide()
        self._update_dots(sim, kart_index)
        if self.banner_timer > 0.0:
            self.banner_timer -= dt
            self.banner_alpha = min(1.0, max(0.0, self.banner_timer / 0.45))
            color = self.banner_color
            self.banner.setFg(Vec4(color[0], color[1], color[2], self.banner_alpha))
            if self.banner_timer <= 0.0:
                self.banner.hide()

    def _update_dots(self, sim: Any, kart_index: int) -> None:
        for index, kart in enumerate(sim.karts[:8]):
            dot = self.dots[index]
            point = self.track.point(kart.s, kart.t)
            mx, mz = self._map_point(point[0], point[1])
            dot.set_pos(mx, 0, mz)
            if index == kart_index:
                dot.set_scale(1.55)
                dot.set_color(CREAM)
            else:
                dot.set_scale(1.0)
                character = BY_KEY[kart.character]
                if kart.is_human:
                    dot.set_color(Vec4(kart.color[0], kart.color[1], kart.color[2], 1.0))
                else:
                    dot.set_color(Vec4(character.accent[0], character.accent[1], character.accent[2], 0.9))
            dot.show()

    def destroy(self) -> None:
        for text in (
            getattr(self, "position_text", None),
            getattr(self, "lap_text", None),
            getattr(self, "time_text", None),
            getattr(self, "item_text", None),
            getattr(self, "speed_text", None),
            getattr(self, "drift_text", None),
            getattr(self, "banner", None),
            getattr(self, "countdown", None),
            getattr(self, "status", None),
            getattr(self, "badge", None),
        ):
            if text is not None:
                text.remove_node()
        for dot in self.dots:
            dot.remove_node()
        self.dots.clear()


def _fmt(seconds: float) -> str:
    if seconds <= 0.0:
        return "—"
    minutes = int(seconds // 60)
    rest = seconds - minutes * 60
    return f"{minutes}:{rest:05.2f}" if minutes else f"{rest:.2f}s"


class StandingsPanel:
    """Tabla compartida para el cuadrante libre del modo 3 jugadores."""

    def __init__(self, ui: NodePath, sim: Any) -> None:
        self.root = ui.attach_new_node("standings")
        maker = CardMaker("standings-card")
        maker.set_frame(0.92, 1.72, -0.98, -0.30)
        card = self.root.attach_new_node(maker.generate())
        card.set_color(Vec4(0.02, 0.02, 0.05, 0.78))
        card.set_transparency(1)
        card.set_bin("fixed", 60)
        card.set_depth_test(False)
        title = OnscreenText(text="POSICIONES", parent=self.root, pos=(1.32, -0.36), scale=0.045, fg=GOLD, align=TextNode.ACenter, mayChange=True)
        title.set_bin("fixed", 61)
        title.set_depth_test(False)
        self.rows: list[OnscreenText] = []
        for index in range(8):
            row = OnscreenText(
                text="",
                parent=self.root,
                pos=(0.98, -0.44 - index * 0.065),
                scale=0.034,
                fg=CREAM,
                align=TextNode.ALeft,
                mayChange=True,
            )
            row.set_bin("fixed", 61)
            row.set_depth_test(False)
            self.rows.append(row)

    def update(self, sim: Any) -> None:
        for index, kart in enumerate(sorted(sim.karts, key=lambda item: item.position)[:8]):
            character = BY_KEY[kart.character]
            name = character.name if not kart.is_human else kart.player_name
            self.rows[index].setText(f"{kart.position}. {name}"[:18])
            color = kart.color if kart.is_human else character.accent
            self.rows[index].setFg(Vec4(color[0], color[1], color[2], 1.0))

    def destroy(self) -> None:
        for row in self.rows:
            row.remove_node()
        self.root.remove_node()
