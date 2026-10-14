"""Numpy synthesis toolkit: oscillators, instruments, drums, filters and reverb."""
import wave
from typing import Sequence

import numpy as np

SR = 32000
TWO_PI = 2 * np.pi


# ------------------------------------------------------------------ basics


def time_axis(duration: float) -> np.ndarray:
    return np.arange(int(round(duration * SR))) / SR


def midi_freq(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12.0)


def adsr(length: int, attack: float = 0.01, decay: float = 0.1, sustain: float = 0.7, release: float = 0.1) -> np.ndarray:
    envelope = np.zeros(length)
    if length == 0:
        return envelope
    release_samples = min(int(release * SR), length)
    body = length - release_samples
    attack_samples = max(1, min(int(attack * SR), max(body, 1)))
    envelope[:attack_samples] = np.linspace(0, 1, attack_samples, endpoint=False)
    decay_samples = min(int(decay * SR), max(0, body - attack_samples))
    if decay_samples > 0:
        envelope[attack_samples : attack_samples + decay_samples] = np.linspace(1, sustain, decay_samples, endpoint=False)
    envelope[attack_samples + decay_samples : body] = sustain
    if release_samples > 0:
        start_level = envelope[body - 1] if body > 0 else sustain
        envelope[body:] = np.linspace(start_level, 0, release_samples)
    return envelope


def harmonic_stack(freq: float, t: np.ndarray, amplitudes: Sequence[float], phase: float = 0.0, vibrato: np.ndarray = None) -> np.ndarray:
    base = TWO_PI * freq * t + phase
    if vibrato is not None:
        base = base + vibrato
    output = np.zeros_like(t)
    for harmonic, amplitude in enumerate(amplitudes, 1):
        if freq * harmonic >= SR * 0.45:
            break
        output += amplitude * np.sin(base * harmonic)
    return output


def saw_amplitudes(count: int, falloff: float = 1.0) -> list:
    return [1.0 / (k ** falloff) for k in range(1, count + 1)]


def vibrato_phase(t: np.ndarray, rate: float, depth_cents: float, freq: float, onset: float = 0.0) -> np.ndarray:
    """Phase modulation giving +-depth_cents of pitch vibrato (fades in after `onset`)."""
    depth = freq * (2 ** (depth_cents / 1200.0) - 1)
    fade = np.clip((t - onset) / 0.5, 0, 1)
    return fade * depth / rate * np.sin(TWO_PI * rate * t)


# ---------------------------------------------------------------- filtering


def fft_filter(signal: np.ndarray, low: float = 0.0, high: float = SR / 2, slope: float = 0.0) -> np.ndarray:
    """Zero-phase band filter with soft edges; `slope` tilts the spectrum (1/f^slope)."""
    spectrum = np.fft.rfft(signal)
    freqs = np.fft.rfftfreq(len(signal), 1 / SR)
    edge = max(30.0, low * 0.25)
    mask = np.ones_like(freqs)
    if low > 0:
        mask *= 1 / (1 + np.exp(-(freqs - low) / (edge * 0.35)))
    if high < SR / 2:
        mask *= 1 / (1 + np.exp((freqs - high) / (max(40.0, high * 0.08) * 0.35)))
    if slope:
        mask *= 1 / np.maximum(freqs, 20.0) ** slope
    return np.fft.irfft(spectrum * mask, len(signal))


def formant_filter(signal: np.ndarray, formants: Sequence[tuple]) -> np.ndarray:
    """formants: (center_hz, bandwidth_hz, gain)."""
    spectrum = np.fft.rfft(signal)
    freqs = np.fft.rfftfreq(len(signal), 1 / SR)
    mask = np.full_like(freqs, 0.02)
    for center, bandwidth, gain in formants:
        mask += gain * np.exp(-((freqs - center) / bandwidth) ** 2)
    return np.fft.irfft(spectrum * mask, len(signal))


def smooth(signal: np.ndarray, window: int) -> np.ndarray:
    kernel = np.ones(window) / window
    return np.convolve(signal, kernel, mode="same")


