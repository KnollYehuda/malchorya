"""Articulated low-poly character and creature models (people, wolf, bog lurker)."""
import math
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Tuple

from panda3d.core import NodePath

from ui3d.meshes import MeshBuilder, rgb

Color = Tuple[int, int, int]


def _mesh(name: str, seed: int, variation: float = 0.05) -> MeshBuilder:
    return MeshBuilder(name, seed, variation)


def _node(parent: NodePath, name: str, position=(0, 0, 0)) -> NodePath:
    node = parent.attachNewNode(name)
    node.setPos(*position)
    return node


@dataclass
class Rig:
    """A posed model. `animate` is driven by the game each frame."""

    root: NodePath
    height: float
    kind: str
    parts: Dict[str, NodePath] = field(default_factory=dict)
    attack_time: float = 99.0
    _animator: Optional[Callable] = None

    def start_attack(self) -> None:
        self.attack_time = 0.0

    def animate(self, delta: float, walk_phase: float, walk_amount: float, clock: float, look_degrees: float = 0.0) -> None:
        self.attack_time += delta
        if self._animator:
            self._animator(self, walk_phase, walk_amount, clock, look_degrees)

    def tint(self, red: float, green: float, blue: float) -> None:
        self.root.setColorScale(red, green, blue, 1)


# ================================================================== humanoid


def _hat(head: NodePath, hat: str, robe: Color, hair: Color, seed: int) -> None:
    builder = _mesh("hat", seed, 0.04)
    if hat == "felt":
        green = rgb(52, 120, 56)
        builder.tube((0, 0, 0.66), (0, 0, 0.72), 0.7, 0.7, green, 10)
        builder.sphere((0, 0, 0.7), (0.47, 0.47, 0.34), rgb(60, 134, 62), rings=2, segments=10)
        builder.tube((0, 0, 0.66), (0, 0, 0.78), 0.5, 0.48, rgb(40, 90, 46), 10)
        builder.tube((0.3, -0.1, 0.84), (0.55, 0.0, 1.12), 0.07, 0.03, rgb(246, 214, 60), 5)
        builder.tube((0.55, 0.0, 1.12), (0.45, 0.1, 1.3), 0.04, 0.0, rgb(250, 226, 90), 5)
    elif hat == "cap":
        color = rgb(*robe)
        builder.sphere((0, 0.02, 0.62), (0.44, 0.44, 0.26), color, rings=2, segments=9)
        builder.box((0, -0.38, 0.52), (0.6, 0.3, 0.06), rgb(max(0, robe[0] - 30), max(0, robe[1] - 30), max(0, robe[2] - 30)))
    elif hat == "helmet":
        steel = rgb(150, 156, 166)
        builder.sphere((0, 0, 0.58), (0.46, 0.46, 0.4), steel, rings=3, segments=10)
        builder.tube((0, 0, 0.5), (0, 0, 0.58), 0.48, 0.48, rgb(118, 124, 138), 10)
        builder.box((0, -0.43, 0.36), (0.08, 0.06, 0.34), rgb(118, 124, 138))
        builder.cone((0, 0, 0.9), 0.06, 0.28, rgb(180, 50, 50), 5)
    elif hat == "hood":
        cloth = rgb(max(0, robe[0] - 8), max(0, robe[1] - 8), max(0, robe[2] - 8))
        builder.sphere((0, 0.1, 0.5), (0.52, 0.56, 0.56), cloth, rings=3, segments=10)
        builder.cone((0, 0.5, 0.45), 0.34, 0.5, cloth, 6)
    elif hat == "straw":
        builder.tube((0, 0, 0.55), (0, 0, 0.6), 0.82, 0.82, rgb(214, 186, 100), 12)
        builder.sphere((0, 0, 0.62), (0.4, 0.4, 0.26), rgb(228, 202, 116), rings=2, segments=10)
        builder.tube((0, 0, 0.6), (0, 0, 0.68), 0.43, 0.42, rgb(150, 80, 60), 10)
    elif hat == "bandana":
        builder.tube((0, 0, 0.52), (0, 0, 0.68), 0.43, 0.43, rgb(170, 40, 40), 10)
        builder.box((0, 0.45, 0.56), (0.14, 0.3, 0.1), rgb(150, 34, 34))
    elif hat == "mitre":
        builder.cone((0, 0, 0.6), 0.4, 0.82, rgb(238, 234, 222), 8)
        builder.tube((0, 0, 0.62), (0, 0, 0.74), 0.4, 0.38, rgb(214, 176, 80), 8)
        builder.box((0, -0.28, 1.05), (0.08, 0.06, 0.34), rgb(214, 176, 80))
        builder.box((0, -0.28, 1.08), (0.28, 0.06, 0.08), rgb(214, 176, 80))
    else:  # bare head: hair
        builder.sphere((0, 0.06, 0.52), (0.43, 0.42, 0.36), rgb(*hair), rings=2, segments=9)
        builder.sphere((0, -0.18, 0.64), (0.4, 0.2, 0.14), rgb(*hair), rings=1, segments=8)
    if hat in ("cap", "straw", "bandana", "mitre"):
        hair_builder = _mesh("hair", seed + 1, 0.04)
        hair_builder.sphere((0, 0.1, 0.42), (0.43, 0.4, 0.3), rgb(*hair), rings=2, segments=9)
        hair_builder.build().reparentTo(head)
    builder.build().reparentTo(head)


