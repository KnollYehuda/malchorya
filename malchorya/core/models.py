from dataclasses import dataclass
from typing import Dict, List
from core.enums import WindDirection


@dataclass(frozen=True)
class Location:
    id: str
    name: str
    description: str
    exits: Dict[WindDirection, str]
    npc_ids: List[str] = None
