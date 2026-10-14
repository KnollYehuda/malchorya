import pygame
from dataclasses import dataclass
from typing import Callable, Optional

from core.state import GameState
from core.clock import format_clock
from ui.props import ENEMY_BUILDERS, NPC_STYLES
from ui.scene import ENTITY_SLOTS, HUB, SceneBuilder
from core.enums import WindDirection
from core.consts import MALCHORYA, WINDOW_W, WINDOW_H, FPS, HUD_W, PADDING, LINE_H
from core.enums import WindDirection




SPRITE_DIR = "malchorya/assets/sprites/player"
SPRITE_FRAME_COUNT = 4
WALK_FRAME_MS = 110
WALK_ANIMATION_MS = 330


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
        self.input_active = False
        self.input_buffer = ""
        self.scene_builder = SceneBuilder()
        self.entity_sprites: dict[str, pygame.Surface] = {}
        self.player_frames: dict[WindDirection, list[pygame.Surface]] = {}
        self.facing = WindDirection.SOUTH
        self.walking_until = 0

    def run(self) -> None:
        pygame.init()
        pygame.display.set_caption(self.config.title)
        screen = pygame.display.set_mode((self.config.width, self.config.height))
        self.load_player_sprites()

        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)
        self.font_big = pygame.font.SysFont(None, 32)

        self.running = True
        while self.running:
            self.clock.tick(self.config.fps)
            self._handle_events()
            self.render(screen)

        pygame.quit()

    def load_player_sprites(self) -> None:
        """Load the pre-cut frames (see tools/extract_sprites.py)."""
        frames: dict[WindDirection, list[pygame.Surface]] = {}
        for direction in (WindDirection.NORTH, WindDirection.SOUTH, WindDirection.WEST):
            frames[direction] = [
                pygame.image.load(f"{SPRITE_DIR}/player_{direction.value}_{frame}.png").convert_alpha()
                for frame in range(SPRITE_FRAME_COUNT)
            ]
        # The sheet's "west" row actually faces right, so it becomes east and west is its mirror.
        frames[WindDirection.EAST] = frames[WindDirection.WEST]
        frames[WindDirection.WEST] = [
            pygame.transform.flip(frame, True, False) for frame in frames[WindDirection.EAST]
        ]
        self.player_frames = frames

    def current_player_sprite(self) -> Optional[pygame.Surface]:
        if not self.player_frames:
            return None
        frames = self.player_frames[self.facing]
        if pygame.time.get_ticks() < self.walking_until:
            return frames[(pygame.time.get_ticks() // WALK_FRAME_MS) % len(frames)]
        return frames[0]

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN:
                if self.input_active:
                    self._handle_input_key(event)
                    continue

                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    return

                raw = None

                if event.key in (pygame.K_RETURN, pygame.K_SLASH):
                    self.input_active = True
                    self.input_buffer = ""
                    continue

                direction = self.key_to_direction(event.key)
                if direction is not None:
                    raw = f"move {direction.name.lower()}"
                    self.facing = direction
                    self.walking_until = pygame.time.get_ticks() + WALK_ANIMATION_MS
                elif event.key == pygame.K_i:
                    raw = "inventory"
                elif event.key == pygame.K_l:
                    raw = "look"
                elif event.key == pygame.K_t:
                    npcs = self.state.npcs_here()
                    if len(npcs) == 1:
                        raw = f"talk {npcs[0].id}"
                    else:
                        raw = "look"
                elif event.key == pygame.K_c:
                    raw = "status"
                elif event.key == pygame.K_q:
                    raw = "quests"
                elif event.key == pygame.K_f:
                    raw = "attack"
                elif event.key == pygame.K_h:
                    raw = "use health_potion"
                elif event.key == pygame.K_z:
                    raw = "rest"
                else:
                    raw = ""
                if raw:
                    self._run_command(raw)

    def _run_command(self, raw: str) -> None:
        result = self.on_command(self.state, raw)
        self.state = result.state
        self.last_message = result.message
        self.messages.append(result.message)
        self.messages = self.messages[-6:]

    def _handle_input_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            self.input_active = False
        elif event.key == pygame.K_RETURN:
            raw = self.input_buffer.strip()
            self.input_active = False
            if raw.lower() == "quit":
                self.running = False
            elif raw:
                self._run_command(raw)
        elif event.key == pygame.K_BACKSPACE:
            self.input_buffer = self.input_buffer[:-1]
        elif event.unicode and event.unicode.isprintable():
            self.input_buffer += event.unicode

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
        w, h = self.config.width, self.config.height
        view_w = w - HUD_W

        view_rect = pygame.Rect(0, 0, view_w, h)
        hud_rect = pygame.Rect(view_w, 0, HUD_W, h)

        self.draw_world(screen, view_rect)
        self.draw_night_tint(screen, view_rect)
        self.draw_hud(screen, hud_rect)

        pygame.display.flip()

    def blit_wrapped_text(
        self,
        screen: pygame.Surface,
        text: str,
        x: int,
        y: int,
        max_width: int,
        *,
        line_h: int = 22,
        max_lines: int | None = None,
    ) -> int:
        assert self.font is not None
        words = text.split()
        line = ""
        lines: list[str] = []

        for w in words:
            test = f"{line} {w}".strip()
            if self.font.size(test)[0] <= max_width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = w

        if line:
            lines.append(line)

        if max_lines is not None:
            lines = lines[:max_lines]

        for ln in lines:
            self.blit_text(screen, ln, x, y)
            y += line_h

        return y

    def draw_night_tint(self, screen: pygame.Surface, view_rect: pygame.Rect) -> None:
        hour = self.state.hour
        if hour >= 21 or hour < 5:
            alpha = 120
        elif hour >= 19 or hour < 6:
            alpha = 60
        else:
            return
        tint = pygame.Surface(view_rect.size, pygame.SRCALPHA)
        tint.fill((5, 8, 30, alpha))
        screen.blit(tint, view_rect.topleft)

    def entity_sprite(self, cache_key: str, builder) -> pygame.Surface:
        if cache_key not in self.entity_sprites:
            self.entity_sprites[cache_key] = builder()
        return self.entity_sprites[cache_key]

    def draw_world(self, screen: pygame.Surface, view_rect: pygame.Rect) -> None:
        from core.enemies import ENEMY_DEFS

        location = self.state.world.locations[self.state.player.location_id]
        scene = self.scene_builder.scene_for(location.id, location.biome, location.exits.keys())
        screen.blit(scene.back, (0, 0))

        # (sort_bottom, surface, rect, label, health_ratio)
        drawables = [(rect.bottom, surface, rect, None, None) for surface, rect in scene.props]

        slot_index = 0
        for enemy in self.state.enemies.get(location.id, [])[: len(ENTITY_SLOTS)]:
            enemy_def = ENEMY_DEFS[enemy.def_id]
            sprite = self.entity_sprite(f"enemy:{enemy.def_id}", ENEMY_BUILDERS[enemy.def_id])
            slot_x, slot_y = ENTITY_SLOTS[slot_index]
            slot_index += 1
            if slot_x > 0:
                sprite = pygame.transform.flip(sprite, True, False)
            rect = sprite.get_rect(midbottom=(HUB[0] + slot_x, HUB[1] + slot_y))
            drawables.append((rect.bottom, sprite, rect, enemy_def.name, enemy.hp / enemy_def.max_hp))

        for npc in self.state.npcs_here()[: len(ENTITY_SLOTS) - slot_index]:
            sprite = self.entity_sprite(f"npc:{npc.kind.value}", NPC_STYLES[npc.kind.value])
            slot_x, slot_y = ENTITY_SLOTS[slot_index]
            slot_index += 1
            rect = sprite.get_rect(midbottom=(HUB[0] + slot_x, HUB[1] + slot_y))
            drawables.append((rect.bottom, sprite, rect, npc.name, None))

        player_sprite = self.current_player_sprite()
        if player_sprite:
            player_rect = player_sprite.get_rect(midbottom=HUB)
            shadow = pygame.Surface((76, 20), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 100), shadow.get_rect())
            screen.blit(shadow, shadow.get_rect(center=(HUB[0], HUB[1] - 3)))
            drawables.append((player_rect.bottom, player_sprite, player_rect, self.state.player.name, None))

        drawables.sort(key=lambda entry: entry[0])
        for _, surface, rect, _, _ in drawables:
            screen.blit(surface, rect)

        screen.blit(scene.overlay, (0, 0))

        for _, _, rect, label, health_ratio in drawables:
            if label is None:
                continue
            self.draw_label(screen, label, rect, health_ratio)

    def draw_label(self, screen: pygame.Surface, label: str, rect: pygame.Rect, health_ratio: Optional[float]) -> None:
        assert self.font is not None
        text = self.font.render(label, True, (240, 236, 220))
        shadow = self.font.render(label, True, (0, 0, 0))
        label_x = rect.centerx - text.get_width() // 2
        label_y = rect.top - 18
        screen.blit(shadow, (label_x + 1, label_y + 1))
        screen.blit(text, (label_x, label_y))
        if health_ratio is not None:
            bar = pygame.Rect(rect.centerx - 24, label_y - 8, 48, 6)
            pygame.draw.rect(screen, (40, 10, 10), bar)
            pygame.draw.rect(screen, (200, 50, 50), (bar.x, bar.y, int(bar.width * max(0, health_ratio)), bar.height))
            pygame.draw.rect(screen, (0, 0, 0), bar, 1)

    def wrap_lines(self, text: str, max_width: int) -> list[str]:
        assert self.font is not None
        lines: list[str] = []
        for paragraph in text.split("\n"):
            current = ""
            for word in paragraph.split():
                candidate = f"{current} {word}".strip()
                if self.font.size(candidate)[0] <= max_width:
                    current = candidate
                else:
                    if current:
                        lines.append(current)
                    current = word
            lines.append(current)
        return lines

    def draw_hud(self, screen: pygame.Surface, hud_rect: pygame.Rect) -> None:
        assert self.font is not None and self.font_big is not None
        from core.enemies import ENEMY_DEFS
        from core.items import ITEM_DEFS
        from core.progression import effective_stats, xp_needed_for_next_level
        from core.quests import QUESTS

        pygame.draw.rect(screen, (12, 12, 18), hud_rect)
        pygame.draw.rect(screen, (60, 60, 90), hud_rect, 2)

        cursor_x = hud_rect.x + PADDING
        cursor_y = hud_rect.y + PADDING
        max_text_w = hud_rect.width - (PADDING * 2)
        small_gap = LINE_H // 2

        player = self.state.player
        location = self.state.world.locations[player.location_id]

        self.blit_text(screen, location.name, cursor_x, cursor_y, big=True)
        cursor_y += 36
        cursor_y = self.blit_wrapped_text(
            screen, location.description, cursor_x, cursor_y,
            max_width=max_text_w, line_h=LINE_H, max_lines=3,
        )
        cursor_y += small_gap

        self.blit_text(screen, format_clock(self.state.minutes), cursor_x, cursor_y, color=(200, 200, 140))
        cursor_y += LINE_H + 2

        max_hp, attack, defense = effective_stats(player)
        bar_rect = pygame.Rect(cursor_x, cursor_y, max_text_w, 14)
        pygame.draw.rect(screen, (50, 20, 20), bar_rect)
        fill_width = int(bar_rect.width * max(0, player.hp) / max_hp)
        pygame.draw.rect(screen, (190, 50, 50), pygame.Rect(cursor_x, cursor_y, fill_width, 14))
        pygame.draw.rect(screen, (90, 90, 110), bar_rect, 1)
        cursor_y += 18
        self.blit_text(
            screen,
            f"HP {player.hp}/{max_hp}  Lv {player.level} ({player.xp}/{xp_needed_for_next_level(player.level)})",
            cursor_x, cursor_y,
        )
        cursor_y += LINE_H
        keter_amount = self.safe_get_keter_amount(player)
        self.blit_text(screen, f"ATK {attack}  DEF {defense}  Keter {keter_amount}", cursor_x, cursor_y)
        cursor_y += LINE_H + small_gap

        exits = ", ".join(direction.name.lower() for direction in location.exits.keys()) or "none"
        self.blit_text(screen, f"Exits: {exits}", cursor_x, cursor_y)
        cursor_y += LINE_H

        npcs_here = self.state.npcs_here()
        if npcs_here:
            npc_line = ", ".join(f"{npc.name} ({npc.id})" for npc in npcs_here)
            cursor_y = self.blit_wrapped_text(
                screen, f"Here: {npc_line}", cursor_x, cursor_y, max_width=max_text_w, line_h=LINE_H, max_lines=3
            )

        loc_items = self.state.location_items.get(location.id, {})
        if loc_items:
            item_line = ", ".join(f"{ITEM_DEFS[item_id].name} x{amount}" for item_id, amount in loc_items.items())
            cursor_y = self.blit_wrapped_text(
                screen, f"Ground: {item_line}", cursor_x, cursor_y, max_width=max_text_w, line_h=LINE_H, max_lines=2
            )

        enemies_here = self.state.enemies.get(location.id, [])
        if enemies_here:
            enemy_line = ", ".join(
                f"{ENEMY_DEFS[enemy.def_id].name} {enemy.hp}/{ENEMY_DEFS[enemy.def_id].max_hp}"
                for enemy in enemies_here
            )
            for line in self.wrap_lines(f"Hostile: {enemy_line}", max_text_w)[:3]:
                self.blit_text(screen, line, cursor_x, cursor_y, color=(255, 130, 130))
                cursor_y += LINE_H

        active_quests = [
            quest_id for quest_id, status in self.state.quest_log.items() if status.value == "in_progress"
        ]
        if active_quests:
            cursor_y += small_gap
            self.blit_text(screen, "Quests:", cursor_x, cursor_y, color=(200, 200, 140))
            cursor_y += LINE_H
            for quest_id in active_quests[:4]:
                cursor_y = self.blit_wrapped_text(
                    screen, f"* {QUESTS[quest_id].name}", cursor_x, cursor_y,
                    max_width=max_text_w, line_h=LINE_H, max_lines=1,
                )

        footer_lines = [
            "WASD move | F attack | H potion",
            "L look | I inv | T talk | C stat",
            "Q quests | Z rest | Enter: command",
        ]
        footer_top = hud_rect.bottom - PADDING - LINE_H * len(footer_lines)

        # Log: as many of the newest lines as fit between the stats and the footer.
        cursor_y += small_gap
        pygame.draw.line(screen, (60, 60, 90), (cursor_x, cursor_y), (cursor_x + max_text_w, cursor_y))
        cursor_y += 4
        log_lines: list[str] = []
        for message in self.messages:
            if not message:
                continue
            wrapped = self.wrap_lines(message, max_text_w - 12)
            log_lines.append("- " + wrapped[0])
            log_lines.extend("  " + line for line in wrapped[1:])
        capacity = max(0, (footer_top - 4 - cursor_y) // (LINE_H - 2))
        for line in log_lines[-capacity:] if capacity else []:
            self.blit_text(screen, line, cursor_x, cursor_y, color=(215, 215, 225))
            cursor_y += LINE_H - 2

        if self.input_active:
            pygame.draw.rect(screen, (30, 30, 50), (hud_rect.x + 6, footer_top + LINE_H * 2 - 4, hud_rect.width - 12, LINE_H + 4))
            self.blit_text(screen, f"> {self.input_buffer}_", cursor_x, footer_top + LINE_H * 2)
        else:
            for index, footer in enumerate(footer_lines):
                self.blit_text(screen, footer, cursor_x, footer_top + index * LINE_H, color=(150, 150, 170))

    def blit_text(self, screen: pygame.Surface, text: str, x: int, y: int, big: bool = False, color=(235, 235, 245)) -> None:
        assert self.font is not None and self.font_big is not None
        font = self.font_big if big else self.font
        surf = font.render(text, True, color)
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