def _held_item(hand: NodePath, held: str) -> None:
    builder = _mesh("held", 3, 0.03)
    wood = rgb(110, 80, 48)
    glow_node = None
    if held == "spear":
        builder.tube((0, 0, -1.0), (0, 0, 1.9), 0.04, 0.04, wood, 5)
        builder.cone((0, 0, 1.9), 0.07, 0.34, rgb(196, 202, 214), 5)
    elif held == "pole":
        builder.tube((0, 0, -1.1), (0.05, 0, 2.1), 0.045, 0.045, rgb(120, 96, 64), 5)
    elif held == "staff":
        builder.tube((0, 0, -1.0), (0, 0, 1.7), 0.045, 0.04, rgb(96, 70, 44), 5)
        glow = _mesh("glow", 4, 0.0)
        glow.sphere((0, 0, 1.82), (0.11, 0.11, 0.11), rgb(130, 230, 220), rings=2, segments=6)
        glow_node = glow.build()
        glow_node.setLightOff()
        glow_node.reparentTo(hand)
    elif held == "hammer":
        builder.tube((0, 0, -0.25), (0, -0.25, 0.4), 0.04, 0.04, wood, 5)
        builder.box((0, -0.28, 0.45), (0.36, 0.2, 0.17), rgb(110, 114, 124))
    elif held == "mug":
        builder.cylinder((0, -0.12, -0.12), 0.07, 0.16, rgb(200, 200, 208), 7)
        builder.cylinder((0, -0.12, 0.0), 0.065, 0.04, rgb(238, 232, 200), 7)
    elif held == "dagger":
        builder.box((0, -0.06, -0.3), (0.04, 0.05, 0.4), rgb(212, 218, 228))
        builder.box((0, -0.06, -0.08), (0.14, 0.05, 0.04), rgb(70, 50, 40))
    else:
        return
    builder.build().reparentTo(hand)


