"""Builds (and caches) the static look of each location."""
import math
import random
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

import pygame

from core.enums import WindDirection
from ui import props as prop_library
from ui.textures import TILE, ground_variants, shade

VIEW_WIDTH = 640
VIEW_HEIGHT = 540
HUB = (320, 290)  # where the player stands (feet)
WALL_HEIGHT = 128
PATH_HALF_WIDTH = 48

# Where NPCs / enemies stand, relative to the hub.
ENTITY_SLOTS = [(-170, -40), (170, -40), (-150, 95), (150, 95)]

PLAYER_ZONE = pygame.Rect(HUB[0] - 70, HUB[1] - 130, 140, 160)

Color = Tuple[int, ...]


@dataclass(frozen=True)
class BiomeStyle:
    ground: str
    base: Color
    variation: int = 7
    path: Optional[str] = "dirt"  # dirt | cobble | None
    path_base: Color = (118, 96, 66)
    hub: Tuple[int, int] = (240, 170)
    indoor: bool = False
    water_rows: int = 0
    special: Optional[str] = None
    props: Tuple[Tuple[str, int], ...] = ()
    fixed: Tuple[Tuple[str, int, int], ...] = ()
    glows: Tuple[Tuple[int, int, int, Color], ...] = ()
    fog: Optional[Color] = None
    vignette: int = 150


