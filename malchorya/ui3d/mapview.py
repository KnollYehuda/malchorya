"""Draws the circular minimap (current room, rotates with the camera) and the world map."""
import math
from typing import Dict, List, Tuple

import pygame

from core.mapping import frontier, layout
from ui.scene import BIOMES, DEFAULT_BIOME
from ui3d.world3d import HALF_WIDTH, PATH_HALF_WIDTH, Y_MIN
from core.enums import WindDirection

MINIMAP_SIZE = 256
WORLD_MAP_SIZE = (1024, 512)
UNITS_ACROSS = 44.0  # world units shown across the minimap

_font_cache: Dict[int, pygame.font.Font] = {}


def _font(size: int) -> pygame.font.Font:
    if not pygame.font.get_init():
        pygame.font.init()
    if size not in _font_cache:
        _font_cache[size] = pygame.font.Font(None, size)
    return _font_cache[size]


def _shade(color, amount: int):
    return tuple(max(0, min(255, channel + amount)) for channel in color[:3])


def draw_minimap(view, player, facing_basis, entities, item_markers, move_target=None, facing=(0.0, 1.0)) -> pygame.Surface:
    """Top-down view of the current room. `facing_basis` = (forward, right) of the camera."""
    size = MINIMAP_SIZE
    forward, right = facing_basis
    center_y = (Y_MIN + view.y_max) / 2
    scale = size / UNITS_ACROSS
    player_x, player_y = player

    def to_screen(world_x: float, world_y: float) -> Tuple[float, float]:
        # Keep the player at the middle so the map scrolls as they walk.
        relative_x, relative_y = world_x - player_x, world_y - player_y
        across = relative_x * right[0] + relative_y * right[1]
        along = relative_x * forward[0] + relative_y * forward[1]
        return size / 2 + across * scale, size / 2 - along * scale

    def polygon_for(x_min, y_min, x_max, y_max) -> List[Tuple[float, float]]:
        return [to_screen(x_min, y_min), to_screen(x_max, y_min), to_screen(x_max, y_max), to_screen(x_min, y_max)]

    style = view.style
    base = style.base
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    surface.fill((10, 12, 18, 255))

    room_top = view.y_max
    room = polygon_for(-HALF_WIDTH, Y_MIN, HALF_WIDTH, room_top)
    if style.special == "dock":
        pygame.draw.polygon(surface, (40, 86, 128), room)
        for rect in view.walk_rects or []:
            clipped = (max(rect[0], -HALF_WIDTH), rect[1], min(rect[2], HALF_WIDTH), rect[3])
            pygame.draw.polygon(surface, (132, 96, 58), polygon_for(*clipped))
    else:
        pygame.draw.polygon(surface, _shade(base, 8 if style.indoor else 0), room)
        if style.water_rows:
            for rect in view.blocked_rects:
                clipped = (max(rect[0], -HALF_WIDTH), max(rect[1], Y_MIN), min(rect[2], HALF_WIDTH), min(rect[3], room_top))
                pygame.draw.polygon(surface, (46, 98, 138), polygon_for(*clipped))
        if style.path and not style.indoor:
            path_color = _shade(style.path_base, 14)
            reach = {
                WindDirection.NORTH: (-PATH_HALF_WIDTH, 0, PATH_HALF_WIDTH, room_top),
                WindDirection.SOUTH: (-PATH_HALF_WIDTH, Y_MIN, PATH_HALF_WIDTH, 0),
                WindDirection.EAST: (0, -PATH_HALF_WIDTH, HALF_WIDTH, PATH_HALF_WIDTH),
                WindDirection.WEST: (-HALF_WIDTH, -PATH_HALF_WIDTH, 0, PATH_HALF_WIDTH),
            }
            for direction in view.exits:
                pygame.draw.polygon(surface, path_color, polygon_for(*reach[direction]))
            hub_radius = style.hub[0] / 2 / 18.0
            pygame.draw.circle(surface, path_color, to_screen(0, 0.5), int(hub_radius * scale * 0.9))
    pygame.draw.polygon(surface, (230, 226, 200) if not style.indoor else (150, 120, 90), room, 3)

    for collider in view.colliders:
        if collider[0] == "circle":
            pygame.draw.circle(surface, (24, 40, 26) if not style.indoor else (60, 44, 30), to_screen(collider[1], collider[2]), max(2, int(collider[3] * scale)))
        else:
            pygame.draw.polygon(surface, (70, 52, 40), polygon_for(collider[1] - collider[3], collider[2] - collider[4], collider[1] + collider[3], collider[2] + collider[4]))

    for marker in item_markers:
        pygame.draw.circle(surface, (255, 220, 90), to_screen(marker["x"], marker["y"]), 3)
    for entity in entities:
        color = (255, 80, 70) if entity["kind"] == "enemy" else (110, 220, 255)
        position = to_screen(entity["x"], entity["y"])
        pygame.draw.circle(surface, color, position, 5)
        pygame.draw.circle(surface, (0, 0, 0), position, 5, 1)

    for direction in view.exits:
        edge = {
            WindDirection.NORTH: (0, room_top), WindDirection.SOUTH: (0, Y_MIN),
            WindDirection.EAST: (HALF_WIDTH, 0), WindDirection.WEST: (-HALF_WIDTH, 0),
        }[direction]
        pygame.draw.circle(surface, (255, 245, 170), to_screen(*edge), 6)

    if move_target is not None:
        target = to_screen(*move_target)
        pygame.draw.circle(surface, (255, 240, 170), target, 6, 2)

    # Player arrow, pointing the way they face (relative to the camera).
    center = (size / 2, size / 2)
    across = facing[0] * right[0] + facing[1] * right[1]
    along = facing[0] * forward[0] + facing[1] * forward[1]
    angle = math.atan2(across, along)
    tip = (center[0] + math.sin(angle) * 14, center[1] - math.cos(angle) * 14)
    left_wing = (center[0] + math.sin(angle + 2.5) * 10, center[1] - math.cos(angle + 2.5) * 10)
    right_wing = (center[0] + math.sin(angle - 2.5) * 10, center[1] - math.cos(angle - 2.5) * 10)
    pygame.draw.polygon(surface, (0, 0, 0), [tip, left_wing, center, right_wing], 0)
    pygame.draw.polygon(surface, (255, 255, 255), [tip, left_wing, center, right_wing], 0)
    pygame.draw.polygon(surface, (20, 20, 20), [tip, left_wing, center, right_wing], 2)

    # Mask to a circle with a border and a north marker.
    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (size // 2, size // 2), size // 2 - 2)
    surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    pygame.draw.circle(surface, (210, 190, 120), (size // 2, size // 2), size // 2 - 2, 3)
    north_angle = math.atan2(forward[0], forward[1])  # where world +Y points on screen
    north_x = size / 2 + math.sin(-north_angle) * (size / 2 - 18)
    north_y = size / 2 - math.cos(-north_angle) * (size / 2 - 18)
    label = _font(26).render("N", True, (255, 240, 170))
    surface.blit(label, label.get_rect(center=(north_x, north_y)))
    return surface


def draw_world_map(state) -> pygame.Surface:
    width, height = WORLD_MAP_SIZE
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(surface, (22, 20, 28, 245), (0, 0, width, height), border_radius=18)
    pygame.draw.rect(surface, (200, 170, 100, 255), (0, 0, width, height), 4, border_radius=18)

    world = state.world
    positions = layout(world)
    visited = set(state.visited)
    unknown = frontier(world, visited)
    shown = {location_id: position for location_id, position in positions.items() if location_id in visited | unknown}

    title = _font(46).render("The World of Malchorya", True, (240, 220, 160))
    surface.blit(title, (28, 14))
    summary = _font(28).render(f"Explored {len(visited)} of {len(world.locations)} places    (M to close)", True, (190, 190, 210))
    surface.blit(summary, (width - summary.get_width() - 28, 24))

    columns = [column for column, _ in shown.values()]
    rows = [row for _, row in shown.values()]
    span_columns = max(columns) - min(columns) + 1
    span_rows = max(rows) - min(rows) + 1
    area = pygame.Rect(40, 76, width - 80, height - 120)
    cell_width = min(area.width / span_columns, 230)
    cell_height = min(area.height / span_rows, 112)
    cell = cell_height
    node_width, node_height = cell_width * 0.74, cell_height * 0.68

    def center_of(location_id: str) -> Tuple[float, float]:
        column, row = shown[location_id]
        return (
            area.centerx + (column - (min(columns) + max(columns)) / 2) * cell_width,
            area.centery + (row - (min(rows) + max(rows)) / 2) * cell_height,
        )

    for location_id in shown:
        for neighbour in world.get_location(location_id).exits.values():
            if neighbour in shown and (location_id in visited or neighbour in visited):
                pygame.draw.line(surface, (150, 130, 90), center_of(location_id), center_of(neighbour), 6)

    for location_id in shown:
        rect = pygame.Rect(0, 0, node_width, node_height)
        rect.center = center_of(location_id)
        if location_id in visited:
            location = world.get_location(location_id)
            style = BIOMES.get(location.biome, DEFAULT_BIOME)
            fill = _shade(style.base, 30)
            pygame.draw.rect(surface, fill, rect, border_radius=12)
            pygame.draw.rect(surface, (20, 18, 14), rect, 2, border_radius=12)
            name = location.name
            font = _font(max(20, int(cell * 0.24)))
            words = name.replace("of Malchorya", "").split()
            lines, current = [], ""
            for word in words:
                trial = f"{current} {word}".strip()
                if font.size(trial)[0] <= rect.width - 10:
                    current = trial
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
            for index, line in enumerate(lines[:3]):
                text = font.render(line, True, (255, 255, 255))
                shadow = font.render(line, True, (0, 0, 0))
                position = text.get_rect(center=(rect.centerx, rect.centery + (index - (len(lines[:3]) - 1) / 2) * font.get_linesize()))
                surface.blit(shadow, position.move(1, 1))
                surface.blit(text, position)
        else:
            pygame.draw.rect(surface, (52, 52, 64), rect, border_radius=12)
            pygame.draw.rect(surface, (90, 90, 110), rect, 2, border_radius=12)
            mark = _font(int(cell * 0.4)).render("?", True, (140, 140, 160))
            surface.blit(mark, mark.get_rect(center=rect.center))

    here = pygame.Rect(0, 0, node_width + 14, node_height + 14)
    here.center = center_of(state.player.location_id)
    pygame.draw.rect(surface, (255, 230, 120), here, 5, border_radius=16)
    marker = _font(22).render("You are here", True, (255, 230, 120))
    surface.blit(marker, marker.get_rect(midtop=(here.centerx, here.bottom + 2)))
    compass = _font(30).render("N ^", True, (210, 190, 120))
    surface.blit(compass, (width - 90, height - 48))
    return surface
