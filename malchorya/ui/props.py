"""Procedurally drawn props, people and creatures. Each returns a Surface whose
bottom-centre is its foot point."""
import random
from typing import Callable, Dict

import pygame

from ui.textures import Canvas, mix, shade

SHADOW = (0, 0, 0, 80)


def _shadow(canvas: Canvas, center_x: float, bottom: float, width: float, height: float = 8) -> None:
    canvas.ellipse(SHADOW, center_x - width / 2, bottom - height / 2, width, height)


# ------------------------------------------------------------------ nature


def tree_round(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(76, 100)
    base = rng.choice([(46, 110, 52), (54, 120, 48), (40, 98, 58)])
    _shadow(canvas, 38, 94, 46, 12)
    canvas.rect((92, 62, 38), 32, 54, 12, 40, radius=3)
    canvas.rect((70, 46, 28), 40, 54, 4, 40)
    canvas.circle(shade(base, -22), (38, 38), 28)
    canvas.circle(shade(base, -8), (23, 46), 19)
    canvas.circle(shade(base, -8), (53, 46), 19)
    canvas.circle(base, (38, 32), 22)
    canvas.circle(shade(base, 16), (30, 26), 14)
    canvas.circle(shade(base, 30), (27, 22), 7)
    for _ in range(9):
        canvas.circle(shade(base, rng.choice([-30, 24])), (rng.randint(14, 62), rng.randint(16, 56)), 2.5)
    return canvas.result()


def pine(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(60, 112)
    base = rng.choice([(28, 82, 54), (34, 90, 58), (24, 74, 50)])
    _shadow(canvas, 30, 106, 34, 10)
    canvas.rect((84, 58, 38), 26, 88, 8, 20)
    layers = [(100, 56, 62), (80, 48, 52), (60, 40, 42), (42, 32, 30), (26, 24, 18)]
    for index, (bottom, width, height) in enumerate(layers):
        color = shade(base, index * 7 - 12)
        canvas.polygon(color, [(30, bottom - height), (30 - width / 2, bottom), (30 + width / 2, bottom)])
        canvas.polygon(
            shade(color, 22),
            [(30, bottom - height), (30 - width / 2, bottom), (30 - width / 5, bottom - 4)],
        )
    return canvas.result()


def dead_tree(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(70, 100)
    bark = (70, 58, 52)
    _shadow(canvas, 35, 94, 36, 10)
    canvas.polygon(bark, [(30, 94), (34, 40), (38, 40), (42, 94)])
    canvas.line(bark, (36, 54), (14, 28), 3.5)
    canvas.line(bark, (36, 44), (58, 20), 3)
    canvas.line(bark, (36, 62), (56, 46), 2.5)
    canvas.line(bark, (14, 28), (6, 18), 2)
    canvas.line(bark, (14, 28), (18, 14), 2)
    canvas.line(bark, (58, 20), (64, 8), 2)
    canvas.line(shade(bark, 20), (34, 90), (35, 48), 1.5)
    return canvas.result()


def rock(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(48, 34)
    base = rng.choice([(118, 116, 112), (104, 106, 110), (128, 120, 108)])
    _shadow(canvas, 24, 30, 40, 9)
    canvas.polygon(shade(base, -20), [(4, 28), (8, 14), (20, 6), (34, 8), (44, 18), (44, 28)])
    canvas.polygon(base, [(6, 26), (10, 14), (20, 8), (32, 10), (36, 18), (30, 26)])
    canvas.polygon(shade(base, 24), [(11, 14), (20, 8), (30, 10), (22, 14)])
    return canvas.result()


def bush(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(50, 36)
    base = rng.choice([(54, 118, 56), (62, 124, 50), (44, 104, 60)])
    _shadow(canvas, 25, 32, 42, 9)
    canvas.circle(shade(base, -22), (16, 22), 11)
    canvas.circle(shade(base, -22), (34, 22), 11)
    canvas.circle(shade(base, -10), (25, 18), 13)
    canvas.circle(base, (22, 16), 9)
    canvas.circle(shade(base, 22), (19, 13), 5)
    for _ in range(3):
        canvas.circle((200, 60, 70), (rng.randint(12, 38), rng.randint(14, 28)), 1.8)
    return canvas.result()


def reeds(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(40, 56)
    _shadow(canvas, 20, 52, 30, 8)
    for _ in range(7):
        base_x = rng.randint(8, 32)
        top_x = base_x + rng.randint(-4, 4)
        top_y = rng.randint(6, 26)
        canvas.line(rng.choice([(96, 130, 60), (80, 112, 52), (112, 142, 70)]), (base_x, 52), (top_x, top_y), 1.8)
        if rng.random() < 0.5:
            canvas.rect((92, 58, 40), top_x - 1.5, top_y - 2, 3, 9, radius=1.5)
    return canvas.result()


def stump(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(40, 30)
    _shadow(canvas, 20, 26, 34, 8)
    canvas.rect((88, 62, 40), 8, 10, 24, 16, radius=3)
    canvas.ellipse((150, 112, 70), 8, 6, 24, 9)
    canvas.ellipse((120, 86, 52), 12, 8, 16, 5)
    return canvas.result()


def mushrooms(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(30, 24)
    _shadow(canvas, 15, 21, 24, 6)
    for index in range(3):
        stem_x = 7 + index * 8
        height = rng.randint(7, 12)
        canvas.rect((220, 214, 196), stem_x - 1, 20 - height, 3, height)
        canvas.ellipse((190, 50, 60), stem_x - 4, 20 - height - 4, 9, 6)
        canvas.circle((245, 235, 225), (stem_x, 20 - height - 1.5), 1)
    return canvas.result()


def flowers(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(46, 24)
    for _ in range(9):
        flower_x, flower_y = rng.randint(4, 42), rng.randint(5, 20)
        canvas.line((60, 110, 50), (flower_x, flower_y), (flower_x, flower_y + 4), 1)
        canvas.circle(rng.choice([(240, 220, 90), (230, 230, 240), (220, 120, 170), (150, 150, 235)]), (flower_x, flower_y), 2.2)
    return canvas.result()


def herbs(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(40, 30)
    _shadow(canvas, 20, 26, 30, 7)
    for _ in range(8):
        base_x = rng.randint(8, 32)
        canvas.line(rng.choice([(88, 140, 70), (110, 160, 80), (70, 120, 64)]), (base_x, 26), (base_x + rng.randint(-5, 5), rng.randint(6, 16)), 1.6)
    return canvas.result()


def pool(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(110, 44)
    canvas.ellipse((38, 52, 40), 0, 2, 110, 40)
    canvas.ellipse((52, 86, 98), 4, 5, 102, 33)
    canvas.ellipse((70, 110, 120), 14, 10, 60, 14)
    canvas.line((150, 190, 205), (24, 17), (46, 15), 1.5)
    return canvas.result()


# --------------------------------------------------------------- structures


def house(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(150, 150)
    wall = rng.choice([(176, 150, 112), (164, 142, 118), (186, 160, 120)])
    roof = rng.choice([(150, 64, 52), (122, 70, 56), (96, 84, 70)])
    _shadow(canvas, 75, 144, 130, 14)
    canvas.rect(wall, 14, 62, 122, 80)
    for row in range(0, 80, 10):
        canvas.line(shade(wall, -14), (14, 62 + row), (136, 62 + row), 1)
    canvas.rect(shade(wall, -34), 14, 62, 122, 6)
    canvas.polygon(shade(roof, -20), [(4, 70), (75, 8), (146, 70)])
    canvas.polygon(roof, [(10, 68), (75, 14), (140, 68)])
    for row in range(5):
        for column in range(14):
            canvas.rect(shade(roof, rng.choice([-10, 0, 8])), 18 + column * 8.5 - row * 2, 22 + row * 10, 8, 4, radius=1)
    canvas.rect((84, 56, 40), 62, 96, 26, 46, radius=3)
    canvas.circle((220, 190, 90), (82, 120), 1.8)
    for window_left in (26, 100):
        canvas.rect((60, 46, 36), window_left - 2, 84, 26, 28)
        canvas.rect((250, 210, 120), window_left, 86, 22, 24)
        canvas.line((60, 46, 36), (window_left + 11, 86), (window_left + 11, 110), 1.5)
        canvas.line((60, 46, 36), (window_left, 98), (window_left + 22, 98), 1.5)
    return canvas.result()


def hut(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(140, 120)
    _shadow(canvas, 70, 114, 120, 12)
    canvas.rect((98, 72, 52), 18, 52, 104, 60, radius=4)
    for column in range(18, 122, 9):
        canvas.line((74, 54, 38), (column, 52), (column, 112), 2)
    canvas.polygon((74, 92, 52), [(6, 62), (70, 6), (134, 62)])
    canvas.polygon((92, 116, 60), [(12, 60), (70, 12), (128, 60)])
    for index in range(7):
        canvas.line((60, 82, 46), (24 + index * 14, 56), (70, 12), 1.2)
    canvas.polygon((24, 20, 16), [(58, 112), (58, 76), (82, 76), (82, 112)])
    canvas.rect((120, 166, 80), 100, 66, 14, 12)
    canvas.line((200, 190, 120), (30, 40), (30, 56), 1)
    return canvas.result()


def tower_ruin(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(130, 140)
    stone = (112, 108, 104)
    _shadow(canvas, 65, 134, 116, 12)
    canvas.rect(shade(stone, -26), 14, 40, 102, 92)
    canvas.polygon(shade(stone, -26), [(14, 40), (30, 20), (44, 36), (60, 14), (76, 38), (100, 22), (116, 40)])
    for row in range(40, 130, 10):
        offset = 0 if (row // 10) % 2 == 0 else 8
        canvas.line(shade(stone, -50), (14, row), (116, row), 1)
        for column in range(14 + offset, 116, 16):
            canvas.line(shade(stone, -50), (column, row), (column, row + 10), 1)
    canvas.rect(stone, 14, 40, 14, 92)
    canvas.polygon((24, 20, 20), [(46, 132), (46, 82), (58, 68), (70, 82), (70, 132)])
    canvas.polygon(shade(stone, 40), [(20, 100), (28, 92), (34, 104)])
    for _ in range(14):
        canvas.circle(shade(stone, rng.choice([-30, 18])), (rng.randint(18, 112), rng.randint(46, 128)), 2)
    canvas.polygon((60, 100, 56), [(100, 134), (112, 124), (126, 134)])
    return canvas.result()


def ruin_wall(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(90, 46)
    stone = (120, 116, 108)
    _shadow(canvas, 45, 42, 84, 9)
    canvas.polygon(shade(stone, -22), [(4, 40), (4, 22), (16, 16), (28, 22), (40, 12), (56, 20), (72, 14), (86, 22), (86, 40)])
    canvas.polygon(stone, [(6, 38), (6, 24), (16, 19), (28, 24), (40, 16), (54, 22), (70, 17), (84, 24), (84, 38)])
    for column in range(10, 84, 14):
        canvas.line(shade(stone, -40), (column, 24), (column, 38), 1)
    canvas.line(shade(stone, -40), (6, 31), (84, 31), 1)
    return canvas.result()


def fence(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(80, 36)
    wood = (118, 88, 56)
    _shadow(canvas, 40, 33, 74, 6)
    for post_x in (6, 40, 74):
        canvas.rect(shade(wood, -14), post_x - 3, 8, 6, 26, radius=1)
    for rail_y in (12, 22):
        canvas.rect(wood, 3, rail_y, 74, 5, radius=1)
        canvas.line(shade(wood, 24), (3, rail_y + 1), (77, rail_y + 1), 1)
    return canvas.result()


def signpost(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(50, 74)
    wood = (110, 80, 50)
    _shadow(canvas, 25, 70, 24, 7)
    canvas.rect(shade(wood, -16), 22, 12, 6, 58)
    canvas.polygon(wood, [(6, 16), (36, 16), (46, 23), (36, 30), (6, 30)])
    canvas.polygon(shade(wood, 12), [(10, 36), (40, 36), (40, 48), (10, 48), (4, 42)])
    canvas.line((60, 40, 30), (10, 23), (32, 23), 1.5)
    canvas.line((60, 40, 30), (12, 42), (34, 42), 1.5)
    return canvas.result()


def lamp_post(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(34, 84)
    _shadow(canvas, 17, 80, 20, 6)
    canvas.rect((50, 50, 56), 15, 22, 4, 58)
    canvas.rect((50, 50, 56), 10, 76, 14, 4, radius=1)
    canvas.rect((50, 50, 56), 9, 10, 16, 14, radius=2)
    canvas.rect((255, 214, 120), 11, 12, 12, 10)
    canvas.polygon((50, 50, 56), [(8, 10), (17, 3), (26, 10)])
    return canvas.result()


def well(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(70, 80)
    stone = (128, 124, 116)
    _shadow(canvas, 35, 74, 60, 10)
    canvas.ellipse(shade(stone, -30), 8, 44, 54, 28)
    canvas.rect(stone, 8, 44, 54, 20)
    canvas.ellipse(shade(stone, 14), 8, 34, 54, 22)
    canvas.ellipse((30, 40, 52), 14, 38, 42, 14)
    canvas.rect((96, 68, 44), 10, 12, 5, 40)
    canvas.rect((96, 68, 44), 55, 12, 5, 40)
    canvas.polygon((120, 64, 48), [(4, 14), (35, 2), (66, 14)])
    return canvas.result()


def dock_post(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(20, 46)
    _shadow(canvas, 10, 42, 16, 5)
    canvas.rect((84, 62, 44), 6, 8, 8, 34, radius=2)
    canvas.ellipse((124, 98, 66), 6, 5, 8, 6)
    return canvas.result()


def boat(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(120, 52)
    wood = (118, 82, 52)
    canvas.ellipse((20, 50, 70, 120), 4, 36, 112, 12)
    canvas.polygon(shade(wood, -20), [(6, 20), (114, 20), (98, 42), (22, 42)])
    canvas.polygon(wood, [(8, 20), (112, 20), (104, 30), (16, 30)])
    canvas.line(shade(wood, 30), (10, 21), (110, 21), 2)
    canvas.line(shade(wood, -40), (20, 30), (100, 30), 1)
    canvas.line((90, 66, 40), (60, 24), (96, 6), 2.5)
    return canvas.result()


def campfire(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(46, 44)
    _shadow(canvas, 23, 38, 36, 8)
    for angle_end in ((8, 34), (38, 34), (12, 28), (34, 28)):
        canvas.line((90, 62, 40), (23, 32), angle_end, 3.4)
    canvas.polygon((240, 110, 30), [(23, 6), (32, 24), (28, 32), (18, 32), (14, 22)])
    canvas.polygon((255, 190, 60), [(23, 14), (28, 26), (24, 32), (19, 30), (18, 24)])
    canvas.polygon((255, 240, 160), [(23, 22), (25, 29), (21, 29)])
    return canvas.result()


def tent(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(100, 76)
    cloth = rng.choice([(130, 70, 60), (96, 84, 70)])
    _shadow(canvas, 50, 70, 90, 10)
    canvas.polygon(shade(cloth, -26), [(50, 6), (4, 68), (96, 68)])
    canvas.polygon(cloth, [(50, 8), (10, 66), (50, 66)])
    canvas.polygon((26, 20, 18), [(50, 36), (36, 68), (64, 68)])
    canvas.line((70, 60, 40), (50, 6), (50, 0), 2)
    return canvas.result()


# ----------------------------------------------------------------- furniture


def barrel(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(34, 42)
    wood = (120, 82, 48)
    _shadow(canvas, 17, 38, 28, 7)
    canvas.ellipse(shade(wood, -16), 3, 24, 28, 14)
    canvas.rect(wood, 3, 8, 28, 22)
    canvas.ellipse(shade(wood, 12), 3, 2, 28, 14)
    canvas.ellipse(shade(wood, -6), 6, 4, 22, 9)
    for band_y in (13, 24):
        canvas.line((54, 54, 60), (3, band_y), (31, band_y), 2)
    return canvas.result()


def crate(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(40, 40)
    wood = (140, 106, 64)
    _shadow(canvas, 20, 36, 34, 7)
    canvas.rect(shade(wood, -18), 4, 10, 32, 24)
    canvas.polygon(shade(wood, 14), [(4, 10), (12, 4), (38, 4), (36, 10)])
    canvas.rect(wood, 5, 11, 30, 22)
    canvas.line(shade(wood, -40), (5, 11), (35, 33), 2)
    canvas.line(shade(wood, -40), (35, 11), (5, 33), 2)
    return canvas.result()


def table(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(86, 56)
    wood = (126, 90, 54)
    _shadow(canvas, 43, 52, 78, 9)
    for leg_x in (10, 70):
        canvas.rect(shade(wood, -34), leg_x, 26, 6, 24)
    canvas.ellipse(shade(wood, -22), 4, 14, 78, 22)
    canvas.ellipse(wood, 4, 10, 78, 22)
    canvas.ellipse(shade(wood, 14), 12, 13, 62, 12)
    canvas.rect((190, 190, 200), 40, 10, 6, 7, radius=1)
    canvas.rect((70, 120, 80), 24, 14, 7, 6, radius=1)
    return canvas.result()


def stool(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(28, 34)
    wood = (120, 84, 50)
    _shadow(canvas, 14, 30, 22, 6)
    canvas.rect(shade(wood, -30), 6, 14, 3, 14)
    canvas.rect(shade(wood, -30), 19, 14, 3, 14)
    canvas.ellipse(shade(wood, 8), 3, 8, 22, 10)
    return canvas.result()


def bar_counter(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(190, 70)
    wood = (104, 70, 42)
    _shadow(canvas, 95, 66, 184, 10)
    canvas.rect(shade(wood, -16), 4, 26, 182, 38)
    for plank_x in range(4, 186, 22):
        canvas.line(shade(wood, -44), (plank_x, 26), (plank_x, 64), 1.5)
    canvas.rect(shade(wood, 18), 0, 16, 190, 12, radius=2)
    canvas.line(shade(wood, 40), (2, 18), (188, 18), 1.5)
    for mug_x in (30, 78, 130, 160):
        canvas.rect((196, 196, 204), mug_x, 6, 8, 11, radius=1.5)
        canvas.rect((238, 236, 224), mug_x, 6, 8, 3)
    return canvas.result()


def fireplace(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(110, 96)
    stone = (112, 106, 100)
    _shadow(canvas, 55, 92, 96, 10)
    canvas.rect(shade(stone, -20), 6, 14, 98, 78)
    canvas.rect(stone, 10, 18, 90, 70)
    canvas.rect((22, 18, 16), 26, 36, 58, 56, radius=4)
    canvas.polygon((230, 100, 30), [(55, 52), (72, 92), (38, 92)])
    canvas.polygon((255, 190, 60), [(55, 66), (64, 92), (46, 92)])
    canvas.rect(shade(stone, 18), 2, 8, 106, 10, radius=2)
    for log_y in (86,):
        canvas.line((80, 52, 30), (32, log_y), (78, log_y), 5)
    return canvas.result()


def shelves(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(120, 60)
    wood = (96, 66, 40)
    for shelf_y in (20, 48):
        canvas.rect(wood, 0, shelf_y, 120, 5)
        for bottle_x in range(8, 112, rng.randint(11, 15)):
            bottle_color = rng.choice([(70, 130, 90), (160, 70, 60), (90, 100, 170), (190, 160, 70)])
            canvas.rect(bottle_color, bottle_x, shelf_y - 14, 6, 14, radius=2)
            canvas.rect(bottle_color, bottle_x + 1.5, shelf_y - 19, 3, 6)
    return canvas.result()


def anvil(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(56, 52)
    iron = (70, 74, 82)
    _shadow(canvas, 28, 48, 44, 8)
    canvas.rect((96, 66, 40), 16, 32, 24, 16, radius=2)
    canvas.polygon(shade(iron, -10), [(6, 20), (50, 20), (44, 30), (38, 34), (18, 34), (14, 30)])
    canvas.polygon(shade(iron, 14), [(6, 20), (50, 20), (52, 17), (2, 17)])
    canvas.polygon(shade(iron, 14), [(50, 20), (58, 18), (50, 24)])
    canvas.line((150, 150, 160), (8, 18), (46, 18), 1)
    return canvas.result()


def furnace(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(130, 120)
    stone = (96, 92, 90)
    _shadow(canvas, 65, 114, 116, 12)
    canvas.rect(shade(stone, -22), 8, 26, 114, 88)
    canvas.rect(stone, 12, 30, 106, 80)
    canvas.polygon(shade(stone, -16), [(30, 30), (44, 4), (86, 4), (100, 30)])
    canvas.rect((30, 22, 20), 36, 56, 58, 54, radius=8)
    canvas.rect((190, 60, 22), 40, 66, 50, 44, radius=6)
    canvas.rect((250, 140, 40), 46, 78, 38, 32, radius=6)
    canvas.rect((255, 220, 120), 54, 92, 22, 18, radius=5)
    for row in range(36, 106, 14):
        canvas.line(shade(stone, -44), (12, row), (118, row), 1)
    return canvas.result()


def weapon_rack(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(90, 74)
    wood = (96, 66, 40)
    _shadow(canvas, 45, 70, 80, 8)
    canvas.rect(wood, 4, 8, 6, 62)
    canvas.rect(wood, 80, 8, 6, 62)
    canvas.rect(wood, 4, 28, 82, 5)
    canvas.rect(wood, 4, 52, 82, 5)
    for index in range(4):
        blade_x = 18 + index * 16
        canvas.line((180, 186, 196), (blade_x, 10), (blade_x, 52), 2.4)
        canvas.rect((70, 50, 40), blade_x - 4, 46, 8, 3)
        canvas.rect((60, 40, 30), blade_x - 1.5, 49, 3, 10)
    return canvas.result()


def candle_stand(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(34, 74)
    _shadow(canvas, 17, 70, 20, 6)
    canvas.rect((60, 56, 50), 15, 28, 4, 40)
    canvas.rect((60, 56, 50), 8, 66, 18, 4, radius=1)
    canvas.rect((230, 224, 200), 13, 18, 8, 12, radius=1)
    canvas.polygon((255, 190, 70), [(17, 4), (21, 14), (13, 14)])
    canvas.polygon((255, 240, 170), [(17, 8), (19, 14), (15, 14)])
    return canvas.result()


def pew(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(110, 48)
    wood = (110, 76, 46)
    _shadow(canvas, 55, 44, 104, 8)
    canvas.rect(shade(wood, -22), 4, 8, 102, 10, radius=2)
    canvas.rect(wood, 4, 18, 102, 14)
    canvas.line(shade(wood, 22), (6, 19), (104, 19), 1.5)
    for leg_x in (10, 94):
        canvas.rect(shade(wood, -34), leg_x, 30, 6, 12)
    return canvas.result()


def altar(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(130, 90)
    stone = (150, 146, 138)
    _shadow(canvas, 65, 86, 120, 10)
    canvas.rect(shade(stone, -26), 10, 34, 110, 48)
    canvas.rect(stone, 14, 34, 102, 44)
    canvas.rect((120, 30, 40), 24, 36, 82, 26)
    canvas.rect((220, 190, 90), 24, 36, 82, 3)
    canvas.rect((220, 190, 90), 24, 59, 82, 3)
    canvas.rect(shade(stone, 20), 6, 26, 118, 10, radius=2)
    for candle_x in (22, 100):
        canvas.rect((236, 230, 206), candle_x, 10, 8, 16, radius=1)
        canvas.polygon((255, 190, 70), [(candle_x + 4, 0), (candle_x + 8, 10), (candle_x, 10)])
    canvas.rect((230, 200, 90), 61, 14, 8, 20)
    canvas.rect((230, 200, 90), 55, 20, 20, 6)
    return canvas.result()


def banner(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(40, 80)
    canvas.rect((80, 58, 40), 2, 2, 36, 4)
    canvas.polygon((140, 40, 50), [(5, 6), (35, 6), (35, 64), (20, 54), (5, 64)])
    canvas.polygon((220, 190, 90), [(20, 18), (26, 28), (14, 28)])
    return canvas.result()


def window(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(48, 74)
    canvas.rect((60, 56, 50), 0, 0, 48, 74, radius=18)
    colors = [(190, 70, 70), (70, 100, 190), (220, 190, 70), (70, 160, 110)]
    for index in range(6):
        pane_x = 6 + (index % 2) * 18
        pane_y = 8 + (index // 2) * 20
        canvas.rect(colors[(index + rng.randint(0, 3)) % 4], pane_x, pane_y, 16, 18, radius=3)
    return canvas.result()


def mat(rng: random.Random) -> pygame.Surface:
    canvas = Canvas(104, 44)
    canvas.rect((92, 40, 36), 0, 0, 104, 44, radius=6)
    canvas.rect((130, 62, 48), 5, 5, 94, 34, radius=4)
    canvas.rect((190, 150, 70), 10, 10, 84, 24, radius=3)
    return canvas.result()


# ------------------------------------------------------------------- people


def person(
    robe=(120, 90, 60),
    trim=(70, 50, 34),
    skin=(228, 190, 156),
    hair=(70, 48, 30),
    hat="none",
    held="none",
    apron=None,
    beard=None,
    mask=False,
) -> pygame.Surface:
    canvas = Canvas(48, 74)
    _shadow(canvas, 24, 68, 28, 8)
    canvas.rect(shade(trim, -20), 15, 52, 7, 14, radius=2)
    canvas.rect(shade(trim, -20), 26, 52, 7, 14, radius=2)
    canvas.ellipse((40, 28, 24), 13, 62, 10, 6)
    canvas.ellipse((40, 28, 24), 25, 62, 10, 6)
    canvas.rect(shade(robe, -22), 9, 28, 6, 22, radius=3)
    canvas.rect(shade(robe, -22), 33, 28, 6, 22, radius=3)
    canvas.circle(skin, (12, 50), 3.2)
    canvas.circle(skin, (36, 50), 3.2)
    canvas.rect(robe, 12, 26, 24, 30, radius=7)
    canvas.rect(shade(robe, 18), 15, 28, 8, 24, radius=4)
    canvas.rect(trim, 12, 42, 24, 4)
    if apron is not None:
        canvas.rect(apron, 15, 36, 18, 22, radius=3)
    canvas.rect(shade(skin, -12), 20, 22, 8, 6)
    canvas.circle(skin, (24, 17), 9.5)
    canvas.circle((40, 30, 30), (21, 17), 1.1)
    canvas.circle((40, 30, 30), (27, 17), 1.1)
    canvas.line(shade(skin, -34), (22.5, 22), (25.5, 22), 1)
    if mask:
        canvas.rect((50, 40, 44), 14, 15, 20, 5)
    if beard is not None:
        canvas.polygon(beard, [(16, 19), (32, 19), (30, 30), (24, 35), (18, 30)])
    if hat in ("none", "cap", "straw", "bandana", "mitre"):
        canvas.ellipse(hair, 14.5, 6, 19, 10)
    if hat == "cap":
        canvas.ellipse(shade(robe, -10), 13, 5, 22, 10)
        canvas.rect(shade(robe, -30), 11, 11, 26, 3, radius=1)
    elif hat == "helmet":
        canvas.ellipse((150, 156, 166), 13, 4, 22, 17)
        canvas.rect((150, 156, 166), 13, 12, 22, 5)
        canvas.rect((118, 124, 138), 22, 12, 4, 10)
    elif hat == "hood":
        canvas.circle(shade(robe, -26), (24, 14), 13)
        canvas.circle((24, 18, 16), (24, 18), 7.5)
        canvas.circle((250, 230, 120), (21.5, 17.5), 1)
        canvas.circle((250, 230, 120), (26.5, 17.5), 1)
    elif hat == "straw":
        canvas.ellipse((214, 186, 100), 6, 8, 36, 8)
        canvas.ellipse((228, 202, 116), 14, 2, 20, 11)
    elif hat == "bandana":
        canvas.rect((170, 40, 40), 14, 8, 20, 4)
        canvas.polygon((170, 40, 40), [(34, 10), (42, 16), (36, 17)])
    elif hat == "mitre":
        canvas.polygon((236, 232, 220), [(14, 11), (24, -3), (34, 11)])
        canvas.line((220, 190, 90), (24, 0), (24, 10), 1.6)
    if held == "spear":
        canvas.line((110, 80, 50), (42, 8), (42, 68), 2.2)
        canvas.polygon((190, 196, 206), [(42, -2), (39, 10), (45, 10)])
    elif held == "pole":
        canvas.line((110, 90, 60), (43, 2), (43, 70), 2.4)
    elif held == "staff":
        canvas.line((96, 70, 44), (43, 6), (43, 68), 2.4)
        canvas.circle((120, 220, 200), (43, 6), 3.2)
    elif held == "hammer":
        canvas.line((100, 72, 44), (40, 34), (44, 52), 2.2)
        canvas.rect((110, 114, 124), 35, 28, 12, 8, radius=1)
    elif held == "mug":
        canvas.rect((196, 196, 204), 38, 44, 7, 9, radius=1.5)
    elif held == "dagger":
        canvas.polygon((200, 206, 216), [(38, 48), (36, 58), (40, 58)])
    elif held == "bag":
        canvas.ellipse((130, 96, 56), 32, 40, 16, 18)
    return canvas.result()


NPC_STYLES: Dict[str, Callable[[], pygame.Surface]] = {
    "merchant": lambda: person(robe=(150, 100, 56), trim=(86, 56, 30), hat="cap", held="bag", beard=(90, 70, 50)),
    "citizen": lambda: person(robe=(88, 118, 150), trim=(54, 70, 96), hat="none", hair=(150, 96, 52)),
    "guard": lambda: person(robe=(98, 110, 130), trim=(60, 66, 84), hat="helmet", held="spear", beard=None),
    "mysterious": lambda: person(robe=(36, 34, 52), trim=(20, 20, 30), hat="hood"),
    "blacksmith": lambda: person(robe=(130, 78, 50), trim=(64, 44, 32), hat="none", held="hammer", apron=(66, 58, 56), hair=(40, 28, 20)),
    "innkeeper": lambda: person(robe=(178, 170, 152), trim=(110, 90, 66), hat="none", apron=(236, 232, 220), held="mug", beard=(150, 120, 84)),
    "ferryman": lambda: person(robe=(74, 112, 104), trim=(40, 66, 62), hat="straw", held="pole", beard=(180, 180, 176)),
    "priest": lambda: person(robe=(232, 228, 214), trim=(206, 170, 76), hat="mitre", held="staff", hair=(180, 180, 180)),
    "hermit": lambda: person(robe=(106, 92, 66), trim=(66, 54, 40), hat="hood", held="staff", beard=(190, 190, 184)),
}


# ---------------------------------------------------------------- creatures


def wolf() -> pygame.Surface:
    canvas = Canvas(84, 56)
    fur = (112, 116, 124)
    _shadow(canvas, 40, 50, 64, 9)
    for leg_x in (18, 28, 52, 62):
        canvas.rect(shade(fur, -34), leg_x - 3, 34, 6, 15, radius=2)
    canvas.polygon(shade(fur, -14), [(10, 26), (0, 14), (4, 12), (16, 22)])
    canvas.ellipse(shade(fur, -16), 8, 18, 56, 26)
    canvas.ellipse(fur, 10, 14, 54, 24)
    canvas.ellipse(shade(fur, 26), 20, 30, 34, 10)
    canvas.ellipse(shade(fur, -22), 14, 14, 30, 8)
    canvas.ellipse(fur, 54, 12, 22, 18)
    canvas.polygon(shade(fur, 10), [(68, 22), (82, 28), (68, 32)])
    canvas.circle((30, 24, 24), (82, 28), 2.4)
    canvas.polygon(shade(fur, -26), [(58, 14), (60, 4), (66, 13)])
    canvas.polygon(shade(fur, -26), [(66, 14), (70, 5), (73, 15)])
    canvas.circle((220, 40, 40), (69, 21), 2)
    canvas.polygon((236, 232, 224), [(72, 31), (74, 36), (76, 31)])
    return canvas.result()


def bandit() -> pygame.Surface:
    return person(
        robe=(98, 54, 48), trim=(44, 30, 26), hat="bandana", held="dagger", mask=True, hair=(30, 24, 20),
    )


def bog_lurker() -> pygame.Surface:
    canvas = Canvas(76, 76)
    mud = (58, 74, 44)
    _shadow(canvas, 38, 68, 58, 10)
    canvas.line(shade(mud, -10), (12, 40), (2, 62), 3.5)
    canvas.line(shade(mud, -10), (64, 40), (74, 60), 3.5)
    canvas.ellipse(shade(mud, -26), 8, 24, 60, 46)
    canvas.ellipse(mud, 10, 20, 56, 44)
    canvas.ellipse(shade(mud, 16), 18, 24, 34, 20)
    for drip_x in (18, 30, 44, 56):
        canvas.polygon(shade(mud, -20), [(drip_x, 58), (drip_x + 4, 58), (drip_x + 2, 68)])
    for reed_x in (28, 38, 48):
        canvas.line((90, 120, 56), (reed_x, 22), (reed_x + (reed_x - 38) // 2, 4), 2)
    canvas.circle((250, 230, 70), (28, 36), 5.5)
    canvas.circle((250, 230, 70), (48, 36), 5.5)
    canvas.circle((30, 20, 10), (28, 37), 2.4)
    canvas.circle((30, 20, 10), (48, 37), 2.4)
    canvas.polygon((24, 14, 14), [(22, 48), (30, 44), (38, 49), (46, 44), (54, 48), (46, 56), (38, 52), (30, 56)])
    for tooth_x in (28, 36, 44):
        canvas.polygon((230, 226, 205), [(tooth_x, 47), (tooth_x + 3, 47), (tooth_x + 1.5, 52)])
    return canvas.result()


ENEMY_BUILDERS: Dict[str, Callable[[], pygame.Surface]] = {
    "wolf": wolf,
    "bandit": bandit,
    "bog_lurker": bog_lurker,
}

# --------------------------------------------------------------------- registry

PROP_BUILDERS: Dict[str, Callable[[random.Random], pygame.Surface]] = {
    "tree_round": tree_round,
    "pine": pine,
    "dead_tree": dead_tree,
    "rock": rock,
    "bush": bush,
    "reeds": reeds,
    "stump": stump,
    "mushrooms": mushrooms,
    "flowers": flowers,
    "herbs": herbs,
    "pool": pool,
    "house": house,
    "hut": hut,
    "tower_ruin": tower_ruin,
    "ruin_wall": ruin_wall,
    "fence": fence,
    "signpost": signpost,
    "lamp_post": lamp_post,
    "well": well,
    "dock_post": dock_post,
    "boat": boat,
    "campfire": campfire,
    "tent": tent,
    "barrel": barrel,
    "crate": crate,
    "table": table,
    "stool": stool,
    "bar_counter": bar_counter,
    "fireplace": fireplace,
    "shelves": shelves,
    "anvil": anvil,
    "furnace": furnace,
    "weapon_rack": weapon_rack,
    "candle_stand": candle_stand,
    "pew": pew,
    "altar": altar,
    "banner": banner,
    "window": window,
    "mat": mat,
}

# Props that lie flat on the ground and never hide the player.
DECALS = {"pool", "flowers", "mat"}