BIOMES: Dict[str, BiomeStyle] = {
    "crossroads": BiomeStyle(
        ground="grass", base=(66, 100, 48),
        props=(("tree_round", 5), ("bush", 6), ("rock", 3), ("flowers", 7), ("fence", 2)),
        fixed=(("signpost", 392, 262),),
    ),
    "pinewood": BiomeStyle(
        ground="needles", base=(46, 70, 46),
        props=(("pine", 17), ("bush", 4), ("rock", 3), ("stump", 2), ("mushrooms", 2)),
        vignette=170,
    ),
    "forest_depths": BiomeStyle(
        ground="needles", base=(28, 44, 32), variation=6, path_base=(76, 62, 46),
        props=(("pine", 13), ("tree_round", 8), ("bush", 5), ("mushrooms", 5), ("stump", 3), ("rock", 3)),
        fog=(20, 36, 30, 46), vignette=200,
    ),
    "hermit_hut": BiomeStyle(
        ground="grass", base=(46, 82, 46), path_base=(96, 80, 56),
        props=(("tree_round", 6), ("pine", 5), ("bush", 5), ("herbs", 6), ("mushrooms", 3), ("stump", 2)),
        fixed=(("hut", 320, 205), ("campfire", 470, 360), ("barrel", 180, 300)),
        glows=((470, 340, 90, (255, 150, 60, 40)),),
        vignette=190,
    ),
    "riverbank": BiomeStyle(
        ground="grass", base=(70, 104, 54), water_rows=4,
        props=(("reeds", 8), ("rock", 4), ("bush", 3), ("tree_round", 2), ("flowers", 5)),
    ),
    "river_dock": BiomeStyle(
        ground="water", base=(40, 86, 128), variation=8, path=None, special="dock",
        props=(("reeds", 4), ("rock", 2)),
        fixed=(("boat", 500, 410),),
    ),
    "town_square": BiomeStyle(
        ground="grass", base=(70, 102, 56), path="cobble", path_base=(128, 122, 112), hub=(520, 340),
        props=(("bush", 3), ("flowers", 4)),
        fixed=(
            ("house", 105, 205), ("house", 535, 205), ("house", 105, 505), ("house", 535, 505),
            ("lamp_post", 235, 345), ("lamp_post", 405, 345), ("barrel", 38, 330),
            ("crate", 602, 330), ("well", 530, 355),
        ),
        glows=((235, 300, 80, (255, 200, 110, 32)), (405, 300, 80, (255, 200, 110, 32))),
        vignette=120,
    ),
    "blacksmith": BiomeStyle(
        ground="slabs", base=(84, 80, 80), variation=8, path=None, indoor=True,
        fixed=(
            ("furnace", 120, 190), ("weapon_rack", 520, 190), ("window", 330, 128),
            ("anvil", 230, 330), ("barrel", 598, 250), ("crate", 40, 420), ("barrel", 80, 470),
            ("crate", 560, 440),
        ),
        glows=((120, 150, 200, (255, 120, 40, 60)), (230, 300, 90, (255, 150, 60, 22))),
        vignette=190,
    ),
    "tavern": BiomeStyle(
        ground="planks", base=(122, 84, 50), variation=8, path=None, indoor=True,
        fixed=(
            ("fireplace", 110, 188), ("shelves", 440, 112), ("bar_counter", 470, 200),
            ("table", 150, 400), ("stool", 100, 430), ("stool", 205, 430),
            ("table", 500, 430), ("stool", 450, 460), ("stool", 555, 460),
            ("barrel", 600, 300), ("barrel", 600, 345), ("mat", 320, 90),
        ),
        glows=((110, 170, 220, (255, 130, 50, 62)), (320, 330, 200, (255, 190, 100, 18))),
        vignette=190,
    ),
    "chapel": BiomeStyle(
        ground="slabs", base=(168, 164, 154), variation=6, path=None, indoor=True,
        fixed=(
            ("altar", 320, 172), ("window", 110, 128), ("window", 530, 128),
            ("banner", 220, 118), ("banner", 420, 118),
            ("candle_stand", 190, 240), ("candle_stand", 450, 240),
            ("pew", 175, 350), ("pew", 465, 350), ("pew", 175, 440), ("pew", 465, 440),
        ),
        glows=((190, 210, 110, (255, 220, 140, 44)), (450, 210, 110, (255, 220, 140, 44)),
               (320, 160, 160, (255, 220, 150, 30))),
        vignette=170,
    ),
    "watchtower": BiomeStyle(
        ground="rubble", base=(96, 92, 80), variation=8, path_base=(100, 86, 62),
        props=(("rock", 6), ("dead_tree", 3), ("ruin_wall", 3), ("crate", 3), ("barrel", 2), ("bush", 2)),
        fixed=(("tower_ruin", 480, 205), ("tent", 125, 195), ("campfire", 410, 390), ("tent", 150, 480)),
        glows=((410, 370, 110, (255, 140, 50, 48)),),
        vignette=190,
    ),
    "south_road": BiomeStyle(
        ground="grass", base=(70, 90, 48), path_base=(92, 76, 54),
        props=(("dead_tree", 3), ("tree_round", 3), ("bush", 6), ("rock", 4), ("reeds", 3), ("fence", 3)),
        fog=(120, 130, 120, 22), vignette=160,
    ),
    "marsh": BiomeStyle(
        ground="marsh", base=(54, 66, 44), variation=6, path=None,
        props=(("pool", 7), ("reeds", 14), ("dead_tree", 5), ("rock", 3), ("mushrooms", 4), ("herbs", 4)),
        fog=(110, 140, 120, 52), vignette=210,
    ),
}
DEFAULT_BIOME = BiomeStyle(ground="grass", base=(60, 96, 50), props=(("tree_round", 4), ("bush", 4)))

PLACED = Tuple[pygame.Surface, pygame.Rect]


@dataclass
class Scene:
    back: pygame.Surface
    props: List[PLACED]
    overlay: pygame.Surface
    style: BiomeStyle = DEFAULT_BIOME


def _radial_overlay(width: int, height: int, strength: int) -> pygame.Surface:
    """Smooth dark vignette: nested ellipses, outermost darkest."""
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.fill((4, 6, 12, strength))
    steps = 90
    for step in range(steps):
        progress = step / steps
        alpha = int(strength * (1 - progress) ** 1.7)
        radius_x = int(width * (0.78 - 0.46 * progress))
        radius_y = int(height * (0.74 - 0.44 * progress))
        pygame.draw.ellipse(
            surface, (4, 6, 12, alpha), (HUB[0] - radius_x, HUB[1] - radius_y, radius_x * 2, radius_y * 2)
        )
    return surface


