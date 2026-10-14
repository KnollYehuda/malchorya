"""3D front end for Malchorya (Panda3D). Game rules live in core/ and logic/."""
import math
import os
import random
from dataclasses import replace
from typing import Callable, Dict, List, Optional, Tuple

import pygame
from direct.gui.DirectGui import DirectFrame
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    WindowProperties,
    AmbientLight,
    CardMaker,
    DirectionalLight,
    Filename,
    Fog,
    KeyboardButton,
    NodePath,
    TextNode,
    TextureStage,
    TransparencyAttrib,
    loadPrcFileData,
)

from core.clock import format_clock
from core.enemies import ENEMY_DEFS
from core.enums import WindDirection
from core.items import ITEM_DEFS, ItemId
from core.progression import effective_stats, xp_needed_for_next_level
from core.quests import QUESTS
from core.state import GameState
from logic.result import CommandResult
from ui import props as props2d
from ui3d.meshes import MeshBuilder, rgb
from ui3d.texturing import surface_to_texture
from ui3d.world3d import (
    HALF_WIDTH,
    Y_MIN,
    LocationView,
    make_card,
    slot_positions,
)

SPRITE_DIR = "malchorya/assets/sprites/player"
SPRITE_FRAME_COUNT = 4
PLAYER_HEIGHT = 2.4
PEOPLE_PIXELS_PER_UNIT = 36.0
PLAYER_SPEED = 6.5
PLAYER_RADIUS = 0.55
TALK_RANGE = 5.5
ITEM_RANGE = 3.0
ATTACK_RANGE = 9.0
WALK_FRAME_SECONDS = 0.11

DAY_SKY = (0.55, 0.74, 0.92)
NIGHT_SKY = (0.02, 0.03, 0.09)
HINTS = "WASD move  |  E talk/pick up  |  F attack  |  H potion  |  Z rest  |  Enter: command  |  right-drag / arrows: camera"
MOUSE_SENSITIVITY = 0.18
MIN_PITCH, MAX_PITCH = 25.0, 80.0


def configure_panda(headless: bool, width: int, height: int) -> None:
    loadPrcFileData("", "window-title Malchorya 3D")
    loadPrcFileData("", f"win-size {width} {height}")
    loadPrcFileData("", "audio-library-name null")
    loadPrcFileData("", "notify-level-display error")
    loadPrcFileData("", "sync-video 1")
    if headless:
        loadPrcFileData("", "window-type offscreen")
        loadPrcFileData("", "load-display p3tinydisplay")
        import ui3d.texturing as texturing

        texturing.POWER_OF_TWO_ONLY = True
    else:
        loadPrcFileData("", "framebuffer-multisample 1")
        loadPrcFileData("", "multisamples 4")


def _mix(first: Tuple[float, ...], second: Tuple[float, ...], ratio: float) -> Tuple[float, ...]:
    return tuple(a_value * (1 - ratio) + b_value * ratio for a_value, b_value in zip(first, second))