def build_humanoid(
    name: str,
    robe: Color = (120, 90, 60),
    trim: Color = (70, 50, 34),
    skin: Color = (228, 190, 156),
    hair: Color = (70, 48, 30),
    hat: str = "none",
    held: str = "none",
    apron: Optional[Color] = None,
    beard: Optional[Color] = None,
    mask: bool = False,
    long_robe: bool = False,
    stripes: Optional[Tuple[Color, Color]] = None,
    backpack: bool = False,
    bag: bool = False,
    glow_eyes: bool = False,
    scale: float = 1.0,
    seed: int = 0,
) -> Rig:
    root = NodePath(name)
    model = _node(root, "model")
    model.setScale(scale)
    parts: Dict[str, NodePath] = {}

    # Legs
    for side, sign in (("leg_l", -1), ("leg_r", 1)):
        pivot = _node(model, side, (sign * 0.2, 0, 0.92))
        leg = _mesh(side, seed + sign, 0.04)
        leg.tube((0, 0, 0), (0, 0, -0.68), 0.14, 0.12, rgb(*trim), 7)
        leg.box((0, -0.06, -0.8), (0.27, 0.42, 0.22), rgb(78, 52, 34))
        leg.build().reparentTo(pivot)
        parts[side] = pivot

    upper = _node(model, "upper")
    parts["upper"] = upper

    # Torso
    torso = _mesh("torso", seed + 5, 0.04)
    if stripes:
        bands = [(0.92, 1.12), (1.12, 1.32), (1.32, 1.52), (1.52, 1.66)]
        for index, (low, high) in enumerate(bands):
            color = stripes[index % 2]
            torso.tube((0, 0, low), (0, 0, high), 0.4 - index * 0.015, 0.4 - (index + 1) * 0.015, rgb(*color), 9)
    else:
        torso.tube((0, 0, 0.92), (0, 0, 1.66), 0.4, 0.34, rgb(*robe), 9)
    torso.tube((0, 0, 1.0), (0, 0, 1.1), 0.42, 0.42, rgb(*trim), 9)
    torso.box((0, 0, 1.05), (0.12, 0.06, 0.1), rgb(214, 180, 90))
    if long_robe:
        torso.tube((0, 0, 0.3), (0, 0, 0.95), 0.58, 0.42, rgb(*robe), 9)
        torso.tube((0, 0, 0.3), (0, 0, 0.38), 0.6, 0.6, rgb(*trim), 9)
    if apron:
        torso.box((0, -0.36, 1.1), (0.5, 0.06, 0.64), rgb(*apron))
    if backpack:
        torso.box((0, 0.42, 1.28), (0.6, 0.34, 0.66), rgb(112, 76, 44))
        torso.tube((-0.34, 0.45, 1.68), (0.34, 0.45, 1.68), 0.14, 0.14, rgb(206, 186, 140), 7)
        torso.box((0, 0.6, 1.2), (0.3, 0.06, 0.3), rgb(86, 56, 34))
    if bag:
        torso.sphere((-0.5, -0.05, 0.98), (0.22, 0.18, 0.24), rgb(130, 96, 56), rings=2, segments=7)
    torso.build().reparentTo(upper)

    # Arms
    for side, sign in (("arm_l", -1), ("arm_r", 1)):
        pivot = _node(upper, side, (sign * 0.5, 0, 1.52))
        arm = _mesh(side, seed + 9 + sign, 0.04)
        sleeve = stripes[1] if stripes else robe
        arm.tube((0, 0, 0), (0, 0, -0.56), 0.115, 0.1, rgb(*sleeve), 7)
        arm.sphere((0, 0, -0.64), (0.11, 0.11, 0.11), rgb(*skin), rings=2, segments=7)
        arm.build().reparentTo(pivot)
        parts[side] = pivot
        if side == "arm_r":
            hand = _node(pivot, "hand", (0, -0.04, -0.64))
            parts["hand"] = hand
            _held_item(hand, held)

    # Head
    head = _node(upper, "head", (0, 0, 1.64))
    head_mesh = _mesh("head", seed + 12, 0.03)
    head_mesh.sphere((0, 0, 0.4), (0.4, 0.38, 0.4), rgb(*skin), rings=3, segments=10)
    head_mesh.sphere((0, -0.4, 0.34), (0.065, 0.07, 0.065), rgb(max(0, skin[0] - 18), max(0, skin[1] - 24), max(0, skin[2] - 24)), rings=1, segments=6)
    for side in (-1, 1):
        head_mesh.sphere((side * 0.16, -0.33, 0.45), (0.06, 0.04, 0.07), rgb(250, 250, 250), rings=1, segments=6)
        head_mesh.sphere((side * 0.16, -0.365, 0.45), (0.035, 0.03, 0.045), rgb(30, 24, 22), rings=1, segments=6)
        head_mesh.box((side * 0.16, -0.34, 0.54), (0.14, 0.03, 0.025), rgb(*hair))
        head_mesh.sphere((side * 0.4, 0.0, 0.38), (0.05, 0.08, 0.1), rgb(*skin), rings=1, segments=6)
    head_mesh.box((0, -0.36, 0.24), (0.12, 0.03, 0.025), rgb(150, 70, 70))
    if mask:
        head_mesh.box((0, -0.34, 0.44), (0.66, 0.1, 0.12), rgb(40, 34, 34))
    if glow_eyes:
        glow = _mesh("glow_eyes", seed + 30, 0.0)
        for side in (-1, 1):
            glow.sphere((side * 0.15, -0.36, 0.46), (0.07, 0.04, 0.05), rgb(255, 214, 70), rings=1, segments=6)
        glow_node = glow.build()
        glow_node.setLightOff()
        glow_node.reparentTo(head)
    if beard:
        head_mesh.sphere((0, -0.2, 0.12), (0.3, 0.2, 0.28), rgb(*beard), rings=2, segments=8)
    head_mesh.build().reparentTo(head)
    # Hat positions are authored relative to the head centre (z = 0 at the neck here).
    hat_holder = _node(head, "hat_holder", (0, 0, 0))
    _hat(hat_holder, hat, robe, hair, seed + 20)
    parts["head"] = head

    rig = Rig(root=root, height=2.3 * scale, kind="humanoid", parts=parts)
    rig._animator = _animate_humanoid
    return rig


