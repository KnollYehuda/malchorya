"""Procedural ground textures and a supersampled drawing canvas."""
import random
from typing import Callable, Dict, Tuple

import pygame

TILE = 32
SUPERSAMPLE = 3

Color = Tuple[int, ...]


def shade(color: Color, amount: int) -> Tuple[int, int, int]:
    return tuple(max(0, min(255, channel + amount)) for channel in color[:3])


def mix(first_color: Color, second_color: Color, ratio: float) -> Tuple[int, int, int]:
    return tuple(
        int(first_channel * (1 - ratio) + second_channel * ratio)
        for first_channel, second_channel in zip(first_color[:3], second_color[:3])
    )


class Canvas:
    """Draw in logical units on an oversized surface, then smooth-scale down."""

    def __init__(self, width: int, height: int, scale: int = SUPERSAMPLE) -> None:
        self.width = width
        self.height = height
        self.scale = scale
        self.surface = pygame.Surface((width * scale, height * scale), pygame.SRCALPHA)

    def _scaled(self, value: float) -> int:
        return int(round(value * self.scale))

    def _point(self, point) -> Tuple[int, int]:
        return self._scaled(point[0]), self._scaled(point[1])

    def circle(self, color: Color, center, radius: float) -> None:
        pygame.draw.circle(self.surface, color, self._point(center), max(1, self._scaled(radius)))

    def ellipse(self, color: Color, left: float, top: float, width: float, height: float) -> None:
        rect = pygame.Rect(self._scaled(left), self._scaled(top), self._scaled(width), self._scaled(height))
        pygame.draw.ellipse(self.surface, color, rect)

    def rect(self, color: Color, left: float, top: float, width: float, height: float, radius: float = 0) -> None:
        rect = pygame.Rect(self._scaled(left), self._scaled(top), self._scaled(width), self._scaled(height))
        pygame.draw.rect(self.surface, color, rect, border_radius=self._scaled(radius))

    def polygon(self, color: Color, points) -> None:
        pygame.draw.polygon(self.surface, color, [self._point(point) for point in points])

    def line(self, color: Color, start, end, thickness: float = 1) -> None:
        pygame.draw.line(
            self.surface, color, self._point(start), self._point(end), max(1, self._scaled(thickness))
        )

    def result(self) -> pygame.Surface:
        return pygame.transform.smoothscale(self.surface, (self.width, self.height))


# ---------------------------------------------------------------- ground tiles


def _noise_surface(rng: random.Random, base: Color, variation: int) -> pygame.Surface:
    tile = pygame.Surface((TILE, TILE))
    for pixel_y in range(TILE):
        for pixel_x in range(TILE):
            tile.set_at((pixel_x, pixel_y), shade(base, rng.randint(-variation, variation)))
    return tile


def grass_tile(rng: random.Random, base: Color, variation: int) -> pygame.Surface:
    tile = _noise_surface(rng, base, variation)
    for _ in range(14):
        blade_x = rng.randrange(TILE)
        blade_y = rng.randrange(3, TILE)
        color = shade(base, rng.choice([-26, -16, 14, 24]))
        pygame.draw.line(tile, color, (blade_x, blade_y), (blade_x + rng.randint(-1, 1), blade_y - rng.randint(2, 4)))
    return tile


def needles_tile(rng: random.Random, base: Color, variation: int) -> pygame.Surface:
    tile = _noise_surface(rng, base, variation)
    for _ in range(18):
        start_x = rng.randrange(TILE)
        start_y = rng.randrange(TILE)
        color = shade(base, rng.choice([-20, 12, 22]))
        pygame.draw.line(tile, color, (start_x, start_y), (start_x + rng.randint(-3, 3), start_y + rng.randint(-2, 2)))
    for _ in range(2):
        pygame.draw.circle(tile, shade(base, -14), (rng.randrange(TILE), rng.randrange(TILE)), 2)
    return tile


def dirt_tile(rng: random.Random, base: Color, variation: int) -> pygame.Surface:
    tile = _noise_surface(rng, base, variation)
    for _ in range(7):
        center = (rng.randrange(TILE), rng.randrange(TILE))
        pygame.draw.circle(tile, shade(base, rng.choice([-24, 20])), center, rng.choice([1, 1, 2]))
    if rng.random() < 0.4:
        start = (rng.randrange(TILE), rng.randrange(TILE))
        pygame.draw.line(tile, shade(base, -22), start, (start[0] + rng.randint(-8, 8), start[1] + rng.randint(-5, 5)))
    return tile


def sand_tile(rng: random.Random, base: Color, variation: int) -> pygame.Surface:
    tile = _noise_surface(rng, base, variation)
    for _ in range(12):
        tile.set_at((rng.randrange(TILE), rng.randrange(TILE)), shade(base, rng.choice([-30, 22])))
    return tile