def noise(rng: np.random.Generator, length: int) -> np.ndarray:
    return rng.standard_normal(length)


# -------------------------------------------------------------- instruments


def strings(freq: float, duration: float, rng: np.random.Generator, brightness: int = 14) -> np.ndarray:
    length = int(duration * SR)
    t = np.arange(length) / SR
    amplitudes = saw_amplitudes(brightness, 1.1)
    voice = np.zeros(length)
    for cents in (-9, 0, 9):
        detuned = freq * 2 ** (cents / 1200.0)
        voice += harmonic_stack(detuned, t, amplitudes, rng.uniform(0, TWO_PI), vibrato_phase(t, 5.2 + rng.uniform(-0.4, 0.4), 6, detuned, 0.4))
    return voice / 3 * adsr(length, 0.45, 0.2, 0.85, 0.7)


def brass(freq: float, duration: float, rng: np.random.Generator, power: float = 1.0) -> np.ndarray:
    length = int(duration * SR)
    t = np.arange(length) / SR
    envelope = adsr(length, 0.09, 0.12, 0.85, 0.25)
    dark = harmonic_stack(freq, t, saw_amplitudes(5, 1.0), 0, vibrato_phase(t, 5.0, 8, freq, 0.25))
    bright = harmonic_stack(freq, t, saw_amplitudes(26, 0.85), 0, vibrato_phase(t, 5.0, 8, freq, 0.25))
    swell = np.clip(envelope ** 0.6 * power, 0, 1)
    return (dark * (1 - swell) + bright * swell) * envelope * 0.6


def choir(freq: float, duration: float, rng: np.random.Generator, vowel: str = "ah") -> np.ndarray:
    formants = {"ah": [(750, 140, 1.0), (1220, 180, 0.6), (2600, 250, 0.25)], "oh": [(500, 100, 1.0), (900, 150, 0.5), (2500, 250, 0.15)], "oo": [(320, 80, 1.0), (800, 120, 0.3)]}[vowel]
    length = int(duration * SR)
    t = np.arange(length) / SR
    voice = np.zeros(length)
    for cents in (-13, -4, 5, 14):
        detuned = freq * 2 ** (cents / 1200.0)
        amplitudes = []
        for harmonic in range(1, 40):
            harmonic_freq = detuned * harmonic
            weight = 0.04 + sum(gain * np.exp(-((harmonic_freq - center) / bandwidth) ** 2) for center, bandwidth, gain in formants)
            amplitudes.append(weight / harmonic ** 0.6)
        voice += harmonic_stack(detuned, t, amplitudes, rng.uniform(0, TWO_PI), vibrato_phase(t, 5.6 + rng.uniform(-0.5, 0.5), 9, detuned, 0.5))
    breath = fft_filter(noise(rng, length), 2000, 7000) * 0.03
    return (voice / 4 + breath) * adsr(length, 0.7, 0.2, 0.9, 1.0) * 0.5


def harp(freq: float, duration: float, rng: np.random.Generator, brightness: float = 1.0) -> np.ndarray:
    length = int(duration * SR)
    t = np.arange(length) / SR
    output = np.zeros(length)
    for harmonic in range(1, 16):
        if freq * harmonic > SR * 0.45:
            break
        decay = 2.2 + harmonic * 1.1 / brightness
        output += (1.0 / harmonic ** 1.15) * np.sin(TWO_PI * freq * harmonic * t) * np.exp(-t * decay)
    return output * np.minimum(1, t / 0.004) * 0.7


def lute(freq: float, duration: float, rng: np.random.Generator) -> np.ndarray:
    return harp(freq, duration, rng, brightness=0.6) * 1.1


def flute(freq: float, duration: float, rng: np.random.Generator) -> np.ndarray:
    length = int(duration * SR)
    t = np.arange(length) / SR
    tone = harmonic_stack(freq, t, [1.0, 0.25, 0.08, 0.03], 0, vibrato_phase(t, 5.0, 14, freq, 0.2))
    breath = fft_filter(noise(rng, length), 1500, 6000) * 0.05
    return (tone + breath) * adsr(length, 0.07, 0.1, 0.8, 0.2) * 0.8