def _animate_humanoid(rig: Rig, walk_phase: float, walk_amount: float, clock: float, look_degrees: float) -> None:
    parts = rig.parts
    swing = math.sin(walk_phase) * 38 * walk_amount
    parts["leg_l"].setP(swing)
    parts["leg_r"].setP(-swing)
    parts["arm_l"].setP(-swing * 0.8 + math.sin(clock * 1.6) * 2 * (1 - walk_amount))
    arm_pitch = swing * 0.8 + math.sin(clock * 1.6 + 1) * 2 * (1 - walk_amount)
    if rig.attack_time < 0.45:
        progress = rig.attack_time / 0.45
        arm_pitch = -140 + 190 * progress if progress < 0.5 else 50 - 100 * (progress - 0.5) * 0.6
        arm_pitch = -150 * math.sin(progress * math.pi) + 20 * progress
    parts["arm_r"].setP(arm_pitch)
    bounce = abs(math.sin(walk_phase)) * 0.07 * walk_amount
    breathing = math.sin(clock * 2.0) * 0.012
    parts["upper"].setZ(bounce)
    parts["upper"].setSz(1.0 + breathing)
    parts["upper"].setR(math.sin(walk_phase) * 3 * walk_amount)
    parts["head"].setH(max(-55, min(55, look_degrees)))
    parts["head"].setP(math.sin(clock * 1.3) * 1.5)


# ===================================================================== wolf


def build_wolf(seed: int = 0) -> Rig:
    root = NodePath("wolf")
    model = _node(root, "model")
    parts: Dict[str, NodePath] = {}
    fur = rgb(112, 116, 124)
    dark = rgb(78, 82, 92)
    light = rgb(176, 180, 188)

    body = _mesh("wolf_body", seed, 0.06)
    body.sphere((0, 0, 0.84), (0.4, 0.82, 0.38), fur, rings=3, segments=9)
    body.sphere((0, -0.46, 0.9), (0.42, 0.42, 0.42), fur, rings=2, segments=8)
    body.sphere((0, 0.46, 0.84), (0.4, 0.42, 0.38), dark, rings=2, segments=8)
    body.sphere((0, -0.05, 0.64), (0.3, 0.62, 0.2), light, rings=2, segments=8)
    body.sphere((0, -0.78, 0.98), (0.34, 0.3, 0.36), dark, rings=2, segments=8)
    for ridge in range(5):
        body.cone((0, -0.4 + ridge * 0.22, 1.18 - abs(ridge - 1.5) * 0.02), 0.07, 0.16, dark, 4)
    body.build().reparentTo(model)

    head = _node(model, "head", (0, -1.0, 1.0))
    skull = _mesh("wolf_head", seed + 1, 0.05)
    skull.sphere((0, 0, 0), (0.28, 0.3, 0.27), fur, rings=2, segments=8)
    skull.box((0, -0.36, -0.07), (0.18, 0.4, 0.16), fur)
    skull.box((0, -0.36, -0.17), (0.16, 0.36, 0.06), light)
    skull.sphere((0, -0.58, -0.03), (0.07, 0.06, 0.06), rgb(24, 22, 24), rings=1, segments=6)
    for side in (-1, 1):
        skull.cone((side * 0.17, 0.05, 0.2), 0.1, 0.3, dark, 4)
        skull.sphere((side * 0.12, -0.24, 0.07), (0.04, 0.03, 0.04), rgb(255, 60, 40), rings=1, segments=6)
    for side in (-0.06, 0.06):
        skull.cone((side, -0.48, -0.16), 0.025, 0.07, rgb(244, 240, 228), 4)
    skull.build().reparentTo(head)
    parts["head"] = head

    tail = _node(model, "tail", (0, 1.2, 0.98))
    tail_mesh = _mesh("wolf_tail", seed + 2, 0.05)
    tail_mesh.tube((0, 0, 0), (0, 0.5, -0.18), 0.12, 0.09, fur, 6)
    tail_mesh.sphere((0, 0.58, -0.22), (0.1, 0.16, 0.1), dark, rings=1, segments=6)
    tail_mesh.build().reparentTo(tail)
    parts["tail"] = tail

    for name, (leg_x, leg_y) in {"leg_fl": (-0.27, -0.52), "leg_fr": (0.27, -0.52), "leg_bl": (-0.27, 0.55), "leg_br": (0.27, 0.55)}.items():
        pivot = _node(model, name, (leg_x, leg_y, 0.74))
        leg = _mesh(name, seed + 3, 0.05)
        leg.tube((0, 0, 0), (0, 0, -0.74), 0.11, 0.07, dark if "b" in name[4:] else fur, 6)
        leg.sphere((0, -0.05, -0.74), (0.1, 0.14, 0.06), dark, rings=1, segments=6)
        leg.build().reparentTo(pivot)
        parts[name] = pivot

    rig = Rig(root=root, height=1.6, kind="wolf", parts=parts)
    rig._animator = _animate_wolf
    return rig


