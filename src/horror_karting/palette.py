"""Paleta de Horror Karting."""

from __future__ import annotations

from panda3d.core import Vec4

RGB = tuple[float, float, float]


def v(rgb: RGB, alpha: float = 1.0) -> Vec4:
    return Vec4(rgb[0], rgb[1], rgb[2], alpha)


SKY_ZENITH: RGB = (0.030, 0.020, 0.080)
SKY_MID: RGB = (0.100, 0.050, 0.200)
SKY_HORIZON: RGB = (0.320, 0.105, 0.220)
SKY_GLOW: RGB = (0.980, 0.420, 0.130)
FOG: RGB = (0.160, 0.120, 0.220)
MOON: RGB = (0.980, 0.945, 0.830)
STAR: RGB = (0.880, 0.910, 1.000)
GROUND: RGB = (0.095, 0.105, 0.135)
GRASS: RGB = (0.135, 0.190, 0.175)
GRASS_2: RGB = (0.175, 0.235, 0.210)
ROAD: RGB = (0.215, 0.210, 0.275)
ROAD_2: RGB = (0.250, 0.245, 0.320)
ROAD_3: RGB = (0.195, 0.190, 0.255)
EDGE: RGB = (0.820, 0.740, 0.540)
STONE: RGB = (0.420, 0.405, 0.465)
STONE_DARK: RGB = (0.265, 0.255, 0.310)
STONE_LIGHT: RGB = (0.585, 0.560, 0.605)
WALL: RGB = (0.360, 0.355, 0.415)
LANTERN: RGB = (1.000, 0.740, 0.320)
PUMPKIN: RGB = (0.920, 0.400, 0.080)
PUMPKIN_LIGHT: RGB = (1.000, 0.620, 0.160)
STEM: RGB = (0.160, 0.260, 0.090)
TREE: RGB = (0.115, 0.085, 0.140)
TREE_2: RGB = (0.145, 0.115, 0.170)
FIREFLY: RGB = (0.650, 1.000, 0.350)
BLOOD: RGB = (0.680, 0.040, 0.070)
CYAN: RGB = (0.450, 0.950, 1.000)
GOLD: RGB = (0.980, 0.780, 0.250)
CREAM: RGB = (0.950, 0.930, 0.880)
SILVER: RGB = (0.750, 0.780, 0.820)
INK: RGB = (0.020, 0.020, 0.030)
WOOD: RGB = (0.460, 0.305, 0.200)
WOOD_2: RGB = (0.330, 0.220, 0.150)
WATER: RGB = (0.060, 0.300, 0.350)
MIST: RGB = (0.240, 0.520, 0.430)
BONE: RGB = (0.870, 0.840, 0.760)

PLAYER_COLORS: tuple[RGB, ...] = (
    (0.950, 0.250, 0.250),
    (0.300, 0.800, 1.000),
    (0.450, 1.000, 0.400),
    (1.000, 0.820, 0.250),
)

DIFFICULTY_LABELS = {"facil": "FÁCIL", "normal": "NORMAL", "dificil": "DIFÍCIL"}
DIFFICULTY_ORDER = ("facil", "normal", "dificil")
