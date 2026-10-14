import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ["SDL_AUDIODRIVER"] = "dummy"

import numpy as np
import pygame

from sound import effects, music, synth
from sound.manager import AudioManager, default_audio_dir


class SynthTest(unittest.TestCase):
    def test_every_track_renders_finite_stereo_without_clipping(self):
        for name, track in music.TRACKS.items():
            audio = music.render_track(track, bars=2)
            self.assertEqual(audio.shape[0], 2, name)
            self.assertTrue(np.isfinite(audio).all(), name)
            self.assertLessEqual(np.abs(audio).max(), 1.0, name)
            self.assertGreater(np.sqrt(np.mean(audio ** 2)), 0.02, f"{name} is silent")
            expected = int(round(2 * 4 * 60.0 / track.bpm * synth.SR))
            self.assertEqual(audio.shape[1], expected, name)

    def test_loops_wrap_so_the_tail_returns_to_the_start(self):
        mix = np.zeros((2, 1000))
        synth.place(mix, np.ones(400), 800, 0.0, 1.0)
        self.assertGreater(mix[0, 799 + 1], 0)
        self.assertGreater(mix[0, 100], 0)   # wrapped part
        self.assertEqual(mix[0, 300], 0)

    def test_stingers_ambience_and_effects_are_valid(self):
        for name, builder in music.STINGERS.items():
            audio = builder()
            self.assertTrue(np.isfinite(audio).all(), name)
        for name in ("wind", "fire", "murmur"):
            audio = effects.AMBIENCE[name]()
            self.assertEqual(audio.shape[1], int(effects.AMBIENCE_SECONDS * synth.SR), name)
            self.assertTrue(np.isfinite(audio).all(), name)
        for name, builder in effects.SFX.items():
            audio = builder()
            self.assertTrue(np.isfinite(audio).all(), name)
            self.assertGreater(np.abs(audio).max(), 0.05, name)
            self.assertLessEqual(np.abs(audio).max(), 1.0, name)

    def test_ambience_loops_are_seamless(self):
        for name in ("wind", "river", "crickets", "forest"):
            audio = effects.AMBIENCE[name]()
            mono = audio.mean(axis=0)
            jump = abs(mono[0] - mono[-1])
            self.assertLess(jump, np.percentile(np.abs(np.diff(mono)), 99.9) * 1.5, name)


class ManagerTest(unittest.TestCase):
    def test_baked_audio_library_is_present(self):
        directory = default_audio_dir()
        files = os.listdir(directory)
        for needed in ("music_overworld.wav", "music_combat.wav", "sting_level_up.wav", "amb_wind.wav", "sfx_pickup.wav", "sfx_step_grass_0.wav"):
            self.assertIn(needed, files)
        self.assertGreaterEqual(len([name for name in files if name.startswith("sfx_")]), 55)

    def test_disabled_manager_records_events_and_runs_delays(self):
        audio = AudioManager(enabled=False)
        audio.sfx("swing")
        audio.sfx("hit_flesh", delay=0.2)
        self.assertEqual(audio.events, [("sfx", "swing")])
        audio.update(0.1)
        self.assertEqual(len(audio.events), 1)
        audio.update(0.15)
        self.assertEqual(audio.events[-1], ("sfx", "hit_flesh"))

    def test_real_mixer_plays_music_ambience_and_effects(self):
        audio = AudioManager(enabled=True)
        self.assertTrue(audio.enabled)
        try:
            audio.set_music("overworld")
            audio.set_ambience({"wind": 0.5, "birds": 0.4})
            audio.sfx("pickup")
            audio.sfx("step_grass", pan=-0.5)
            for _ in range(60):
                audio.update(0.05)
            self.assertTrue(pygame.mixer.get_busy())
            self.assertGreater(pygame.mixer.Channel(audio.music_active).get_volume(), 0.1)
            self.assertEqual(len(audio.ambience), 2)

            audio.set_music("combat")
            for _ in range(80):
                audio.update(0.05)
            self.assertEqual(audio.music_name, "combat")
            old_channel = 1 - audio.music_active
            self.assertFalse(pygame.mixer.Channel(old_channel).get_busy())

            audio.stinger("victory")
            audio.update(0.5)
            self.assertLess(audio.duck, 0.9)
            audio.set_ambience({})
            for _ in range(80):
                audio.update(0.05)
            self.assertEqual(audio.ambience, {})
        finally:
            audio.shutdown()


if __name__ == "__main__":
    unittest.main()
