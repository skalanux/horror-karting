"""Plantel de Horror Karting: stats, nombres y paleta.

Sin Panda3D: este módulo se usa tanto por la simulación como por la vista.
"""

from __future__ import annotations

from dataclasses import dataclass

RGB = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class Character:
    key: str
    name: str
    epithet: str
    speed: int
    accel: int
    grip: int
    item_bias: str
    body: RGB
    accent: RGB

    @property
    def label(self) -> str:
        if self.epithet:
            return f"{self.name} «{self.epithet}»"
        return self.name


CHARACTERS: tuple[Character, ...] = (
    Character(
        key="dracula",
        name="Drácula",
        epithet="",
        speed=4,
        accel=3,
        grip=4,
        item_bias="shield",
        body=(0.09, 0.02, 0.05),
        accent=(0.80, 0.07, 0.12),
    ),
    Character(
        key="frank",
        name="Frankenstein",
        epithet="",
        speed=3,
        accel=2,
        grip=5,
        item_bias="oil",
        body=(0.16, 0.33, 0.18),
        accent=(0.62, 0.88, 0.45),
    ),
    Character(
        key="mummy",
        name="La Momia",
        epithet="",
        speed=3,
        accel=4,
        grip=4,
        item_bias="web",
        body=(0.64, 0.53, 0.32),
        accent=(0.92, 0.78, 0.38),
    ),
    Character(
        key="wolf",
        name="Hombre Lobo",
        epithet="",
        speed=5,
        accel=4,
        grip=2,
        item_bias="nitro",
        body=(0.27, 0.17, 0.11),
        accent=(0.82, 0.68, 0.44),
    ),
    Character(
        key="phantom",
        name="Fantasma de la Ópera",
        epithet="",
        speed=3,
        accel=5,
        grip=3,
        item_bias="bomb",
        body=(0.21, 0.08, 0.28),
        accent=(0.96, 0.91, 0.86),
    ),
    Character(
        key="llorona",
        name="La Llorona",
        epithet="",
        speed=4,
        accel=4,
        grip=3,
        item_bias="shield",
        body=(0.09, 0.24, 0.28),
        accent=(0.58, 0.98, 0.92),
    ),
    Character(
        key="milei",
        name="Javier Milei",
        epithet="El Gatito Mimoso",
        speed=5,
        accel=3,
        grip=2,
        item_bias="motosierra",
        body=(0.10, 0.09, 0.08),
        accent=(0.97, 0.77, 0.16),
    ),
    Character(
        key="kuchisake",
        name="Kuchisake-onna",
        epithet="",
        speed=4,
        accel=3,
        grip=4,
        item_bias="web",
        body=(0.46, 0.05, 0.08),
        accent=(0.96, 0.91, 0.87),
    ),
)

BY_KEY: dict[str, Character] = {character.key: character for character in CHARACTERS}
KEYS: tuple[str, ...] = tuple(character.key for character in CHARACTERS)

ITEM_LABELS: dict[str, str] = {
    "nitro": "NITRO",
    "oil": "ACEITE",
    "bomb": "CALABAZA",
    "shield": "ATAÚD",
    "web": "TELARAÑA",
    "motosierra": "MOTOSIERRA",
}

ITEM_COLORS: dict[str, RGB] = {
    "nitro": (0.25, 0.95, 1.0),
    "oil": (0.16, 0.14, 0.10),
    "bomb": (1.0, 0.52, 0.10),
    "shield": (0.68, 0.88, 1.0),
    "web": (0.92, 0.92, 0.96),
    "motosierra": (1.0, 0.82, 0.2),
}
