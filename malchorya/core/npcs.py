from dataclasses import dataclass, field
from enum import Enum
from core.entity import Entity


class NpcKind(Enum):
    MERCHANT = "merchant"
    CITIZEN = "citizen"
    GUARD = "guard"
    MYSTERIOUS = "mysterious"


@dataclass
class Npc(Entity):
    location_id: str = None
    tags: frozenset[str] = field(default_factory=set)
