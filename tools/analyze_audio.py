"""Sanity-checks generated audio and draws spectrograms: analyze_audio.py <audio_dir> <out_dir> [spectrogram names...]"""
import glob
import os
import sys
import wave

import numpy as np

directory, out_dir = sys.argv[1], sys.argv[2]


def load(path):
    with wave.open(path) as handle:
        rate = handle.getframerate()
        data = np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2").reshape(-1, handle.getnchannels()) / 32768.0
    return rate, data


print(f"{'file':<26}{'sec':>6}{'peak':>7}{'rms':>7}{'clip%':>7}{'low%':>6}{'mid%':>6}{'high%':>6}{'seam':>7}  flags")
for path in sorted(glob.glob(os.path.join(directory, "*.wav"))):
    rate, data = load(path)
    mono = data.mean(axis=1)
    spectrum = np.abs(np.fft.rfft(mono)) ** 2
    freqs = np.fft.rfftfreq(len(mono), 1 / rate)
    total = spectrum.sum() + 1e-12
    low = spectrum[freqs < 250].sum() / total * 100
    mid = spectrum[(freqs >= 250) & (freqs < 2500)].sum() / total * 100
    high = spectrum[freqs >= 2500].sum() / total * 100
    peak = np.abs(data).max()
    rms = np.sqrt(np.mean(data ** 2))
    clip = (np.abs(data) > 0.995).mean() * 100
    # Loop seam: jump between last and first sample relative to typical sample-to-sample change.
    typical = np.abs(np.diff(mono)).mean() + 1e-9
    seam = abs(mono[0] - mono[-1]) / typical
    flags = []
    name = os.path.basename(path)
    if not np.isfinite(data).all():
        flags.append("NAN")
    if clip > 0.05:
        flags.append("CLIPS")
    if rms < 0.01:
        flags.append("QUIET")
    if name.startswith(("music_", "amb_")) and seam > 12:
        flags.append("SEAM?")
    print(f"{name[:-4]:<26}{len(mono) / rate:6.1f}{peak:7.2f}{rms:7.3f}{clip:7.2f}{low:6.0f}{mid:6.0f}{high:6.0f}{seam:7.1f}  {' '.join(flags)}")

if len(sys.argv) > 3:
    import pygame
    for name in sys.argv[3:]:
        rate, data = load(os.path.join(directory, name + ".wav"))
        mono = data.mean(axis=1)
        window, hop = 2048, 1024
        frames = (len(mono) - window) // hop
        shape = np.hanning(window)
        spec = np.array([np.abs(np.fft.rfft(mono[i * hop : i * hop + window] * shape))[:420] for i in range(frames)]).T
        spec = np.log10(spec + 1e-4)
        spec = np.clip((spec - spec.max() + 4.2) / 4.2, 0, 1)
        picture = (spec[::-1] * 255).astype(np.uint8)
        surface = pygame.Surface((picture.shape[1], picture.shape[0]))
        array = np.stack([picture, (picture * 0.8).astype(np.uint8), (255 - picture * 0.6).astype(np.uint8)], axis=2)
        pygame.surfarray.blit_array(surface, np.transpose(array, (1, 0, 2)))
        surface = pygame.transform.scale(surface, (1200, 300))
        pygame.image.save(surface, os.path.join(out_dir, f"spec_{name}.png"))