def cobble_tile(rng: random.Random, base: Color, variation: int) -> pygame.Surface:
    tile = pygame.Surface((TILE, TILE))
    tile.fill(shade(base, -48))
    stone_width, stone_height = 16, 8
    for row in range(TILE // stone_height):
        row_offset = 0 if row % 2 == 0 else stone_width // 2
        for column in range(3):
            left = -row_offset + column * stone_width
            color = shade(base, rng.randint(-variation, variation))
            rect = pygame.Rect(left + 1, row * stone_height + 1, stone_width - 2, stone_height - 2)
            pygame.draw.rect(tile, color, rect, border_radius=2)
            pygame.draw.line(tile, shade(color, 16), rect.topleft, (rect.right - 2, rect.top))
            pygame.draw.line(tile, shade(color, -18), (rect.left + 1, rect.bottom - 1), (rect.right - 2, rect.bottom - 1))
    return tile


def planks_tile(rng: random.Random, base: Color, variation: int) -> pygame.Surface:
    tile = pygame.Surface((TILE, TILE))
    board_height = 8
    for row in range(TILE // board_height):
        board_color = shade(base, rng.randint(-variation, variation))
        top = row * board_height
        pygame.draw.rect(tile, board_color, (0, top, TILE, board_height))
        for _ in range(3):
            grain_x = rng.randrange(TILE - 8)
            grain_y = top + rng.randint(1, board_height - 2)
            pygame.draw.line(tile, shade(board_color, -14), (grain_x, grain_y), (grain_x + rng.randint(4, 10), grain_y))
        pygame.draw.line(tile, shade(board_color, -42), (0, top + board_height - 1), (TILE, top + board_height - 1))
        pygame.draw.line(tile, shade(board_color, 14), (0, top), (TILE, top))
    return tile


def slabs_tile(rng: random.Random, base: Color, variation: int) -> pygame.Surface:
    tile = pygame.Surface((TILE, TILE))
    slab_size = 16
    for row in range(2):
        for column in range(2):
            color = shade(base, rng.randint(-variation, variation))
            rect = pygame.Rect(column * slab_size, row * slab_size, slab_size, slab_size)
            pygame.draw.rect(tile, color, rect)
            for _ in range(10):
                tile.set_at(
                    (rect.left + rng.randrange(slab_size), rect.top + rng.randrange(slab_size)),
                    shade(color, rng.choice([-12, 10])),
                )
            pygame.draw.line(tile, shade(color, -36), rect.bottomleft, rect.bottomright)
            pygame.draw.line(tile, shade(color, -36), rect.topright, rect.bottomright)
            pygame.draw.line(tile, shade(color, 12), rect.topleft, (rect.right - 1, rect.top))
    return tile


def water_tile(rng: random.Random, base: Color, variation: int) -> pygame.Surface:
    tile = _noise_surface(rng, base, variation)
    for _ in range(3):
        left = rng.randrange(TILE - 10)
        top = rng.randrange(4, TILE - 4)
        pygame.draw.arc(tile, shade(base, 38), (left, top, rng.randint(8, 14), 5), 0.2, 2.9)
    if rng.random() < 0.35:
        tile.set_at((rng.randrange(TILE), rng.randrange(TILE)), (225, 240, 250))
    return tile


def marsh_tile(rng: random.Random, base: Color, variation: int) -> pygame.Surface:
    tile = _noise_surface(rng, base, variation)
    for _ in range(4):
        center = (rng.randrange(TILE), rng.randrange(TILE))
        pygame.draw.circle(tile, shade(base, rng.choice([-18, 16])), center, rng.randint(2, 4))
    for _ in range(8):
        blade_x = rng.randrange(TILE)
        blade_y = rng.randrange(3, TILE)
        pygame.draw.line(tile, shade(base, 28), (blade_x, blade_y), (blade_x, blade_y - 3))
    return tile


def rubble_tile(rng: random.Random, base: Color, variation: int) -> pygame.Surface:
    tile = _noise_surface(rng, base, variation)
    for _ in range(5):
        center = (rng.randrange(TILE), rng.randrange(TILE))
        pygame.draw.circle(tile, shade(base, rng.choice([-26, 18])), center, rng.randint(1, 3))
    for _ in range(2):
        start = (rng.randrange(TILE), rng.randrange(TILE))
        pygame.draw.line(tile, shade(base, -30), start, (start[0] + rng.randint(-9, 9), start[1] + rng.randint(-9, 9)))
    return tile


def brick_wall_tile(rng: random.Random, base: Color, variation: int) -> pygame.Surface:
    tile = pygame.Surface((TILE, TILE))
    tile.fill(shade(base, -50))
    brick_width, brick_height = 16, 8
    for row in range(TILE // brick_height):
        row_offset = 0 if row % 2 == 0 else brick_width // 2
        for column in range(3):
            left = -row_offset + column * brick_width
            color = shade(base, rng.randint(-variation, variation))
            rect = pygame.Rect(left + 1, row * brick_height + 1, brick_width - 2, brick_height - 2)
            pygame.draw.rect(tile, color, rect)
            pygame.draw.line(tile, shade(color, 14), rect.topleft, (rect.right - 1, rect.top))
    return tile


GROUND_BUILDERS: Dict[str, Callable[[random.Random, Color, int], pygame.Surface]] = {
    "grass": grass_tile,
    "needles": needles_tile,
    "dirt": dirt_tile,
    "sand": sand_tile,
    "cobble": cobble_tile,
    "planks": planks_tile,
    "slabs": slabs_tile,
    "water": water_tile,
    "marsh": marsh_tile,
    "rubble": rubble_tile,
    "brick": brick_wall_tile,
}

_tile_cache: Dict[Tuple[str, Color, int], list] = {}


def ground_variants(kind: str, base: Color, variation: int, count: int = 5) -> list:
    key = (kind, tuple(base), variation)
    if key not in _tile_cache:
        rng = random.Random(f"{kind}{base}{variation}")
        _tile_cache[key] = [GROUND_BUILDERS[kind](rng, base, variation) for _ in range(count)]
    return _tile_cache[key]
