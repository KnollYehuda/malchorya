from dataclasses import replace
from typing import List, Tuple

from core.enums import CombatClass, Race
from core.items import ITEM_DEFS, ItemKind

BASE_STATS_BY_CLASS = {
    CombatClass.KNIGHT: {"max_hp": 40, "attack": 4, "defense": 2},
    CombatClass.ASSASSIN: {"max_hp": 30, "attack": 6, "defense": 1},
    CombatClass.MAGE: {"max_hp": 25, "attack": 7, "defense": 0},
}

RACE_BONUS = {
    Race.HUMAN: {"max_hp": 2, "attack": 0, "defense": 0},
    Race.ELF: {"max_hp": 0, "attack": 1, "defense": 0},
    Race.DWARF: {"max_hp": 5, "attack": 0, "defense": 1},
    Race.ORC: {"max_hp": 8, "attack": 1, "defense": 0},
}

HP_PER_LEVEL = 8
XP_PER_LEVEL = 20


def xp_needed_for_next_level(level: int) -> int:
    return level * XP_PER_LEVEL


def effective_stats(player) -> Tuple[int, int, int]:
    """Return (max_hp, attack, defense) including level scaling and equipment."""
    base = BASE_STATS_BY_CLASS[player.combat_class]
    bonus = RACE_BONUS[player.race]
    levels_gained = player.level - 1

    max_hp = base["max_hp"] + bonus["max_hp"] + levels_gained * HP_PER_LEVEL
    attack = base["attack"] + bonus["attack"] + levels_gained
    defense = base["defense"] + bonus["defense"] + levels_gained // 2

    for item_id in player.equipment.values():
        item_def = ITEM_DEFS[item_id]
        attack += item_def.attack_bonus
        defense += item_def.defense_bonus

    return max_hp, attack, defense


def grant_xp(player, amount: int) -> Tuple[object, List[str]]:
    """Add xp, applying any level-ups. Returns the new player and messages."""
    messages: List[str] = []
    level = player.level
    xp = player.xp + amount

    while xp >= xp_needed_for_next_level(level):
        xp -= xp_needed_for_next_level(level)
        level += 1
        messages.append(f"[Level up! You are now level {level}.]")

    new_player = replace(player, level=level, xp=xp)
    if level != player.level:
        max_hp, _, _ = effective_stats(new_player)
        new_player = replace(new_player, hp=max_hp)
    return new_player, messages


def equipment_slot_for(item_kind: ItemKind) -> bool:
    return item_kind in (ItemKind.WEAPON, ItemKind.ARMOR)
