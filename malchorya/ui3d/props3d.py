"""3D versions of the world props, built from low-poly primitives."""
import random
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

from panda3d.core import NodePath

from ui3d.meshes import MeshBuilder, rgb, Color


@dataclass
class Prop3D:
    node: NodePath
    # ("circle", radius) or ("box", half_x, half_y); None = walk-through
    collider: Optional[Tuple] = None
    # (color rgb 0-1, height above ground, flicker) for a point light
    light: Optional[Tuple[Tuple[float, float, float], float, bool]] = None
    emissive: bool = False  # draw without lighting (fires, lanterns)


def _vary(rng: random.Random, color: Color, amount: int = 14) -> Color:
    shift = rng.randint(-amount, amount) / 255.0
    return (max(0, min(1, color[0] + shift)), max(0, min(1, color[1] + shift)), max(0, min(1, color[2] + shift)), 1.0)


WOOD = rgb(120, 86, 52)
DARK_WOOD = rgb(84, 58, 36)
STONE = rgb(122, 118, 110)
DARK_STONE = rgb(86, 84, 80)
IRON = rgb(70, 74, 82)


def tree_round(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("tree_round", rng.randint(0, 9999))
    scale = rng.uniform(0.85, 1.35)
    leaf = _vary(rng, rgb(*rng.choice([(54, 128, 58), (66, 140, 54), (46, 112, 64)])), 10)
    builder.tube((0, 0, 0), (0, 0, 2.6 * scale), 0.34 * scale, 0.22 * scale, WOOD, 7)
    builder.sphere((0, 0, 3.4 * scale), (1.7 * scale, 1.7 * scale, 1.35 * scale), leaf, rings=3, segments=8, jitter=0.12)
    builder.sphere((0.9 * scale, 0.3 * scale, 2.8 * scale), (1.1 * scale,) * 3, _vary(rng, leaf, 8), rings=2, segments=7, jitter=0.12)
    builder.sphere((-0.9 * scale, -0.4 * scale, 2.9 * scale), (1.15 * scale,) * 3, _vary(rng, leaf, 8), rings=2, segments=7, jitter=0.12)
    return Prop3D(builder.build(), ("circle", 0.5 * scale))


def pine(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("pine", rng.randint(0, 9999))
    scale = rng.uniform(0.9, 1.4)
    needle = _vary(rng, rgb(*rng.choice([(30, 92, 60), (36, 100, 64), (26, 82, 56)])), 8)
    builder.tube((0, 0, 0), (0, 0, 1.4 * scale), 0.26 * scale, 0.18 * scale, DARK_WOOD, 6)
    for level, (base, radius, height) in enumerate([(0.8, 1.6, 1.8), (1.9, 1.35, 1.6), (2.9, 1.05, 1.4), (3.8, 0.72, 1.2)]):
        builder.cone((0, 0, base * scale), radius * scale, height * scale, _vary(rng, needle, 6 + level), 7)
    return Prop3D(builder.build(), ("circle", 0.45 * scale))


def dead_tree(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("dead_tree", rng.randint(0, 9999))
    bark = rgb(74, 62, 56)
    builder.tube((0, 0, 0), (0, 0, 3.8), 0.32, 0.12, bark, 6)
    for _ in range(4):
        height = rng.uniform(1.8, 3.2)
        reach = rng.uniform(0.9, 1.7)
        angle = rng.uniform(0, 6.28)
        import math
        end = (math.cos(angle) * reach, math.sin(angle) * reach, height + rng.uniform(0.6, 1.2))
        builder.tube((0, 0, height), end, 0.1, 0.03, bark, 5)
    return Prop3D(builder.build(), ("circle", 0.4))


def rock(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("rock", rng.randint(0, 9999), variation=0.1)
    base = rng.choice([rgb(118, 116, 112), rgb(104, 106, 110), rgb(128, 120, 108)])
    size = rng.uniform(0.7, 1.4)
    builder.sphere((0, 0, 0.25 * size), (size, size * 0.8, 0.65 * size), base, rings=2, segments=6, jitter=0.25)
    return Prop3D(builder.build(), ("circle", 0.8 * size))


def bush(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("bush", rng.randint(0, 9999))
    leaf = _vary(rng, rgb(*rng.choice([(58, 122, 56), (66, 130, 52), (46, 106, 62)])), 8)
    builder.sphere((0, 0, 0.5), (0.9, 0.9, 0.62), leaf, rings=2, segments=7, jitter=0.12)
    builder.sphere((0.55, 0.2, 0.42), (0.6, 0.6, 0.45), _vary(rng, leaf, 8), rings=2, segments=6, jitter=0.1)
    for _ in range(3):
        builder.sphere((rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6), rng.uniform(0.6, 0.95)), (0.08,) * 3, rgb(210, 60, 70), 1, 5)
    return Prop3D(builder.build(), ("circle", 0.6))


def stump(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("stump", rng.randint(0, 9999))
    builder.cylinder((0, 0, 0), 0.4, 0.55, WOOD, 7, cap_color=rgb(170, 130, 86))
    return Prop3D(builder.build(), ("circle", 0.4))


def house(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("house", rng.randint(0, 9999), variation=0.04)
    wall = rng.choice([rgb(188, 160, 120), rgb(172, 148, 124), rgb(196, 168, 128)])
    roof = rng.choice([rgb(160, 66, 54), rgb(128, 72, 58), rgb(100, 88, 74)])
    builder.box((0, 0, 1.4), (6.4, 4.8, 2.8), wall)
    builder.gable_roof((0, 0, 2.8), 6.4, 4.8, 2.4, roof, wall)
    builder.box((0.4, -2.42, 0.95), (1.2, 0.12, 1.9), rgb(92, 60, 38))
    for window_x in (-2.0, 2.2):
        builder.box((window_x, -2.42, 1.7), (0.95, 0.1, 0.95), rgb(70, 50, 36))
        builder.box((window_x, -2.47, 1.7), (0.75, 0.08, 0.75), rgb(250, 214, 124))
    builder.box((2.0, 1.0, 4.4), (0.7, 0.7, 1.8), STONE)
    return Prop3D(builder.build(), ("box", 3.4, 2.6))


def hut(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("hut", rng.randint(0, 9999))
    builder.cylinder((0, 0, 0), 2.3, 2.1, rgb(106, 78, 52), 9)
    builder.cone((0, 0, 2.0), 3.0, 2.4, rgb(96, 118, 66), 9)
    builder.box((0, -2.2, 0.8), (0.9, 0.2, 1.6), rgb(32, 24, 18))
    builder.box((1.4, -1.2, 1.3), (0.5, 0.1, 0.5), rgb(240, 200, 110))
    return Prop3D(builder.build(), ("circle", 2.5))


def tent(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("tent", rng.randint(0, 9999))
    cloth = rng.choice([rgb(140, 72, 62), rgb(104, 92, 76)])
    builder.cone((0, 0, 0), 2.4, 2.4, cloth, 4)
    builder.box((0, -1.25, 0.6), (0.9, 0.12, 1.2), rgb(26, 20, 18))
    return Prop3D(builder.build(), ("circle", 1.8))


def tower_ruin(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("tower_ruin", rng.randint(0, 9999))
    builder.cylinder((0, 0, 0), 2.8, 4.6, rgb(112, 108, 104), 10)
    for index in range(6):
        angle = index * 1.05
        import math
        height = rng.uniform(0.5, 1.4)
        builder.box((math.cos(angle) * 2.5, math.sin(angle) * 2.5, 4.6 + height / 2), (1.0, 0.7, height), rgb(104, 100, 96), heading=angle * 57)
    builder.box((0, -2.75, 0.9), (1.2, 0.3, 1.8), rgb(24, 20, 18))
    builder.box((1.9, -2.0, 0.4), (1.5, 1.2, 0.8), rgb(96, 92, 88))
    return Prop3D(builder.build(), ("circle", 3.0))


def ruin_wall(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("ruin_wall", rng.randint(0, 9999))
    for index in range(5):
        height = rng.uniform(0.5, 1.6)
        builder.box((-2.0 + index * 1.0, 0, height / 2), (1.0, 0.7, height), _vary(rng, STONE, 10))
    return Prop3D(builder.build(), ("box", 2.6, 0.5))


def fence(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("fence", rng.randint(0, 9999))
    for post_x in (-1.8, 0, 1.8):
        builder.box((post_x, 0, 0.55), (0.18, 0.18, 1.1), DARK_WOOD)
    for rail_z in (0.45, 0.85):
        builder.box((0, 0, rail_z), (3.8, 0.1, 0.14), WOOD)
    return Prop3D(builder.build(), ("box", 1.9, 0.2))


def signpost(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("signpost", rng.randint(0, 9999))
    builder.box((0, 0, 1.2), (0.16, 0.16, 2.4), DARK_WOOD)
    builder.box((0.5, -0.12, 2.0), (1.4, 0.07, 0.38), WOOD, heading=-6)
    builder.box((-0.4, -0.12, 1.45), (1.3, 0.07, 0.36), WOOD, heading=8)
    return Prop3D(builder.build(), ("circle", 0.3))


def lamp_post(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("lamp_post", rng.randint(0, 9999))
    builder.cylinder((0, 0, 0), 0.1, 3.4, rgb(46, 46, 52), 6)
    builder.box((0, 0, 3.6), (0.5, 0.5, 0.6), rgb(255, 218, 130))
    builder.cone((0, 0, 3.9), 0.45, 0.35, rgb(46, 46, 52), 4)
    return Prop3D(builder.build(), ("circle", 0.25), light=((1.0, 0.78, 0.45), 3.4, False))


def well(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("well", rng.randint(0, 9999))
    builder.cylinder((0, 0, 0), 1.2, 0.95, rgb(128, 124, 116), 10)
    builder.cylinder((0, 0, 0.9), 0.85, 0.02, rgb(26, 40, 56), 10)
    for post_x in (-1.1, 1.1):
        builder.box((post_x, 0, 1.6), (0.16, 0.16, 1.7), DARK_WOOD)
    builder.gable_roof((0, 0, 2.4), 2.4, 1.2, 0.9, rgb(130, 70, 54), DARK_WOOD, 0.2)
    return Prop3D(builder.build(), ("circle", 1.3))


def barrel(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("barrel", rng.randint(0, 9999))
    builder.cylinder((0, 0, 0), 0.5, 1.1, rgb(124, 86, 50), 9, cap_color=rgb(150, 110, 70))
    for band_z in (0.22, 0.8):
        builder.cylinder((0, 0, band_z), 0.53, 0.08, rgb(54, 54, 60), 9)
    return Prop3D(builder.build(), ("circle", 0.5))


def crate(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("crate", rng.randint(0, 9999))
    size = rng.uniform(0.9, 1.2)
    builder.box((0, 0, size / 2), (size, size, size), rgb(146, 110, 66), heading=rng.uniform(-15, 15))
    return Prop3D(builder.build(), ("circle", size * 0.6))


def table(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("table", rng.randint(0, 9999))
    builder.box((0, 0, 0.85), (2.4, 1.4, 0.12), WOOD)
    for leg_x in (-1.0, 1.0):
        for leg_y in (-0.5, 0.5):
            builder.box((leg_x, leg_y, 0.4), (0.14, 0.14, 0.8), DARK_WOOD)
    builder.cylinder((0.5, 0.1, 0.91), 0.12, 0.2, rgb(200, 200, 208), 6)
    builder.cylinder((-0.5, -0.2, 0.91), 0.1, 0.16, rgb(70, 124, 84), 6)
    return Prop3D(builder.build(), ("box", 1.2, 0.7))


def stool(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("stool", rng.randint(0, 9999))
    builder.cylinder((0, 0, 0.3), 0.32, 0.1, WOOD, 7)
    for offset in (-0.18, 0.18):
        builder.box((offset, offset, 0.15), (0.08, 0.08, 0.3), DARK_WOOD)
    return Prop3D(builder.build(), ("circle", 0.3))


def bar_counter(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("bar_counter", rng.randint(0, 9999))
    builder.box((0, 0, 0.6), (10.0, 1.3, 1.2), rgb(104, 70, 42))
    builder.box((0, 0, 1.25), (10.4, 1.6, 0.14), rgb(138, 96, 58))
    for mug_x in (-3.5, -1, 2, 4):
        builder.cylinder((mug_x, 0, 1.32), 0.12, 0.28, rgb(200, 200, 208), 6)
    return Prop3D(builder.build(), ("box", 5.2, 0.8))


def fireplace(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("fireplace", rng.randint(0, 9999))
    builder.box((0, 0, 1.6), (5.2, 1.2, 3.2), rgb(112, 106, 100))
    builder.box((0, -0.55, 0.9), (2.4, 0.2, 1.7), rgb(26, 20, 16))
    builder.cone((0, -0.45, 0.2), 0.6, 1.1, rgb(255, 150, 40), 5)
    builder.cone((0, -0.45, 0.2), 0.35, 0.8, rgb(255, 226, 120), 5)
    return Prop3D(builder.build(), ("box", 2.8, 0.8), light=((1.0, 0.55, 0.22), 1.4, True))


def anvil(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("anvil", rng.randint(0, 9999))
    builder.cylinder((0, 0, 0), 0.4, 0.6, rgb(96, 66, 40), 7)
    builder.box((0, 0, 0.8), (1.5, 0.6, 0.3), IRON)
    builder.box((0.95, 0, 0.8), (0.6, 0.3, 0.2), IRON)
    return Prop3D(builder.build(), ("circle", 0.7))


def furnace(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("furnace", rng.randint(0, 9999))
    builder.box((0, 0, 1.4), (5.0, 2.6, 2.8), rgb(98, 94, 92))
    builder.box((0, -1.2, 0.9), (2.2, 0.3, 1.4), rgb(32, 24, 20))
    builder.box((0, -1.25, 0.75), (1.6, 0.2, 0.9), rgb(255, 150, 50))
    builder.box((0, -1.28, 0.6), (1.0, 0.2, 0.5), rgb(255, 226, 130))
    builder.cylinder((1.2, 0.6, 2.8), 0.5, 1.8, rgb(86, 82, 80), 7)
    return Prop3D(builder.build(), ("box", 2.6, 1.4), light=((1.0, 0.5, 0.2), 1.0, True))


def weapon_rack(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("weapon_rack", rng.randint(0, 9999))
    for post_x in (-2.0, 2.0):
        builder.box((post_x, 0, 1.2), (0.16, 0.16, 2.4), DARK_WOOD)
    for rail_z in (0.8, 1.6):
        builder.box((0, 0, rail_z), (4.2, 0.12, 0.12), WOOD)
    for index in range(4):
        blade_x = -1.5 + index * 1.0
        builder.box((blade_x, -0.1, 1.5), (0.1, 0.05, 1.7), rgb(190, 196, 208))
        builder.box((blade_x, -0.1, 0.7), (0.4, 0.07, 0.08), rgb(70, 50, 40))
    return Prop3D(builder.build(), ("box", 2.2, 0.4))


def candle_stand(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("candle_stand", rng.randint(0, 9999))
    builder.cylinder((0, 0, 0), 0.08, 1.7, rgb(60, 56, 50), 6)
    builder.cylinder((0, 0, 1.7), 0.14, 0.4, rgb(236, 230, 206), 6)
    builder.cone((0, 0, 2.1), 0.1, 0.3, rgb(255, 200, 80), 5)
    return Prop3D(builder.build(), ("circle", 0.3), light=((1.0, 0.8, 0.45), 2.3, True))


def pew(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("pew", rng.randint(0, 9999))
    builder.box((0, 0, 0.5), (5.2, 0.9, 0.12), WOOD)
    builder.box((0, 0.5, 1.0), (5.2, 0.12, 1.0), DARK_WOOD)
    for leg_x in (-2.4, 2.4):
        builder.box((leg_x, 0, 0.25), (0.14, 0.8, 0.5), DARK_WOOD)
    return Prop3D(builder.build(), ("box", 2.6, 0.6))


def altar(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("altar", rng.randint(0, 9999))
    builder.box((0, 0, 0.7), (6.0, 1.8, 1.4), rgb(152, 148, 140))
    builder.box((0, -0.1, 1.45), (6.4, 2.0, 0.14), rgb(172, 168, 160))
    builder.box((0, -0.92, 1.0), (4.2, 0.06, 1.1), rgb(130, 34, 44))
    builder.box((0, 0.2, 2.1), (0.2, 0.2, 1.1), rgb(228, 196, 90))
    builder.box((0, 0.2, 2.35), (0.8, 0.2, 0.2), rgb(228, 196, 90))
    for candle_x in (-2.4, 2.4):
        builder.cylinder((candle_x, 0, 1.52), 0.12, 0.5, rgb(238, 232, 208), 6)
        builder.cone((candle_x, 0, 2.02), 0.1, 0.28, rgb(255, 200, 80), 5)
    return Prop3D(builder.build(), ("box", 3.2, 1.0), light=((1.0, 0.82, 0.5), 2.2, True))


def campfire(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("campfire", rng.randint(0, 9999))
    for angle in range(0, 360, 90):
        import math
        radians = math.radians(angle)
        builder.tube(
            (math.cos(radians) * 0.8, math.sin(radians) * 0.8, 0.12),
            (math.cos(radians) * 0.1, math.sin(radians) * 0.1, 0.4),
            0.1, 0.09, rgb(88, 60, 38), 5,
        )
    builder.cone((0, 0, 0.2), 0.45, 1.1, rgb(255, 130, 30), 6)
    builder.cone((0, 0, 0.2), 0.28, 0.8, rgb(255, 214, 100), 6)
    return Prop3D(builder.build(), ("circle", 0.7), light=((1.0, 0.5, 0.2), 1.2, True), emissive=False)


def boat(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("boat", rng.randint(0, 9999))
    builder.box((0, 0, 0.1), (5.0, 1.8, 0.5), rgb(116, 82, 52))
    builder.box((2.8, 0, 0.2), (1.2, 1.0, 0.4), rgb(116, 82, 52), heading=0)
    builder.box((0, 0, 0.45), (4.4, 1.4, 0.06), rgb(150, 112, 70))
    return Prop3D(builder.build(), None)


def dock_post(rng: random.Random) -> Prop3D:
    builder = MeshBuilder("dock_post", rng.randint(0, 9999))
    builder.cylinder((0, 0, -0.5), 0.16, 1.6, rgb(84, 62, 44), 6)
    return Prop3D(builder.build(), ("circle", 0.2))


PROP3D_BUILDERS: Dict[str, Callable[[random.Random], Prop3D]] = {
    "tree_round": tree_round,
    "pine": pine,
    "dead_tree": dead_tree,
    "rock": rock,
    "bush": bush,
    "stump": stump,
    "house": house,
    "hut": hut,
    "tent": tent,
    "tower_ruin": tower_ruin,
    "ruin_wall": ruin_wall,
    "fence": fence,
    "signpost": signpost,
    "lamp_post": lamp_post,
    "well": well,
    "barrel": barrel,
    "crate": crate,
    "table": table,
    "stool": stool,
    "bar_counter": bar_counter,
    "fireplace": fireplace,
    "anvil": anvil,
    "furnace": furnace,
    "weapon_rack": weapon_rack,
    "candle_stand": candle_stand,
    "pew": pew,
    "altar": altar,
    "campfire": campfire,
    "boat": boat,
    "dock_post": dock_post,
}

# Props that stay flat 2D art: lie on the ground / hang on a wall / stand as upright cards.
GROUND_DECALS = {"pool", "flowers", "mat"}
WALL_DECOR = {"shelves", "banner", "window"}
STANDING_CARDS = {"reeds", "mushrooms", "herbs"}
