from dataclasses import dataclass, field
from typing import Dict, List

from core.enums import CombatClass, Race
from core.inventory import Inventory
from core.items import ItemId, ItemKind
from core.quests import QuestStatus
from core.world import World
from core.enemies import EnemyInstance, create_initial_enemies
from core.progression import effective_stats
import random

from core.clock import START_MINUTES, hour_of
from core.entity import Entity


@dataclass
class Player(Entity):
    race: Race = field(default=None)
    combat_class: CombatClass = field(default=None)
    location_id: str = field(default="")
    inventory: Inventory = field(default_factory=Inventory)
    hp: int = 1
    level: int = 1
    xp: int = 0
    equipment: Dict[ItemKind, ItemId] = field(default_factory=dict)


@dataclass
class GameState:
    world: World
    player: Player
    log: List[str] = field(default_factory=list)
    quest_log: Dict[str, QuestStatus] = field(default_factory=dict)
    location_items: Dict[str, Dict[ItemId, int]] = field(default_factory=dict)
    enemies: Dict[str, List[EnemyInstance]] = field(default_factory=dict)
    quest_progress: Dict[str, int] = field(default_factory=dict)
    rng: random.Random = field(default_factory=random.Random)
    minutes: int = START_MINUTES
    visited: frozenset = frozenset()

    @property
    def hour(self) -> int:
        return hour_of(self.minutes)

    def npcs_here(self):
        return self.world.get_npcs_in_location(self.player.location_id, self.hour)

    def push_log(self, msg: str) -> None:
        self.log.append(msg)


def create_initial_state(world: World) -> GameState:
    player = Player(
        name="Joab",
        race=Race.HUMAN,
        combat_class=CombatClass.KNIGHT,
        location_id="crossroads",
        sentient=True,
    )
    player.inventory.add(ItemId.KETER, 10)
    player.hp = effective_stats(player)[0]

    location_items: Dict[str, Dict[ItemId, int]] = {
        "forest_depths": {ItemId.PINE_CONE: 5},
        "marsh": {ItemId.MOONPETAL: 4},
    }

    return GameState(
        world=world,
        player=player,
        location_items=location_items,
        enemies=create_initial_enemies(),
        visited=frozenset({player.location_id}),
    )
