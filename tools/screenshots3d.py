"""Render locations in the 3D client headless. Run via ./build.sh screenshots3d [ids]."""
import os
import sys
from dataclasses import replace

import pygame

from core.world import create_world
from core.state import create_initial_state
from logic.handle_command import handle_command
from ui3d.app3d import Game3D


def main(out_dir: str, only: list[str]) -> None:
    pygame.init()
    world = create_world()
    base_state = create_initial_state(world)
    game = Game3D(base_state, handle_command, headless=True, size=(1280, 720))
    ids = only or list(world.locations)
    for location_id in ids:
        for label, minutes in (("day", 12 * 60), ("night", 23 * 60)):
            game.state = replace(
                game.state, minutes=minutes, player=replace(game.state.player, location_id=location_id)
            )
            game.sync_world(arrival=(0.0, -4.0))
            game.update(0.016)
            game.save_screenshot(os.path.join(out_dir, f"{location_id}_{label}.png"))
            if not only:
                break


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
