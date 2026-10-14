"""Builds the 3D scene for one location from the same biome data as the 2D game."""
import heapq
import math
import random
from typing import Dict, List, Optional, Tuple

import pygame
from panda3d.core import (
    CardMaker,
    NodePath,
    PointLight,
    TextureStage,
    TransparencyAttrib,
)

from core.enums import WindDirection
from ui import props as props2d
from ui.scene import BIOMES, DEFAULT_BIOME, ENTITY_SLOTS, BiomeStyle
from ui.textures import ground_variants
from ui3d.meshes import MeshBuilder, flat_ellipse, flat_quad, rgb, vertical_quad
from ui3d.props3d import GROUND_DECALS, PROP3D_BUILDERS, STANDING_CARDS, WALL_DECOR, WALL_LIFT, Prop3D
from ui3d.texturing import surface_to_texture, tiled_ground_texture

PIXELS_PER_UNIT = 18.0
CARD_PIXELS_PER_UNIT = 28.0
HALF_WIDTH = 17.8
Y_MIN, Y_MAX = -13.9, 16.1
WALL_Y = 9.0  # indoor north wall
WALL_HEIGHT = 5.4
PATH_HALF_WIDTH = 2.7
BIG = 70.0

Collider = Tuple  # ("circle", x, y, r) | ("box", x, y, half_x, half_y)

TREE_NAMES = ("tree_round", "pine", "dead_tree", "bush", "rock")


def to_world(pixel_x: float, pixel_y: float) -> Tuple[float, float]:
    return (pixel_x - 320) / PIXELS_PER_UNIT, (290 - pixel_y) / PIXELS_PER_UNIT


def slot_positions() -> List[Tuple[float, float]]:
    return [(slot_x / PIXELS_PER_UNIT, -slot_y / PIXELS_PER_UNIT) for slot_x, slot_y in ENTITY_SLOTS]


def make_card(texture, width: float, height: float, name: str = "card") -> NodePath:
    maker = CardMaker(name)
    maker.setFrame(-width / 2, width / 2, 0, height)
    card = NodePath(maker.generate())
    card.setTexture(texture)
    card.setTransparency(TransparencyAttrib.M_alpha)
    return card


