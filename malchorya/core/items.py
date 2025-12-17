from dataclasses import dataclass
from enum import Enum


class ItemId(Enum):
    KETER = "keter"


@dataclass(frozen=True)
class ItemStack:
    item_id: ItemId
    amount: int
