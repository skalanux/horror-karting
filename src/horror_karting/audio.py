"""Audio procedural: música, motor y efectos generados a WAV al iniciar."""

from __future__ import annotations

import math
import random
import shutil
import struct
import tempfile
import wave
from pathlib import Path
from typing import Any

RATE = 22050
TAU = math.tau


def _write(path: Path, samples: list[float]) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        frames = bytearray()
        for value in samples:
            clipped = max(-1.0, min(1.0, value))
            frames += struct.pack("<h", int(clipped * 32767))
        handle.writeframes(bytes(frames))


def _env(index: int, total: int, attack: float = 0.01, release: float = 0.08) -> float:
    t = index / RATE
    duration = total / RATE
    if t < attack:
        return t / attack
    if t > duration - release:
        return max(0.0, (duration - t) / release)
    return 1.0


def _add(buffer: list[float], start: int, data: list[float], gain: float = 1.0) -> None:
    for index, value in enumerate(data):
        position = start + index
        if 0 <= position < len(buffer):
            buffer[position] += value * gain


def _sine(freq: float, duration: float, volume: float = 0.3, vibrato: float = 0.0) -> list[float]:
    count = max(1, int(duration * RATE))
    result = []
    phase = 0.0
    for index in range(count):
        t = index / RATE
        mod = 1.0 + math.sin(TAU * 5.0 * t) * vibrato if vibrato else 1.0
        phase += TAU * freq * mod / RATE
        result.append(math.sin(phase) * volume * _env(index, count))
    return result


def _square(freq: float, duration: float, volume: float = 0.2) -> list[float]:
    count = max(1, int(duration * RATE))
    result = []
    phase = 0.0
    for index in range(count):
        phase += freq / RATE
        value = 1.0 if phase % 1.0 < 0.5 else -1.0
        result.append(value * volume * _env(index, count, 0.004, 0.05))
    return result


def _noise(duration: float, volume: float = 0.2, rng: random.Random | None = None) -> list[float]:
    generator = rng or random.Random(4)
    count = max(1, int(duration * RATE))
    return [generator.uniform(-1.0, 1.0) * volume * _env(index, count, 0.002, 0.04) for index in range(count)]


def _sweep(f0: float, f1: float, duration: float, volume: float = 0.25, noise: float = 0.0) -> list[float]:
    count = max(1, int(duration * RATE))
    result = []
    phase = 0.0
    generator = random.Random(9)
    for index in range(count):
        t = index / count
        freq = f0 + (f1 - f0) * t
        phase += TAU * freq / RATE
        value = math.sin(phase) * volume
        if noise:
            value += generator.uniform(-1.0, 1.0) * noise * (1.0 - t)
        result.append(value * _env(index, count, 0.005, 0.08))
    return result


def _bell(freq: float, duration: float, volume: float = 0.3) -> list[float]:
    count = max(1, int(duration * RATE))
    result = []
    for index in range(count):
        t = index / RATE
        decay = math.exp(-t * 4.2)
        value = math.sin(TAU * freq * t) * 0.7 + math.sin(TAU * freq * 2.01 * t) * 0.2 + math.sin(TAU * freq * 3.02 * t) * 0.1
        result.append(value * volume * decay)
    return result


