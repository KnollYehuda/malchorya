"""Render every location headless and save PNGs. Run via ./build.sh screenshots."""
import os
import sys
from dataclasses import replace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from core.world import create_world
from core.state import create_initial_state
from logic.handle_command import handle_command
from ui.app import App


def main(out_dir: str, only: list[str]) -> None:
    world = create_world()
    base_state = create_initial_state(world)
    pygame.init()
    screen = pygame.display.set_mode((960, 540))
    for location_id in world.locations:
        if only and location_id not in only:
            continue
        for label, minutes in (("day", 12 * 60), ("night", 23 * 60)):
            state = replace(base_state, minutes=minutes, player=replace(base_state.player, location_id=location_id))
            app = App(state, handle_command)
            app.font = pygame.font.SysFont(None, 24)
            app.font_big = pygame.font.SysFont(None, 32)
            app.load_player_sprites()
            app.render(screen)
            pygame.image.save(screen, os.path.join(out_dir, f"{location_id}_{label}.png"))
            if not only:
                break


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
