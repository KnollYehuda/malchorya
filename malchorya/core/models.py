from dataclasses import dataclass, field
from typing import Dict, List
from core.enums import WindDirection
from core.entity import Entity


@dataclass
class Location(Entity):
    exits: Dict[WindDirection, str] = field(default_factory=frozenset)
    npc_ids: List[str] = None