class Game3D(ShowBase):
    def __init__(
        self,
        state: GameState,
        on_command: Callable[[GameState, str], CommandResult],
        headless: bool = False,
        size: Tuple[int, int] = (1280, 720),
    ) -> None:
        configure_panda(headless, *size)
        ShowBase.__init__(self)
        self.headless = headless
        self.state = state
        self.on_command = on_command
        self.disableMouse()

        self.views: Dict[str, LocationView] = {}
        self.view: Optional[LocationView] = None
        self.dynamic_root: Optional[NodePath] = None
        self.entities: List[Dict] = []  # {"kind", "id", "x", "y", "node", "label"}
        self.item_markers: List[Dict] = []
        self.sprite_cache: Dict[str, Tuple] = {}

        self.player_x, self.player_y = 0.0, -4.0
        self.facing = (0.0, -1.0)
        self.moving = False
        self.walk_clock = 0.0
        self.camera_yaw = 0.0
        self.camera_distance = 27.0
        self.camera_pitch = 52.0
        self.camera_target = [0.0, 0.0]
        self.input_active = False
        self.dragging = False
        self.input_buffer = ""
        self.messages: List[str] = []
        self.hit_flash: Dict[str, float] = {}
        self.clock_seconds = 0.0
        self.transition_lock = 0.0

        self._setup_lights()
        self._load_player_sprites()
        self._setup_hud()
        self._setup_input()

        self.player_node = render.attachNewNode("player")
        self.player_card: Optional[NodePath] = None
        self._build_player_visual()
        self.sync_world(arrival=None)
        self._snap_camera()
        self.taskMgr.add(self._update, "update")

    # ------------------------------------------------------------------ setup

    def _setup_lights(self) -> None:
        self.ambient = AmbientLight("ambient")
        self.ambient_np = render.attachNewNode(self.ambient)
        render.setLight(self.ambient_np)
        self.sun = DirectionalLight("sun")
        self.sun_np = render.attachNewNode(self.sun)
        render.setLight(self.sun_np)
        self.fog = Fog("fog")
        self.fog.setExpDensity(0.012)

    def _load_player_sprites(self) -> None:
        from core.enums import WindDirection as Direction

        self.player_textures: Dict[Direction, List] = {}
        raw: Dict[Direction, List[pygame.Surface]] = {}
        for direction in (Direction.NORTH, Direction.SOUTH, Direction.WEST):
            raw[direction] = [
                pygame.image.load(f"{SPRITE_DIR}/player_{direction.value}_{frame}.png")
                for frame in range(SPRITE_FRAME_COUNT)
            ]
        # The sheet's "west" row faces right: it is east; west is its mirror.
        raw[Direction.EAST] = raw[Direction.WEST]
        raw[Direction.WEST] = [pygame.transform.flip(surface, True, False) for surface in raw[Direction.EAST]]
        for direction, surfaces in raw.items():
            self.player_textures[direction] = [(surface_to_texture(surface), surface.get_size()) for surface in surfaces]

    def _setup_input(self) -> None:
        for key, command in (
            ("h", "use health_potion"), ("z", "rest"), ("i", "inventory"), ("c", "status"),
            ("q", "quests"), ("l", "look"), ("t", "time"),
        ):
            self.accept(key, self._hotkey, [command])
        self.accept("e", self._hotkey_interact)
        self.accept("f", self._hotkey_attack)
        self.accept("space", self._hotkey_attack)
        self.accept("enter", self._enter_pressed)
        self.accept("escape", self._escape_pressed)
        self.accept("backspace", self._backspace)
        self.accept("mouse3", self._start_drag)
        self.accept("mouse3-up", self._stop_drag)
        self.accept("wheel_up", self._zoom, [-1.5])
        self.accept("wheel_down", self._zoom, [1.5])
        if self.buttonThrowers:
            self.buttonThrowers[0].node().setKeystrokeEvent("keystroke")
        self.accept("keystroke", self._keystroke)

    def _setup_hud(self) -> None:
        font_scale = 0.045
        self.title_text = OnscreenText(
            text="", parent=self.a2dTopLeft, pos=(0.05, -0.1), scale=0.075, fg=(1, 1, 1, 1),
            shadow=(0, 0, 0, 1), align=TextNode.ALeft, mayChange=True,
        )
        self.clock_text = OnscreenText(
            text="", parent=self.a2dTopLeft, pos=(0.05, -0.17), scale=0.05, fg=(0.9, 0.85, 0.55, 1),
            shadow=(0, 0, 0, 1), align=TextNode.ALeft, mayChange=True,
        )
        self.panel = DirectFrame(
            parent=self.a2dTopRight, frameColor=(0.03, 0.03, 0.06, 0.62), frameSize=(-0.78, 0, -1.1, 0), pos=(-0.02, 0, -0.02)
        )
        self.hp_back = DirectFrame(
            parent=self.panel, frameColor=(0.2, 0.05, 0.05, 0.9), frameSize=(0, 0.7, -0.03, 0.03), pos=(-0.74, 0, -0.08)
        )
        self.hp_fill = DirectFrame(
            parent=self.hp_back, frameColor=(0.78, 0.2, 0.2, 1), frameSize=(0, 0.7, -0.03, 0.03)
        )
        self.stats_text = OnscreenText(
            text="", parent=self.panel, pos=(-0.74, -0.16), scale=font_scale, fg=(0.93, 0.93, 0.97, 1),
            align=TextNode.ALeft, mayChange=True, wordwrap=15,
        )
        self.log_frame = DirectFrame(
            parent=self.a2dBottomLeft, frameColor=(0.03, 0.03, 0.06, 0.6), frameSize=(0, 1.55, 0, 0.5), pos=(0.02, 0, 0.1)
        )
        self.log_text = OnscreenText(
            text="", parent=self.log_frame, pos=(0.03, 0.44), scale=0.04, fg=(0.9, 0.9, 0.95, 1),
            align=TextNode.ALeft, mayChange=True, wordwrap=37,
        )
        self.hint_text = OnscreenText(
            text=HINTS, parent=self.a2dBottomCenter, pos=(0, 0.04), scale=0.036, fg=(0.8, 0.8, 0.88, 1),
            shadow=(0, 0, 0, 1), mayChange=True,
        )
        self.input_text = OnscreenText(
            text="", parent=self.a2dBottomLeft, pos=(0.05, 0.62), scale=0.05, fg=(1, 1, 0.7, 1),
            shadow=(0, 0, 0, 1), align=TextNode.ALeft, mayChange=True,
        )

    # ----------------------------------------------------------------- world

    def _build_player_visual(self) -> None:
        blob = self._shadow_blob(2.2, 1.4)
        self.player_blob = blob
        self.player_label = self._make_label(self.state.player.name, PLAYER_HEIGHT + 0.1)
        self.player_label.reparentTo(self.player_node)

    def _shadow_blob(self, width: float, depth: float) -> NodePath:
        if not hasattr(self, "_blob_texture"):
            surface = pygame.Surface((64, 64), pygame.SRCALPHA)
            for ring in range(32, 0, -1):
                alpha = int(150 * (1 - ring / 32) ** 0.6)
                pygame.draw.circle(surface, (0, 0, 0, alpha), (32, 32), ring)
            self._blob_texture = surface_to_texture(surface)
        maker = CardMaker("blob")
        maker.setFrame(-width / 2, width / 2, -depth / 2, depth / 2)
        blob = NodePath(maker.generate())
        blob.setTexture(self._blob_texture)
        blob.setP(-90)
        blob.setZ(0.06)
        blob.setTransparency(TransparencyAttrib.M_alpha)
        blob.setLightOff()
        blob.setDepthWrite(False)
        return blob

    def _make_label(self, text: str, height: float) -> NodePath:
        label = TextNode("label")
        label.setText(text)
        label.setAlign(TextNode.ACenter)
        label.setTextColor(1, 1, 0.92, 1)
        label.setShadow(0.06, 0.06)
        label.setShadowColor(0, 0, 0, 1)
        node = NodePath(label)
        node.setScale(0.5)
        node.setZ(height)
        node.setBillboardPointEye()
        node.setLightOff()
        node.setBin("fixed", 50)
        node.setDepthTest(False)
        return node

    def _people_card(self, cache_key: str, builder) -> Tuple:
        if cache_key not in self.sprite_cache:
            surface = builder()
            width, height = surface.get_size()
            self.sprite_cache[cache_key] = (
                surface_to_texture(surface), width / PEOPLE_PIXELS_PER_UNIT, height / PEOPLE_PIXELS_PER_UNIT,
            )
        return self.sprite_cache[cache_key]

    def sync_world(self, arrival: Optional[Tuple[float, float]]) -> None:
        location = self.state.world.locations[self.state.player.location_id]
        if self.view is None or self.view.location_id != location.id:
            if self.view is not None:
                self.view.root.detachNode()
            if location.id not in self.views:
                self.views[location.id] = LocationView(location.id, location.biome, list(location.exits.keys()))
            self.view = self.views[location.id]
            self.view.root.reparentTo(render)
            if arrival is None:
                self.player_x, self.player_y = 0.0, -4.0
            else:
                self.player_x, self.player_y = arrival
            self._snap_camera()
        self._rebuild_dynamic(location)
        self._apply_time_of_day()
        self._refresh_hud()

    def _rebuild_dynamic(self, location) -> None:
        if self.dynamic_root is not None:
            self.dynamic_root.removeNode()
        self.dynamic_root = render.attachNewNode("dynamic")
        self.entities = []
        self.item_markers = []
        slots = slot_positions()
        slot_index = 0

        for enemy in self.state.enemies.get(location.id, [])[: len(slots)]:
            enemy_def = ENEMY_DEFS[enemy.def_id]
            texture, width, height = self._people_card(f"enemy:{enemy.def_id}", props2d.ENEMY_BUILDERS[enemy.def_id])
            slot_x, slot_y = slots[slot_index]
            slot_index += 1
            node = self._spawn_creature(texture, width, height, enemy_def.name, (slot_x, slot_y), enemy.hp / enemy_def.max_hp)
            self.entities.append({"kind": "enemy", "id": enemy.instance_id, "x": slot_x, "y": slot_y, "node": node})

        for npc in self.state.npcs_here()[: len(slots) - slot_index]:
            texture, width, height = self._people_card(f"npc:{npc.kind.value}", props2d.NPC_STYLES[npc.kind.value])
            slot_x, slot_y = slots[slot_index]
            slot_index += 1
            node = self._spawn_creature(texture, width, height, npc.name, (slot_x, slot_y), None)
            self.entities.append({"kind": "npc", "id": npc.id, "x": slot_x, "y": slot_y, "node": node})

        self._spawn_items(location.id)

    def _spawn_creature(self, texture, width: float, height: float, name: str, position, health_ratio: Optional[float]) -> NodePath:
        node = self.dynamic_root.attachNewNode(name)
        node.setPos(position[0], position[1], 0)
        card = make_card(texture, width, height)
        card.setBillboardAxis()
        card.setLightOff()
        card.reparentTo(node)
        self._shadow_blob(width * 1.1, 1.0).reparentTo(node)
        self._make_label(name, height + 0.15).reparentTo(node)
        if health_ratio is not None:
            bar = node.attachNewNode("bar")
            bar.setZ(height + 0.85)
            bar.setBillboardPointEye()
            bar.setLightOff()
            for index, (color, scale_x) in enumerate((((0.25, 0.04, 0.04, 1), 1.0), ((0.85, 0.2, 0.2, 1), max(0.0, health_ratio)))):
                maker = CardMaker("segment")
                maker.setFrame(-0.8, 0.8, -0.07, 0.07)
                segment = bar.attachNewNode(maker.generate())
                segment.setColor(*color)
                segment.setX(0)
                if index == 1:
                    segment.setSx(max(0.001, scale_x))
                    segment.setX(-0.8 * (1 - scale_x))
                segment.setY(-0.01 * index)
        node.setPythonTag("card", card)
        return node

    def _spawn_items(self, location_id: str) -> None:
        ground = self.state.location_items.get(location_id, {})
        for item_id, amount in ground.items():
            rng = random.Random(f"{location_id}:{item_id.value}")
            positions = []
            for _ in range(40):
                angle = rng.uniform(0, 6.28)
                distance = rng.uniform(5.0, 12.0)
                positions.append((math.cos(angle) * distance, math.sin(angle) * distance * 0.7))
            placed = 0
            for position in positions:
                if placed >= amount:
                    break
                if self.view and (not self.view.is_walkable(*position) or self.view._collides(position[0], position[1], 0.3)):
                    continue
                if abs(position[0]) > HALF_WIDTH - 1.5 or position[1] < Y_MIN + 1.5 or position[1] > (self.view.y_max - 1.5):
                    continue
                self._spawn_item_marker(item_id, position)
                placed += 1

    def _spawn_item_marker(self, item_id: ItemId, position: Tuple[float, float]) -> None:
        builder = MeshBuilder("item", hash(position) & 0xFFFF)
        glow = False
        if item_id == ItemId.PINE_CONE:
            builder.cone((0, 0, 0.0), 0.22, 0.45, rgb(122, 84, 48), 6)
        elif item_id == ItemId.MOONPETAL:
            builder.tube((0, 0, 0), (0, 0, 0.35), 0.03, 0.03, rgb(70, 130, 80), 5)
            builder.sphere((0, 0, 0.5), (0.2, 0.2, 0.14), rgb(210, 230, 255), rings=1, segments=6)
            glow = True
        else:
            builder.sphere((0, 0, 0.3), (0.22, 0.22, 0.22), rgb(236, 196, 80), rings=2, segments=6)
            glow = True
        node = builder.build()
        node.reparentTo(self.dynamic_root)
        node.setPos(position[0], position[1], 0)
        if glow:
            node.setLightOff()
        self.item_markers.append({"item": item_id, "x": position[0], "y": position[1], "node": node})

    # ---------------------------------------------------------- time of day

    def _apply_time_of_day(self) -> None:
        hour = (self.state.minutes % 1440) / 60.0
        daylight = max(0.0, math.sin(math.pi * (hour - 5) / 15)) if 5 < hour < 20 else 0.0
        brightness = min(1.0, daylight * 1.7)
        indoor = self.view is not None and self.view.indoor

        if indoor:
            sky = (0.02, 0.02, 0.03)
            ambient = (0.82, 0.74, 0.66)
            sun_color = (0, 0, 0)
            tone = (1.0, 0.95, 0.9)
        else:
            sky = _mix(NIGHT_SKY, DAY_SKY, brightness)
            ambient = _mix((0.26, 0.3, 0.5), (0.5, 0.52, 0.56), brightness)
            sun_color = _mix((0.2, 0.26, 0.46), _mix((1.0, 0.7, 0.45), (1.0, 0.97, 0.9), min(1.0, daylight * 1.3)), min(1.0, daylight * 1.5))
            tone = _mix((0.55, 0.62, 0.95), (1.0, 1.0, 1.0), brightness)
        self.setBackgroundColor(*sky)
        self.ambient.setColor((*ambient, 1))
        self.sun.setColor((*sun_color, 1))
        self.sun_np.setHpr(-130 + (hour - 6) * 11, -52 + 18 * (1 - brightness), 0)
        if self.view is not None:
            self.view.card_root.setColorScale(*tone, 1)
        if self.dynamic_root is not None:
            for entity in self.entities:
                card = entity["node"].getPythonTag("card")
                if card:
                    card.setColorScale(*tone, 1)
        self.player_tone = tone
        if indoor:
            render.clearFog()
        else:
            self.fog.setColor(*sky)
            fog_boost = 1.0
            if self.view and self.view.style.fog:
                fog_boost = 2.4
            self.fog.setExpDensity(0.010 * fog_boost)
            render.setFog(self.fog)

    # -------------------------------------------------------------------- hud

    def _refresh_hud(self) -> None:
        player = self.state.player
        location = self.state.world.locations[player.location_id]
        max_hp, attack, defense = effective_stats(player)
        self.title_text.setText(location.name)
        self.clock_text.setText(format_clock(self.state.minutes))
        ratio = max(0.0, min(1.0, player.hp / max_hp))
        self.hp_fill["frameSize"] = (0, 0.7 * ratio, -0.03, 0.03)
        lines = [
            f"HP {player.hp}/{max_hp}   Lv {player.level}",
            f"XP {player.xp}/{xp_needed_for_next_level(player.level)}",
            f"ATK {attack}  DEF {defense}  Keter {player.inventory.count(ItemId.KETER)}",
            "",
            "Exits: " + (", ".join(direction.name.lower() for direction in location.exits) or "none"),
        ]
        people = [f"{npc.name}" for npc in self.state.npcs_here()]
        if people:
            lines.append("Here: " + ", ".join(people))
        ground = self.state.location_items.get(location.id, {})
        if ground:
            lines.append("Ground: " + ", ".join(f"{ITEM_DEFS[item].name} x{amount}" for item, amount in ground.items()))
        enemies = self.state.enemies.get(location.id, [])
        if enemies:
            lines.append("Hostile: " + ", ".join(f"{ENEMY_DEFS[enemy.def_id].name} {enemy.hp}" for enemy in enemies))
        active = [QUESTS[quest_id].name for quest_id, status in self.state.quest_log.items() if status.value == "in_progress"]
        if active:
            lines.extend(["", "Quests:"] + [f"* {name}" for name in active[:4]])
        self.stats_text.setText("\n".join(lines))
        wrapped_lines = sum(1 + len(line) // 27 for line in lines)
        self.panel["frameSize"] = (-0.78, 0, -(0.2 + 0.052 * wrapped_lines), 0)
        log_lines: List[str] = []
        for message in self.messages[-6:]:
            log_lines.extend(message.split("\n"))
        shown = log_lines[-9:]
        self.log_text.setText("\n".join(shown))
        self.log_frame.setScale(1, 1, 1)
        if shown:
            self.log_frame.show()
            self.log_frame["frameSize"] = (0, 1.55, 0, 0.08 + 0.045 * len(shown))
            self.log_text.setPos(0.03, 0.045 * len(shown) + 0.025)
        else:
            self.log_frame.hide()
        self.input_text.setText(f"> {self.input_buffer}_" if self.input_active else "")

    def log(self, message: str) -> None:
        if message:
            self.messages.append(message)
            self.messages = self.messages[-12:]

    # ----------------------------------------------------------------- input

    def run_command(self, raw: str, arrival: Optional[Tuple[float, float]] = None) -> CommandResult:
        previous_location = self.state.player.location_id
        previous_hp = self.state.player.hp
        result = self.on_command(self.state, raw)
        self.state = result.state
        self.log(result.message)
        if raw.startswith("attack") or raw.startswith("use"):
            for entity in self.entities:
                if entity["kind"] == "enemy":
                    self.hit_flash[entity["id"]] = 0.3
        spawn = arrival if self.state.player.location_id != previous_location else None
        if self.state.player.location_id != previous_location and spawn is None:
            spawn = (0.0, -4.0)
        self.sync_world(arrival=spawn if self.state.player.location_id != previous_location else None)
        return result

    def _hotkey(self, command: str) -> None:
        if not self.input_active:
            self.run_command(command)

    def _nearest(self, collection: List[Dict], kind: Optional[str], limit: float) -> Optional[Dict]:
        best, best_distance = None, limit
        for entry in collection:
            if kind is not None and entry.get("kind") != kind:
                continue
            distance = math.hypot(entry["x"] - self.player_x, entry["y"] - self.player_y)
            if distance < best_distance:
                best, best_distance = entry, distance
        return best

    def _hotkey_interact(self) -> None:
        if self.input_active:
            return
        npc = self._nearest(self.entities, "npc", TALK_RANGE)
        if npc is not None:
            self.run_command(f"talk {npc['id']}")
            return
        marker = self._nearest(self.item_markers, None, ITEM_RANGE)
        if marker is not None:
            self.run_command(f"take {marker['item'].value}")
            return
        self.log("Nothing to interact with here.")
        self._refresh_hud()

    def _hotkey_attack(self) -> None:
        if self.input_active:
            return
        enemies = [entity for entity in self.entities if entity["kind"] == "enemy"]
        if not enemies:
            self.run_command("attack")
            return
        target = self._nearest(enemies, "enemy", ATTACK_RANGE)
        if target is None:
            self.log("Get closer to attack.")
            self._refresh_hud()
            return
        self.run_command(f"attack {target['id']}")

    def _enter_pressed(self) -> None:
        if self.input_active:
            raw = self.input_buffer.strip()
            self.input_active = False
            self.input_buffer = ""
            if raw.lower() == "quit":
                self.userExit()
            elif raw:
                self.run_command(raw)
            self._refresh_hud()
        else:
            self.input_active = True
            self.input_buffer = ""
            self._refresh_hud()

    def _escape_pressed(self) -> None:
        if self.input_active:
            self.input_active = False
            self.input_buffer = ""
            self._refresh_hud()
        else:
            self.userExit()

    def _backspace(self) -> None:
        if self.input_active:
            self.input_buffer = self.input_buffer[:-1]
            self._refresh_hud()

    def _keystroke(self, text: str) -> None:
        if self.input_active and text.isprintable():
            self.input_buffer += text
            self._refresh_hud()

    def _start_drag(self) -> None:
        self.dragging = True
        if not self.headless:
            properties = WindowProperties()
            properties.setCursorHidden(True)
            self.win.requestProperties(properties)
            self.win.movePointer(0, self.win.getXSize() // 2, self.win.getYSize() // 2)

    def _stop_drag(self) -> None:
        self.dragging = False
        if not self.headless:
            properties = WindowProperties()
            properties.setCursorHidden(False)
            self.win.requestProperties(properties)

    def rotate_camera(self, delta_x: float, delta_y: float) -> None:
        """Mouse-drag orbit: horizontal turns the camera, vertical tilts it."""
        self.camera_yaw -= delta_x * MOUSE_SENSITIVITY
        self.camera_pitch = max(MIN_PITCH, min(MAX_PITCH, self.camera_pitch + delta_y * MOUSE_SENSITIVITY))

    def _drag_camera(self) -> None:
        if not self.dragging or self.headless or not self.win.getProperties().getForeground():
            return
        center_x, center_y = self.win.getXSize() // 2, self.win.getYSize() // 2
        pointer = self.win.getPointer(0)
        self.rotate_camera(pointer.getX() - center_x, pointer.getY() - center_y)
        self.win.movePointer(0, center_x, center_y)

    def _zoom(self, amount: float) -> None:
        self.camera_distance = max(10.0, min(40.0, self.camera_distance + amount))

    # ---------------------------------------------------------------- update

    def _key_down(self, *names: str) -> bool:
        if not self.mouseWatcherNode:
            return False
        for name in names:
            button = getattr(KeyboardButton, name)() if name in ("left", "right", "up", "down") else KeyboardButton.asciiKey(name)
            if self.mouseWatcherNode.is_button_down(button):
                return True
        return False

    def _update(self, task):
        delta = min(globalClock.getDt(), 0.1)
        self.update(delta)
        return task.cont

    def update(self, delta: float) -> None:
        """Advance one frame (also called directly by tests)."""
        self.clock_seconds += delta
        self.transition_lock = max(0.0, self.transition_lock - delta)

        self._drag_camera()
        if self._key_down("left"):
            self.camera_yaw += 90 * delta
        if self._key_down("right"):
            self.camera_yaw -= 90 * delta
        if self._key_down("up"):
            self._zoom(-8 * delta)
        if self._key_down("down"):
            self._zoom(8 * delta)

        move_x = move_y = 0.0
        if not self.input_active:
            move_y += (1 if self._key_down("w") else 0) - (1 if self._key_down("s") else 0)
            move_x += (1 if self._key_down("d") else 0) - (1 if self._key_down("a") else 0)
        self.step_player(move_x, move_y, delta)
        self._animate(delta)
        self._update_camera(delta)

    def _camera_basis(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        yaw = math.radians(self.camera_yaw)
        forward = (-math.sin(yaw), math.cos(yaw))
        right = (math.cos(yaw), math.sin(yaw))
        return forward, right

    def step_player(self, move_x: float, move_y: float, delta: float) -> None:
        self.moving = bool(move_x or move_y)
        if not self.moving or self.view is None:
            return
        forward, right = self._camera_basis()
        direction_x = right[0] * move_x + forward[0] * move_y
        direction_y = right[1] * move_x + forward[1] * move_y
        length = math.hypot(direction_x, direction_y)
        direction_x, direction_y = direction_x / length, direction_y / length
        self.facing = (direction_x, direction_y)

        new_x = self.player_x + direction_x * PLAYER_SPEED * delta
        new_y = self.player_y + direction_y * PLAYER_SPEED * delta
        view = self.view

        if self._try_exit(new_x, new_y):
            return
        edge_margin = 0.6
        new_x = max(-HALF_WIDTH + edge_margin, min(HALF_WIDTH - edge_margin, new_x))
        new_y = max(Y_MIN + edge_margin, min(view.y_max - edge_margin, new_y))
        if not view.is_walkable(new_x, new_y):
            if view.is_walkable(new_x, self.player_y):
                new_y = self.player_y
            elif view.is_walkable(self.player_x, new_y):
                new_x = self.player_x
            else:
                return
        new_x, new_y = view.resolve(new_x, new_y, PLAYER_RADIUS)
        for entity in self.entities:
            offset_x, offset_y = new_x - entity["x"], new_y - entity["y"]
            distance = math.hypot(offset_x, offset_y)
            if distance < 0.9:
                distance = distance or 1.0
                new_x = entity["x"] + offset_x / distance * 0.9
                new_y = entity["y"] + offset_y / distance * 0.9
        self.player_x, self.player_y = new_x, new_y

    def _try_exit(self, new_x: float, new_y: float) -> bool:
        view = self.view
        if view is None or self.transition_lock > 0:
            return False
        margin = 0.5
        checks = [
            (WindDirection.NORTH, new_y > view.y_max - margin, abs(new_x) < 3.4, (0.0, Y_MIN + 1.8)),
            (WindDirection.SOUTH, new_y < Y_MIN + margin, abs(new_x) < 3.4, (0.0, view.y_max - 1.8)),
            (WindDirection.EAST, new_x > HALF_WIDTH - margin, abs(new_y) < 3.4, (-HALF_WIDTH + 1.8, 0.0)),
            (WindDirection.WEST, new_x < -HALF_WIDTH + margin, abs(new_y) < 3.4, (HALF_WIDTH - 1.8, 0.0)),
        ]
        for direction, beyond_edge, in_doorway, arrival in checks:
            if beyond_edge and in_doorway and direction in view.exits:
                self.transition_lock = 0.6
                target = self.state.world.locations[self.state.player.location_id].exits[direction]
                arrival_x, arrival_y = arrival
                destination = self.state.world.get_location(target)
                arrival = self._fit_arrival(destination, direction, arrival)
                self.run_command(f"move {direction.value}", arrival=arrival)
                return True
        return False

    def _fit_arrival(self, destination, direction: WindDirection, arrival: Tuple[float, float]) -> Tuple[float, float]:
        if destination.biome in ("blacksmith", "tavern", "chapel"):
            return (arrival[0], min(arrival[1], 7.2))
        return arrival

    def _animate(self, delta: float) -> None:
        if self.view is None:
            return
        if self.moving:
            self.walk_clock += delta
        else:
            self.walk_clock = 0.0
        self.player_node.setPos(self.player_x, self.player_y, 0)
        self._update_player_sprite()

        for entity in self.entities:
            flash = self.hit_flash.get(entity["id"], 0.0)
            card = entity["node"].getPythonTag("card")
            if card is None:
                continue
            if flash > 0:
                self.hit_flash[entity["id"]] = max(0.0, flash - delta)
                card.setColorScale(1.0, 0.35, 0.35, 1)
            else:
                bob = 0.04 * math.sin(self.clock_seconds * 2.0 + entity["x"])
                entity["node"].setZ(bob if entity["kind"] == "npc" else 0)
        for light_node, base_color, flicker in self.view.lights:
            if flicker:
                level = 0.85 + 0.15 * math.sin(self.clock_seconds * 11 + light_node.getX()) + random.uniform(-0.04, 0.04)
                light_node.node().setColor((base_color[0] * 2.6 * level, base_color[1] * 2.6 * level, base_color[2] * 2.6 * level, 1))
        for water in self.view.water_nodes:
            water.setTexOffset(TextureStage.getDefault(), self.clock_seconds * 0.01, self.clock_seconds * 0.006)

    def _update_player_sprite(self) -> None:
        forward, right = self._camera_basis()
        across = self.facing[0] * right[0] + self.facing[1] * right[1]
        along = self.facing[0] * forward[0] + self.facing[1] * forward[1]
        if abs(along) >= abs(across):
            direction = WindDirection.NORTH if along > 0 else WindDirection.SOUTH
        else:
            direction = WindDirection.EAST if across > 0 else WindDirection.WEST
        frame = int(self.walk_clock / WALK_FRAME_SECONDS) % SPRITE_FRAME_COUNT if self.moving else 0
        texture, (pixel_width, pixel_height) = self.player_textures[direction][frame]
        key = (direction, frame)
        if getattr(self, "_player_key", None) == key and self.player_card is not None:
            return
        self._player_key = key
        if self.player_card is not None:
            self.player_card.removeNode()
        height = PLAYER_HEIGHT
        width = height * pixel_width / pixel_height
        self.player_card = make_card(texture, width, height, "player_card")
        self.player_card.setBillboardAxis()
        self.player_card.setLightOff()
        tone = getattr(self, "player_tone", (1, 1, 1))
        self.player_card.setColorScale(*tone, 1)
        self.player_card.reparentTo(self.player_node)

    def _snap_camera(self) -> None:
        self.camera_target = [self.player_x, self.player_y]
        self._place_camera()

    def _update_camera(self, delta: float) -> None:
        blend = min(1.0, delta * 6)
        self.camera_target[0] += (self.player_x - self.camera_target[0]) * blend
        self.camera_target[1] += (self.player_y - self.camera_target[1]) * blend
        self._place_camera()

    def _place_camera(self) -> None:
        yaw = math.radians(self.camera_yaw)
        pitch = math.radians(self.camera_pitch)
        horizontal = self.camera_distance * math.cos(pitch)
        vertical = self.camera_distance * math.sin(pitch)
        target_x, target_y = self.camera_target
        self.camera.setPos(
            target_x + math.sin(yaw) * horizontal,
            target_y - math.cos(yaw) * horizontal,
            vertical + 1.0,
        )
        self.camera.lookAt(target_x, target_y, 1.2)
        self.camLens.setFov(58)
        self.camLens.setNearFar(0.5, 220)

    # --------------------------------------------------------------- capture

    def render_frames(self, count: int = 3) -> None:
        for _ in range(count):
            self.graphicsEngine.renderFrame()

    def save_screenshot(self, path: str) -> None:
        self.render_frames()
        self.win.saveScreenshot(Filename(path))
