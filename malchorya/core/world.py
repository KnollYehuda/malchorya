from dataclasses import dataclass
from typing import Dict, List, Optional

from core.models import Location
from core.enums import WindDirection
from core.npcs import Npc, NpcKind
from core.items import ItemId
from core.consts import MALCHORYA


@dataclass(frozen=True)
class World:
    name: str
    locations: Dict[str, Location]
    npcs: Dict[str, Npc]

    def get_location(self, location_id: str) -> Location:
        if location_id not in self.locations:
            raise KeyError(f"Unknown location_id: {location_id}")
        return self.locations[location_id]

    def get_npcs_in_location(self, location_id: str, hour: Optional[int] = None) -> List[Npc]:
        if hour is None:
            return [npc for npc in self.npcs.values() if npc.location_id == location_id]
        return [npc for npc in self.npcs.values() if npc.location_at(hour) == location_id]


def get_locations() -> List[Location]:
    return [
        Location(
            id="crossroads",
            biome="crossroads",
            name="Crossroads of Malchorya",
            description="A worn stone sign points to ancient paths. The smell of forge-smoke drifts from the west.",
            exits={
                WindDirection.NORTH: "pinewood",
                WindDirection.EAST: "riverbank",
                WindDirection.WEST: "town_square",
                WindDirection.SOUTH: "south_road",
            },
        ),
        Location(
            id="pinewood",
            biome="pinewood",
            name="Pinewood",
            description="Tall pines whisper in a cold wind. A guard eyes you carefully.",
            exits={
                WindDirection.SOUTH: "crossroads",
                WindDirection.NORTH: "forest_depths",
                WindDirection.EAST: "watchtower",
            },
        ),
        Location(
            id="riverbank",
            biome="riverbank",
            name="Riverbank",
            description="A shallow river glitters. You spot a small dock to the east.",
            exits={WindDirection.WEST: "crossroads", WindDirection.EAST: "river_dock"},
        ),
        Location(
            id="town_square",
            biome="town_square",
            name="Town Square",
            description="The heart of the settlement. A forge glows to the north; ale-smell drifts from the south.",
            exits={
                WindDirection.EAST: "crossroads",
                WindDirection.NORTH: "blacksmith",
                WindDirection.SOUTH: "tavern",
                WindDirection.WEST: "chapel",
            },
        ),
        Location(
            id="blacksmith",
            biome="blacksmith",
            name="Elara's Forge",
            description="Heat radiates from an open furnace. Blades and armor line the walls.",
            exits={WindDirection.SOUTH: "town_square"},
        ),
        Location(
            id="tavern",
            biome="tavern",
            name="The Rusted Flagon",
            description="A low-ceilinged room thick with ale-smoke and pine resin.",
            exits={WindDirection.NORTH: "town_square"},
        ),
        Location(
            id="forest_depths",
            biome="forest_depths",
            name="Forest Depths",
            description="The trees grow dense here. Pine cones litter the ground — use 'take pine_cone'.",
            exits={WindDirection.SOUTH: "pinewood", WindDirection.NORTH: "hermit_hut"},
        ),
        Location(
            id="hermit_hut",
            biome="hermit_hut",
            name="Hermit's Hut",
            description="A hut of bent branches, hung with dried herbs and animal bones. Smoke curls from a hole in the roof.",
            exits={WindDirection.SOUTH: "forest_depths"},
        ),
        Location(
            id="chapel",
            biome="chapel",
            name="Chapel of the Quiet Flame",
            description="A small stone chapel. Candles gutter along the walls and the air smells of wax and old incense.",
            exits={WindDirection.EAST: "town_square"},
        ),
        Location(
            id="south_road",
            biome="south_road",
            name="South Road",
            description="A rutted road sinking slowly into wet ground. Mist gathers to the south.",
            exits={WindDirection.NORTH: "crossroads", WindDirection.SOUTH: "marsh"},
        ),
        Location(
            id="marsh",
            biome="marsh",
            name="Blackwater Marsh",
            description="Stagnant pools and twisted reeds. Pale flowers cling to the hummocks, shut tight against the light.",
            exits={WindDirection.NORTH: "south_road"},
        ),
        Location(
            id="watchtower",
            biome="watchtower",
            name="Ruined Watchtower",
            description="A collapsed tower, its stones blackened by old fires. Bandits have made camp here.",
            exits={WindDirection.WEST: "pinewood"},
        ),
        Location(
            id="river_dock",
            biome="river_dock",
            name="River Dock",
            description="A ferryman waits beside a weathered boat, pole in hand.",
            exits={WindDirection.WEST: "riverbank"},
        ),
    ]


def get_npcs() -> List[Npc]:
    return [
        Npc(
            id="merchant_eron",
            name="Eron",
            kind=NpcKind.MERCHANT,
            location_id="riverbank",
            sentient=True,
            shop_inventory={ItemId.HEALTH_POTION: 3},
            schedule=((8, 18, "riverbank"), (18, 22, "tavern")),
        ),
        Npc(
            id="lysa_wanderer",
            name="Lysa",
            kind=NpcKind.CITIZEN,
            location_id="crossroads",
            sentient=True,
            schedule=((6, 20, "crossroads"), (20, 23, "tavern")),
        ),
        Npc(
            id="borin_guard",
            name="Borin Stonehand",
            kind=NpcKind.GUARD,
            location_id="pinewood",
            sentient=True,
            schedule=((6, 20, "pinewood"), (20, 6, "crossroads")),
        ),
        Npc(
            id="silent_one",
            name="The Silent One",
            kind=NpcKind.MYSTERIOUS,
            location_id="unknown",
        ),
        Npc(
            id="elara_blacksmith",
            name="Elara",
            kind=NpcKind.BLACKSMITH,
            location_id="blacksmith",
            sentient=True,
            shop_inventory={ItemId.IRON_SWORD: 3, ItemId.LEATHER_ARMOR: 2, ItemId.STEEL_SWORD: 1},
            schedule=((7, 19, "blacksmith"), (19, 22, "tavern")),
        ),
        Npc(
            id="vorn_innkeeper",
            name="Vorn",
            kind=NpcKind.INNKEEPER,
            location_id="tavern",
            sentient=True,
            shop_inventory={ItemId.HEALTH_POTION: 5},
        ),
        Npc(
            id="ferryman_tol",
            name="Tol the Ferryman",
            kind=NpcKind.FERRYMAN,
            location_id="river_dock",
            sentient=True,
            schedule=((6, 20, "river_dock"),),
        ),
        Npc(
            id="maren_priest",
            name="Maren",
            kind=NpcKind.PRIEST,
            location_id="chapel",
            sentient=True,
            shop_inventory={ItemId.HEALTH_POTION: 4},
            schedule=((6, 21, "chapel"),),
        ),
        Npc(
            id="oren_hermit",
            name="Oren the Hermit",
            kind=NpcKind.HERMIT,
            location_id="hermit_hut",
            sentient=True,
        ),
    ]


def create_world() -> World:
    return World(
        name=MALCHORYA,
        locations={location.id: location for location in get_locations()},
        npcs={npc.id: npc for npc in get_npcs()},
    )
