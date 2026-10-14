"""Runtime audio: music crossfades, layered ambience, positional one-shots (pygame.mixer)."""
import os
import random
from typing import Callable, Dict, List, Optional, Tuple

import pygame

from sound.synth import SR

MUSIC_VOLUME = 0.5
AMBIENCE_VOLUME = 0.5
SFX_VOLUME = 0.9
STINGER_VOLUME = 0.85
MUSIC_FADE_SECONDS = 2.5
AMBIENCE_FADE_SECONDS = 2.0
DUCK_LEVEL = 0.3
MUSIC_CHANNELS = (0, 1)
AMBIENCE_CHANNELS = (2, 3, 4, 5)
RESERVED = 6


def default_audio_dir() -> str:
    return os.environ.get("MALCHORYA_AUDIO_DIR", "malchorya/assets/audio")


class AudioManager:
    def __init__(self, directory: Optional[str] = None, enabled: bool = True) -> None:
        self.directory = directory or default_audio_dir()
        self.enabled = enabled
        self.events: List[Tuple[str, str]] = []  # (kind, name) - also recorded when disabled, for tests
        self.sounds: Dict[str, Optional[pygame.mixer.Sound]] = {}
        self.variants: Dict[str, List[str]] = {}
        self.rng = random.Random()
        self.pending: List[List] = []
        self.music_name: Optional[str] = None
        self.music_levels: Dict[int, List[float]] = {channel: [0.0, 0.0] for channel in MUSIC_CHANNELS}  # [current, target]
        self.music_active: Optional[int] = None
        self.ambience: Dict[str, List] = {}  # name -> [channel_index, current, target]
        self.duck = 1.0
        self.duck_target = 1.0
        self.duck_hold = 0.0
        self.master = 1.0
        self.available = False

        if os.path.isdir(self.directory):
            for filename in os.listdir(self.directory):
                if filename.startswith("sfx_") and filename.endswith(".wav"):
                    stem = filename[4:-4]
                    base, _, tail = stem.rpartition("_")
                    key = base if tail.isdigit() else stem
                    self.variants.setdefault(key, []).append("sfx_" + stem)
                    self.variants.setdefault(stem, ["sfx_" + stem])
            self.available = True
        if self.enabled:
            try:
                pygame.mixer.pre_init(SR, -16, 2, 512)
                pygame.mixer.init()
                pygame.mixer.set_num_channels(24)
                pygame.mixer.set_reserved(RESERVED)
            except pygame.error:
                self.enabled = False

    # ------------------------------------------------------------- internals

    def _sound(self, name: str) -> Optional["pygame.mixer.Sound"]:
        if name not in self.sounds:
            path = os.path.join(self.directory, name + ".wav")
            try:
                self.sounds[name] = pygame.mixer.Sound(path)
            except (pygame.error, FileNotFoundError):
                self.sounds[name] = None
        return self.sounds[name]

    def after(self, delay: float, action: Callable[[], None]) -> None:
        self.pending.append([delay, action])

    # --------------------------------------------------------------- music

    def set_music(self, name: Optional[str]) -> None:
        if name == self.music_name:
            return
        self.events.append(("music", str(name)))
        previous = self.music_active
        self.music_name = name
        if previous is not None:
            self.music_levels[previous][1] = 0.0
        if name is None:
            self.music_active = None
            return
        incoming = MUSIC_CHANNELS[1] if previous == MUSIC_CHANNELS[0] else MUSIC_CHANNELS[0]
        self.music_active = incoming
        self.music_levels[incoming] = [0.0, MUSIC_VOLUME]
        if self.enabled:
            sound = self._sound("music_" + name)
            if sound is not None:
                channel = pygame.mixer.Channel(incoming)
                channel.set_volume(0.0)
                channel.play(sound, loops=-1)

    # ------------------------------------------------------------ ambience

    def set_ambience(self, layers: Dict[str, float]) -> None:
        """layers: ambience name -> relative level (0..1)."""
        key = ",".join(f"{name}:{level:.2f}" for name, level in sorted(layers.items()))
        if key == getattr(self, "_ambience_key", None):
            return
        self._ambience_key = key
        self.events.append(("ambience", key))
        for name, entry in self.ambience.items():
            if name not in layers:
                entry[2] = 0.0
        for name, level in layers.items():
            if name in self.ambience:
                self.ambience[name][2] = level * AMBIENCE_VOLUME
                continue
            used = {entry[0] for entry in self.ambience.values()}
            free = [channel for channel in AMBIENCE_CHANNELS if channel not in used]
            if not free:
                continue
            self.ambience[name] = [free[0], 0.0, level * AMBIENCE_VOLUME]
            if self.enabled:
                sound = self._sound("amb_" + name)
                if sound is not None:
                    channel = pygame.mixer.Channel(free[0])
                    channel.set_volume(0.0)
                    channel.play(sound, loops=-1)

    # ------------------------------------------------------------- one-shots

    def sfx(self, name: str, volume: float = 1.0, pan: float = 0.0, delay: float = 0.0) -> None:
        if delay > 0:
            self.after(delay, lambda: self.sfx(name, volume, pan))
            return
        self.events.append(("sfx", name))
        if not self.enabled:
            return
        options = self.variants.get(name)
        if not options:
            return
        sound = self._sound(self.rng.choice(options))
        if sound is None:
            return
        channel = pygame.mixer.find_channel()
        if channel is None:
            return
        level = SFX_VOLUME * volume * self.master * self.rng.uniform(0.9, 1.0)
        pan = max(-1.0, min(1.0, pan))
        channel.set_volume(level * min(1.0, 1.0 - pan * 0.7), level * min(1.0, 1.0 + pan * 0.7))
        channel.play(sound)

    def stinger(self, name: str, delay: float = 0.0) -> None:
        if delay > 0:
            self.after(delay, lambda: self.stinger(name))
            return
        self.events.append(("stinger", name))
        if not self.enabled:
            return
        sound = self._sound("sting_" + name)
        if sound is None:
            return
        channel = pygame.mixer.find_channel(force=True)
        channel.set_volume(STINGER_VOLUME * self.master)
        channel.play(sound)
        self.duck_target = DUCK_LEVEL
        self.duck_hold = sound.get_length() * 0.8

    # --------------------------------------------------------------- update

    def update(self, delta: float) -> None:
        for entry in list(self.pending):
            entry[0] -= delta
            if entry[0] <= 0:
                self.pending.remove(entry)
                entry[1]()

        if self.duck_hold > 0:
            self.duck_hold -= delta
        else:
            self.duck_target = 1.0
        self.duck += (self.duck_target - self.duck) * min(1.0, delta * (6 if self.duck_target < self.duck else 1.2))

        for channel_index, levels in self.music_levels.items():
            step = MUSIC_VOLUME / MUSIC_FADE_SECONDS * delta
            levels[0] += max(-step, min(step, levels[1] - levels[0]))
            if self.enabled:
                channel = pygame.mixer.Channel(channel_index)
                channel.set_volume(levels[0] * self.duck * self.master)
                if levels[0] <= 0.0 and levels[1] <= 0.0 and channel.get_busy():
                    channel.stop()

        for name, entry in list(self.ambience.items()):
            step = AMBIENCE_VOLUME / AMBIENCE_FADE_SECONDS * delta
            entry[1] += max(-step, min(step, entry[2] - entry[1]))
            if self.enabled:
                channel = pygame.mixer.Channel(entry[0])
                channel.set_volume(entry[1] * self.master)
                if entry[1] <= 0.0 and entry[2] <= 0.0:
                    channel.stop()
                    del self.ambience[name]
            elif entry[1] <= 0.0 and entry[2] <= 0.0:
                del self.ambience[name]

    def shutdown(self) -> None:
        if self.enabled:
            pygame.mixer.stop()
            pygame.mixer.quit()
