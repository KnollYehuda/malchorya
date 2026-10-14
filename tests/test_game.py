import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from core.enums import WindDirection
from core.world import create_world
from core.state import create_initial_state
from core.items import ItemId
from core.quests import QuestStatus
from logic.handle_command import handle_command


class GameTest(unittest.TestCase):
    def setUp(self):
        self.state = create_initial_state(create_world())
        self.state.rng.seed(1)

    def run_commands(self, *commands):
        message = ""
        for raw in commands:
            result = handle_command(self.state, raw)
            self.state = result.state
            message = result.message
        return message

    def test_fighting_wolf_gives_xp_and_pelt(self):
        self.run_commands("move north", "move north")
        for _ in range(10):
            self.run_commands("attack")
            if self.state.player.inventory.count(ItemId.WOLF_PELT):
                break
        self.assertGreaterEqual(self.state.player.inventory.count(ItemId.WOLF_PELT), 1)
        self.assertGreater(self.state.player.xp + self.state.player.level, 1)

    def test_death_respawns_at_tavern_and_loses_keter(self):
        self.run_commands("move north", "move north")
        self.state.player.hp = 1
        keter_before = self.state.player.inventory.count(ItemId.KETER)
        message = self.run_commands("attack")
        self.assertIn("collapse", message)
        self.assertEqual(self.state.player.location_id, "tavern")
        self.assertEqual(self.state.player.inventory.count(ItemId.KETER), keter_before - keter_before // 2)
        self.assertGreater(self.state.player.hp, 1)
        self.assertEqual(len(self.state.enemies["forest_depths"]), 2)

    def test_kill_quest_progress_and_reward(self):
        self.run_commands("move north", "talk borin_guard")
        self.state.quest_log["borin_errand"] = QuestStatus.COMPLETE
        self.run_commands("talk borin_guard")
        self.assertEqual(self.state.quest_log["borin_wolves"], QuestStatus.IN_PROGRESS)
        self.state.player.inventory.add(ItemId.IRON_SWORD, 1)
        self.run_commands("equip iron_sword", "move north")
        for _ in range(40):
            if self.state.quest_progress.get("borin_wolves", 0) >= 2:
                break
            self.run_commands("attack", "use health_potion")
            if self.state.player.location_id != "forest_depths":
                break
        self.assertGreaterEqual(self.state.quest_progress.get("borin_wolves", 0), 1)

    def test_equipment_changes_stats(self):
        from core.progression import effective_stats
        _, attack_before, _ = effective_stats(self.state.player)
        self.state.player.inventory.add(ItemId.IRON_SWORD, 1)
        self.run_commands("equip iron_sword")
        _, attack_after, _ = effective_stats(self.state.player)
        self.assertEqual(attack_after, attack_before + 4)

    def test_sell_and_rest(self):
        self.state.player.inventory.add(ItemId.WOLF_PELT, 1)
        self.run_commands("move west", "move south")
        self.run_commands("sell wolf_pelt")
        self.assertEqual(self.state.player.inventory.count(ItemId.WOLF_PELT), 0)
        self.state.player.hp = 1
        self.run_commands("rest")
        self.assertGreater(self.state.player.hp, 1)

    def test_npc_schedule_moves_npcs(self):
        world = self.state.world
        self.assertEqual(world.npcs["elara_blacksmith"].location_at(10), "blacksmith")
        self.assertEqual(world.npcs["elara_blacksmith"].location_at(20), "tavern")
        self.assertIsNone(world.npcs["elara_blacksmith"].location_at(2))
        self.assertEqual(world.npcs["borin_guard"].location_at(23), "crossroads")
        self.assertEqual(world.npcs["borin_guard"].location_at(3), "crossroads")

    def test_absent_npc_cannot_be_talked_to_or_traded_with(self):
        self.run_commands("move west", "move north")
        self.assertIn("Elara", self.run_commands("look"))
        self.state.minutes = 2 * 60
        self.assertIn("not here", self.run_commands("talk elara_blacksmith"))
        self.assertIn("Nobody here sells", self.run_commands("buy leather_armor"))

    def test_time_advances_and_wait(self):
        start = self.state.minutes
        self.run_commands("move east")
        self.assertEqual(self.state.minutes, start + 30)
        self.run_commands("move north")  # invalid exit: no time passes
        self.assertEqual(self.state.minutes, start + 30)
        self.run_commands("wait 3")
        self.assertEqual(self.state.minutes, start + 30 + 180)
        self.assertIn("Day 1", self.run_commands("time"))

    def test_moonpetal_only_at_night(self):
        self.run_commands("move south", "move south")
        self.assertEqual(self.state.player.location_id, "marsh")
        self.state.enemies["marsh"] = []
        self.assertIn("shut tight", self.run_commands("take moonpetal"))
        self.state.minutes = 23 * 60
        self.run_commands("take moonpetal")
        self.assertEqual(self.state.player.inventory.count(ItemId.MOONPETAL), 1)

    def test_moonpetal_quest(self):
        self.state.minutes = 10 * 60
        self.run_commands("move west", "move west", "move west")
        self.assertEqual(self.state.player.location_id, "chapel")
        self.run_commands("talk maren_priest")
        self.assertEqual(self.state.quest_log["maren_moonpetal"], QuestStatus.IN_PROGRESS)
        self.state.player.inventory.add(ItemId.MOONPETAL, 2)
        self.run_commands("talk maren_priest")
        self.assertEqual(self.state.quest_log["maren_moonpetal"], QuestStatus.COMPLETE)
        self.assertEqual(self.state.player.inventory.count(ItemId.MOONPETAL), 0)
        self.assertEqual(self.state.player.inventory.count(ItemId.HEALTH_POTION), 3)

    def test_rest_sleeps_until_morning(self):
        self.state.minutes = 21 * 60
        self.run_commands("move west", "move south")
        self.state.minutes = 21 * 60
        self.run_commands("rest")
        self.assertEqual(self.state.hour, 6)
        self.assertEqual(self.state.minutes // 1440, 1)

    def test_ui_renders_headless(self):
        import pygame
        from ui.app import App
        app = App(self.state, handle_command)
        pygame.init()
        screen = pygame.display.set_mode((960, 540))
        app.load_player_sprites()
        app.font = pygame.font.SysFont(None, 24)
        app.font_big = pygame.font.SysFont(None, 32)
        for raw in ["move north", "move north", "attack"]:
            app._run_command(raw)
        for facing in WindDirection:
            app.facing = facing
            app.render(screen)
        self.assertIsNotNone(app.current_player_sprite())
        app.input_active = True
        app.input_buffer = "look"
        app.render(screen)
        pygame.quit()


    def test_every_location_and_enemy_renders(self):
        import pygame
        from dataclasses import replace
        from ui.app import App
        pygame.init()
        screen = pygame.display.set_mode((960, 540))
        for location_id in self.state.world.locations:
            for minutes in (12 * 60, 23 * 60):
                state = replace(
                    self.state, minutes=minutes, player=replace(self.state.player, location_id=location_id)
                )
                app = App(state, handle_command)
                app.font = pygame.font.SysFont(None, 24)
                app.font_big = pygame.font.SysFont(None, 32)
                app.load_player_sprites()
                app.render(screen)
        pygame.quit()


if __name__ == "__main__":
    unittest.main()
