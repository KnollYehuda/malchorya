"""Generates every audio file into a directory (cached by name)."""
import os
import time
from typing import Callable, Dict, Optional

import numpy as np

from sound import effects, music, synth

MUSIC_TARGET_RMS = 0.16


def _save(path: str, stereo: np.ndarray) -> None:
    synth.write_wav(path, stereo)


def generate_all(directory: str, only: Optional[str] = None, progress: Callable[[str], None] = print, force: bool = False) -> None:
    os.makedirs(directory, exist_ok=True)

    def wanted(name: str) -> bool:
        return (only is None or only in name) and (force or not os.path.exists(os.path.join(directory, name + ".wav")))

    jobs: Dict[str, Callable[[], np.ndarray]] = {}
    for name, track in music.TRACKS.items():
        jobs[f"music_{name}"] = (lambda track=track: music.render_track(track))
    for name, builder in music.STINGERS.items():
        jobs[f"sting_{name}"] = builder
    for name, builder in effects.AMBIENCE.items():
        jobs[f"amb_{name}"] = builder
    for name, builder in effects.SFX.items():
        jobs[f"sfx_{name}"] = builder

    for name, job in jobs.items():
        if not wanted(name):
            continue
        started = time.time()
        stereo = job()
        _save(os.path.join(directory, name + ".wav"), stereo)
        progress(f"  {name:<28} {stereo.shape[1] / synth.SR:5.1f}s  ({time.time() - started:4.1f}s)")


def audio_files_present(directory: str) -> bool:
    return os.path.exists(os.path.join(directory, "music_overworld.wav")) and os.path.exists(os.path.join(directory, "sfx_pickup.wav"))
