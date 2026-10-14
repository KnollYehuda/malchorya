"""3D front end for Malchorya (Panda3D). Game rules live in core/ and logic/."""
import math
import os
import random
import zlib
from dataclasses import replace
from typing import Callable, Dict, List, Optional, Tuple

import pygame
from direct.gui.DirectGui import DirectFrame
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    Plane,
    Point3,
    Vec3,
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
from core.clock import is_night
from core.items import ITEM_DEFS, ItemId, ItemKind
from core.progression import effective_stats, xp_needed_for_next_level
from core.quests import QUESTS
from core.state import GameState
from logic.result import CommandResult
from ui import props as props2d
from ui3d.meshes import MeshBuilder, rgb
from ui3d.models3d import ENEMY_RIGS, NPC_RIGS, Rig, build_player
from ui3d.mapview import MINIMAP_SIZE, WORLD_MAP_SIZE, draw_minimap, draw_world_map
from sound.manager import AudioManager
from ui3d.texturing import surface_to_texture, update_texture
from ui3d.world3d import (
    HALF_WIDTH,
    Y_MIN,
    LocationView,
    make_card,
    slot_positions,
)

PLAYER_HEIGHT = 2.4
WALK_PHASE_SPEED = 11.0
PLAYER_SPEED = 6.5
PLAYER_RADIUS = 0.55
TALK_RANGE = 5.5
ITEM_RANGE = 3.0
ATTACK_RANGE = 9.0
WALK_FRAME_SECONDS = 0.11