def _animate_wolf(rig: Rig, walk_phase: float, walk_amount: float, clock: float, look_degrees: float) -> None:
    parts = rig.parts
    swing = math.sin(walk_phase) * 30 * walk_amount
    parts["leg_fl"].setP(swing)
    parts["leg_br"].setP(swing)
    parts["leg_fr"].setP(-swing)
    parts["leg_bl"].setP(-swing)
    snarl = 0.0
    if rig.attack_time < 0.4:
        snarl = math.sin(rig.attack_time / 0.4 * math.pi)
    parts["head"].setP(math.sin(clock * 1.7) * 3 - snarl * 25)
    parts["head"].setH(max(-40, min(40, look_degrees)))
    parts["tail"].setH(math.sin(clock * 3.1) * 22)
    parts["tail"].setP(-10 + math.sin(clock * 1.2) * 4)
    rig.parts["head"].setZ(1.0 + math.sin(clock * 2.0) * 0.015)


# ============================================================== bog lurker


def build_lurker(seed: int = 0) -> Rig:
    root = NodePath("lurker")
    model = _node(root, "model")
    parts: Dict[str, NodePath] = {}
    mud = rgb(62, 80, 46)
    dark = rgb(40, 54, 34)
    pale = rgb(98, 118, 70)

    body_pivot = _node(model, "body", (0, 0, 0))
    body = _mesh("lurker_body", seed, 0.07)
    body.sphere((0, 0, 0.78), (0.95, 0.85, 0.78), mud, rings=3, segments=10, jitter=0.06)
    body.sphere((0, -0.32, 0.55), (0.62, 0.5, 0.5), pale, rings=2, segments=8)
    for drip_x, drip_y in ((-0.5, -0.4), (0.1, -0.6), (0.55, -0.2), (-0.2, 0.5)):
        body.cone((drip_x, drip_y, 0.05), 0.12, 0.38, dark, 5)
    for reed_x in (-0.35, 0.0, 0.4):
        body.tube((reed_x, 0.1, 1.45), (reed_x * 1.5, 0.15, 2.2), 0.04, 0.025, rgb(96, 124, 60), 4)
    body.build().reparentTo(body_pivot)
    parts["body"] = body_pivot

    face = _node(body_pivot, "face", (0, 0, 0))
    face_mesh = _mesh("lurker_face", seed + 1, 0.0)
    for side in (-1, 1):
        face_mesh.sphere((side * 0.38, -0.7, 1.05), (0.19, 0.12, 0.19), rgb(252, 230, 70), rings=2, segments=8)
        face_mesh.sphere((side * 0.38, -0.8, 1.05), (0.07, 0.05, 0.1), rgb(24, 16, 10), rings=1, segments=6)
    face_mesh.build().reparentTo(face)
    face.setLightOff()
    face.setColorScale(1, 1, 1, 1)
    mouth = _node(body_pivot, "mouth", (0, -0.78, 0.6))
    mouth_mesh = _mesh("lurker_mouth", seed + 2, 0.0)
    mouth_mesh.box((0, 0, 0), (0.72, 0.1, 0.26), rgb(20, 12, 12))
    for tooth_x in (-0.24, -0.08, 0.08, 0.24):
        mouth_mesh.cone((tooth_x, -0.06, 0.1), 0.04, 0.11, rgb(238, 232, 210), 4)
    mouth_mesh.build().reparentTo(mouth)
    parts["mouth"] = mouth

    for side, sign in (("arm_l", -1), ("arm_r", 1)):
        pivot = _node(body_pivot, side, (sign * 0.85, -0.1, 0.95))
        arm = _mesh(side, seed + 3, 0.05)
        arm.tube((0, 0, 0), (sign * 0.25, -0.35, -0.5), 0.14, 0.1, mud, 6)
        arm.tube((sign * 0.25, -0.35, -0.5), (sign * 0.3, -0.6, -0.85), 0.1, 0.04, dark, 5)
        arm.build().reparentTo(pivot)
        parts[side] = pivot

    rig = Rig(root=root, height=2.4, kind="lurker", parts=parts)
    rig._animator = _animate_lurker
    return rig


