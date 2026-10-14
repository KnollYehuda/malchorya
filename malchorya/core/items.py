from dataclasses import dataclass
from enum import Enum
from typing import Dict


class ItemKind(Enum):
    CURRENCY = "currency"
    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    QUEST_ITEM = "quest_item"
    MATERIAL = "material"


class ItemId(Enum):
    KETER = "keter"
    IRON_SWORD = "iron_sword"
    LEATHER_ARMOR = "leather_armor"
    HEALTH_POTION = "health_potion"
    PINE_CONE = "pine_cone"
    WOLF_PELT = "wolf_pelt"
    STEEL_SWORD = "steel_sword"
    MOONPETAL = "moonpetal"


@dataclass(frozen=True)
class ItemStack:
    item_id: ItemId
    amount: int


@dataclass(frozen=True)
class ItemDef:
    id: ItemId
    name: str
    kind: ItemKind
    description: str
    value: int = 0
    attack_bonus: int = 0
    defense_bonus: int = 0
    heal_amount: int = 0
    night_only: bool = False


ITEM_DEFS: Dict[ItemId, ItemDef] = {
    ItemId.KETER: ItemDef(
        id=ItemId.KETER,
        name="Keter",
        kind=ItemKind.CURRENCY,
        description="The coin of the realm.",
        value=1,
    ),
    ItemId.IRON_SWORD: ItemDef(
        id=ItemId.IRON_SWORD,
        name="Iron Sword",
        kind=ItemKind.WEAPON,
        description="A sturdy iron blade.",
        value=15,
        attack_bonus=4,
    ),
    ItemId.LEATHER_ARMOR: ItemDef(
        id=ItemId.LEATHER_ARMOR,
        name="Leather Armor",
        kind=ItemKind.ARMOR,
        description="Light but protective.",
        value=10,
        defense_bonus=2,
    ),
    ItemId.HEALTH_POTION: ItemDef(
        id=ItemId.HEALTH_POTION,
        name="Health Potion",
        kind=ItemKind.CONSUMABLE,
        description="Restores vitality. Warm and bitter.",
        value=5,
        heal_amount=20,
    ),
    ItemId.PINE_CONE: ItemDef(
        id=ItemId.PINE_CONE,
        name="Pine Cone",
        kind=ItemKind.QUEST_ITEM,
        description="A fresh pine cone from the forest depths.",
        value=0,
    ),
    ItemId.WOLF_PELT: ItemDef(
        id=ItemId.WOLF_PELT,
        name="Wolf Pelt",
        kind=ItemKind.MATERIAL,
        description="A thick grey pelt. Traders pay well for these.",
        value=8,
    ),
    ItemId.STEEL_SWORD: ItemDef(
        id=ItemId.STEEL_SWORD,
        name="Steel Sword",
        kind=ItemKind.WEAPON,
        description="Folded steel with a keen edge.",
        value=40,
        attack_bonus=8,
    ),
    ItemId.MOONPETAL: ItemDef(
        id=ItemId.MOONPETAL,
        name="Moonpetal",
        kind=ItemKind.QUEST_ITEM,
        description="A pale flower that blooms only in darkness.",
        value=0,
        night_only=True,
    ),
}
