from dataclasses import dataclass, field
from enum import Enum


class NpcKind(Enum):
    MERCHANT = "merchant"
    CITIZEN = "citizen"
    GUARD = "guard"
    MYSTERIOUS = "mysterious"


@dataclass(frozen=True)
class Npc:
    id: str
    name: str
    kind: NpcKind
    location_id: str
    tags: frozenset[str] = field(default_factory=frozenset)