def fiddle(freq: float, duration: float, rng: np.random.Generator) -> np.ndarray:
    length = int(duration * SR)
    t = np.arange(length) / SR
    tone = harmonic_stack(freq, t, saw_amplitudes(20, 0.9), 0, vibrato_phase(t, 6.2, 22, freq, 0.12))
    scrape = fft_filter(noise(rng, length), 2500, 9000) * 0.04
    return (tone + scrape) * adsr(length, 0.05, 0.1, 0.8, 0.15) * 0.45


def bell(freq: float, duration: float, rng: np.random.Generator) -> np.ndarray:
    length = int(duration * SR)
    t = np.arange(length) / SR
    output = np.zeros(length)
    for ratio, amplitude, decay in ((1.0, 1.0, 1.0), (2.0, 0.55, 1.4), (2.76, 0.5, 1.8), (5.4, 0.3, 2.6), (8.93, 0.18, 3.6)):
        if freq * ratio < SR * 0.45:
            output += amplitude * np.sin(TWO_PI * freq * ratio * t) * np.exp(-t * decay * 1.2)
    return output * np.minimum(1, t / 0.002) * 0.5


def cello(freq: float, duration: float, rng: np.random.Generator) -> np.ndarray:
    length = int(duration * SR)
    t = np.arange(length) / SR
    tone = harmonic_stack(freq, t, saw_amplitudes(12, 1.0), 0, vibrato_phase(t, 5.0, 8, freq, 0.3))
    tone += 0.6 * np.sin(TWO_PI * freq * t)
    return tone * adsr(length, 0.12, 0.2, 0.85, 0.3) * 0.5


def sub_drone(freq: float, duration: float, rng: np.random.Generator) -> np.ndarray:
    length = int(duration * SR)
    t = np.arange(length) / SR
    tone = np.sin(TWO_PI * freq * t) + 0.35 * np.sin(TWO_PI * freq * 2 * t + 1) + 0.15 * harmonic_stack(freq * 1.005, t, saw_amplitudes(6, 1.2))
    return tone * adsr(length, 1.2, 0.2, 0.9, 1.5) * 0.5


# --------------------------------------------------------------------- drums


def taiko(rng: np.random.Generator, power: float = 1.0, length_seconds: float = 0.9) -> np.ndarray:
    t = time_axis(length_seconds)
    pitch = 52 + 60 * np.exp(-t * 28)
    body = np.sin(TWO_PI * np.cumsum(pitch) / SR) * np.exp(-t * 4.2)
    skin = fft_filter(noise(rng, len(t)), 150, 1500) * np.exp(-t * 30) * 0.6
    click = fft_filter(noise(rng, len(t)), 2000, 6000) * np.exp(-t * 90) * 0.3
    return (body + skin + click) * power


def kick(rng: np.random.Generator, power: float = 1.0) -> np.ndarray:
    t = time_axis(0.35)
    pitch = 46 + 90 * np.exp(-t * 40)
    return (np.sin(TWO_PI * np.cumsum(pitch) / SR) * np.exp(-t * 11) + fft_filter(noise(rng, len(t)), 800, 5000) * np.exp(-t * 120) * 0.2) * power


def snare(rng: np.random.Generator, power: float = 1.0) -> np.ndarray:
    t = time_axis(0.3)
    tone = np.sin(TWO_PI * 190 * t) * np.exp(-t * 28)
    rattle = fft_filter(noise(rng, len(t)), 1200, 9000) * np.exp(-t * 17)
    return (tone * 0.6 + rattle * 0.8) * power


def hat(rng: np.random.Generator, power: float = 1.0, open_hat: bool = False) -> np.ndarray:
    t = time_axis(0.22 if open_hat else 0.06)
    return fft_filter(noise(rng, len(t)), 6000, 14000) * np.exp(-t * (14 if open_hat else 70)) * power * 0.6