def _glow(radius: int, color: Color) -> pygame.Surface:
    surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    steps = 14
    for step in range(steps):
        step_radius = radius * (1 - step / steps)
        alpha = int(color[3] * (step + 1) / steps * 0.5)
        pygame.draw.circle(surface, (*color[:3], alpha), (radius, radius), int(step_radius))
    return surface


class SceneBuilder:
    def __init__(self) -> None:
        self._cache: Dict[str, Scene] = {}
        self._overlay_cache: Dict[int, pygame.Surface] = {}

    def scene_for(self, location_id: str, biome: str, exits: Iterable[WindDirection]) -> Scene:
        if location_id not in self._cache:
            self._cache[location_id] = self._build(location_id, biome, list(exits))
        return self._cache[location_id]

    # ------------------------------------------------------------------ build

    def _build(self, location_id: str, biome: str, exits: List[WindDirection]) -> Scene:
        style = BIOMES.get(biome, DEFAULT_BIOME)
        rng = random.Random(location_id)
        back = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
        blocked: List[pygame.Rect] = []

        self._fill_ground(back, style, rng)
        if style.indoor:
            self._draw_walls(back, rng)
            blocked.append(pygame.Rect(0, 0, VIEW_WIDTH, WALL_HEIGHT))
        elif style.special == "dock":
            blocked.extend(self._draw_dock(back, rng))
        elif style.water_rows:
            blocked.extend(self._draw_river(back, style, rng))

        if style.path and not style.indoor:
            blocked.extend(self._draw_paths(back, style, exits, rng))
        self._draw_exit_markers(back, style, exits)

        props = self._place_props(back, style, rng, blocked)
        overlay = self._build_overlay(style)
        return Scene(back=back, props=props, overlay=overlay, style=style)

    def _fill_ground(self, surface: pygame.Surface, style: BiomeStyle, rng: random.Random) -> None:
        variants = ground_variants(style.ground, style.base, style.variation)
        for tile_y in range(0, VIEW_HEIGHT, TILE):
            for tile_x in range(0, VIEW_WIDTH, TILE):
                surface.blit(rng.choice(variants), (tile_x, tile_y))
        if style.ground in ("grass", "needles") and not style.indoor:
            self._scatter_patches(surface, style, rng)

    def _scatter_patches(self, surface: pygame.Surface, style: BiomeStyle, rng: random.Random) -> None:
        for _ in range(26):
            patch = pygame.Surface((90, 50), pygame.SRCALPHA)
            tint = shade(style.base, rng.choice([-14, 12]))
            pygame.draw.ellipse(patch, (*tint, 70), patch.get_rect())
            surface.blit(patch, (rng.randrange(VIEW_WIDTH - 60), rng.randrange(VIEW_HEIGHT - 40)))

    def _draw_walls(self, surface: pygame.Surface, rng: random.Random) -> None:
        wall_base = (118, 104, 92)
        variants = ground_variants("brick", wall_base, 9)
        for tile_y in range(0, WALL_HEIGHT, TILE):
            for tile_x in range(0, VIEW_WIDTH, TILE):
                surface.blit(rng.choice(variants), (tile_x, tile_y))
        shadow = pygame.Surface((VIEW_WIDTH, 26), pygame.SRCALPHA)
        for row in range(26):
            pygame.draw.line(shadow, (0, 0, 0, int(110 * (1 - row / 26))), (0, row), (VIEW_WIDTH, row))
        surface.blit(shadow, (0, WALL_HEIGHT))
        pygame.draw.rect(surface, (70, 52, 40), (0, WALL_HEIGHT - 8, VIEW_WIDTH, 8))
        pygame.draw.line(surface, (140, 112, 84), (0, WALL_HEIGHT - 8), (VIEW_WIDTH, WALL_HEIGHT - 8), 2)

    def _draw_river(self, surface: pygame.Surface, style: BiomeStyle, rng: random.Random) -> List[pygame.Rect]:
        water = ground_variants("water", (46, 98, 138), 8)
        sand = ground_variants("sand", (176, 160, 112), 8)
        for row in range(style.water_rows):
            for tile_x in range(0, VIEW_WIDTH, TILE):
                surface.blit(rng.choice(water), (tile_x, row * TILE))
        shore_y = style.water_rows * TILE
        for tile_x in range(0, VIEW_WIDTH, TILE):
            if rng.random() < 0.85:
                surface.blit(rng.choice(sand), (tile_x, shore_y - rng.randint(0, 10)))
        foam = pygame.Surface((VIEW_WIDTH, 6), pygame.SRCALPHA)
        for foam_x in range(0, VIEW_WIDTH, 5):
            pygame.draw.circle(foam, (230, 240, 245, 120), (foam_x, 3 + rng.randint(-1, 1)), 2)
        surface.blit(foam, (0, shore_y - 6))
        return [pygame.Rect(0, 0, VIEW_WIDTH, shore_y + 4)]

    def _draw_dock(self, surface: pygame.Surface, rng: random.Random) -> List[pygame.Rect]:
        planks = ground_variants("planks", (132, 96, 58), 8)
        dock_rect = pygame.Rect(0, HUB[1] - 44, 440, 96)
        platform = pygame.Rect(360, HUB[1] - 76, 160, 160)
        for outline_rect in (dock_rect, platform):
            pygame.draw.rect(surface, (52, 34, 20), outline_rect.inflate(6, 6))
        for tile_x in range(dock_rect.left, dock_rect.right, TILE):
            for tile_y in range(dock_rect.top, dock_rect.bottom, TILE):
                surface.blit(rng.choice(planks), (tile_x, tile_y))
        for tile_x in range(platform.left, platform.right, TILE):
            for tile_y in range(platform.top, platform.bottom, TILE):
                surface.blit(rng.choice(planks), (tile_x, tile_y))
        for post_x in range(40, 360, 80):
            for post_y in (dock_rect.top - 2, dock_rect.bottom - 6):
                pygame.draw.rect(surface, (84, 58, 34), (post_x, post_y, 8, 8))
                pygame.draw.rect(surface, (46, 30, 18), (post_x, post_y, 8, 8), 1)
        return [dock_rect.inflate(20, 20), platform.inflate(20, 20)]

    def _draw_paths(
        self, surface: pygame.Surface, style: BiomeStyle, exits: List[WindDirection], rng: random.Random
    ) -> List[pygame.Rect]:
        variants = ground_variants(style.path, style.path_base, 8)
        real_surface = surface
        surface = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT), pygame.SRCALPHA)
        rects: List[pygame.Rect] = []
        hub_x, hub_y = HUB
        corridors = {
            WindDirection.NORTH: pygame.Rect(hub_x - PATH_HALF_WIDTH, 0, PATH_HALF_WIDTH * 2, hub_y),
            WindDirection.SOUTH: pygame.Rect(hub_x - PATH_HALF_WIDTH, hub_y, PATH_HALF_WIDTH * 2, VIEW_HEIGHT - hub_y),
            WindDirection.WEST: pygame.Rect(0, hub_y - PATH_HALF_WIDTH, hub_x, PATH_HALF_WIDTH * 2),
            WindDirection.EAST: pygame.Rect(hub_x, hub_y - PATH_HALF_WIDTH, VIEW_WIDTH - hub_x, PATH_HALF_WIDTH * 2),
        }
        for direction in exits:
            corridor = corridors[direction]
            rects.append(corridor.inflate(24, 24))
            self._blit_ragged(surface, variants, corridor, rng, rng_skip=0.28)

        hub_width, hub_height = style.hub
        hub_rect = pygame.Rect(0, 0, hub_width, hub_height)
        hub_rect.center = (hub_x, hub_y - 10)
        self._blit_ellipse(surface, variants, hub_rect, rng)
        rects.append(hub_rect.inflate(16, 16))

        silhouette = pygame.mask.from_surface(surface).to_surface(
            setcolor=(14, 12, 6, 120), unsetcolor=(0, 0, 0, 0)
        )
        blurred = pygame.transform.smoothscale(
            pygame.transform.smoothscale(silhouette, (VIEW_WIDTH // 6, VIEW_HEIGHT // 6)),
            (VIEW_WIDTH, VIEW_HEIGHT),
        )
        real_surface.blit(blurred, (0, 3))
        real_surface.blit(surface, (0, 0))
        return rects

    @staticmethod
    def _blit_ragged(
        surface: pygame.Surface, variants: list, rect: pygame.Rect, rng: random.Random, rng_skip: float
    ) -> None:
        for tile_y in range(rect.top - TILE, rect.bottom + TILE, TILE):
            for tile_x in range(rect.left - TILE // 2, rect.right + TILE // 2, TILE):
                center = (tile_x + TILE // 2, tile_y + TILE // 2)
                if not rect.inflate(TILE, TILE).collidepoint(center):
                    continue
                on_edge = not rect.inflate(-TILE, -TILE).collidepoint(center)
                if on_edge and rng.random() < rng_skip:
                    continue
                surface.blit(rng.choice(variants), (tile_x + rng.randint(-2, 2), tile_y + rng.randint(-2, 2)))

    @staticmethod
    def _blit_ellipse(surface: pygame.Surface, variants: list, rect: pygame.Rect, rng: random.Random) -> None:
        radius_x, radius_y = rect.width / 2, rect.height / 2
        for tile_y in range(rect.top, rect.bottom, TILE):
            for tile_x in range(rect.left, rect.right, TILE):
                offset_x = (tile_x + TILE / 2 - rect.centerx) / radius_x
                offset_y = (tile_y + TILE / 2 - rect.centery) / radius_y
                distance = offset_x * offset_x + offset_y * offset_y
                if distance > 1.05 or (distance > 0.78 and rng.random() < 0.4):
                    continue
                surface.blit(rng.choice(variants), (tile_x + rng.randint(-2, 2), tile_y + rng.randint(-2, 2)))

    def _draw_exit_markers(self, surface: pygame.Surface, style: BiomeStyle, exits: List[WindDirection]) -> None:
        hub_x, hub_y = HUB
        for direction in exits:
            if style.indoor and direction == WindDirection.NORTH:
                door = pygame.Rect(hub_x - 30, WALL_HEIGHT - 92, 60, 92)
                pygame.draw.rect(surface, (44, 30, 22), door.inflate(10, 6), border_top_left_radius=30, border_top_right_radius=30)
                pygame.draw.rect(surface, (96, 64, 38), door, border_top_left_radius=26, border_top_right_radius=26)
                for plank_x in (door.left + 15, door.left + 30, door.left + 45):
                    pygame.draw.line(surface, (66, 44, 26), (plank_x, door.top + 10), (plank_x, door.bottom), 2)
                pygame.draw.circle(surface, (220, 190, 90), (door.right - 10, door.centery + 10), 3)
                continue
            if style.indoor:
                mat_rect = {
                    WindDirection.SOUTH: pygame.Rect(hub_x - 52, VIEW_HEIGHT - 44, 104, 44),
                    WindDirection.WEST: pygame.Rect(0, hub_y - 52, 44, 104),
                    WindDirection.EAST: pygame.Rect(VIEW_WIDTH - 44, hub_y - 52, 44, 104),
                }.get(direction)
                if mat_rect is not None:
                    pygame.draw.rect(surface, (92, 40, 36), mat_rect, border_radius=6)
                    pygame.draw.rect(surface, (190, 150, 70), mat_rect.inflate(-12, -12), 2, border_radius=4)
            self._chevron(surface, direction)

    @staticmethod
    def _chevron(surface: pygame.Surface, direction: WindDirection) -> None:
        hub_x, hub_y = HUB
        centers = {
            WindDirection.NORTH: (hub_x, 26),
            WindDirection.SOUTH: (hub_x, VIEW_HEIGHT - 26),
            WindDirection.WEST: (26, hub_y),
            WindDirection.EAST: (VIEW_WIDTH - 26, hub_y),
        }
        center_x, center_y = centers[direction]
        offsets = {
            WindDirection.NORTH: [(-14, 8), (0, -8), (14, 8)],
            WindDirection.SOUTH: [(-14, -8), (0, 8), (14, -8)],
            WindDirection.WEST: [(8, -14), (-8, 0), (8, 14)],
            WindDirection.EAST: [(-8, -14), (8, 0), (-8, 14)],
        }[direction]
        points = [(center_x + offset_x, center_y + offset_y) for offset_x, offset_y in offsets]
        layer = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT), pygame.SRCALPHA)
        pygame.draw.lines(layer, (0, 0, 0, 110), False, points, 7)
        pygame.draw.lines(layer, (240, 235, 200, 190), False, points, 4)
        surface.blit(layer, (0, 0))

    # ------------------------------------------------------------------ props

    def _place_props(
        self, back: pygame.Surface, style: BiomeStyle, rng: random.Random, blocked: List[pygame.Rect]
    ) -> List[PLACED]:
        placed: List[PLACED] = []
        occupied: List[pygame.Rect] = []

        slot_footprints = [
            pygame.Rect(HUB[0] + slot_x - 36, HUB[1] + slot_y - 40, 72, 50) for slot_x, slot_y in ENTITY_SLOTS
        ]

        def add(surface: pygame.Surface, foot: Tuple[int, int], name: str) -> None:
            rect = surface.get_rect(midbottom=foot)
            if name in prop_library.DECALS:
                back.blit(surface, rect)
                return
            placed.append((surface, rect))
            occupied.append(pygame.Rect(rect.centerx - rect.width * 0.3, rect.bottom - 14, rect.width * 0.6, 14))

        for name, foot_x, foot_y in style.fixed:
            add(prop_library.PROP_BUILDERS[name](rng), (foot_x, foot_y), name)

        area = pygame.Rect(0, WALL_HEIGHT if style.indoor else 0, VIEW_WIDTH, VIEW_HEIGHT)
        for name, count in style.props:
            for _ in range(count):
                for _attempt in range(40):
                    surface = prop_library.PROP_BUILDERS[name](rng)
                    width, height = surface.get_size()
                    foot_x = rng.randint(width // 2, VIEW_WIDTH - width // 2)
                    foot_y = rng.randint(area.top + height, VIEW_HEIGHT - 2)
                    rect = surface.get_rect(midbottom=(foot_x, foot_y))
                    footprint = pygame.Rect(rect.centerx - rect.width * 0.3, rect.bottom - 14, rect.width * 0.6, 14)
                    is_decal = name in prop_library.DECALS
                    if any(footprint.colliderect(zone) for zone in blocked + slot_footprints):
                        continue
                    if not is_decal and (
                        rect.colliderect(PLAYER_ZONE)
                        or any(footprint.inflate(10, 6).colliderect(other) for other in occupied)
                    ):
                        continue
                    add(surface, (foot_x, foot_y), name)
                    break

        placed.sort(key=lambda entry: entry[1].bottom)
        return placed

    # ---------------------------------------------------------------- overlay

    def _build_overlay(self, style: BiomeStyle) -> pygame.Surface:
        if style.vignette not in self._overlay_cache:
            self._overlay_cache[style.vignette] = _radial_overlay(VIEW_WIDTH, VIEW_HEIGHT, style.vignette)
        # Fog is the base layer so the vignette blends over it without a colour seam.
        overlay = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT), pygame.SRCALPHA)
        if style.fog:
            overlay.fill(style.fog)
        overlay.blit(self._overlay_cache[style.vignette], (0, 0))
        for glow_x, glow_y, radius, color in style.glows:
            glow = _glow(radius, color)
            overlay.blit(glow, (glow_x - radius, glow_y - radius))
        return overlay
