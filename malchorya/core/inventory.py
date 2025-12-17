from dataclasses import dataclass, field
from typing import Dict

from core.items import ItemId


@dataclass
class Inventory:
    items: Dict[ItemId, int] = field(default_factory=dict)

    def add(self, item_id: ItemId, amount: int) -> None:
        if amount <= 0:
            raise ValueError("amount must be > 0")
        self.items[item_id] = self.items.get(item_id, 0) + amount

    def remove(self, item_id: ItemId, amount: int) -> None:
        if amount <= 0:
            raise ValueError("amount must be > 0")
        current = self.items.get(item_id, 0)
        if current < amount:
            raise ValueError("not enough items")
        new_amount = current - amount
        if new_amount == 0:
            self.items.pop(item_id, None)
        else:
            self.items[item_id] = new_amount
    
    def is_empty(self) -> bool:
        return not self.items or all(value <= 0 for value in self.items.values())

    def count(self, item_id: ItemId) -> int:
        return self.items.get(item_id, 0)