def shaker(rng: np.random.Generator, power: float = 1.0) -> np.ndarray:
    t = time_axis(0.12)
    return fft_filter(noise(rng, len(t)), 4000, 12000) * np.sin(np.pi * np.clip(t / 0.12, 0, 1)) ** 2 * power * 0.5


def stomp(rng: np.random.Generator, power: float = 1.0) -> np.ndarray:
    t = time_axis(0.25)
    return (np.sin(TWO_PI * (80 + 40 * np.exp(-t * 30)) * t) * np.exp(-t * 15) + fft_filter(noise(rng, len(t)), 100, 900) * np.exp(-t * 40) * 0.5) * power


def cymbal_swell(rng: np.random.Generator, duration: float, power: float = 1.0) -> np.ndarray:
    length = int(duration * SR)
    t = np.arange(length) / SR
    hiss = fft_filter(noise(rng, length), 3500, 13000)
    return hiss * (t / duration) ** 2.2 * power * 0.6


def cymbal_crash(rng: np.random.Generator, power: float = 1.0) -> np.ndarray:
    t = time_axis(3.0)
    return fft_filter(noise(rng, len(t)), 3000, 14000) * np.exp(-t * 1.6) * np.minimum(1, t / 0.005) * power * 0.7


# ------------------------------------------------------------ mixing helpers


def place(buffer: np.ndarray, mono: np.ndarray, start: int, pan: float = 0.0, gain: float = 1.0) -> None:
    """Add a mono sound into a stereo loop buffer at `start`, wrapping past the end."""
    total = buffer.shape[1]
    angle = (pan + 1) * np.pi / 4
    left, right = np.cos(angle) * gain, np.sin(angle) * gain
    start %= total
    first = min(len(mono), total - start)
    buffer[0, start : start + first] += mono[:first] * left
    buffer[1, start : start + first] += mono[:first] * right
    remaining = len(mono) - first
    while remaining > 0:
        chunk = min(remaining, total)
        buffer[0, :chunk] += mono[first : first + chunk] * left
        buffer[1, :chunk] += mono[first : first + chunk] * right
        first += chunk
        remaining -= chunk


def reverb(buffer: np.ndarray, rng: np.random.Generator, seconds: float = 2.8, wet: float = 0.35, damping: float = 5000.0) -> np.ndarray:
    """Convolution reverb that wraps around so loops stay seamless."""
    total = buffer.shape[1]
    impulse_length = int(seconds * SR)
    t = np.arange(impulse_length) / SR
    output = np.zeros_like(buffer)
    size = 1 << int(np.ceil(np.log2(total + impulse_length)))
    for channel in range(2):
        impulse = noise(rng, impulse_length) * np.exp(-t * (6.9 / seconds))
        impulse = fft_filter(impulse, 120, damping)
        impulse *= np.minimum(1, t / 0.02)
        impulse /= np.sqrt(np.sum(impulse ** 2)) + 1e-9
        linear = np.fft.irfft(np.fft.rfft(buffer[channel], size) * np.fft.rfft(impulse, size), size)[: total + impulse_length - 1]
        folded = linear[:total].copy()
        tail = linear[total:]
        folded[: len(tail)] += tail
        output[channel] = folded
    return buffer * (1 - wet * 0.5) + output * wet


def master(buffer: np.ndarray, target_rms: float = 0.16, ceiling: float = 0.92) -> np.ndarray:
    buffer = buffer - buffer.mean(axis=1, keepdims=True)
    rms = np.sqrt(np.mean(buffer ** 2)) + 1e-9
    buffer = buffer * (target_rms / rms)
    buffer = np.tanh(buffer * 1.4) / np.tanh(1.4)
    peak = np.max(np.abs(buffer)) + 1e-9
    return buffer * min(1.0, ceiling / peak)


def to_stereo(mono: np.ndarray) -> np.ndarray:
    return np.vstack([mono, mono])


def write_wav(path: str, stereo: np.ndarray) -> None:
    data = np.clip(stereo.T, -1, 1)
    pcm = (data * 32767).astype("<i2")
    with wave.open(path, "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(SR)
        handle.writeframes(pcm.tobytes())
