from dataclasses import dataclass, field
from enum import Enum

class EntityKind(Enum):
    PLAYER = "player"
    NPC = "npc"
    INANIMATE = "inanimate"

@dataclass
class Entity:
    id: str = None
    name: str = None
    kind: str = None
    description: str = None
    sentient: bool = None
