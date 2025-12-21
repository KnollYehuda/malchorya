from dataclasses import dataclass
from typing import Dict, List

from core.models import Location
from core.enums import WindDirection
from core.npcs import Npc, NpcKind
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
    
    def get_npcs_in_location(self, location_id: str) -> List[Npc]:
        return [npc for npc in self.npcs.values() if npc.location_id == location_id]

def get_locations() -> List[Location]:
    return [
        Location(
            id="crossroads",
            name="Crossroads of Malchorya",
            description="A worn stone sign points to ancient paths.",
            exits={WindDirection.NORTH: "pinewood", WindDirection.EAST: "riverbank"},
        ),
        Location(
            id="pinewood",
            name="Pinewood",
            description="Tall pines whisper in a cold wind.",
            exits={WindDirection.SOUTH: "crossroads"},
        ),
        Location(
            id="riverbank",
            name="Riverbank",
            description="A shallow river glitters. You spot a small dock.",
            exits={WindDirection.WEST: "crossroads"},
        )
    ]


def get_npcs() -> List[Npc]:
    return [
        Npc(
            id="merchant_eron",
            name="Eron",
            kind=NpcKind.MERCHANT,
            location_id="riverbank",
            sentient=True
        ),
        Npc(
            id="lysa_wanderer",
            name="Lysa",
            kind=NpcKind.CITIZEN,
            location_id="crossroads",
            sentient=True
        ),
        Npc(
            id="borin_guard",
            name="Borin Stonehand",
            kind=NpcKind.GUARD,
            location_id="pinewood",
            sentient=True
        ),
        Npc(
            id="silent_one",
            name="The Silent One",
            kind=NpcKind.MYSTERIOUS,
            location_id="unknown"
        ),
    ]

def create_world() -> World:
    return World(name=MALCHORYA,
                 locations={location.id: location for location in get_locations()},
                 npcs={npc.id: npc for npc in get_npcs()})
