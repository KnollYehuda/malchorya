"""Sound effects (one-shots) and seamless ambience loops, all synthesized."""
from typing import Callable, Dict, List

import numpy as np

from sound import synth as S

AMBIENCE_SECONDS = 16.0


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def _finish(mono: np.ndarray, peak: float = 0.8) -> np.ndarray:
    mono = mono - np.mean(mono)
    mono = mono / (np.max(np.abs(mono)) + 1e-9) * peak
    fade = min(len(mono) // 20, 400)
    mono[-fade:] *= np.linspace(1, 0, fade)
    return np.vstack([mono, mono])


# ----------------------------------------------------------------- footsteps


def footstep(kind: str, seed: int) -> np.ndarray:
    rng = _rng(seed + hash(kind) % 1000)
    t = S.time_axis(0.16)
    n = len(t)
    if kind == "grass":
        body = S.fft_filter(S.noise(rng, n), 250, 2600) * np.exp(-t * 38)
        body += 0.5 * np.sin(S.TWO_PI * 95 * t) * np.exp(-t * 50)
    elif kind == "dirt":
        body = S.fft_filter(S.noise(rng, n), 500, 4200) * np.exp(-t * 52)
        body += 0.6 * np.sin(S.TWO_PI * 110 * t) * np.exp(-t * 60)
    elif kind == "stone":
        body = S.fft_filter(S.noise(rng, n), 1500, 7000) * np.exp(-t * 80)
        body += 0.5 * np.sin(S.TWO_PI * (1700 + rng.uniform(-200, 200)) * t) * np.exp(-t * 140)
        body += 0.4 * np.sin(S.TWO_PI * 130 * t) * np.exp(-t * 60)
    elif kind == "wood":
        body = np.sin(S.TWO_PI * (135 + rng.uniform(-15, 15)) * t) * np.exp(-t * 34)
        body += S.fft_filter(S.noise(rng, n), 400, 1800) * np.exp(-t * 45) * 0.6
        if rng.random() < 0.25:
            body += 0.15 * np.sin(S.TWO_PI * (380 + 600 * t) * t) * np.exp(-t * 20)
    else:  # mud / marsh
        body = S.fft_filter(S.noise(rng, n), 120, 900) * np.exp(-t * 22)
        body += 0.5 * np.sin(S.TWO_PI * (180 - 700 * t) * t) * np.exp(-t * 28)
    body *= np.minimum(1, t / 0.003)
    return _finish(body, 0.45)


def sword_swing(seed: int = 0) -> np.ndarray:
    rng = _rng(100 + seed)
    t = S.time_axis(0.42)
    n = len(t)
    source = S.noise(rng, n)
    low = S.fft_filter(source, 300, 1400)
    mid = S.fft_filter(source, 1200, 4000)
    high = S.fft_filter(source, 3500, 9000)
    progress = t / t[-1]
    sweep = low * np.exp(-((progress - 0.25) / 0.2) ** 2) + mid * np.exp(-((progress - 0.5) / 0.18) ** 2) + high * np.exp(-((progress - 0.72) / 0.15) ** 2)
    envelope = np.sin(np.pi * np.clip(progress, 0, 1)) ** 1.5
    metal = 0.08 * np.sin(S.TWO_PI * (900 + 1800 * progress) * t) * envelope
    return _finish(sweep * envelope + metal, 0.75)


def hit(kind: str, seed: int) -> np.ndarray:
    rng = _rng(200 + seed)
    t = S.time_axis(0.4)
    n = len(t)
    thump = np.sin(S.TWO_PI * np.cumsum(55 + 120 * np.exp(-t * 35)) / S.SR) * np.exp(-t * 14)
    slap = S.fft_filter(S.noise(rng, n), 300, 3200) * np.exp(-t * 40)
    crack = S.fft_filter(S.noise(rng, n), 3500, 9000) * np.exp(-t * 110)
    ring = 0.0
    if kind == "metal":
        ring = 0.25 * np.sin(S.TWO_PI * 1250 * t) * np.exp(-t * 18) + 0.15 * np.sin(S.TWO_PI * 2740 * t) * np.exp(-t * 25)
    return _finish(thump * 0.9 + slap * 0.7 + crack * 0.5 + ring, 0.85)


def voice(freqs: List[float], duration: float, formants, seed: int, roughness: float = 0.0, am_rate: float = 0.0) -> np.ndarray:
    rng = _rng(300 + seed)
    n = int(duration * S.SR)
    t = np.arange(n) / S.SR
    progress = np.linspace(0, 1, n)
    pitch = np.interp(progress, np.linspace(0, 1, len(freqs)), freqs)
    phase = np.cumsum(pitch) * S.TWO_PI / S.SR
    source = sum(np.sin(phase * k) / k ** 0.8 for k in range(1, 30) if True)
    source = source + roughness * S.noise(rng, n) * 0.3
    if am_rate:
        source = source * (0.55 + 0.45 * np.sin(S.TWO_PI * am_rate * t))
    shaped = S.formant_filter(source, formants)
    envelope = np.sin(np.pi * np.clip(progress, 0, 1)) ** 0.7
    return shaped * envelope


def wolf_growl(seed: int = 0) -> np.ndarray:
    mono = voice([95, 80, 88, 70], 1.0, [(550, 150, 1.0), (1000, 200, 0.6), (2300, 400, 0.2)], seed, roughness=1.2, am_rate=26)
    return _finish(mono, 0.75)


def wolf_howl(seed: int = 0) -> np.ndarray:
    mono = voice([260, 420, 520, 500, 380], 1.8, [(700, 180, 1.0), (1300, 250, 0.4)], seed, roughness=0.15)
    return _finish(mono, 0.6)


def bandit_grunt(seed: int = 0) -> np.ndarray:
    mono = voice([135, 150, 105], 0.38, [(700, 120, 1.0), (1150, 160, 0.7), (2500, 250, 0.2)], seed, roughness=0.5)
    return _finish(mono, 0.7)


def lurker_roar(seed: int = 0) -> np.ndarray:
    rng = _rng(400)
    mono = voice([48, 62, 52, 40], 1.5, [(320, 100, 1.0), (700, 150, 0.7), (1400, 250, 0.2)], seed, roughness=1.5, am_rate=17)
    t = S.time_axis(1.5)
    bubbles = S.fft_filter(S.noise(rng, len(t)), 100, 700) * (0.5 + 0.5 * np.sin(S.TWO_PI * 11 * t)) * 0.5
    return _finish(mono + bubbles[: len(mono)], 0.8)


def player_hurt(seed: int = 0) -> np.ndarray:
    mono = voice([210, 170, 120], 0.34, [(650, 120, 1.0), (1100, 160, 0.6)], seed, roughness=0.4)
    return _finish(mono + hit("flesh", seed)[0][: len(mono)] * 0.4, 0.7)


def enemy_death(seed: int = 0) -> np.ndarray:
    mono = voice([330, 220, 110, 70], 0.7, [(600, 150, 1.0), (1000, 200, 0.5)], seed, roughness=0.7)
    t = S.time_axis(0.7)
    thud = np.sin(S.TWO_PI * 60 * np.clip(t - 0.5, 0, None)) * np.exp(-np.clip(t - 0.5, 0, None) * 18) * (t > 0.5)
    return _finish(mono[: len(t)] + thud, 0.75)


# -------------------------------------------------------------------- pickups


def pickup() -> np.ndarray:
    rng = _rng(500)
    mono = np.zeros(int(0.5 * S.SR))
    for index, freq in enumerate((880, 1318, 1760)):
        note = S.bell(freq, 0.5, rng)[: len(mono) - int(index * 0.07 * S.SR)]
        mono[int(index * 0.07 * S.SR) : int(index * 0.07 * S.SR) + len(note)] += note
    return _finish(mono, 0.6)


def coin() -> np.ndarray:
    rng = _rng(510)
    mono = np.zeros(int(0.6 * S.SR))
    for index, base in enumerate((3300, 4300, 3700)):
        t = S.time_axis(0.35)
        clink = (np.sin(S.TWO_PI * base * t) + 0.5 * np.sin(S.TWO_PI * base * 1.51 * t)) * np.exp(-t * 14) * np.minimum(1, t / 0.001)
        offset = int(index * 0.09 * S.SR)
        mono[offset : offset + len(clink)] += clink
    return _finish(mono, 0.6)


def drink() -> np.ndarray:
    rng = _rng(520)
    mono = np.zeros(int(0.9 * S.SR))
    for index in range(3):
        t = S.time_axis(0.14)
        gulp = np.sin(S.TWO_PI * np.cumsum(250 - 700 * t) / S.SR) * np.sin(np.pi * t / t[-1]) ** 2
        gulp += 0.3 * S.fft_filter(S.noise(rng, len(t)), 200, 1200) * np.sin(np.pi * t / t[-1])
        offset = int((0.05 + index * 0.2) * S.SR)
        mono[offset : offset + len(gulp)] += gulp * 0.8
    sparkle = S.bell(1568, 0.4, rng) * 0.5
    mono[int(0.65 * S.SR) : int(0.65 * S.SR) + len(sparkle)] += sparkle[: len(mono) - int(0.65 * S.SR)]
    return _finish(mono, 0.65)


def whoosh() -> np.ndarray:
    rng = _rng(530)
    t = S.time_axis(0.7)
    source = S.noise(rng, len(t))
    shaped = S.fft_filter(source, 150, 1800) * np.sin(np.pi * t / t[-1]) ** 2 + 0.3 * S.fft_filter(source, 1500, 5000) * np.sin(np.pi * t / t[-1]) ** 4
    return _finish(shaped, 0.5)


def ui_click(opening: bool = True) -> np.ndarray:
    rng = _rng(540)
    notes = (659, 988) if opening else (988, 659)
    mono = np.zeros(int(0.35 * S.SR))
    for index, freq in enumerate(notes):
        note = S.bell(freq, 0.3, rng)
        offset = int(index * 0.07 * S.SR)
        mono[offset : offset + len(note)] += note[: len(mono) - offset]
    return _finish(mono, 0.5)


def click_walk() -> np.ndarray:
    rng = _rng(550)
    t = S.time_axis(0.2)
    ping = np.sin(S.TWO_PI * 784 * t) * np.exp(-t * 24) * 0.5 + np.sin(S.TWO_PI * 1176 * t) * np.exp(-t * 30) * 0.3
    tick = S.fft_filter(S.noise(rng, len(t)), 1500, 5000) * np.exp(-t * 120) * 0.5
    return _finish(ping + tick, 0.45)


def talk(seed: int) -> np.ndarray:
    """A burst of short vowel blips, like muffled speech."""
    rng = _rng(600 + seed)
    center = 120 + seed * 38
    total = int(1.1 * S.SR)
    mono = np.zeros(total)
    cursor = 0.0
    while cursor < 0.95:
        duration = rng.uniform(0.06, 0.13)
        freq = center * rng.uniform(0.85, 1.35)
        formants = [(float(rng.choice([450, 650, 800])), 120, 1.0), (float(rng.choice([1000, 1300, 1700])), 180, 0.5)]
        blip = voice([freq, freq * rng.uniform(0.9, 1.1)], duration, formants, int(rng.integers(1000)), roughness=0.15)
        offset = int(cursor * S.SR)
        mono[offset : offset + len(blip)] += blip[: total - offset]
        cursor += duration + rng.uniform(0.0, 0.05)
    return _finish(mono, 0.5)


SFX: Dict[str, Callable[[], np.ndarray]] = {}
for _index in range(4):
    for _kind in ("grass", "dirt", "stone", "wood", "mud"):
        SFX[f"step_{_kind}_{_index}"] = (lambda kind=_kind, index=_index: footstep(kind, index))
for _index in range(3):
    SFX[f"swing_{_index}"] = (lambda index=_index: sword_swing(index))
    SFX[f"hit_flesh_{_index}"] = (lambda index=_index: hit("flesh", index))
    SFX[f"hit_metal_{_index}"] = (lambda index=_index: hit("metal", index))
    SFX[f"hurt_{_index}"] = (lambda index=_index: player_hurt(index))
    SFX[f"growl_wolf_{_index}"] = (lambda index=_index: wolf_growl(index))
    SFX[f"grunt_bandit_{_index}"] = (lambda index=_index: bandit_grunt(index))
    SFX[f"roar_lurker_{_index}"] = (lambda index=_index: lurker_roar(index))
    SFX[f"death_{_index}"] = (lambda index=_index: enemy_death(index))
SFX["howl_wolf"] = wolf_howl
SFX["pickup"] = pickup
SFX["coin"] = coin
SFX["drink"] = drink
SFX["whoosh"] = whoosh
SFX["ui_open"] = lambda: ui_click(True)
SFX["ui_close"] = lambda: ui_click(False)
SFX["click_walk"] = click_walk
for _index in range(6):
    SFX[f"talk_{_index}"] = (lambda index=_index: talk(index))


# ----------------------------------------------------------------- ambience


def _loop_noise(rng: np.random.Generator) -> np.ndarray:
    return S.noise(rng, int(AMBIENCE_SECONDS * S.SR))


def _periodic(t: np.ndarray, cycles: float, phase: float = 0.0) -> np.ndarray:
    """LFO with a whole number of cycles per loop, so the loop stays seamless."""
    return np.sin(S.TWO_PI * round(cycles) * t / AMBIENCE_SECONDS + phase)


def _stereo_loop(left: np.ndarray, right: np.ndarray, level: float = 0.5) -> np.ndarray:
    stereo = np.vstack([left, right])
    stereo = stereo / (np.max(np.abs(stereo)) + 1e-9) * level
    return stereo


def _scatter(mix: np.ndarray, sound: np.ndarray, start: int, pan: float, gain: float) -> None:
    S.place(mix, sound, start, pan, gain)


def ambience_wind(seed: int = 1, strength: float = 1.0) -> np.ndarray:
    rng = _rng(700 + seed)
    t = np.arange(int(AMBIENCE_SECONDS * S.SR)) / S.SR
    channels = []
    for _ in range(2):
        base = S.fft_filter(_loop_noise(rng), 60, 700, slope=0.4)
        howl = S.fft_filter(_loop_noise(rng), 500, 1400)
        gust = 0.55 + 0.25 * _periodic(t, 2, rng.uniform(0, 6)) + 0.2 * _periodic(t, 5, rng.uniform(0, 6))
        whistle = np.clip(_periodic(t, 3, rng.uniform(0, 6)), 0, 1) ** 2
        channels.append(base * gust + howl * whistle * 0.35 * strength)
    return _stereo_loop(channels[0], channels[1], 0.5)


def ambience_forest(seed: int = 2) -> np.ndarray:
    rng = _rng(710 + seed)
    t = np.arange(int(AMBIENCE_SECONDS * S.SR)) / S.SR
    channels = []
    for _ in range(2):
        leaves = S.fft_filter(_loop_noise(rng), 2500, 7500)
        rustle = np.clip(0.5 + 0.5 * _periodic(t, 3, rng.uniform(0, 6)) * _periodic(t, 7, rng.uniform(0, 6)), 0, 1)
        deep = S.fft_filter(_loop_noise(rng), 60, 420, slope=0.3) * (0.6 + 0.3 * _periodic(t, 2, rng.uniform(0, 6)))
        channels.append(leaves * rustle * 0.4 + deep)
    return _stereo_loop(channels[0], channels[1], 0.45)


def ambience_birds(seed: int = 3) -> np.ndarray:
    rng = _rng(720 + seed)
    total = int(AMBIENCE_SECONDS * S.SR)
    mix = np.zeros((2, total))
    for _ in range(9):
        start = int(rng.uniform(0, AMBIENCE_SECONDS) * S.SR)
        pan = rng.uniform(-0.8, 0.8)
        base = rng.uniform(2400, 4200)
        gain = rng.uniform(0.3, 0.6)
        for chirp in range(int(rng.integers(2, 5))):
            t = S.time_axis(0.11)
            sweep = base * (1 + 0.5 * np.sin(np.pi * t / t[-1]) * rng.choice([-1, 1]) + 0.3 * t / t[-1])
            tone = np.sin(np.cumsum(sweep) * S.TWO_PI / S.SR) * np.sin(np.pi * t / t[-1]) ** 0.8
            tone += 0.3 * np.sin(np.cumsum(sweep * 2) * S.TWO_PI / S.SR) * np.sin(np.pi * t / t[-1])
            _scatter(mix, tone, start + int(chirp * 0.15 * S.SR), pan, gain)
    breeze = ambience_wind(seed, 0.3)
    return mix * 0.8 + breeze * 0.4


def ambience_crickets(seed: int = 4) -> np.ndarray:
    rng = _rng(730 + seed)
    total = int(AMBIENCE_SECONDS * S.SR)
    t = np.arange(total) / S.SR
    channels = []
    for voice_index in range(2):
        signal = np.zeros(total)
        for cricket in range(5):
            freq = rng.uniform(3900, 5200)
            chirp_rate = rng.uniform(2.1, 3.2)
            pulse_rate = rng.uniform(28, 38)
            burst = np.clip(np.sin(S.TWO_PI * round(chirp_rate * AMBIENCE_SECONDS) * t / AMBIENCE_SECONDS + rng.uniform(0, 6)), 0, 1) ** 0.5
            pulses = np.clip(np.sin(S.TWO_PI * round(pulse_rate * AMBIENCE_SECONDS) * t / AMBIENCE_SECONDS), 0, 1)
            signal += np.sin(S.TWO_PI * freq * t) * burst * pulses * rng.uniform(0.3, 0.6)
        channels.append(signal)
    wind = ambience_wind(seed, 0.2)
    return _stereo_loop(channels[0], channels[1], 0.4) * 0.8 + wind * 0.25


def ambience_river(seed: int = 5) -> np.ndarray:
    rng = _rng(740 + seed)
    t = np.arange(int(AMBIENCE_SECONDS * S.SR)) / S.SR
    channels = []
    for _ in range(2):
        flow = S.fft_filter(_loop_noise(rng), 250, 3500, slope=0.3)
        splash = S.fft_filter(_loop_noise(rng), 1200, 6000)
        wobble = 0.65 + 0.2 * _periodic(t, 11, rng.uniform(0, 6)) + 0.15 * _periodic(t, 23, rng.uniform(0, 6))
        channels.append(flow * wobble + splash * 0.25 * np.clip(_periodic(t, 17, rng.uniform(0, 6)), 0, 1))
    return _stereo_loop(channels[0], channels[1], 0.5)


def ambience_fire(seed: int = 6) -> np.ndarray:
    rng = _rng(750 + seed)
    total = int(AMBIENCE_SECONDS * S.SR)
    mix = np.zeros((2, total))
    roar = S.fft_filter(_loop_noise(rng), 40, 280)
    mix[0] += roar * 0.9
    mix[1] += S.fft_filter(_loop_noise(rng), 40, 280) * 0.9
    for _ in range(int(AMBIENCE_SECONDS * 11)):
        start = int(rng.uniform(0, AMBIENCE_SECONDS) * S.SR)
        length = int(rng.uniform(0.006, 0.05) * S.SR)
        burst = S.fft_filter(S.noise(rng, length), 900, 6500) * np.exp(-np.arange(length) / (length / 4))
        _scatter(mix, burst, start, rng.uniform(-0.7, 0.7), rng.uniform(0.2, 1.0))
    return mix / (np.max(np.abs(mix)) + 1e-9) * 0.5


def ambience_murmur(seed: int = 7) -> np.ndarray:
    rng = _rng(760 + seed)
    t = np.arange(int(AMBIENCE_SECONDS * S.SR)) / S.SR
    total = len(t)
    mix = np.zeros((2, total))
    for talker in range(7):
        center = rng.uniform(150, 260)
        n = total
        phase = np.cumsum(center * (1 + 0.15 * _periodic(t, int(rng.integers(3, 9)), rng.uniform(0, 6)))) * S.TWO_PI / S.SR
        source = sum(np.sin(phase * k) / k for k in range(1, 18))
        syllables = np.clip(_periodic(t, int(rng.integers(40, 70)), rng.uniform(0, 6)), 0, 1) * np.clip(0.5 + _periodic(t, int(rng.integers(2, 5)), rng.uniform(0, 6)), 0, 1)
        voice_signal = S.formant_filter(source, [(float(rng.choice([500, 700])), 130, 1.0), (float(rng.choice([1100, 1500])), 200, 0.5)]) * syllables
        pan = rng.uniform(-0.8, 0.8)
        angle = (pan + 1) * np.pi / 4
        mix[0] += voice_signal * np.cos(angle)
        mix[1] += voice_signal * np.sin(angle)
    for _ in range(14):
        start = int(rng.uniform(0, AMBIENCE_SECONDS) * S.SR)
        _scatter(mix, S.bell(float(rng.uniform(2600, 4200)), 0.25, rng) * 0.25, start, rng.uniform(-0.8, 0.8), 0.5)
    return mix / (np.max(np.abs(mix)) + 1e-9) * 0.5


def ambience_forge(seed: int = 8) -> np.ndarray:
    rng = _rng(770 + seed)
    total = int(AMBIENCE_SECONDS * S.SR)
    fire = ambience_fire(seed)
    mix = np.zeros((2, total))
    for index in range(11):
        start = int((index * AMBIENCE_SECONDS / 11 + rng.uniform(-0.05, 0.05)) * S.SR)
        t = S.time_axis(0.9)
        ring = (np.sin(S.TWO_PI * 680 * t) + 0.6 * np.sin(S.TWO_PI * 1710 * t) + 0.35 * np.sin(S.TWO_PI * 3120 * t)) * np.exp(-t * 7)
        thud = np.sin(S.TWO_PI * 90 * t) * np.exp(-t * 40)
        _scatter(mix, ring * 0.7 + thud, start, 0.2, 0.9 if index % 3 else 0.5)
    mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.45
    return mix + fire * 0.55


def ambience_marsh(seed: int = 9) -> np.ndarray:
    rng = _rng(780 + seed)
    total = int(AMBIENCE_SECONDS * S.SR)
    t = np.arange(total) / S.SR
    mix = np.zeros((2, total))
    for _ in range(14):
        start = int(rng.uniform(0, AMBIENCE_SECONDS) * S.SR)
        length = S.time_axis(0.28)
        base = rng.uniform(170, 300)
        ribbit = np.sin(S.TWO_PI * np.cumsum(base * (1 + 0.5 * length / length[-1])) / S.SR) * np.clip(np.sin(S.TWO_PI * 24 * length), 0, 1) * np.sin(np.pi * length / length[-1])
        _scatter(mix, ribbit, start, rng.uniform(-0.9, 0.9), rng.uniform(0.3, 0.8))
    for _ in range(12):
        start = int(rng.uniform(0, AMBIENCE_SECONDS) * S.SR)
        pop = np.sin(S.TWO_PI * np.cumsum(260 + 900 * S.time_axis(0.08)) / S.SR) * np.exp(-S.time_axis(0.08) * 40)
        _scatter(mix, pop, start, rng.uniform(-0.9, 0.9), 0.4)
    insects = S.fft_filter(_loop_noise(rng), 5000, 9000) * (0.4 + 0.3 * _periodic(t, 6)) * 0.12
    mix += insects
    wind = ambience_wind(seed, 0.4)
    return mix / (np.max(np.abs(mix)) + 1e-9) * 0.45 + wind * 0.45


def ambience_hall(seed: int = 10) -> np.ndarray:
    rng = _rng(790 + seed)
    total = int(AMBIENCE_SECONDS * S.SR)
    air = S.fft_filter(_loop_noise(rng), 60, 500, slope=0.5)
    mix = np.zeros((2, total))
    mix[0] += air
    mix[1] += S.fft_filter(_loop_noise(rng), 60, 500, slope=0.5)
    for _ in range(4):
        start = int(rng.uniform(0, AMBIENCE_SECONDS) * S.SR)
        _scatter(mix, S.bell(float(rng.uniform(1100, 1500)), 0.4, rng) * 0.2, start, rng.uniform(-0.6, 0.6), 0.7)
    mix = S.reverb(mix / (np.max(np.abs(mix)) + 1e-9) * 0.5, rng, 2.5, 0.5)
    return mix / (np.max(np.abs(mix)) + 1e-9) * 0.4


AMBIENCE: Dict[str, Callable[[], np.ndarray]] = {
    "wind": ambience_wind,
    "forest": ambience_forest,
    "birds": ambience_birds,
    "crickets": ambience_crickets,
    "river": ambience_river,
    "fire": ambience_fire,
    "murmur": ambience_murmur,
    "forge": ambience_forge,
    "marsh": ambience_marsh,
    "hall": ambience_hall,
}
