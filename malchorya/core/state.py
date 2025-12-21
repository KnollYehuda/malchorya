from dataclasses import dataclass, field
from typing import List

from core.enums import CombatClass, Race
from core.inventory import Inventory
from core.items import ItemId
from core.world import World
from core.entity import Entity


@dataclass
class Player(Entity):
    race: Race = field(default_factory=None)
    combat_class: CombatClass = field(default_factory=None)
    location_id: str = field(default_factory="")
    inventory: Inventory = field(default_factory=Inventory)


@dataclass
class GameState:
    world: World
    player: Player
    log: List[str] = field(default_factory=list)

    def push_log(self, msg: str) -> None:
        self.log.append(msg)


def create_initial_state(world: World) -> GameState:
    player = Player(
        name="Joab",
        race=Race.HUMAN,
        combat_class=CombatClass.KNIGHT,
        location_id="crossroads",
        sentient=True
    )
    player.inventory.add(ItemId.KETER, 10)
    return GameState(world=world, player=player)
