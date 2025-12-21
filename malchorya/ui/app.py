import pygame
from dataclasses import dataclass
from typing import Callable, Optional

from core.state import GameState
from core.enums import WindDirection
from core.consts import MALCHORYA, WINDOW_W, WINDOW_H, FPS
from core.enums import WindDirection




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
        on_command: Callable[[GameState, WindDirection], GameState],
        config: UiConfig = UiConfig(),
    ) -> None:
        self.state = state
        self.on_command = on_command
        self.config = config

        self.running = False
        self.clock: Optional[pygame.time.Clock] = None
        self.font: Optional[pygame.font.Font] = None
        self.font_big: Optional[pygame.font.Font] = None
        self.last_message = ""
        self.messages = []

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
            self._handle_events()
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

                raw = None

                direction = self.key_to_direction(event.key)
                if direction is not None:
                    raw = f"move {direction.name.lower()}"
                elif event.key == pygame.K_i:
                    raw = "inventory"
                elif event.key == pygame.K_l:
                    raw = "look"
                elif event.key == pygame.K_t:
                    npcs = self.state.world.get_npcs_in_location(self.state.player.location_id)
                    if len(npcs) == 1:
                        raw = f"talk {npcs[0].id}"
                    else:
                        raw = "look"
                elif event.key == pygame.K_c:
                    raw = "status"
                else:
                    raw = ""
                if raw:
                    result = self.on_command(self.state, raw)
                    self.state = result.state
                    self.last_message = result.message
                    self.messages.append(result.message)
                    self.messages = self.messages[-6:]

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

        y = 190
        for msg in self.messages[-6:]:
            if not msg:
                continue
            self.blit_text(screen, msg, 20, y)
            y += 22
        
    def blit_text(self, screen: pygame.Surface, text: str, x: int, y: int, big: bool = False) -> None:
        assert self.font is not None and self.font_big is not None
        font = self.font_big if big else self.font
        surf = font.render(text, True, (235, 235, 245))
        screen.blit(surf, (x, y))

    def safe_get_keter_amount(self, player) -> int:
        inv = getattr(player, "inventory", None)
        if inv is None:
            return 0

        items = getattr(inv, "items", None)
        if isinstance(items, dict):
            for item_id, amount in items.items():
                # item_id הוא Enum עם value כמו "keter"
                if getattr(item_id, "value", None) == "keter":
                    return int(amount)
                # fallback נוסף אם זה Enum עם name
                if getattr(item_id, "name", "").lower() == "keter":
                    return int(amount)

        return 0
