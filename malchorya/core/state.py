from dataclasses import dataclass, field
from typing import List

from core.enums import CombatClass, Race
from core.inventory import Inventory
from core.items import ItemId
from core.world import World


@dataclass
class Player:
    name: str
    race: Race
    combat_class: CombatClass
    location_id: str
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
    )
    player.inventory.add(ItemId.KETER, 10)
    return GameState(world=world, player=player)
