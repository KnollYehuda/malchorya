"""Converts pygame surfaces (the procedural 2D art) into Panda3D textures."""
import random

import pygame
from panda3d.core import SamplerState, Texture


POWER_OF_TWO_ONLY = False  # set for the software test renderer


def _rgba_surface(surface: pygame.Surface) -> pygame.Surface:
    converted = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    converted.blit(surface, (0, 0))
    return converted


def _power_of_two(surface: pygame.Surface) -> pygame.Surface:
    def next_power(value: int) -> int:
        power = 1
        while power < value:
            power *= 2
        return power

    width, height = surface.get_size()
    target = (next_power(width), next_power(height))
    if target == (width, height):
        return surface
    return pygame.transform.smoothscale(surface, target)


def surface_to_texture(
    surface: pygame.Surface, *, repeat: bool = False, smooth: bool = True, with_alpha: bool = True
) -> Texture:
    if POWER_OF_TWO_ONLY:
        surface = _power_of_two(_rgba_surface(surface))
    width, height = surface.get_size()
    data = pygame.image.tostring(_rgba_surface(surface), "RGBA", True)
    texture = Texture()
    texture.setup2dTexture(width, height, Texture.T_unsigned_byte, Texture.F_rgba8 if with_alpha else Texture.F_rgb8)
    texture.setRamImageAs(data, "RGBA")
    wrap = SamplerState.WM_repeat if repeat else SamplerState.WM_clamp
    texture.setWrapU(wrap)
    texture.setWrapV(wrap)
    if smooth:
        texture.setMinfilter(SamplerState.FT_linear_mipmap_linear if repeat else SamplerState.FT_linear)
        texture.setMagfilter(SamplerState.FT_linear)
    else:
        texture.setMinfilter(SamplerState.FT_nearest)
        texture.setMagfilter(SamplerState.FT_nearest)
    return texture


def tiled_ground_texture(variants: list, size_tiles: int = 16, seed: int = 1, tile_pixels: int = 32) -> Texture:
    """Composite random ground tile variants into one repeating texture."""
    rng = random.Random(seed)
    surface = pygame.Surface((size_tiles * tile_pixels, size_tiles * tile_pixels))
    for tile_row in range(size_tiles):
        for tile_column in range(size_tiles):
            surface.blit(rng.choice(variants), (tile_column * tile_pixels, tile_row * tile_pixels))
    return surface_to_texture(surface, repeat=True, with_alpha=False)