DAY_SKY = (0.55, 0.74, 0.92)
NIGHT_SKY = (0.02, 0.03, 0.09)
HINTS = "WASD move  |  E talk/pick up  |  F attack  |  H potion  |  Z rest  |  Enter: command  |  M: world map  |  left-click: walk  |  right-drag: camera"
MOUSE_SENSITIVITY = 0.18
BIOME_MUSIC = {
    "crossroads": "overworld", "riverbank": "overworld", "river_dock": "overworld", "south_road": "overworld",
    "pinewood": "forest", "forest_depths": "forest", "hermit_hut": "forest",
    "town_square": "town", "blacksmith": "town", "tavern": "tavern", "chapel": "sacred",
    "watchtower": "dark", "marsh": "dark",
}
BIOME_AMBIENCE = {
    "crossroads": {"wind": 0.5}, "pinewood": {"forest": 0.7, "wind": 0.3}, "forest_depths": {"forest": 0.9},
    "hermit_hut": {"forest": 0.6, "fire": 0.35}, "riverbank": {"river": 0.7, "wind": 0.3},
    "river_dock": {"river": 0.9, "wind": 0.35}, "town_square": {"murmur": 0.35, "wind": 0.2},
    "south_road": {"wind": 0.5}, "marsh": {"marsh": 0.9}, "watchtower": {"wind": 0.5, "fire": 0.4},
    "blacksmith": {"forge": 0.9}, "tavern": {"murmur": 0.8, "fire": 0.35}, "chapel": {"hall": 0.8},
}
OUTDOOR_BIRDS = {"crossroads", "pinewood", "riverbank", "town_square", "hermit_hut", "south_road"}
SURFACE_BY_GROUND = {
    "grass": "grass", "needles": "grass", "dirt": "dirt", "sand": "dirt", "rubble": "stone",
    "cobble": "stone", "slabs": "stone", "planks": "wood", "marsh": "mud", "water": "wood",
}
ENEMY_VOICE = {"wolf": "growl_wolf", "bandit": "grunt_bandit", "bog_lurker": "roar_lurker"}
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
        audio: Optional[AudioManager] = None,
    ) -> None:
        configure_panda(headless, *size)
        ShowBase.__init__(self)
        self.headless = headless
        self.state = state
        self.on_command = on_command
        self.disableMouse()
        self.audio = audio if audio is not None else AudioManager(enabled=not headless)
        self.growl_timer = 6.0
        self.step_index = 0

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
        self.camera_distance = 24.0
        self.camera_pitch = 45.0
        self.camera_target = [0.0, 0.0]
        self.input_active = False
        self.dragging = False
        self.map_visible = False
        self.minimap_clock = 0.0
        self.move_target: Optional[Tuple[float, float]] = None
        self.move_path: List[Tuple[float, float]] = []
        self.stuck_seconds = 0.0
        self.target_marker: Optional[NodePath] = None
        self.input_buffer = ""
        self.messages: List[str] = []
        self.hit_flash: Dict[str, float] = {}
        self.clock_seconds = 0.0
        self.transition_lock = 0.0

        self._setup_lights()
        self._setup_hud()
        self._setup_input()

        self.player_node = render.attachNewNode("player")
        self.player_rig: Optional[Rig] = None
        self.player_heading = 0.0
        self.player_phase = 0.0
        self.lunges: Dict[str, float] = {}
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
        self.accept("m", self.toggle_world_map)
        self.accept("mouse1", self._left_click)
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
        self.minimap_texture = surface_to_texture(pygame.Surface((MINIMAP_SIZE, MINIMAP_SIZE), pygame.SRCALPHA))
        self.minimap_frame = DirectFrame(
            parent=self.a2dTopLeft, frameTexture=self.minimap_texture, frameSize=(-1, 1, -1, 1),
            scale=0.25, pos=(0.31, 0, -0.5), frameColor=(1, 1, 1, 1),
        )
        self.minimap_frame.setTransparency(TransparencyAttrib.M_alpha)
        self.world_map_texture = surface_to_texture(pygame.Surface(WORLD_MAP_SIZE, pygame.SRCALPHA))
        self.world_map_frame = DirectFrame(
            parent=self.aspect2d, frameTexture=self.world_map_texture, frameSize=(-1, 1, -0.5, 0.5),
            scale=0.9, pos=(0, 0, 0), frameColor=(1, 1, 1, 1),
        )
        self.world_map_frame.setTransparency(TransparencyAttrib.M_alpha)
        self.world_map_frame.hide()
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
        blob.reparentTo(self.player_node)
        self.player_blob = blob
        self.player_rig = build_player()
        self.player_rig.root.reparentTo(self.player_node)
        self.player_label = self._make_label(self.state.player.name, self.player_rig.height + 0.45)
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

    def sync_world(self, arrival: Optional[Tuple[float, float]]) -> None:
        location = self.state.world.locations[self.state.player.location_id]
        if self.view is None or self.view.location_id != location.id:
            if self.view is not None:
                self.view.root.detachNode()
            if location.id not in self.views:
                self.views[location.id] = LocationView(location.id, location.biome, list(location.exits.keys()))
            self.view = self.views[location.id]
            self.move_target = None
            self.view.root.reparentTo(render)
            if arrival is None:
                self.player_x, self.player_y = 0.0, -4.0
            else:
                self.player_x, self.player_y = arrival
            self._snap_camera()
        self._rebuild_dynamic(location)
        self._apply_time_of_day()
        self._refresh_hud()
        self._update_audio_scene(location)
        if self.map_visible:
            update_texture(self.world_map_texture, draw_world_map(self.state))

    def _update_audio_scene(self, location) -> None:
        in_combat = bool(self.state.enemies.get(location.id))
        night = is_night(self.state.hour)
        indoor = self.view is not None and self.view.indoor
        mood = BIOME_MUSIC.get(location.biome, "overworld")
        if night and not indoor and mood in ("overworld", "forest", "town"):
            mood = "night"
        self.audio.set_music("combat" if in_combat else mood)
        layers = dict(BIOME_AMBIENCE.get(location.biome, {"wind": 0.4}))
        if not indoor:
            if night and (location.biome in OUTDOOR_BIRDS or location.biome == "marsh"):
                layers["crickets"] = 0.45
            elif not night and location.biome in OUTDOOR_BIRDS:
                layers["birds"] = 0.45
        self.audio.set_ambience(layers)

    def _audio_for_command(self, raw: str, before: GameState, message: str, changed_location: bool) -> None:
        audio = self.audio
        after = self.state
        words = raw.split()
        verb = words[0] if words else ""
        first_enemy_id = None
        for enemy in before.enemies.get(before.player.location_id, []):
            first_enemy_id = enemy.def_id
            break
        if changed_location:
            audio.sfx("whoosh", 0.5)
        if verb == "attack" and "nothing here" not in message and "No such enemy" not in message:
            audio.sfx("swing", 0.9)
            killed = "You slay" in message
            if "You hit" in message or killed:
                metal = ItemKind.WEAPON in after.player.equipment
                audio.sfx("hit_metal" if metal else "hit_flesh", 1.0, delay=0.14)
                if first_enemy_id and not killed:
                    audio.sfx(ENEMY_VOICE.get(first_enemy_id, "growl_wolf"), 0.55, delay=0.22)
            if killed:
                audio.sfx("death", 0.9, delay=0.3)
                cleared = not after.enemies.get(before.player.location_id)
                if "Level up" not in message and cleared and "collapse" not in message:
                    audio.stinger("victory", delay=0.9)
        if after.player.hp < before.player.hp and not changed_location and "collapse" not in message:
            audio.sfx("hurt", 0.9, delay=0.5)
            if first_enemy_id:
                audio.sfx(ENEMY_VOICE.get(first_enemy_id, "growl_wolf"), 0.8, delay=0.36)
        if "collapse" in message:
            audio.stinger("defeat", delay=0.4)
        if "Level up" in message:
            audio.stinger("level_up", delay=1.0)
        if "[Quest started" in message:
            audio.stinger("quest_start", delay=0.8)
        if "[Quest complete" in message:
            audio.stinger("quest_complete", delay=0.8)
        if verb == "talk" and len(words) > 1 and "can't talk" not in message and "not here" not in message:
            audio.sfx(f"talk_{zlib.crc32(words[1].encode()) % 6}", 0.8)
        elif verb in ("buy", "sell") and ("You buy" in message or "You sell" in message):
            audio.sfx("coin", 0.9)
        elif verb == "take" and "You pick up" in message:
            audio.sfx("pickup", 0.9)
        elif verb == "use" and "You drink" in message:
            audio.sfx("drink", 0.9)
        elif verb == "equip" and "You equip" in message:
            audio.sfx("pickup", 0.6)

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
            rig = ENEMY_RIGS[enemy.def_id]()
            slot_x, slot_y = slots[slot_index]
            slot_index += 1
            node = self._spawn_creature(rig, enemy_def.name, (slot_x, slot_y), enemy.hp / enemy_def.max_hp)
            self.entities.append({
                "kind": "enemy", "id": enemy.instance_id, "x": slot_x, "y": slot_y, "home": (slot_x, slot_y),
                "node": node, "rig": rig, "phase": 0.0, "heading": 0.0,
            })

        for npc in self.state.npcs_here()[: len(slots) - slot_index]:
            rig = NPC_RIGS[npc.kind.value]()
            slot_x, slot_y = slots[slot_index]
            slot_index += 1
            node = self._spawn_creature(rig, npc.name, (slot_x, slot_y), None)
            self.entities.append({
                "kind": "npc", "id": npc.id, "x": slot_x, "y": slot_y, "home": (slot_x, slot_y),
                "node": node, "rig": rig, "phase": 0.0, "heading": 0.0,
            })

        self._spawn_items(location.id)

    def _spawn_creature(self, rig: Rig, name: str, position, health_ratio: Optional[float]) -> NodePath:
        node = self.dynamic_root.attachNewNode(name)
        node.setPos(position[0], position[1], 0)
        rig.root.reparentTo(node)
        self._shadow_blob(2.0, 1.4).reparentTo(node)
        self._make_label(name, rig.height + 0.35).reparentTo(node)
        if health_ratio is not None:
            bar = node.attachNewNode("bar")
            bar.setZ(rig.height + 1.05)
            bar.setBillboardPointEye()
            bar.setLightOff()
            for index, (color, scale_x) in enumerate((((0.25, 0.04, 0.04, 1), 1.0), ((0.85, 0.2, 0.2, 1), max(0.0, health_ratio)))):
                maker = CardMaker("segment")
                maker.setFrame(-0.8, 0.8, -0.07, 0.07)
                segment = bar.attachNewNode(maker.generate())
                segment.setColor(*color)
                if index == 1:
                    segment.setSx(max(0.001, scale_x))
                    segment.setX(-0.8 * (1 - scale_x))
                segment.setY(-0.01 * index)
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
        before_state = self.state
        previous_location = self.state.player.location_id
        previous_hp = self.state.player.hp
        target_id = raw.split()[1] if raw.startswith("attack") and len(raw.split()) > 1 else None
        first_enemy = next((entity["id"] for entity in self.entities if entity["kind"] == "enemy"), None)
        result = self.on_command(self.state, raw)
        self.state = result.state
        self.log(result.message)
        changed_location = self.state.player.location_id != previous_location
        spawn = (arrival or (0.0, -4.0)) if changed_location else None
        self.sync_world(arrival=spawn)

        self._audio_for_command(raw, before_state, result.message, changed_location)
        if raw.startswith("attack") and not changed_location and self.player_rig is not None:
            self.player_rig.start_attack()
            self.hit_flash[target_id or first_enemy or ""] = 0.3
        if self.state.player.hp < previous_hp and not changed_location:
            for entity in self.entities:
                if entity["kind"] == "enemy":
                    entity["rig"].start_attack()
                    self.lunges[entity["id"]] = 0.0
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
        if self.map_visible:
            self.toggle_world_map()
        elif self.input_active:
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

    # ----------------------------------------------------------- click to walk

    def screen_to_ground(self, mouse_x: float, mouse_y: float) -> Optional[Tuple[float, float]]:
        """Intersect the camera ray through normalized screen coords with the ground plane."""
        near, far = Point3(), Point3()
        if not self.camLens.extrude((mouse_x, mouse_y), near, far):
            return None
        near_world = render.getRelativePoint(self.cam, near)
        far_world = render.getRelativePoint(self.cam, far)
        hit = Point3()
        if Plane(Vec3(0, 0, 1), Point3(0, 0, 0)).intersectsLine(hit, near_world, far_world):
            return hit.getX(), hit.getY()
        return None

    def _over_hud(self, mouse_x: float, mouse_y: float) -> bool:
        aspect = self.getAspectRatio()
        point_x, point_y = mouse_x * aspect, mouse_y
        if self.map_visible:
            return True
        for frame in (self.panel, self.log_frame, self.minimap_frame):
            if frame.isHidden():
                continue
            bounds = frame.getTightBounds(self.aspect2d)
            if bounds is None:
                continue
            low, high = bounds
            if low.getX() <= point_x <= high.getX() and low.getZ() <= point_y <= high.getZ():
                return True
        return False

    def _left_click(self) -> None:
        if self.input_active or self.dragging or not self.mouseWatcherNode.hasMouse():
            return
        mouse = self.mouseWatcherNode.getMouse()
        if self._over_hud(mouse.getX(), mouse.getY()):
            return
        ground = self.screen_to_ground(mouse.getX(), mouse.getY())
        if ground is not None and self.set_move_target(*ground):
            self.audio.sfx("click_walk", 0.6)

    def set_move_target(self, target_x: float, target_y: float) -> bool:
        view = self.view
        if view is None:
            return False
        beyond_room = abs(target_x) > HALF_WIDTH or target_y < Y_MIN or target_y > view.y_max
        if not beyond_room and not view.is_walkable(target_x, target_y):
            self.log("You can't walk there.")
            self._refresh_hud()
            return False
        if not beyond_room:
            target_x, target_y = view.resolve(target_x, target_y, PLAYER_RADIUS)
        self.move_target = (target_x, target_y)
        self.stuck_seconds = 0.0
        npc_circles = [(entity["x"], entity["y"], 0.9) for entity in self.entities]
        path = view.find_path((self.player_x, self.player_y), (target_x, target_y), npc_circles)
        if beyond_room:
            # Walk to the edge of the room, then straight out through the exit.
            edge_x = max(-HALF_WIDTH + 0.7, min(HALF_WIDTH - 0.7, target_x))
            edge_y = max(Y_MIN + 0.7, min(view.y_max - 0.7, target_y))
            path = view.find_path((self.player_x, self.player_y), (edge_x, edge_y), npc_circles)
            path = (path or []) + [(target_x, target_y)]
        self.move_path = path or [(target_x, target_y)]
        return True

    def _show_target_marker(self) -> None:
        if self.target_marker is None:
            surface = pygame.Surface((64, 64), pygame.SRCALPHA)
            pygame.draw.circle(surface, (255, 240, 170, 230), (32, 32), 28, 5)
            pygame.draw.circle(surface, (255, 240, 170, 120), (32, 32), 14, 3)
            maker = CardMaker("target")
            maker.setFrame(-0.7, 0.7, -0.7, 0.7)
            marker = NodePath(maker.generate())
            marker.setTexture(surface_to_texture(surface))
            marker.setP(-90)
            marker.setTransparency(TransparencyAttrib.M_alpha)
            marker.setLightOff()
            marker.setDepthWrite(False)
            marker.setBin("fixed", 10)
            self.target_marker = marker
        if self.move_target is None:
            self.target_marker.detachNode()
            return
        self.target_marker.reparentTo(render)
        pulse = 1.0 + 0.15 * math.sin(self.clock_seconds * 6)
        self.target_marker.setPos(self.move_target[0], self.move_target[1], 0.08)
        self.target_marker.setScale(pulse)

    def _walk_to_target(self, delta: float) -> None:
        assert self.move_target is not None and self.view is not None
        while len(self.move_path) > 1 and math.hypot(
            self.move_path[0][0] - self.player_x, self.move_path[0][1] - self.player_y
        ) < 0.4:
            self.move_path.pop(0)
        waypoint = self.move_path[0] if self.move_path else self.move_target
        offset_x, offset_y = waypoint[0] - self.player_x, waypoint[1] - self.player_y
        distance = math.hypot(offset_x, offset_y)
        if distance < 0.25 and waypoint == self.move_target:
            self.move_target = None
            return
        step = min(PLAYER_SPEED * delta, distance)
        angle = math.atan2(offset_y, offset_x)
        candidate_x = self.player_x + math.cos(angle) * step
        candidate_y = self.player_y + math.sin(angle) * step
        if self._try_exit(candidate_x, candidate_y):
            self.move_target = None
            return
        final = self._resolve_step(candidate_x, candidate_y)
        moved = 0.0 if final is None else math.hypot(final[0] - self.player_x, final[1] - self.player_y)
        if final is None or moved < step * 0.25:
            self.stuck_seconds += delta
            if self.stuck_seconds > 0.4:
                self.move_target = None
            return
        self.stuck_seconds = 0.0
        self.player_x, self.player_y = final
        self.facing = (math.cos(angle), math.sin(angle))
        self.moving = True

    def toggle_world_map(self) -> None:
        self.map_visible = not self.map_visible
        self.audio.sfx("ui_open" if self.map_visible else "ui_close", 0.7)
        if self.map_visible:
            update_texture(self.world_map_texture, draw_world_map(self.state))
            self.world_map_frame.show()
        else:
            self.world_map_frame.hide()

    def refresh_minimap(self) -> None:
        if self.view is None:
            return
        surface = draw_minimap(
            self.view, (self.player_x, self.player_y), self._camera_basis(), self.entities,
            self.item_markers, self.move_target, self.facing,
        )
        update_texture(self.minimap_texture, surface)

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
        self.audio.update(delta)
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
        if self.move_target is not None and not self.input_active and not (move_x or move_y):
            self._walk_to_target(delta)
        elif self.move_target is not None and self.input_active:
            self.move_target = None
        self._show_target_marker()
        self.minimap_clock -= delta
        if self.minimap_clock <= 0:
            self.minimap_clock = 0.1
            self.refresh_minimap()
        self._animate(delta)
        self._update_camera(delta)

    def _camera_basis(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        yaw = math.radians(self.camera_yaw)
        forward = (-math.sin(yaw), math.cos(yaw))
        right = (math.cos(yaw), math.sin(yaw))
        return forward, right

    def step_player(self, move_x: float, move_y: float, delta: float) -> None:
        """Keyboard movement (inputs are relative to the camera)."""
        self.moving = bool(move_x or move_y)
        if not self.moving or self.view is None:
            return
        self.move_target = None
        forward, right = self._camera_basis()
        direction_x = right[0] * move_x + forward[0] * move_y
        direction_y = right[1] * move_x + forward[1] * move_y
        length = math.hypot(direction_x, direction_y)
        direction_x, direction_y = direction_x / length, direction_y / length
        self.facing = (direction_x, direction_y)

        new_x = self.player_x + direction_x * PLAYER_SPEED * delta
        new_y = self.player_y + direction_y * PLAYER_SPEED * delta
        if self._try_exit(new_x, new_y):
            return
        final = self._resolve_step(new_x, new_y)
        if final is not None:
            self.player_x, self.player_y = final

    def _resolve_step(self, new_x: float, new_y: float) -> Optional[Tuple[float, float]]:
        """Apply room bounds, water/walls and solid props. None if the step is impossible."""
        view = self.view
        edge_margin = 0.6
        new_x = max(-HALF_WIDTH + edge_margin, min(HALF_WIDTH - edge_margin, new_x))
        new_y = max(Y_MIN + edge_margin, min(view.y_max - edge_margin, new_y))
        if not view.is_walkable(new_x, new_y):
            if view.is_walkable(new_x, self.player_y):
                new_y = self.player_y
            elif view.is_walkable(self.player_x, new_y):
                new_x = self.player_x
            else:
                return None
        new_x, new_y = view.resolve(new_x, new_y, PLAYER_RADIUS)
        for entity in self.entities:
            offset_x, offset_y = new_x - entity["x"], new_y - entity["y"]
            distance = math.hypot(offset_x, offset_y)
            if distance < 0.9:
                distance = distance or 1.0
                new_x = entity["x"] + offset_x / distance * 0.9
                new_y = entity["y"] + offset_y / distance * 0.9
        return new_x, new_y

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

    @staticmethod
    def _turn_toward(current: float, target: float, rate: float) -> float:
        difference = ((target - current + 180) % 360) - 180
        return current + difference * min(1.0, rate)

    def _animate(self, delta: float) -> None:
        if self.view is None or self.player_rig is None:
            return
        # Player
        target_amount = 1.0 if self.moving else 0.0
        self.walk_amount = getattr(self, "walk_amount", 0.0)
        self.walk_amount += (target_amount - self.walk_amount) * min(1.0, delta * 10)
        if self.moving:
            self.player_phase += delta * WALK_PHASE_SPEED
        self.player_node.setPos(self.player_x, self.player_y, 0)
        wanted = math.degrees(math.atan2(self.facing[0], -self.facing[1]))
        self.player_heading = self._turn_toward(self.player_heading, wanted, delta * 12)
        self.player_rig.root.setH(self.player_heading)
        self.player_rig.animate(delta, self.player_phase, self.walk_amount, self.clock_seconds)
        step_index = int(self.player_phase / math.pi)
        if step_index != self.step_index:
            self.step_index = step_index
            if self.moving and self.walk_amount > 0.4:
                ground = self.view.style.ground
                self.audio.sfx(f"step_{SURFACE_BY_GROUND.get(ground, 'dirt')}", 0.55)
        enemies_here = [entity for entity in self.entities if entity["kind"] == "enemy"]
        self.growl_timer -= delta
        if self.growl_timer <= 0:
            self.growl_timer = random.uniform(6.0, 12.0)
            if enemies_here:
                chosen = random.choice(enemies_here)
                enemy = next((e for e in self.state.enemies.get(self.state.player.location_id, []) if e.instance_id == chosen["id"]), None)
                if enemy is not None:
                    self.audio.sfx(ENEMY_VOICE.get(enemy.def_id, "growl_wolf"), 0.55, pan=chosen["x"] / 18.0)

        # NPCs and enemies
        for entity in self.entities:
            rig, node = entity["rig"], entity["node"]
            offset_x, offset_y = self.player_x - entity["x"], self.player_y - entity["y"]
            distance = math.hypot(offset_x, offset_y)
            toward_player = math.degrees(math.atan2(offset_x, -offset_y))
            if entity["kind"] == "enemy" or distance < 9.0:
                wanted_heading = toward_player
            else:
                wanted_heading = 0.0
            entity["heading"] = self._turn_toward(entity["heading"], wanted_heading, delta * 6)
            rig.root.setH(entity["heading"])

            position_x, position_y = entity["home"]
            walk_amount = 0.0
            lunge_time = self.lunges.get(entity["id"])
            if lunge_time is not None:
                lunge_time += delta
                if lunge_time > 0.45:
                    self.lunges.pop(entity["id"], None)
                else:
                    self.lunges[entity["id"]] = lunge_time
                    reach = math.sin(lunge_time / 0.45 * math.pi) * min(1.6, max(0.0, distance - 1.4))
                    unit_x, unit_y = (offset_x / distance, offset_y / distance) if distance else (0.0, 0.0)
                    position_x += unit_x * reach
                    position_y += unit_y * reach
                    walk_amount = 1.0
                    entity["phase"] += delta * WALK_PHASE_SPEED * 1.4
            node.setPos(position_x, position_y, 0)
            rig.animate(delta, entity["phase"], walk_amount, self.clock_seconds + entity["home"][0])

            flash = self.hit_flash.get(entity["id"], 0.0)
            if flash > 0:
                self.hit_flash[entity["id"]] = max(0.0, flash - delta)
                rig.tint(1.0, 0.4, 0.4)
            else:
                rig.tint(1.0, 1.0, 1.0)

        for light_node, base_color, flicker in self.view.lights:
            if flicker:
                level = 0.85 + 0.15 * math.sin(self.clock_seconds * 11 + light_node.getX()) + random.uniform(-0.04, 0.04)
                light_node.node().setColor((base_color[0] * 2.6 * level, base_color[1] * 2.6 * level, base_color[2] * 2.6 * level, 1))
        for water in self.view.water_nodes:
            water.setTexOffset(TextureStage.getDefault(), self.clock_seconds * 0.01, self.clock_seconds * 0.006)

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
