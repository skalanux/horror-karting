"""Pantallas 2D compartidas: título, selección, pausa, podio y contrarreloj."""

from __future__ import annotations

from typing import Any

from direct.gui.OnscreenText import OnscreenText
from panda3d.core import CardMaker, NodePath, TextNode, Vec4

from .characters import BY_KEY, ITEM_LABELS, KEYS
from .palette import BLOOD as _BLOOD_RGB, CREAM as _CREAM_RGB, CYAN as _CYAN_RGB, GOLD as _GOLD_RGB, SILVER as _SILVER_RGB, v

BLOOD = v(_BLOOD_RGB)
CREAM = v(_CREAM_RGB)
CYAN = v(_CYAN_RGB)
GOLD = v(_GOLD_RGB)
SILVER = v(_SILVER_RGB)

MUTED = Vec4(0.62, 0.66, 0.78, 1.0)
INK_CARD = Vec4(0.015, 0.015, 0.035, 0.78)
INK_CARD_SOLID = Vec4(0.015, 0.015, 0.035, 0.93)
CONTROLS = "X ELEGIR   T AL AZAR   STICK IZQ/DER   OPT VOLVER"


class Screens:
    def __init__(self, ui: NodePath) -> None:
        self.ui = ui
        self.title = ui.attach_new_node("screen-title")
        self.select = ui.attach_new_node("screen-select")
        self.pause = ui.attach_new_node("screen-pause")
        self.podium = ui.attach_new_node("screen-podium")
        self.results = ui.attach_new_node("screen-results")
        for root in (self.select, self.pause, self.podium, self.results):
            root.hide()
        self._build_title()
        self._build_select()
        self._build_pause()
        self._build_podium()
        self._build_results()

    # ------------------------------------------------------------------ utils

    def _card(self, root: NodePath, x0: float, x1: float, z0: float, z1: float, color: Vec4, sort: int = 50) -> NodePath:
        maker = CardMaker("card")
        maker.set_frame(x0, x1, z0, z1)
        card = root.attach_new_node(maker.generate())
        card.set_color(color)
        card.set_transparency(1)
        card.set_bin("fixed", sort)
        card.set_depth_test(False)
        card.set_depth_write(False)
        card.set_light_off(1)
        return card

    def _text(self, root: NodePath, value: str, pos: tuple[float, float], scale: float, color: Vec4 = CREAM, align: int = TextNode.ACenter, sort: int = 60) -> OnscreenText:
        text = OnscreenText(
            text=value,
            parent=root,
            pos=pos,
            scale=scale,
            fg=color,
            align=align,
            mayChange=True,
            shadow=Vec4(0.0, 0.0, 0.0, 0.85),
        )
        text.set_bin("fixed", sort)
        text.set_depth_test(False)
        text.set_depth_write(False)
        return text

    # ------------------------------------------------------------------ title

    def _build_title(self) -> None:
        root = self.title
        self._card(root, -1.78, 1.78, -1.0, -0.30, Vec4(0.01, 0.01, 0.025, 0.55), sort=40)
        self.title_horror = self._text(root, "HORROR", (0, 0.70), 0.24, CREAM)
        self.title_karting = self._text(root, "KARTING", (0, 0.49), 0.20, BLOOD)
        self.title_sub = self._text(root, "CEMENTERIO DEL PUEBLO", (0, 0.30), 0.062, GOLD)
        self.title_join = self._text(root, "X  SUMATE", (0, 0.14), 0.082, CREAM)
        self.title_start = self._text(root, "OPT  LARGAR", (0, 0.03), 0.062, GOLD)
        self.title_trial = self._text(root, "T  CONTRARRELOJ", (0, -0.06), 0.058, CYAN)
        self.title_diff = self._text(root, "DIFICULTAD: NORMAL", (0, -0.15), 0.05, MUTED)
        self.title_slots: list[tuple[NodePath, OnscreenText, OnscreenText]] = []
        for index in range(4):
            x = -1.23 + index * 0.82
            border = self._card(root, x - 0.31, x + 0.31, -0.72, -0.37, Vec4(0.28, 0.28, 0.35, 0.75), sort=46)
            name = self._text(root, f"P{index + 1}", (x, -0.47), 0.055, MUTED, sort=61)
            state = self._text(root, "—", (x, -0.60), 0.042, MUTED, sort=61)
            self.title_slots.append((border, name, state))
        self.title_footer = self._text(root, "GIRÁ EL TELÉFONO COMO VOLANTE | HTTP: STICK", (0, -0.87), 0.036, MUTED)

    def show_title(self, players: list[tuple[int, tuple[float, float, float]]], difficulty: str, *, trial: bool = False) -> None:
        self.hide_all()
        self.title.show()
        for index, (border, name, state) in enumerate(self.title_slots):
            player = next((item for item in players if item[0] == index), None)
            if player:
                rgb = player[1]
                border.set_color(Vec4(rgb[0], rgb[1], rgb[2], 0.9))
                name.setFg(Vec4(rgb[0], rgb[1], rgb[2], 1.0))
                state.setText("LISTO")
                state.setFg(CREAM)
            else:
                border.set_color(Vec4(0.24, 0.24, 0.30, 0.65))
                name.setFg(MUTED)
                state.setText("-")
                state.setFg(MUTED)
        from .palette import DIFFICULTY_LABELS

        self.title_diff.setText(f"DIFICULTAD: {DIFFICULTY_LABELS.get(difficulty, 'NORMAL')}")
        self.title_join.setText("X  SUMATE")
        self.title_start.setText("OPT  LARGAR")
        self.title_trial.setText("T  CONTRARRELOJ")

    # ---------------------------------------------------------------- select

    def _build_select(self) -> None:
        root = self.select
        self._card(root, 0.18, 1.78, -1.0, 1.0, Vec4(0.01, 0.01, 0.03, 0.88), sort=48)
        self._card(root, 0.18, 0.22, -1.0, 1.0, Vec4(0.55, 0.04, 0.07, 0.75), sort=49)
        self.select_player = self._text(root, "JUGADOR 1", (0.28, 0.88), 0.072, CREAM, TextNode.ALeft)
        self.select_name = self._text(root, "", (0.28, 0.68), 0.13, GOLD, TextNode.ALeft)
        self.select_epithet = self._text(root, "", (0.28, 0.56), 0.052, MUTED, TextNode.ALeft)
        self.select_stats: list[tuple[OnscreenText, list[NodePath]]] = []
        for index, label in enumerate(("VELOCIDAD", "ACELERACIÓN", "AGARRE")):
            z = 0.40 - index * 0.15
            text = self._text(root, label, (0.28, z), 0.043, CREAM, TextNode.ALeft)
            bars: list[NodePath] = []
            for segment in range(5):
                x = 0.90 + segment * 0.105
                bar = self._card(root, x, x + 0.085, z - 0.018, z + 0.018, Vec4(0.2, 0.2, 0.26, 0.9), sort=50)
                bars.append(bar)
            self.select_stats.append((text, bars))
        self.select_item = self._text(root, "", (0.28, -0.09), 0.046, CYAN, TextNode.ALeft)
        self.select_help = self._text(root, CONTROLS, (0.28, -0.22), 0.038, MUTED, TextNode.ALeft)
        self.select_chips: list[tuple[NodePath, NodePath]] = []
        for index in range(8):
            x = 0.30 + index * 0.185
            chip = self._card(root, x - 0.07, x + 0.07, -0.46, -0.36, Vec4(0.3, 0.3, 0.35, 0.8), sort=52)
            inner = self._card(root, x - 0.055, x + 0.055, -0.445, -0.375, Vec4(0.2, 0.2, 0.25, 0.9), sort=53)
            self.select_chips.append((chip, inner))
        self.select_footer = self._text(root, "STICK IZQ/DER ELEGIR | X CONFIRMAR | T AL AZAR", (0.28, -0.62), 0.038, MUTED, TextNode.ALeft)
        self.select_player_line = self._text(root, "", (0.28, -0.90), 0.036, CREAM, TextNode.ALeft)

    def show_select(self, player_index: int, color: tuple[float, float, float], choice: str, taken: set[str], label: str) -> None:
        self.hide_all()
        self.select.show()
        character = BY_KEY[choice]
        rgb = Vec4(color[0], color[1], color[2], 1.0)
        self.select_player.setText(label.upper())
        self.select_player.setFg(rgb)
        self.select_name.setText(character.name)
        self.select_epithet.setText(character.epithet.upper() if character.epithet else "")
        values = (character.speed, character.accel, character.grip)
        for (text, bars), value in zip(self.select_stats, values, strict=True):
            for index, bar in enumerate(bars):
                if index < value:
                    bar.set_color(rgb)
                else:
                    bar.set_color(Vec4(0.20, 0.20, 0.26, 0.9))
        self.select_item.setText(f"ÍTEM FAVORITO: {ITEM_LABELS.get(character.item_bias, character.item_bias.upper())}")
        for index, (key, (chip, inner)) in enumerate(zip(KEYS, self.select_chips, strict=False)):
            character_chip = BY_KEY[key]
            accent = character_chip.accent
            if key in taken:
                chip.set_color(Vec4(0.15, 0.15, 0.18, 0.7))
                inner.set_color(Vec4(0.08, 0.08, 0.10, 0.9))
            else:
                chip.set_color(Vec4(accent[0], accent[1], accent[2], 0.8))
                inner.set_color(Vec4(accent[0] * 0.7, accent[1] * 0.7, accent[2] * 0.7, 0.9))
            if key == choice:
                chip.set_color(CREAM)
                inner.set_color(rgb)
        self.select_player_line.setText(f"{label} ELIGE | {sum(1 for key in KEYS if key in taken)} TOMADOS")

    # ----------------------------------------------------------------- pause

    def _build_pause(self) -> None:
        root = self.pause
        self._card(root, -1.78, 1.78, -1.0, 1.0, Vec4(0.0, 0.0, 0.0, 0.55), sort=70)
        self._card(root, -0.82, 0.82, -0.86, 0.86, INK_CARD_SOLID, sort=71)
        self._card(root, -0.82, -0.78, -0.86, 0.86, Vec4(0.55, 0.04, 0.07, 0.85), sort=72)
        self.pause_title = self._text(root, "PAUSA", (0, 0.71), 0.12, CREAM, sort=80)
        self.pause_owner = self._text(root, "", (0, 0.60), 0.045, MUTED, sort=80)
        self.pause_highlight = self._card(root, 0.0, 1.0, 0.0, 1.0, Vec4(0.55, 0.08, 0.10, 0.35), sort=73)
        self.pause_rows: list[OnscreenText] = []
        for index in range(7):
            z = 0.42 - index * 0.15
            row = self._text(root, "", (0, z), 0.056, CREAM, sort=80)
            self.pause_rows.append(row)
        self.pause_footer = self._text(root, "STICK ARRIBA/ABAJO ELEGIR | IZQ/DER CAMBIAR | X ACEPTAR | OPT REANUDAR", (0, -0.76), 0.034, MUTED, sort=80)

    def show_pause(self, owner: str, rows: list[str], selected: int) -> None:
        self.hide_all()
        self.pause.show()
        self.pause_owner.setText(owner)
        for index, row in enumerate(self.pause_rows):
            if index < len(rows):
                row.setText(rows[index])
                row.show()
            else:
                row.hide()
        z = 0.42 - selected * 0.15
        self.pause_highlight.set_pos(-0.70, 0, z - 0.055)
        self.pause_highlight.set_scale(1.40, 1.0, 0.11)

    # ----------------------------------------------------------------- podium

    def _build_podium(self) -> None:
        root = self.podium
        self._card(root, 0.62, 1.78, -1.0, 1.0, Vec4(0.01, 0.01, 0.03, 0.86), sort=70)
        self._card(root, 0.62, 0.66, -1.0, 1.0, Vec4(0.98, 0.78, 0.25, 0.8), sort=71)
        self.podium_title = self._text(root, "PODIO", (1.20, 0.86), 0.10, GOLD, sort=80)
        self.podium_winner = self._text(root, "", (1.20, 0.72), 0.052, CREAM, sort=80)
        self._text(root, "PILOTO", (0.68, 0.60), 0.034, MUTED, TextNode.ALeft, sort=80)
        self._text(root, "TIEMPO", (1.38, 0.60), 0.034, MUTED, TextNode.ARight, sort=80)
        self._text(root, "MEJOR", (1.72, 0.60), 0.034, MUTED, TextNode.ARight, sort=80)
        self.podium_rows: list[tuple[OnscreenText, OnscreenText, OnscreenText]] = []
        for index in range(8):
            z = 0.51 - index * 0.088
            name = self._text(root, "", (0.68, z), 0.036, CREAM, TextNode.ALeft, sort=80)
            time_text = self._text(root, "", (1.38, z), 0.036, CREAM, TextNode.ARight, sort=80)
            best_text = self._text(root, "", (1.72, z), 0.036, CREAM, TextNode.ARight, sort=80)
            self.podium_rows.append((name, time_text, best_text))
        self.podium_help = self._text(root, "X REVANCHA   CUAD ESPEJADA   OPT TÍTULO", (1.20, -0.90), 0.034, MUTED, sort=80)

    def show_podium(self, results: list[dict[str, object]]) -> None:
        self.hide_all()
        self.podium.show()
        if results:
            winner = results[0]
            self.podium_winner.setText(f"GANADOR: {winner['name']}")
        colors = (GOLD, SILVER, Vec4(0.78, 0.42, 0.22, 1.0))
        for index, row in enumerate(self.podium_rows):
            name_text, time_text, best_text = row
            if index >= len(results):
                name_text.hide()
                time_text.hide()
                best_text.hide()
                continue
            data = results[index]
            time = data.get("time")
            best = data.get("best_lap") or 0.0
            name = str(data.get("name", ""))
            player = str(data.get("player", ""))
            label = name if not data.get("human") else f"{name} ({player})"
            name_text.setText(f"{index + 1}. {label[:18]}")
            time_text.setText(('~' if data.get('estimated') else '') + _fmt(time))
            best_text.setText(_fmt(best))
            color = colors[index] if index < 3 else CREAM
            name_text.setFg(color)
            time_text.setFg(color)
            best_text.setFg(color)
            name_text.show()
            time_text.show()
            best_text.show()

    # ---------------------------------------------------------------- results

    def _build_results(self) -> None:
        root = self.results
        self._card(root, -1.78, 1.78, -0.95, 0.95, Vec4(0.0, 0.0, 0.0, 0.45), sort=70)
        self._card(root, -0.80, 0.80, -0.62, 0.62, INK_CARD_SOLID, sort=71)
        self._card(root, -0.80, -0.76, -0.62, 0.62, Vec4(0.45, 0.95, 1.0, 0.8), sort=72)
        self.results_title = self._text(root, "CONTRARRELOJ", (0, 0.45), 0.095, CYAN, sort=80)
        self.results_total = self._text(root, "", (0, 0.23), 0.072, CREAM, sort=80)
        self.results_best = self._text(root, "", (0, 0.08), 0.058, GOLD, sort=80)
        self.results_record = self._text(root, "", (0, -0.09), 0.052, CYAN, sort=80)
        self.results_help = self._text(root, "X REINTENTAR    OPT TÍTULO", (0, -0.44), 0.042, MUTED, sort=80)

    def show_results(self, total: float, best: float, record: float | None, *, new_record: bool = False) -> None:
        self.hide_all()
        self.results.show()
        self.results_total.setText(f"TIEMPO TOTAL  {_fmt(total)}")
        self.results_best.setText(f"MEJOR VUELTA  {_fmt(best)}")
        if record and record > 0.0:
            self.results_record.setText(
                ("¡NUEVO RÉCORD DE SESIÓN!  " if new_record else "RÉCORD DE SESIÓN: ") + _fmt(record)
            )
        else:
            self.results_record.setText("SIN RÉCORD PREVIO")

    # ------------------------------------------------------------------ misc

    def hide_all(self) -> None:
        for root in (self.title, self.select, self.pause, self.podium, self.results):
            root.hide()

    def destroy(self) -> None:
        for root in (self.title, self.select, self.pause, self.podium, self.results):
            root.remove_node()


def _fmt(seconds: Any) -> str:
    try:
        value = float(seconds)
    except (TypeError, ValueError):
        return "—"
    if value <= 0.0:
        return "—"
    minutes = int(value // 60)
    rest = value - minutes * 60
    return f"{minutes}:{rest:05.2f}" if minutes else f"{rest:.2f}s"