class AudioManager:
    def __init__(self, base: Any) -> None:
        self.base = base
        self.dir = Path(tempfile.mkdtemp(prefix="hk-audio-"))
        self.sounds: dict[str, Any] = {}
        self.music: Any = None
        self.engine_sound: Any = None
        self.muted = False
        self.music_playing = False
        self.engine_on = False
        self._generate()
        self._load()

    # ------------------------------------------------------------------ build

    def _generate(self) -> None:
        beat = 60.0 / 132.0
        bars = 8
        total = int(beat * 4 * bars * RATE)
        music = [0.0] * total
        bass_notes = (55.0, 55.0, 43.65, 43.65, 49.0, 49.0, 41.2, 41.2)
        for index in range(16):
            freq = bass_notes[index % len(bass_notes)]
            note = _square(freq, beat * 2.0, 0.18)
            _add(music, int(index * beat * 2.0 * RATE), note)
        lead_notes = (440.0, 523.25, 659.25, 587.33, 523.25, 493.88, 440.0, 392.0, 440.0, 523.25, 698.46, 659.25, 587.33, 523.25, 493.88, 440.0)
        for index in range(16):
            freq = lead_notes[index % len(lead_notes)]
            note = _sine(freq, beat * 1.8, 0.10, vibrato=0.012)
            _add(music, int(index * beat * 2.0 * RATE), note)
        for bar in range(bars):
            start = int(bar * beat * 4 * RATE)
            _add(music, start, _bell(880.0, 1.4, 0.06), 0.7)
            for beat_index in (0, 2):
                _add(music, start + int(beat_index * beat * RATE), _sweep(110.0, 45.0, 0.16, 0.30), 0.8)
            for beat_index in (1, 3):
                _add(music, start + int(beat_index * beat * RATE), _noise(0.12, 0.10), 0.8)
            for eighth in range(8):
                _add(music, start + int(eighth * beat * 0.5 * RATE), _noise(0.025, 0.035), 0.7)
        peak = max(1e-6, max(abs(value) for value in music))
        scale = 0.72 / peak
        music = [value * scale for value in music]
        _write(self.dir / "music.wav", music)

        engine_len = int(0.5 * RATE)
        engine = []
        for index in range(engine_len):
            t = index / RATE
            modulation = 0.7 + 0.3 * math.sin(TAU * 12.0 * t)
            value = (
                math.sin(TAU * 56.0 * t) * 0.45
                + math.sin(TAU * 112.0 * t) * 0.22
                + math.sin(TAU * 168.0 * t) * 0.10
            )
            engine.append(value * modulation * 0.5)
        _write(self.dir / "engine.wav", engine)

        effects = {
            "boost": _sweep(220.0, 1200.0, 0.35, 0.30, noise=0.05),
            "pickup": _bell(1046.5, 0.28, 0.30),
            "hit": [a + b for a, b in zip(_sweep(160.0, 60.0, 0.3, 0.35), _noise(0.3, 0.12), strict=False)],
            "explosion": [a + b for a, b in zip(_sweep(120.0, 35.0, 0.5, 0.4), _noise(0.5, 0.25), strict=False)],
            "oil": _sweep(520.0, 110.0, 0.35, 0.22, noise=0.04),
            "web": _sweep(1500.0, 500.0, 0.22, 0.18, noise=0.12),
            "shield": [a + b for a, b in zip(_bell(1318.5, 0.5, 0.3), _bell(1975.5, 0.5, 0.18), strict=False)],
            "saw": _square(82.0, 0.35, 0.28),
            "countdown": _sine(660.0, 0.12, 0.28),
            "go": _sine(990.0, 0.35, 0.32),
            "lap": _bell(1318.5, 0.45, 0.28),
            "last_lap": [a + b for a, b in zip(_bell(1568.0, 0.6, 0.3), _bell(2093.0, 0.6, 0.15), strict=False)],
            "finish": _bell(1046.5, 0.9, 0.35),
            "wall": _sweep(90.0, 50.0, 0.18, 0.28, noise=0.15),
            "bump": _sweep(140.0, 80.0, 0.12, 0.2, noise=0.08),
            "mini_turbo": _sweep(300.0, 900.0, 0.28, 0.22, noise=0.04),
            "jump": _sweep(300.0, 700.0, 0.22, 0.18, noise=0.05),
            "land": _sweep(100.0, 45.0, 0.18, 0.25, noise=0.12),
        }
        for name, data in effects.items():
            _write(self.dir / f"{name}.wav", data)

    def _load(self) -> None:
        loader = self.base.loader
        try:
            self.music = loader.loadSfx(str(self.dir / "music.wav"))
            self.music.setLoop(True)
            self.music.setVolume(0.28)
        except Exception:
            self.music = None
        try:
            self.engine_sound = loader.loadSfx(str(self.dir / "engine.wav"))
            self.engine_sound.setLoop(True)
            self.engine_sound.setVolume(0.0)
        except Exception:
            self.engine_sound = None
        for path in self.dir.glob("*.wav"):
            name = path.stem
            if name in ("music", "engine"):
                continue
            try:
                self.sounds[name] = loader.loadSfx(str(path))
            except Exception:
                continue

    # ------------------------------------------------------------------ play

    def start_music(self) -> None:
        if self.muted or self.music is None:
            return
        try:
            self.music.play()
            self.music_playing = True
        except Exception:
            self.music_playing = False

    def play(self, name: str, volume: float = 0.5, rate: float = 1.0) -> None:
        if self.muted:
            return
        sound = self.sounds.get(name)
        if sound is None:
            return
        try:
            sound.setVolume(volume)
            sound.setPlayRate(rate)
            sound.play()
        except Exception:
            return

    def update_engine(self, active: bool, speed_ratio: float) -> None:
        if self.engine_sound is None:
            return
        if self.muted:
            active = False
        if active:
            try:
                if not self.engine_on:
                    self.engine_sound.play()
                    self.engine_on = True
                self.engine_sound.setPlayRate(0.72 + min(1.0, max(0.0, speed_ratio)) * 0.9)
                self.engine_sound.setVolume(0.16)
            except Exception:
                self.engine_on = False
        elif self.engine_on:
            try:
                self.engine_sound.stop()
            except Exception:
                pass
            self.engine_on = False

    def set_muted(self, value: bool) -> None:
        self.muted = value
        if value:
            try:
                if self.music is not None:
                    self.music.stop()
                if self.engine_sound is not None:
                    self.engine_sound.stop()
            except Exception:
                pass
            self.music_playing = False
            self.engine_on = False
        else:
            self.start_music()

    def destroy(self) -> None:
        try:
            if self.music is not None:
                self.music.stop()
            if self.engine_sound is not None:
                self.engine_sound.stop()
            for sound in self.sounds.values():
                try:
                    sound.stop()
                except Exception:
                    pass
        except Exception:
            pass
        shutil.rmtree(self.dir, ignore_errors=True)