def _animate_lurker(rig: Rig, walk_phase: float, walk_amount: float, clock: float, look_degrees: float) -> None:
    parts = rig.parts
    squish = math.sin(clock * 2.2) * 0.04 + abs(math.sin(walk_phase)) * 0.06 * walk_amount
    parts["body"].setSz(1.0 - squish)
    parts["body"].setSx(1.0 + squish * 0.6)
    bite = 0.0
    if rig.attack_time < 0.4:
        bite = math.sin(rig.attack_time / 0.4 * math.pi)
        parts["body"].setSy(1.0 + 0.2 * bite)
    else:
        parts["body"].setSy(1.0)
    parts["mouth"].setSz(1.0 + bite * 2.4 + math.sin(clock * 1.5) * 0.1)
    parts["arm_l"].setP(math.sin(clock * 1.8) * 12 - bite * 40)
    parts["arm_r"].setP(math.sin(clock * 1.8 + 2) * 12 - bite * 40)
    parts["body"].setH(max(-30, min(30, look_degrees)) * 0.5)


# ================================================================ registries

NPC_RIGS: Dict[str, Callable[[], Rig]] = {
    "merchant": lambda: build_humanoid("merchant", robe=(150, 100, 56), trim=(86, 56, 30), hat="cap", bag=True, beard=(90, 70, 50), seed=1),
    "citizen": lambda: build_humanoid("citizen", robe=(88, 118, 150), trim=(54, 70, 96), hair=(150, 96, 52), seed=2),
    "guard": lambda: build_humanoid("guard", robe=(98, 110, 130), trim=(60, 66, 84), hat="helmet", held="spear", scale=1.08, seed=3),
    "mysterious": lambda: build_humanoid("mysterious", robe=(36, 34, 52), trim=(20, 20, 30), hat="hood", long_robe=True, glow_eyes=True, seed=4),
    "blacksmith": lambda: build_humanoid("blacksmith", robe=(130, 78, 50), trim=(64, 44, 32), held="hammer", apron=(66, 58, 56), hair=(40, 28, 20), scale=1.1, seed=5),
    "innkeeper": lambda: build_humanoid("innkeeper", robe=(178, 170, 152), trim=(110, 90, 66), held="mug", apron=(236, 232, 220), beard=(150, 120, 84), seed=6),
    "ferryman": lambda: build_humanoid("ferryman", robe=(74, 112, 104), trim=(40, 66, 62), hat="straw", held="pole", beard=(180, 180, 176), seed=7),
    "priest": lambda: build_humanoid("priest", robe=(232, 228, 214), trim=(206, 170, 76), hat="mitre", held="staff", hair=(180, 180, 180), long_robe=True, seed=8),
    "hermit": lambda: build_humanoid("hermit", robe=(106, 92, 66), trim=(66, 54, 40), hat="hood", held="staff", beard=(190, 190, 184), long_robe=True, seed=9),
}

ENEMY_RIGS: Dict[str, Callable[[], Rig]] = {
    "wolf": build_wolf,
    "bandit": lambda: build_humanoid("bandit", robe=(98, 54, 48), trim=(44, 30, 26), hat="bandana", held="dagger", mask=True, hair=(30, 24, 20), seed=10),
    "bog_lurker": build_lurker,
}


def build_player() -> Rig:
    return build_humanoid(
        "player",
        robe=(120, 90, 60),
        trim=(86, 62, 40),
        hat="felt",
        stripes=((60, 140, 64), (120, 84, 50)),
        backpack=True,
        hair=(120, 78, 44),
        scale=1.08,
        seed=99,
    )