class LocationView:
    def __init__(self, location_id: str, biome: str, exits: List[WindDirection]) -> None:
        self.location_id = location_id
        self.style: BiomeStyle = BIOMES.get(biome, DEFAULT_BIOME)
        self.exits = exits
        self.indoor = self.style.indoor
        self.rng = random.Random(location_id)
        self.root = NodePath(f"location_{location_id}")
        self.card_root = self.root.attachNewNode("cards")
        self.colliders: List[Collider] = []
        self.blocked_rects: List[Tuple[float, float, float, float]] = []
        self.walk_rects: Optional[List[Tuple[float, float, float, float]]] = None
        self.lights: List[Tuple[NodePath, Tuple[float, float, float], bool]] = []
        self.water_nodes: List[NodePath] = []
        self.y_max = WALL_Y if self.indoor else Y_MAX

        self._build_terrain()
        self._build_props()

    # --------------------------------------------------------------- terrain

    def _ground_texture(self, kind: str, base, variation: int, seed: int = 1):
        return tiled_ground_texture(ground_variants(kind, base, variation), seed=seed)

    def _build_terrain(self) -> None:
        style = self.style
        if self.style.special == "dock":
            self._build_dock()
            return

        ground_top = self.y_max if self.indoor else (WALL_Y - 1.0 if style.water_rows else BIG)
        ground = flat_quad(-BIG, -BIG, BIG, ground_top, 0.0, 1 / 16, "ground")
        ground.setTexture(self._ground_texture(style.ground, style.base, style.variation))
        ground.reparentTo(self.root)

        if self.indoor:
            self._build_walls()
        elif style.water_rows:
            self._build_river()

        if style.path and not self.indoor:
            self._build_paths()

    def _build_river(self) -> None:
        shore_y = WALL_Y - 1.0
        sand = flat_quad(-BIG, shore_y, BIG, shore_y + 1.6, 0.01, 1 / 16, "sand")
        sand.setTexture(self._ground_texture("sand", (176, 160, 112), 8, seed=4))
        sand.reparentTo(self.root)
        water = flat_quad(-BIG, shore_y + 1.0, BIG, BIG, -0.12, 1 / 16, "water")
        water.setTexture(self._ground_texture("water", (46, 98, 138), 8, seed=5))
        water.reparentTo(self.root)
        self.water_nodes.append(water)
        self.blocked_rects.append((-BIG, shore_y + 0.8, BIG, BIG))

    def _build_dock(self) -> None:
        water = flat_quad(-BIG, -BIG, BIG, BIG, -0.25, 1 / 16, "water")
        water.setTexture(self._ground_texture("water", self.style.base, self.style.variation, seed=5))
        water.reparentTo(self.root)
        self.water_nodes.append(water)

        planks = self._ground_texture("planks", (132, 96, 58), 8, seed=7)
        dock_rect = (-BIG, -2.9, 6.7, 2.4)
        platform_rect = (2.2, -4.7, 11.1, 4.2)
        self.walk_rects = [dock_rect, platform_rect]
        for x_min, y_min, x_max, y_max in (dock_rect, platform_rect):
            deck = flat_quad(x_min, y_min, x_max, y_max, 0.32, 1 / 16, "deck")
            deck.setTexture(planks)
            deck.reparentTo(self.root)
            builder = MeshBuilder("dock_side", 3)
            builder.box(((x_min + x_max) / 2, (y_min + y_max) / 2, 0.1), (x_max - x_min, y_max - y_min, 0.4), rgb(70, 48, 30))
            side = builder.build()
            side.reparentTo(self.root)
        for post_x in range(-16, 6, 4):
            for post_y in (-2.9, 2.4):
                self._add_prop_node("dock_post", (post_x, post_y), 0)

    def _build_walls(self) -> None:
        wall_texture = tiled_ground_texture(ground_variants("brick", (118, 104, 92), 9), seed=9)
        segments = [
            ((-HALF_WIDTH, WALL_Y), (HALF_WIDTH, WALL_Y), (0, -1)),
            ((-HALF_WIDTH, Y_MIN), (-HALF_WIDTH, WALL_Y), (1, 0)),
            ((HALF_WIDTH, Y_MIN), (HALF_WIDTH, WALL_Y), (-1, 0)),
        ]
        for start, end, facing in segments:
            wall = vertical_quad(start, end, 0.0, WALL_HEIGHT, facing, 1 / 16, "wall")
            wall.setTexture(wall_texture)
            wall.reparentTo(self.root)
        trim = MeshBuilder("trim", 4, variation=0.02)
        trim.box((0, WALL_Y - 0.1, 0.18), (HALF_WIDTH * 2, 0.2, 0.36), rgb(70, 52, 40))
        trim.box((-HALF_WIDTH + 0.1, (Y_MIN + WALL_Y) / 2, 0.18), (0.2, WALL_Y - Y_MIN, 0.36), rgb(70, 52, 40))
        trim.box((HALF_WIDTH - 0.1, (Y_MIN + WALL_Y) / 2, 0.18), (0.2, WALL_Y - Y_MIN, 0.36), rgb(70, 52, 40))
        trim.build().reparentTo(self.root)
        self.blocked_rects.append((-BIG, WALL_Y - 0.3, BIG, BIG))

        for direction in self.exits:
            door = MeshBuilder("door", 5, variation=0.03)
            if direction == WindDirection.NORTH:
                door.box((0, WALL_Y - 0.15, 2.0), (3.2, 0.3, 4.0), rgb(44, 30, 22))
                door.box((0, WALL_Y - 0.3, 1.85), (2.7, 0.2, 3.7), rgb(100, 68, 40))
                door.box((1.0, WALL_Y - 0.45, 1.8), (0.16, 0.12, 0.16), rgb(228, 196, 96))
            elif direction in (WindDirection.EAST, WindDirection.WEST):
                sign = 1 if direction == WindDirection.EAST else -1
                door.box((sign * (HALF_WIDTH - 0.15), 0, 2.0), (0.3, 3.2, 4.0), rgb(44, 30, 22))
                door.box((sign * (HALF_WIDTH - 0.3), 0, 1.85), (0.2, 2.7, 3.7), rgb(100, 68, 40))
            else:
                door.box((0, Y_MIN + 0.8, 0.05), (3.4, 1.4, 0.1), rgb(120, 48, 44))
            door.build().reparentTo(self.root)

    def _build_paths(self) -> None:
        style = self.style
        texture = self._ground_texture(style.path, style.path_base, 8, seed=11)
        spans = {
            WindDirection.NORTH: (-PATH_HALF_WIDTH, 0, PATH_HALF_WIDTH, BIG),
            WindDirection.SOUTH: (-PATH_HALF_WIDTH, -BIG, PATH_HALF_WIDTH, 0),
            WindDirection.EAST: (0, -PATH_HALF_WIDTH, BIG, PATH_HALF_WIDTH),
            WindDirection.WEST: (-BIG, -PATH_HALF_WIDTH, 0, PATH_HALF_WIDTH),
        }
        for direction in self.exits:
            x_min, y_min, x_max, y_max = spans[direction]
            strip = flat_quad(x_min, y_min, x_max, y_max, 0.02, 1 / 16, "path")
            strip.setTexture(texture)
            strip.reparentTo(self.root)
        hub = flat_ellipse(style.hub[0] / 2 / PIXELS_PER_UNIT, style.hub[1] / 2 / PIXELS_PER_UNIT, 0.022, 1 / 16, name="hub")
        hub.setTexture(texture)
        hub.setPos(0, 0.5, 0)
        hub.reparentTo(self.root)

    # ----------------------------------------------------------------- props

    def _add_prop_node(self, name: str, position: Tuple[float, float], heading: float) -> Optional[Prop3D]:
        builder = PROP3D_BUILDERS.get(name)
        if builder is None:
            return None
        prop = builder(self.rng)
        prop.node.reparentTo(self.root)
        if name in WALL_LIFT:
            prop.node.setPos(position[0], WALL_Y - 0.3, WALL_LIFT[name])
            return prop
        prop.node.setPos(position[0], position[1], 0)
        prop.node.setH(heading)
        if prop.collider is not None:
            if prop.collider[0] == "circle":
                self.colliders.append(("circle", position[0], position[1], prop.collider[1]))
            else:
                self.colliders.append(("box", position[0], position[1], prop.collider[1], prop.collider[2]))
        if prop.light is not None and len(self.lights) < 5:
            color, height, flicker = prop.light
            light = PointLight(f"light_{name}")
            light.setColor((color[0] * 2.6, color[1] * 2.6, color[2] * 2.6, 1))
            light.setAttenuation((1.0, 0.0, 0.035))
            light_node = self.root.attachNewNode(light)
            light_node.setPos(position[0], position[1], height)
            self.root.setLight(light_node)
            self.lights.append((light_node, color, flicker))
        return prop

    def _add_card_prop(self, name: str, position: Tuple[float, float]) -> None:
        surface = props2d.PROP_BUILDERS[name](self.rng)
        texture = surface_to_texture(surface)
        width = surface.get_width() / CARD_PIXELS_PER_UNIT
        height = surface.get_height() / CARD_PIXELS_PER_UNIT
        if name in GROUND_DECALS:
            decal = flat_quad(-width / 2, -height / 2, width / 2, height / 2, 0.03, 1.0, "decal")
            decal.setTexture(TextureStage.getDefault(), texture)
            decal.setTexScale(TextureStage.getDefault(), 1 / width, 1 / height)
            decal.setTexOffset(TextureStage.getDefault(), 0.5, 0.5)
            decal.setTransparency(TransparencyAttrib.M_alpha)
            decal.setPos(position[0], position[1], 0)
            decal.reparentTo(self.root)
        elif name in WALL_DECOR:
            card = make_card(texture, width, height, name)
            lift = {"window": 1.2, "banner": 0.9, "shelves": 1.7}[name]
            card.setPos(position[0], WALL_Y - 0.35, lift)
            card.setLightOff()
            card.reparentTo(self.card_root)
        else:
            card = make_card(texture, width, height, name)
            card.setPos(position[0], position[1], 0)
            card.setBillboardAxis()
            card.setLightOff()
            card.reparentTo(self.card_root)

    def _place(self, name: str, position: Tuple[float, float], heading: float = 0.0) -> None:
        if name in PROP3D_BUILDERS:
            self._add_prop_node(name, position, heading)
        elif name in props2d.PROP_BUILDERS:
            self._add_card_prop(name, position)

    def _in_corridor(self, pos_x: float, pos_y: float) -> bool:
        margin = PATH_HALF_WIDTH + 0.9
        for direction in self.exits:
            if direction == WindDirection.NORTH and abs(pos_x) < margin and pos_y > -1:
                return True
            if direction == WindDirection.SOUTH and abs(pos_x) < margin and pos_y < 1:
                return True
            if direction == WindDirection.EAST and abs(pos_y) < margin and pos_x > -1:
                return True
            if direction == WindDirection.WEST and abs(pos_y) < margin and pos_x < 1:
                return True
        return False

    def _collides(self, pos_x: float, pos_y: float, radius: float) -> bool:
        for collider in self.colliders:
            if collider[0] == "circle":
                if math.hypot(pos_x - collider[1], pos_y - collider[2]) < radius + collider[3] + 0.4:
                    return True
            else:
                if abs(pos_x - collider[1]) < radius + collider[3] + 0.4 and abs(pos_y - collider[2]) < radius + collider[4] + 0.4:
                    return True
        return False

    def _build_props(self) -> None:
        style = self.style
        slots = slot_positions()

        for name, pixel_x, pixel_y in style.fixed:
            position = to_world(pixel_x, pixel_y)
            self._place(name, position)

        if self.style.special == "dock":
            for name, count in style.props:
                pass
            return

        y_limit = self.y_max - 1.2 if not self.indoor else WALL_Y - 2.0
        for name, count in style.props:
            for _ in range(count):
                for _attempt in range(50):
                    pos_x = self.rng.uniform(-HALF_WIDTH + 1.2, HALF_WIDTH - 1.2)
                    pos_y = self.rng.uniform(Y_MIN + 1.2, y_limit)
                    if math.hypot(pos_x, pos_y) < 4.8 or self._in_corridor(pos_x, pos_y):
                        continue
                    if any(math.hypot(pos_x - slot_x, pos_y - slot_y) < 3.2 for slot_x, slot_y in slots):
                        continue
                    if any(x_min < pos_x < x_max and y_min < pos_y < y_max for x_min, y_min, x_max, y_max in self.blocked_rects):
                        continue
                    if name in GROUND_DECALS or name in STANDING_CARDS:
                        if self._collides(pos_x, pos_y, 0.2) and name not in GROUND_DECALS:
                            continue
                    elif self._collides(pos_x, pos_y, 1.0):
                        continue
                    self._place(name, (pos_x, pos_y), self.rng.uniform(0, 360))
                    break

        if not self.indoor:
            self._build_border()

    def _build_border(self) -> None:
        """Ring of trees/rocks beyond the walkable area so the world feels continuous."""
        candidates = [name for name, _ in self.style.props if name in TREE_NAMES] or ["bush"]
        if self.style.water_rows:
            candidates = [name for name in candidates if name in ("tree_round", "rock", "bush")] or ["rock"]
        for _ in range(46):
            side = self.rng.choice(["west", "east", "south", "north"])
            depth = self.rng.uniform(0.4, 9.0)
            if side == "west":
                position = (-HALF_WIDTH - depth, self.rng.uniform(Y_MIN - 6, Y_MAX + 6))
            elif side == "east":
                position = (HALF_WIDTH + depth, self.rng.uniform(Y_MIN - 6, Y_MAX + 6))
            elif side == "south":
                position = (self.rng.uniform(-HALF_WIDTH - 8, HALF_WIDTH + 8), Y_MIN - depth)
            else:
                if self.style.water_rows:
                    continue
                position = (self.rng.uniform(-HALF_WIDTH - 8, HALF_WIDTH + 8), Y_MAX + depth)
            if self._in_corridor(*position):
                continue
            builder = PROP3D_BUILDERS[self.rng.choice(candidates)]
            prop = builder(self.rng)
            prop.node.reparentTo(self.root)
            prop.node.setPos(position[0], position[1], 0)
            prop.node.setH(self.rng.uniform(0, 360))

    # ------------------------------------------------------------- movement

    def is_walkable(self, pos_x: float, pos_y: float) -> bool:
        if self.walk_rects is not None:
            return any(x_min < pos_x < x_max and y_min < pos_y < y_max for x_min, y_min, x_max, y_max in self.walk_rects)
        return not any(x_min < pos_x < x_max and y_min < pos_y < y_max for x_min, y_min, x_max, y_max in self.blocked_rects)

    def resolve(self, pos_x: float, pos_y: float, radius: float) -> Tuple[float, float]:
        for collider in self.colliders:
            if collider[0] == "circle":
                _, center_x, center_y, collider_radius = collider
                delta_x, delta_y = pos_x - center_x, pos_y - center_y
                distance = math.hypot(delta_x, delta_y)
                minimum = radius + collider_radius
                if distance < minimum:
                    if distance < 1e-4:
                        delta_x, delta_y, distance = 1.0, 0.0, 1.0
                    pos_x = center_x + delta_x / distance * minimum
                    pos_y = center_y + delta_y / distance * minimum
            else:
                _, center_x, center_y, half_x, half_y = collider
                closest_x = max(center_x - half_x, min(pos_x, center_x + half_x))
                closest_y = max(center_y - half_y, min(pos_y, center_y + half_y))
                delta_x, delta_y = pos_x - closest_x, pos_y - closest_y
                distance = math.hypot(delta_x, delta_y)
                if distance < radius:
                    if distance < 1e-4:
                        pos_y = center_y - half_y - radius
                    else:
                        pos_x = closest_x + delta_x / distance * radius
                        pos_y = closest_y + delta_y / distance * radius
        return pos_x, pos_y

    # ------------------------------------------------------------ pathfinding

    PATH_CELL = 0.6
    PATH_CLEARANCE = 0.7

    def _free(self, pos_x: float, pos_y: float, extra_circles=()) -> bool:
        if not self.is_walkable(pos_x, pos_y):
            return False
        clearance = self.PATH_CLEARANCE
        for collider in self.colliders:
            if collider[0] == "circle":
                if math.hypot(pos_x - collider[1], pos_y - collider[2]) < collider[3] + clearance:
                    return False
            else:
                closest_x = max(collider[1] - collider[3], min(pos_x, collider[1] + collider[3]))
                closest_y = max(collider[2] - collider[4], min(pos_y, collider[2] + collider[4]))
                if math.hypot(pos_x - closest_x, pos_y - closest_y) < clearance:
                    return False
        for circle_x, circle_y, circle_radius in extra_circles:
            if math.hypot(pos_x - circle_x, pos_y - circle_y) < circle_radius + clearance * 0.6:
                return False
        return True

    def _line_clear(self, start, end, extra_circles) -> bool:
        distance = math.hypot(end[0] - start[0], end[1] - start[1])
        samples = max(1, int(distance / 0.3))
        for index in range(1, samples + 1):
            ratio = index / samples
            if not self._free(start[0] + (end[0] - start[0]) * ratio, start[1] + (end[1] - start[1]) * ratio, extra_circles):
                return False
        return True

    def find_path(self, start, goal, extra_circles=()) -> Optional[List[Tuple[float, float]]]:
        """A* over a grid of the room; returns smoothed waypoints ending at `goal`."""
        cell = self.PATH_CELL
        min_x, max_x = -HALF_WIDTH + 0.6, HALF_WIDTH - 0.6
        min_y, max_y = Y_MIN + 0.6, self.y_max - 0.6
        columns = int((max_x - min_x) / cell) + 1
        rows = int((max_y - min_y) / cell) + 1

        def to_cell(point):
            return (
                max(0, min(columns - 1, round((point[0] - min_x) / cell))),
                max(0, min(rows - 1, round((point[1] - min_y) / cell))),
            )

        def to_point(index):
            return (min_x + index[0] * cell, min_y + index[1] * cell)

        blocked_cache: Dict[Tuple[int, int], bool] = {}

        def blocked(index) -> bool:
            if index not in blocked_cache:
                blocked_cache[index] = not self._free(*to_point(index), extra_circles)
            return blocked_cache[index]

        start_cell = to_cell(start)
        goal_cell = to_cell(goal)
        if blocked(goal_cell):
            # Nearest free cell to the clicked spot.
            best = None
            for radius in range(1, 8):
                ring = [
                    (goal_cell[0] + offset_x, goal_cell[1] + offset_y)
                    for offset_x in range(-radius, radius + 1)
                    for offset_y in range(-radius, radius + 1)
                    if max(abs(offset_x), abs(offset_y)) == radius
                    and 0 <= goal_cell[0] + offset_x < columns
                    and 0 <= goal_cell[1] + offset_y < rows
                ]
                free_cells = [index for index in ring if not blocked(index)]
                if free_cells:
                    best = min(free_cells, key=lambda index: math.hypot(index[0] - goal_cell[0], index[1] - goal_cell[1]))
                    break
            if best is None:
                return None
            goal_cell = best

        def heuristic(index) -> float:
            delta_x, delta_y = abs(index[0] - goal_cell[0]), abs(index[1] - goal_cell[1])
            return (delta_x + delta_y) + (math.sqrt(2) - 2) * min(delta_x, delta_y)

        open_heap = [(heuristic(start_cell), 0.0, start_cell)]
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        cost_so_far = {start_cell: 0.0}
        found = False
        while open_heap:
            _, cost, current = heapq.heappop(open_heap)
            if current == goal_cell:
                found = True
                break
            if cost > cost_so_far.get(current, 1e9):
                continue
            for step_x in (-1, 0, 1):
                for step_y in (-1, 0, 1):
                    if not step_x and not step_y:
                        continue
                    neighbour = (current[0] + step_x, current[1] + step_y)
                    if not (0 <= neighbour[0] < columns and 0 <= neighbour[1] < rows) or blocked(neighbour):
                        continue
                    if step_x and step_y and (blocked((current[0] + step_x, current[1])) or blocked((current[0], current[1] + step_y))):
                        continue
                    new_cost = cost + (math.sqrt(2) if step_x and step_y else 1.0)
                    if new_cost < cost_so_far.get(neighbour, 1e9):
                        cost_so_far[neighbour] = new_cost
                        came_from[neighbour] = current
                        heapq.heappush(open_heap, (new_cost + heuristic(neighbour), new_cost, neighbour))
        if not found:
            return None

        cells = [goal_cell]
        while cells[-1] != start_cell:
            cells.append(came_from[cells[-1]])
        cells.reverse()
        points = [to_point(index) for index in cells]
        points[-1] = goal if self._free(*goal, extra_circles) else points[-1]

        # Drop waypoints that have a clear straight line to a later one.
        smoothed = [start]
        anchor = start
        index = 0
        while index < len(points):
            furthest = index
            for later in range(len(points) - 1, index - 1, -1):
                if self._line_clear(anchor, points[later], extra_circles):
                    furthest = later
                    break
            anchor = points[furthest]
            smoothed.append(anchor)
            index = furthest + 1
        return smoothed[1:]
