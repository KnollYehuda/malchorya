import pygame
from dataclasses import dataclass
from typing import Callable, Optional

from core.state import GameState
from core.enums import WindDirection
from core.consts import MALCHORYA, WINDOW_W, WINDOW_H, FPS




@dataclass
class UiConfig:
    title: str = MALCHORYA
    width: int = WINDOW_W
    height: int = WINDOW_H
    fps: int = FPS


class App:
    def __init__(
        self,
        state: GameState,
        on_move: Callable[[GameState, WindDirection], GameState],
        config: UiConfig = UiConfig(),
    ) -> None:
        self.state = state
        self.on_move = on_move
        self.config = config

        self.running = False
        self.clock: Optional[pygame.time.Clock] = None
        self.font: Optional[pygame.font.Font] = None
        self.font_big: Optional[pygame.font.Font] = None

    def run(self) -> None:
        pygame.init()
        pygame.display.set_caption(self.config.title)
        screen = pygame.display.set_mode((self.config.width, self.config.height))

        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)
        self.font_big = pygame.font.SysFont(None, 32)

        self.running = True
        while self.running:
            self.clock.tick(self.config.fps)
            self.handle_events()
            self.render(screen)

        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    return

                direction = self.key_to_direction(event.key)
                if direction is not None:
                    self.state = self.on_move(self.state, direction)

    @staticmethod
    def key_to_direction(key: int) -> Optional[WindDirection]:
        if key in (pygame.K_UP, pygame.K_w):
            return WindDirection.NORTH
        if key in (pygame.K_DOWN, pygame.K_s):
            return WindDirection.SOUTH
        if key in (pygame.K_LEFT, pygame.K_a):
            return WindDirection.WEST
        if key in (pygame.K_RIGHT, pygame.K_d):
            return WindDirection.EAST
        return None

    def render(self, screen: pygame.Surface) -> None:
        screen.fill((18, 18, 24))
        self.draw_hud(screen)
        pygame.display.flip()

    def draw_hud(self, screen: pygame.Surface) -> None:
        assert self.font is not None and self.font_big is not None

        player = self.state.player
        world = self.state.world
        location = world.locations[player.location_id]

        self.blit_text(screen, location.name, 20, 16, big=True)
        self.blit_text(screen, location.description, 20, 56)

        exits = ", ".join([d.name.lower() for d in location.exits.keys()]) or "none"
        self.blit_text(screen, f"Exits: {exits}", 20, 92)

        npcs_here = world.get_npcs_in_location(location.id)
        npc_line = ", ".join([f"{n.name} ({n.id})" for n in npcs_here]) if npcs_here else "none"
        self.blit_text(screen, f"NPCs: {npc_line}", 20, 124)

        keter_amount = self.safe_get_keter_amount(player)
        self.blit_text(screen, f"Keter: {keter_amount}", 20, 156)

        self.blit_text(screen, "Move: arrows/WASD | ESC: quit", 20, self.config.height - 32)

    def blit_text(self, screen: pygame.Surface, text: str, x: int, y: int, big: bool = False) -> None:
        assert self.font is not None and self.font_big is not None
        font = self.font_big if big else self.font
        surf = font.render(text, True, (235, 235, 245))
        screen.blit(surf, (x, y))

    @staticmethod
    def safe_get_keter_amount(player) -> int:
        inv = getattr(player, "inventory", None)
        if inv is None:
            return 0
        if hasattr(inv, "count"):
            try:
                return int(inv.count("keter"))
            except Exception:
                pass
        keter = getattr(inv, "keter", None)
        if keter is not None and hasattr(keter, "amount"):
            try:
                return int(keter.amount)
            except Exception:
                pass
        return 0
