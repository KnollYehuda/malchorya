import os
import unittest
from dataclasses import replace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from core.enums import WindDirection
from core.items import ItemId
from core.state import create_initial_state
from core.world import create_world
from logic.handle_command import handle_command
from ui3d.app3d import Game3D


class Game3DTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.game = Game3D(create_initial_state(create_world()), handle_command, headless=True, size=(640, 360))

    def setUp(self):
        game = self.game
        game.state = replace(create_initial_state(game.state.world), minutes=12 * 60)
        game.messages = []
        game.input_active = False
        game.camera_yaw, game.camera_pitch = 0.0, 52.0
        game.sync_world(arrival=(0.0, -4.0))

    def teleport(self, location_id, position=(0.0, -4.0)):
        game = self.game
        game.state = replace(game.state, player=replace(game.state.player, location_id=location_id))
        game.sync_world(arrival=position)

    def test_every_location_renders_day_and_night(self):
        for location_id in self.game.state.world.locations:
            for minutes in (12 * 60, 23 * 60):
                self.game.state = replace(self.game.state, minutes=minutes)
                self.teleport(location_id)
                self.game.update(0.016)
                self.game.render_frames(1)

    def test_walking_off_the_north_edge_moves_to_next_location(self):
        game = self.game
        self.assertEqual(game.state.player.location_id, "crossroads")
        game.player_x, game.player_y = 0.0, game.view.y_max - 0.3
        game.step_player(0, 1, 0.1)
        self.assertEqual(game.state.player.location_id, "pinewood")
        self.assertLess(game.player_y, -10)
        self.assertGreater(game.state.minutes, 12 * 60)

    def test_solid_props_block_the_player(self):
        game = self.game
        self.teleport("crossroads")
        game.view.colliders.append(("circle", 3.0, 0.0, 1.0))
        game.player_x, game.player_y = 1.0, 0.0
        for _ in range(30):
            game.step_player(1, 0, 0.05)
        self.assertLess(game.player_x, 3.0 - 1.0 + 0.01)

    def test_interact_talks_to_nearby_npc(self):
        game = self.game
        npc = next(entity for entity in game.entities if entity["kind"] == "npc")
        game.player_x, game.player_y = npc["x"] + 1.5, npc["y"]
        game._hotkey_interact()
        self.assertTrue(any("Lysa" in message for message in game.messages))

    def test_attack_requires_getting_close(self):
        game = self.game
        self.teleport("forest_depths", position=(0.0, -12.0))
        game._hotkey_attack()
        self.assertIn("Get closer", game.messages[-1])
        enemy = next(entity for entity in game.entities if entity["kind"] == "enemy")
        game.player_x, game.player_y = enemy["x"] + 2.0, enemy["y"]
        game._hotkey_attack()
        self.assertIn("You hit", game.messages[-1])

    def test_pick_up_ground_item(self):
        game = self.game
        self.teleport("forest_depths")
        game.state.enemies["forest_depths"] = []
        game.sync_world(arrival=(0.0, -4.0))
        marker = game.item_markers[0]
        game.player_x, game.player_y = marker["x"], marker["y"]
        game._hotkey_interact()
        self.assertEqual(game.state.player.inventory.count(ItemId.PINE_CONE), 1)

    def test_mouse_drag_rotates_and_tilts_camera(self):
        game = self.game
        yaw, pitch = game.camera_yaw, game.camera_pitch
        game.rotate_camera(100, 0)
        self.assertLess(game.camera_yaw, yaw)
        game.rotate_camera(-200, 0)
        self.assertGreater(game.camera_yaw, yaw)
        game.rotate_camera(0, 10000)
        self.assertEqual(game.camera_pitch, 80.0)
        game.rotate_camera(0, -10000)
        self.assertEqual(game.camera_pitch, 25.0)
        game.camera_pitch = pitch

    def test_command_line_input(self):
        game = self.game
        game._enter_pressed()
        for character in "time":
            game._keystroke(character)
        game._enter_pressed()
        self.assertIn("Day 1", game.messages[-1])
        self.assertFalse(game.input_active)


if __name__ == "__main__":
    unittest.main()
