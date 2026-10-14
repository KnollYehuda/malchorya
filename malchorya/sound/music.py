"""Procedural music: composes and orchestrates looping tracks and short stingers."""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np

from sound import synth as S

CHORDS = {"M": [0, 4, 7], "m": [0, 3, 7], "sus2": [0, 2, 7], "5": [0, 7], "dim": [0, 3, 6], "M7": [0, 4, 7, 11], "m7": [0, 3, 7, 10]}
SCALES = {
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "major": [0, 2, 4, 5, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
}
RHYTHMS = {
    "epic": [[3, 1, 2, 2], [2, 2, 4], [1.5, 0.5, 2, 4], [4, 2, 2]],
    "gentle": [[2, 1, 1, 4], [3, 1, 4], [1, 1, 2, 4]],
    "lively": [[1, 0.5, 0.5, 1, 1, 0.5, 0.5, 1, 1, 1], [0.5, 0.5, 1, 0.5, 0.5, 1, 1, 1, 1, 1], [1, 1, 0.5, 0.5, 1, 1, 1, 1, 1]],
    "jig": [[0.5] * 16, [0.5, 0.5, 1, 0.5, 0.5, 1, 0.5, 0.5, 1, 0.5, 0.5, 1]],
    "sparse": [[4, 4], [2, 6], [3, 5]],
}


@dataclass
class Track:
    name: str
    bpm: float
    bars: int
    root: int
    scale: str
    progression: List[Tuple[int, str]]
    layers: Dict[str, dict]
    seed: int = 1
    reverb_seconds: float = 2.8
    reverb_wet: float = 0.35
    beats: int = 4


def _fold(note: int, low: int, high: int) -> int:
    while note < low:
        note += 12
    while note > high:
        note -= 12
    return note


def _scale_notes(tonic: int, scale: str, low: int, high: int) -> List[int]:
    return sorted(note for octave in range(-2, 9) for degree in SCALES[scale] if low <= (note := tonic % 12 + 12 * octave + degree) <= high)


def _staccato(freq: float, duration: float, rng: np.random.Generator) -> np.ndarray:
    t = S.time_axis(duration)
    tone = S.harmonic_stack(freq, t, S.saw_amplitudes(18, 0.95), rng.uniform(0, S.TWO_PI))
    tone += S.harmonic_stack(freq * 1.006, t, S.saw_amplitudes(14, 1.0), rng.uniform(0, S.TWO_PI))
    return tone * 0.5 * S.adsr(len(t), 0.004, 0.05, 0.45, 0.05)


def render_track(track: Track, bars: int = None) -> np.ndarray:
    """Returns a mastered stereo float array, shaped (2, samples), that loops seamlessly."""
    rng = np.random.default_rng(track.seed)
    bars = bars or track.bars
    beat = 60.0 / track.bpm
    bar_length = beat * track.beats
    total = int(round(bars * bar_length * S.SR))
    mix = np.zeros((2, total))
    layers = track.layers

    def start_of(bar: int, beat_offset: float = 0.0) -> int:
        return int(round((bar * bar_length + beat_offset * beat) * S.SR))

    def chord_at(bar: int) -> Tuple[int, str]:
        offset, kind = track.progression[bar % len(track.progression)]
        return track.root + offset, kind

    def chord_pitches(bar: int) -> List[int]:
        root, kind = chord_at(bar)
        return [root + interval for interval in CHORDS[kind]]

    # ---- pad: sustained strings
    if "pad" in layers:
        spec = layers["pad"]
        span = spec.get("span", 1)
        for bar in range(0, bars, span):
            pitches = chord_pitches(bar)
            voicing = sorted({_fold(p, 55, 72) for p in pitches} | {_fold(pitches[0], 43, 55) + 12})
            for index, midi in enumerate(voicing):
                note = S.strings(S.midi_freq(midi), bar_length * span + 0.8, rng, spec.get("brightness", 14))
                if spec.get("tremolo"):
                    note = note * (0.65 + 0.35 * np.sin(S.TWO_PI * spec["tremolo"] * np.arange(len(note)) / S.SR))
                S.place(mix, note, start_of(bar), pan=-0.5 + index * (1.0 / max(1, len(voicing) - 1)), gain=spec["gain"] / len(voicing) ** 0.5)

    # ---- choir
    if "choir" in layers:
        spec = layers["choir"]
        span = spec.get("span", 2)
        vowels = spec.get("vowels", ["ah", "oh"])
        for index, bar in enumerate(range(0, bars, span)):
            pitches = chord_pitches(bar)
            voicing = [_fold(pitches[0], 52, 62), _fold(pitches[-1], 60, 70), _fold(pitches[0] + 12, 67, 79)]
            for voice, midi in enumerate(voicing):
                note = S.choir(S.midi_freq(midi), bar_length * span + 1.0, rng, vowels[(index + voice) % len(vowels)])
                S.place(mix, note, start_of(bar), pan=-0.6 + voice * 0.6, gain=spec["gain"] / 3 ** 0.5)

    # ---- bass
    if "bass" in layers:
        spec = layers["bass"]
        style = spec.get("style", "half")
        for bar in range(bars):
            root = _fold(chord_at(bar)[0], 33, 46)
            if style == "half":
                for beat_offset in (0, 2):
                    S.place(mix, S.cello(S.midi_freq(root), beat * 1.9, rng), start_of(bar, beat_offset), 0, spec["gain"])
            elif style == "eighths":
                for step in range(8):
                    midi = root + (12 if step % 4 == 3 else 0)
                    S.place(mix, S.cello(S.midi_freq(midi), beat * 0.45, rng), start_of(bar, step * 0.5), 0, spec["gain"] * (1.0 if step % 2 == 0 else 0.7))
            elif style == "pluck":
                for beat_offset, interval in ((0, 0), (1.5, 7), (2, 0), (3.5, 7)):
                    S.place(mix, S.lute(S.midi_freq(root + 12 + interval - (12 if interval else 0)), beat * 1.2, rng), start_of(bar, beat_offset), 0, spec["gain"])
            elif style == "pedal":
                S.place(mix, S.sub_drone(S.midi_freq(root - 12 if root > 40 else root), bar_length + 0.6, rng), start_of(bar), 0, spec["gain"])

    if "drone" in layers:
        spec = layers["drone"]
        for bar in range(0, bars, 2):
            root = _fold(track.root, 24, 36)
            S.place(mix, S.sub_drone(S.midi_freq(root), bar_length * 2 + 1.0, rng), start_of(bar), 0, spec["gain"])
            S.place(mix, S.sub_drone(S.midi_freq(root + 7), bar_length * 2 + 1.0, rng), start_of(bar), 0, spec["gain"] * 0.4)

    # ---- arpeggio
    if "arp" in layers:
        spec = layers["arp"]
        instrument = {"harp": S.harp, "lute": S.lute}[spec.get("inst", "harp")]
        subdivision = spec.get("subdiv", 0.5)
        for bar in range(bars):
            pitches = chord_pitches(bar)
            pool = sorted({_fold(p + 12 * k, spec.get("low", 60), spec.get("high", 84)) for p in pitches for k in (0, 1)})
            steps = int(track.beats / subdivision)
            order = list(range(len(pool))) + list(range(len(pool) - 2, 0, -1)) if spec.get("pattern", "updown") == "updown" else list(range(len(pool)))
            for step in range(steps):
                if rng.random() < spec.get("skip", 0.0):
                    continue
                midi = pool[order[step % len(order)]]
                S.place(mix, instrument(S.midi_freq(midi), beat * 2.0, rng), start_of(bar, step * subdivision), pan=-0.4 + 0.8 * ((step % 4) / 3), gain=spec["gain"] * rng.uniform(0.7, 1.0))

    # ---- lead melody
    if "lead" in layers:
        spec = layers["lead"]
        instrument = {"brass": lambda f, d, r: S.brass(f, d, r, 1.0), "flute": S.flute, "fiddle": S.fiddle, "bell": S.bell, "harp": S.harp}[spec["inst"]]
        low, high = spec.get("range", (62, 80))
        notes = _scale_notes(track.root, track.scale, low, high)
        rhythm_options = RHYTHMS[spec.get("rhythm", "epic")]
        phrases: Dict[str, Tuple[list, list]] = {}
        for index, bar in enumerate(range(0, bars, 2)):
            label = "AABA"[index % 4]
            if label not in phrases:
                rhythm = list(rhythm_options[rng.integers(len(rhythm_options))])
                moves = [int(rng.choice([-2, -1, -1, 1, 1, 2, 3, -3, 0])) for _ in rhythm]
                phrases[label] = (rhythm, moves)
            rhythm, moves = phrases[label]
            chord_tones = {p % 12 for p in chord_pitches(bar)}
            current = min(range(len(notes)), key=lambda i: abs(notes[i] - (low + high) / 2 + (3 if label == "B" else 0)) + (0 if notes[i] % 12 in chord_tones else 6))
            cursor = 0.0
            for duration, move in zip(rhythm, moves):
                if cursor >= track.beats * 2:
                    break
                current = max(0, min(len(notes) - 1, current + move))
                on_strong = abs(cursor % 2) < 1e-6
                if on_strong and notes[current] % 12 not in chord_tones:
                    candidates = [i for i in range(max(0, current - 2), min(len(notes), current + 3)) if notes[i] % 12 in chord_tones]
                    if candidates:
                        current = min(candidates, key=lambda i: abs(i - current))
                if rng.random() >= spec.get("rest", 0.0):
                    S.place(mix, instrument(S.midi_freq(notes[current]), max(0.15, duration * beat * 0.98), rng), start_of(bar, cursor), pan=0.15, gain=spec["gain"])
                cursor += duration

    # ---- ostinato and stabs (combat)
    if "ostinato" in layers:
        spec = layers["ostinato"]
        for bar in range(bars):
            root = _fold(chord_at(bar)[0], 45, 57)
            for step in range(16):
                midi = root + (7 if step % 8 in (3, 6) else 0) + (12 if step % 8 == 7 else 0)
                accent = 1.0 if step % 4 == 0 else 0.65
                note = _staccato(S.midi_freq(midi), beat * 0.22, rng)
                S.place(mix, note, start_of(bar, step * 0.25), pan=-0.3 + 0.6 * (step % 2), gain=spec["gain"] * accent)
    if "stabs" in layers:
        spec = layers["stabs"]
        for bar in range(bars):
            pitches = chord_pitches(bar)
            for beat_offset in spec["beats"]:
                for midi in (_fold(pitches[0], 50, 58), _fold(pitches[1], 58, 66), _fold(pitches[2], 62, 74)):
                    S.place(mix, S.brass(S.midi_freq(midi), beat * 0.4, rng, 1.2), start_of(bar, beat_offset), 0, spec["gain"] / 3 ** 0.5)

    # ---- bells
    if "bells" in layers:
        spec = layers["bells"]
        for bar in range(bars):
            if rng.random() < spec.get("prob", 0.5):
                pitches = chord_pitches(bar)
                midi = _fold(pitches[int(rng.integers(len(pitches)))] + (1 if spec.get("detune") else 0), 76, 96)
                S.place(mix, S.bell(S.midi_freq(midi), 4.0, rng), start_of(bar, float(rng.choice([0, 0, 1, 2]))), pan=float(rng.uniform(-0.7, 0.7)), gain=spec["gain"])

    # ---- drums
    if "drums" in layers:
        spec = layers["drums"]
        style, power = spec["style"], spec["gain"]
        for bar in range(bars):
            fill = bar % 4 == 3
            if style == "taiko":
                S.place(mix, S.taiko(rng, 1.0), start_of(bar, 0), 0, power)
                S.place(mix, S.taiko(rng, 0.7), start_of(bar, 2), 0, power)
                if fill:
                    for step, level in ((3, 0.7), (3.5, 0.8), (3.75, 0.9)):
                        S.place(mix, S.taiko(rng, level, 0.5), start_of(bar, step), 0, power)
                for step in range(8):
                    S.place(mix, S.shaker(rng, 0.35), start_of(bar, step * 0.5), 0.3, power * 0.35)
            elif style == "war":
                for step in range(8):
                    S.place(mix, S.taiko(rng, 1.0 if step % 4 == 0 else 0.6, 0.5), start_of(bar, step * 0.5), 0, power * (1.0 if step % 2 == 0 else 0.7))
                S.place(mix, S.snare(rng, 0.8), start_of(bar, 1), 0.1, power * 0.7)
                S.place(mix, S.snare(rng, 0.8), start_of(bar, 3), -0.1, power * 0.7)
                for step in range(16):
                    S.place(mix, S.hat(rng, 0.7), start_of(bar, step * 0.25), 0.4, power * 0.3)
                if fill:
                    for step in range(4):
                        S.place(mix, S.snare(rng, 0.7 + step * 0.1), start_of(bar, 3 + step * 0.25), 0, power * 0.8)
            elif style == "frame":
                S.place(mix, S.taiko(rng, 0.45, 0.6), start_of(bar, 0), 0, power)
                S.place(mix, S.taiko(rng, 0.3, 0.5), start_of(bar, 2.5), 0, power)
                for step in range(4):
                    S.place(mix, S.shaker(rng, 0.4), start_of(bar, step), 0.3, power * 0.4)
            elif style == "light":
                S.place(mix, S.taiko(rng, 0.4, 0.5), start_of(bar, 0), 0, power)
                for step in range(8):
                    S.place(mix, S.shaker(rng, 0.5 if step % 2 == 0 else 0.3), start_of(bar, step * 0.5), 0.4, power * 0.5)
                S.place(mix, S.hat(rng, 0.5), start_of(bar, 1), 0.3, power * 0.4)
                S.place(mix, S.hat(rng, 0.5), start_of(bar, 3), 0.3, power * 0.4)
            elif style == "jig":
                for beat_offset in (0, 2):
                    S.place(mix, S.stomp(rng, 1.0), start_of(bar, beat_offset), 0, power)
                for beat_offset in (1, 3):
                    S.place(mix, S.snare(rng, 0.45), start_of(bar, beat_offset), 0.2, power * 0.6)
                for step in range(8):
                    S.place(mix, S.shaker(rng, 0.6), start_of(bar, step * 0.5 + 0.25), 0.4, power * 0.5)
            elif style == "sparse":
                if bar % 2 == 0:
                    S.place(mix, S.taiko(rng, 1.0, 1.4), start_of(bar, 0), 0, power)
                if bar % 4 == 3:
                    S.place(mix, S.taiko(rng, 0.7, 1.0), start_of(bar, 3), 0, power * 0.8)

    if layers.get("swell"):
        S.place(mix, S.cymbal_swell(rng, bar_length, 1.0), start_of(bars - 1), 0, layers["swell"]["gain"])
        S.place(mix, S.cymbal_crash(rng, 0.9), 0, 0, layers["swell"]["gain"])

    mix = S.reverb(mix, rng, track.reverb_seconds, track.reverb_wet)
    return S.master(mix, 0.11)


TRACKS: Dict[str, Track] = {
    "overworld": Track(
        "overworld", bpm=96, bars=16, root=50, scale="minor", seed=11, reverb_seconds=3.2, reverb_wet=0.4,
        progression=[(0, "m"), (-4, "M"), (3, "M"), (-2, "M"), (0, "m"), (-4, "M"), (5, "m"), (7, "M")],
        layers={
            "pad": {"gain": 0.55},
            "choir": {"gain": 0.45, "span": 2},
            "bass": {"style": "half", "gain": 0.7},
            "drone": {"gain": 0.22},
            "arp": {"inst": "harp", "subdiv": 0.5, "gain": 0.2, "skip": 0.12},
            "lead": {"inst": "brass", "gain": 0.5, "range": (62, 79), "rhythm": "epic"},
            "drums": {"style": "taiko", "gain": 0.85},
            "bells": {"gain": 0.14, "prob": 0.5},
            "swell": {"gain": 0.35},
        },
    ),
    "forest": Track(
        "forest", bpm=68, bars=8, root=52, scale="dorian", seed=21, reverb_seconds=3.6, reverb_wet=0.5,
        progression=[(0, "m"), (5, "M"), (-2, "M"), (0, "m"), (0, "m"), (5, "M"), (-2, "M"), (7, "m")],
        layers={
            "pad": {"gain": 0.4, "brightness": 8},
            "drone": {"gain": 0.3},
            "arp": {"inst": "harp", "subdiv": 1.0, "gain": 0.22, "skip": 0.25, "low": 64, "high": 88},
            "lead": {"inst": "flute", "gain": 0.55, "range": (64, 84), "rhythm": "gentle", "rest": 0.3},
            "drums": {"style": "frame", "gain": 0.4},
            "bells": {"gain": 0.12, "prob": 0.4},
        },
    ),
    "town": Track(
        "town", bpm=112, bars=16, root=55, scale="mixolydian", seed=31, reverb_seconds=1.6, reverb_wet=0.22,
        progression=[(0, "M"), (5, "M"), (7, "M"), (0, "M"), (0, "M"), (-3, "m"), (5, "M"), (7, "M")],
        layers={
            "pad": {"gain": 0.2, "brightness": 6},
            "bass": {"style": "pluck", "gain": 0.6},
            "arp": {"inst": "lute", "subdiv": 0.5, "gain": 0.4, "skip": 0.1, "low": 62, "high": 84},
            "lead": {"inst": "flute", "gain": 0.5, "range": (67, 86), "rhythm": "lively", "rest": 0.1},
            "drums": {"style": "light", "gain": 0.5},
        },
    ),
    "tavern": Track(
        "tavern", bpm=128, bars=16, root=57, scale="dorian", seed=41, reverb_seconds=1.2, reverb_wet=0.18,
        progression=[(0, "m"), (-2, "M"), (0, "m"), (-2, "M"), (0, "m"), (-2, "M"), (5, "M"), (7, "m")],
        layers={
            "bass": {"style": "pluck", "gain": 0.65},
            "arp": {"inst": "lute", "subdiv": 1.0, "gain": 0.3, "low": 57, "high": 76},
            "lead": {"inst": "fiddle", "gain": 0.6, "range": (69, 88), "rhythm": "jig", "rest": 0.05},
            "drums": {"style": "jig", "gain": 0.65},
        },
    ),
    "sacred": Track(
        "sacred", bpm=58, bars=8, root=48, scale="lydian", seed=51, reverb_seconds=5.0, reverb_wet=0.6,
        progression=[(0, "M"), (7, "M"), (-3, "m"), (5, "M"), (0, "M"), (7, "M"), (-3, "m"), (5, "M")],
        layers={
            "choir": {"gain": 0.85, "span": 1, "vowels": ["ah", "oh", "oo"]},
            "pad": {"gain": 0.35, "brightness": 6, "span": 2},
            "bells": {"gain": 0.3, "prob": 0.85},
            "arp": {"inst": "harp", "subdiv": 2.0, "gain": 0.15, "low": 64, "high": 88},
            "drone": {"gain": 0.25},
        },
    ),
    "dark": Track(
        "dark", bpm=60, bars=8, root=47, scale="phrygian", seed=61, reverb_seconds=4.5, reverb_wet=0.55,
        progression=[(0, "5"), (1, "M"), (0, "m"), (-2, "M"), (0, "5"), (1, "M"), (0, "m"), (3, "dim")],
        layers={
            "drone": {"gain": 0.6},
            "pad": {"gain": 0.45, "brightness": 10, "tremolo": 7.5},
            "choir": {"gain": 0.3, "span": 2, "vowels": ["oo", "oh"]},
            "bells": {"gain": 0.25, "prob": 0.6, "detune": True},
            "drums": {"style": "sparse", "gain": 0.7},
            "swell": {"gain": 0.25},
        },
    ),
    "night": Track(
        "night", bpm=54, bars=8, root=45, scale="minor", seed=71, reverb_seconds=4.2, reverb_wet=0.55,
        progression=[(0, "m"), (-4, "M"), (3, "M"), (-2, "M"), (0, "m"), (-4, "M"), (3, "M"), (-2, "M")],
        layers={
            "pad": {"gain": 0.4, "brightness": 7},
            "drone": {"gain": 0.3},
            "arp": {"inst": "harp", "subdiv": 1.0, "gain": 0.3, "low": 69, "high": 93, "skip": 0.2},
            "lead": {"inst": "flute", "gain": 0.3, "range": (69, 84), "rhythm": "sparse", "rest": 0.4},
            "bells": {"gain": 0.18, "prob": 0.5},
        },
    ),
    "combat": Track(
        "combat", bpm=146, bars=16, root=50, scale="harmonic_minor", seed=81, reverb_seconds=2.0, reverb_wet=0.28,
        progression=[(0, "m"), (0, "m"), (-4, "M"), (-4, "M"), (0, "m"), (0, "m"), (-2, "M"), (7, "M")],
        layers={
            "ostinato": {"gain": 0.34},
            "stabs": {"gain": 0.7, "beats": [0, 1.5, 3]},
            "choir": {"gain": 0.45, "span": 2, "vowels": ["ah", "oh"]},
            "bass": {"style": "eighths", "gain": 0.7},
            "lead": {"inst": "brass", "gain": 0.4, "range": (62, 81), "rhythm": "epic", "rest": 0.1},
            "drums": {"style": "war", "gain": 1.0},
            "swell": {"gain": 0.4},
        },
    ),
}


# ----------------------------------------------------------------- stingers


def _note_sequence(spec: List[Tuple[float, float, float, str]], tail: float = 3.0, seed: int = 5, wet: float = 0.35) -> np.ndarray:
    """spec: (start_seconds, midi, duration_seconds, instrument)."""
    rng = np.random.default_rng(seed)
    total = int((max(start + duration for start, _, duration, _ in spec) + tail) * S.SR)
    mix = np.zeros((2, total))
    instruments = {
        "brass": lambda f, d, r: S.brass(f, d, r, 1.3),
        "strings": S.strings,
        "choir": S.choir,
        "harp": S.harp,
        "bell": S.bell,
        "cello": S.cello,
    }
    for start, midi, duration, name in spec:
        S.place(mix, instruments[name](S.midi_freq(midi), duration, rng), int(start * S.SR), 0, 0.6)
    return mix, rng


def stinger_level_up() -> np.ndarray:
    spec = [(0.0 + i * 0.11, m, 1.2, "harp") for i, m in enumerate([62, 66, 69, 74, 78, 81, 86])]
    spec += [(0.0, 50, 2.6, "strings"), (0.0, 62, 2.6, "choir"), (0.55, 74, 2.6, "choir"), (0.8, 86, 3.0, "bell"), (0.8, 90, 3.0, "bell")]
    mix, rng = _note_sequence(spec)
    return S.master(S.reverb(mix, rng, 3.0, 0.4), 0.12)


def stinger_victory() -> np.ndarray:
    spec = [(0.0, 62, 0.5, "brass"), (0.0, 50, 0.5, "cello"), (0.5, 66, 0.5, "brass"), (1.0, 69, 0.5, "brass"), (1.5, 74, 1.9, "brass"),
            (1.5, 62, 1.9, "strings"), (1.5, 66, 1.9, "strings"), (1.5, 69, 1.9, "strings"), (1.5, 50, 1.9, "cello"), (1.6, 78, 2.5, "choir")]
    mix, rng = _note_sequence(spec, tail=3.5)
    S.place(mix, S.taiko(rng, 1.0, 1.2), 0, 0, 0.9)
    S.place(mix, S.taiko(rng, 1.0, 1.4), int(1.5 * S.SR), 0, 1.0)
    S.place(mix, S.cymbal_crash(rng, 0.8), int(1.5 * S.SR), 0, 0.6)
    return S.master(S.reverb(mix, rng, 3.0, 0.4), 0.13)


def stinger_quest_start() -> np.ndarray:
    spec = [(0.0, 57, 0.9, "brass"), (0.9, 64, 1.6, "brass"), (0.9, 57, 1.6, "strings"), (0.9, 61, 1.6, "strings"), (1.6, 76, 2.0, "bell"), (1.0, 69, 2.2, "choir")]
    mix, rng = _note_sequence(spec, tail=3.0)
    S.place(mix, S.taiko(rng, 0.9, 1.2), 0, 0, 0.7)
    return S.master(S.reverb(mix, rng, 3.0, 0.4), 0.12)


def stinger_quest_complete() -> np.ndarray:
    spec = [(0.0, 62, 0.45, "brass"), (0.45, 66, 0.45, "brass"), (0.9, 69, 0.45, "brass"), (1.35, 74, 0.45, "brass"),
            (1.8, 78, 2.6, "brass"), (1.8, 62, 2.6, "strings"), (1.8, 66, 2.6, "strings"), (1.8, 69, 2.6, "strings"), (1.8, 50, 2.6, "cello"),
            (1.9, 74, 3.0, "choir"), (2.0, 81, 3.0, "choir"), (2.2, 90, 3.0, "bell"), (2.6, 93, 3.0, "bell")]
    spec += [(0.1 + i * 0.1, m, 1.2, "harp") for i, m in enumerate([74, 78, 81, 86, 90])]
    mix, rng = _note_sequence(spec, tail=3.5)
    S.place(mix, S.taiko(rng, 1.0, 1.4), int(1.8 * S.SR), 0, 1.0)
    S.place(mix, S.cymbal_crash(rng, 0.9), int(1.8 * S.SR), 0, 0.7)
    return S.master(S.reverb(mix, rng, 3.4, 0.42), 0.13)


def stinger_defeat() -> np.ndarray:
    spec = [(0.0, 50, 1.4, "brass"), (1.2, 49, 1.4, "brass"), (2.4, 46, 3.2, "brass"), (2.4, 34, 3.4, "cello"), (0.0, 38, 6.0, "strings"), (2.4, 58, 3.2, "choir")]
    mix, rng = _note_sequence(spec, tail=3.5)
    for start, power in ((0.0, 1.0), (1.2, 0.9), (2.4, 1.0)):
        S.place(mix, S.taiko(rng, power, 1.6), int(start * S.SR), 0, 1.0)
    return S.master(S.reverb(mix, rng, 4.0, 0.5), 0.12)


STINGERS = {
    "level_up": stinger_level_up,
    "victory": stinger_victory,
    "quest_start": stinger_quest_start,
    "quest_complete": stinger_quest_complete,
    "defeat": stinger_defeat,
}
