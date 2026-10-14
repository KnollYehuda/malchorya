from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Tuple
from core.entity import Entity
from core.items import ItemId


class NpcKind(Enum):
    MERCHANT = "merchant"
    CITIZEN = "citizen"
    GUARD = "guard"
    MYSTERIOUS = "mysterious"
    BLACKSMITH = "blacksmith"
    INNKEEPER = "innkeeper"
    FERRYMAN = "ferryman"
    PRIEST = "priest"
    HERMIT = "hermit"


@dataclass
class Npc(Entity):
    location_id: str = None
    tags: frozenset = field(default_factory=frozenset)
    shop_inventory: Dict[ItemId, int] = field(default_factory=dict)
    # (start_hour, end_hour, location_id or None for off-stage); end < start wraps midnight.
    schedule: Tuple[Tuple[int, int, Optional[str]], ...] = ()

    def location_at(self, hour: int) -> Optional[str]:
        if not self.schedule:
            return self.location_id
        for start_hour, end_hour, location_id in self.schedule:
            if start_hour < end_hour:
                inside = start_hour <= hour < end_hour
            else:
                inside = hour >= start_hour or hour < end_hour
            if inside:
                return location_id
        return None
