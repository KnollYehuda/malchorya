from dataclasses import replace
from typing import Dict, List, Optional, Tuple

from core.clock import format_clock, minutes_until_hour
from core.enemies import ENEMY_DEFS, EnemyInstance, create_initial_enemies
from core.inventory import Inventory
from core.items import ITEM_DEFS, ItemId, ItemKind
from core.progression import effective_stats, grant_xp
from core.quests import QUESTS, QuestStatus
from core.state import GameState, Player

RESPAWN_LOCATION_ID = "tavern"
REST_COST_KETER = 5
WAKE_HOUR = 6
UNCONSCIOUS_MINUTES = 6 * 60


def copy_inventory(inventory: Inventory) -> Inventory:
    return Inventory(items=dict(inventory.items))


def find_item_id(raw: str) -> Optional[ItemId]:
    normalized = raw.lower().strip()
    for item_id in ItemId:
        if item_id.value == normalized:
            return item_id
    return None


def _player_damage(state: GameState, defense: int) -> int:
    _, attack, _ = effective_stats(state.player)
    return max(1, attack - defense + state.rng.randint(-1, 2))


def enemy_retaliation(state: GameState, location_id: str) -> Tuple[GameState, List[str]]:
    """Every living enemy at the location strikes the player once."""
    messages: List[str] = []
    player = state.player
    _, _, player_defense = effective_stats(player)

    for enemy in state.enemies.get(location_id, []):
        enemy_def = ENEMY_DEFS[enemy.def_id]
        damage = max(1, enemy_def.attack - player_defense + state.rng.randint(-1, 1))
        player = replace(player, hp=max(0, player.hp - damage))
        messages.append(f"The {enemy_def.name} hits you for {damage}. (HP {player.hp})")
        if player.hp <= 0:
            break

    return replace(state, player=player), messages


def resolve_death(state: GameState) -> Tuple[GameState, str]:
    """Respawn at the tavern, losing half the keter; the wilds repopulate."""
    new_inventory = copy_inventory(state.player.inventory)
    keter_held = new_inventory.count(ItemId.KETER)
    keter_lost = keter_held // 2
    if keter_lost > 0:
        new_inventory.remove(ItemId.KETER, keter_lost)

    max_hp, _, _ = effective_stats(state.player)
    new_player = replace(
        state.player,
        hp=max_hp,
        location_id=RESPAWN_LOCATION_ID,
        inventory=new_inventory,
    )
    new_state = replace(
        state,
        player=new_player,
        enemies=create_initial_enemies(),
        minutes=state.minutes + UNCONSCIOUS_MINUTES,
    )
    return new_state, f"You collapse... You wake in the Rusted Flagon, {keter_lost} keter lighter."


def _record_kill(state: GameState, enemy: EnemyInstance) -> Tuple[GameState, List[str]]:
    enemy_def = ENEMY_DEFS[enemy.def_id]
    messages = [f"You slay the {enemy_def.name}! (+{enemy_def.xp_reward} xp)"]

    new_inventory = copy_inventory(state.player.inventory)
    if enemy_def.keter_reward > 0:
        new_inventory.add(ItemId.KETER, enemy_def.keter_reward)
        messages.append(f"It carried {enemy_def.keter_reward} keter.")
    if enemy_def.loot_item is not None:
        new_inventory.add(enemy_def.loot_item, 1)
        messages.append(f"You take a {ITEM_DEFS[enemy_def.loot_item].name}.")

    player = replace(state.player, inventory=new_inventory)
    player, level_messages = grant_xp(player, enemy_def.xp_reward)
    messages.extend(level_messages)

    new_progress = dict(state.quest_progress)
    for quest in QUESTS.values():
        if (
            quest.kill_target == enemy.def_id
            and state.quest_log.get(quest.id) == QuestStatus.IN_PROGRESS
            and new_progress.get(quest.id, 0) < quest.kill_count
        ):
            new_progress[quest.id] = new_progress.get(quest.id, 0) + 1
            messages.append(
                f"[{quest.name}: {new_progress[quest.id]}/{quest.kill_count}]"
            )

    return replace(state, player=player, quest_progress=new_progress), messages


def _find_target(state: GameState, raw_target: Optional[str]) -> Optional[EnemyInstance]:
    enemies_here = state.enemies.get(state.player.location_id, [])
    if not enemies_here:
        return None
    if raw_target is None:
        return enemies_here[0]
    normalized = raw_target.lower()
    for enemy in enemies_here:
        if normalized in (enemy.instance_id, enemy.def_id):
            return enemy
    return None


def attack_enemy(state: GameState, raw_target: Optional[str]) -> Tuple[GameState, str]:
    location_id = state.player.location_id
    if not state.enemies.get(location_id):
        return state, "There is nothing here to fight."

    target = _find_target(state, raw_target)
    if target is None:
        return state, "No such enemy here."

    enemy_def = ENEMY_DEFS[target.def_id]
    damage = _player_damage(state, enemy_def.defense)
    remaining_hp = target.hp - damage
    messages = [f"You hit the {enemy_def.name} for {damage}."]

    new_enemies: Dict[str, List[EnemyInstance]] = {
        key: list(value) for key, value in state.enemies.items()
    }
    new_enemies[location_id] = [
        enemy for enemy in new_enemies[location_id] if enemy.instance_id != target.instance_id
    ]

    if remaining_hp > 0:
        index = state.enemies[location_id].index(target)
        new_enemies[location_id].insert(index, replace(target, hp=remaining_hp))
        new_state = replace(state, enemies=new_enemies)
    else:
        new_state, kill_messages = _record_kill(replace(state, enemies=new_enemies), target)
        messages.extend(kill_messages)

    new_state, retaliation_messages = enemy_retaliation(new_state, location_id)
    messages.extend(retaliation_messages)

    if new_state.player.hp <= 0:
        new_state, death_message = resolve_death(new_state)
        messages.append(death_message)

    return new_state, "\n".join(messages)


def equip_item(state: GameState, item_id: ItemId) -> Tuple[GameState, str]:
    item_def = ITEM_DEFS[item_id]
    if item_def.kind not in (ItemKind.WEAPON, ItemKind.ARMOR):
        return state, f"You can't equip the {item_def.name}."
    if state.player.inventory.count(item_id) < 1:
        return state, f"You don't have a {item_def.name}."

    new_inventory = copy_inventory(state.player.inventory)
    new_inventory.remove(item_id, 1)
    new_equipment = dict(state.player.equipment)

    previous_item_id = new_equipment.get(item_def.kind)
    if previous_item_id is not None:
        new_inventory.add(previous_item_id, 1)
    new_equipment[item_def.kind] = item_id

    new_player = replace(state.player, inventory=new_inventory, equipment=new_equipment)
    max_hp, _, _ = effective_stats(new_player)
    new_player = replace(new_player, hp=min(new_player.hp, max_hp))
    return replace(state, player=new_player), f"You equip the {item_def.name}."


def unequip_item(state: GameState, slot_name: str) -> Tuple[GameState, str]:
    slot_by_name = {"weapon": ItemKind.WEAPON, "armor": ItemKind.ARMOR}
    slot = slot_by_name.get(slot_name.lower())
    if slot is None:
        return state, "Unequip which slot? (weapon/armor)"

    item_id = state.player.equipment.get(slot)
    if item_id is None:
        return state, f"Nothing equipped in {slot_name.lower()} slot."

    new_equipment = {key: value for key, value in state.player.equipment.items() if key != slot}
    new_inventory = copy_inventory(state.player.inventory)
    new_inventory.add(item_id, 1)
    new_player = replace(state.player, inventory=new_inventory, equipment=new_equipment)
    return replace(state, player=new_player), f"You unequip the {ITEM_DEFS[item_id].name}."


def use_item(state: GameState, item_id: ItemId) -> Tuple[GameState, str]:
    item_def = ITEM_DEFS[item_id]
    if item_def.kind != ItemKind.CONSUMABLE:
        return state, f"You can't use the {item_def.name}."
    if state.player.inventory.count(item_id) < 1:
        return state, f"You don't have a {item_def.name}."

    max_hp, _, _ = effective_stats(state.player)
    if state.player.hp >= max_hp:
        return state, "You are already at full health."

    new_inventory = copy_inventory(state.player.inventory)
    new_inventory.remove(item_id, 1)
    healed_hp = min(max_hp, state.player.hp + item_def.heal_amount)
    new_player = replace(state.player, inventory=new_inventory, hp=healed_hp)
    new_state = replace(state, player=new_player)
    messages = [f"You drink the {item_def.name}. (HP {healed_hp}/{max_hp})"]

    # Drinking in the middle of a fight costs a turn.
    location_id = state.player.location_id
    if new_state.enemies.get(location_id):
        new_state, retaliation_messages = enemy_retaliation(new_state, location_id)
        messages.extend(retaliation_messages)
        if new_state.player.hp <= 0:
            new_state, death_message = resolve_death(new_state)
            messages.append(death_message)

    return new_state, "\n".join(messages)


def rest_at_inn(state: GameState) -> Tuple[GameState, str]:
    if state.player.location_id != RESPAWN_LOCATION_ID:
        return state, "You can only rest at the Rusted Flagon."
    keter_held = state.player.inventory.count(ItemId.KETER)
    if keter_held < REST_COST_KETER:
        return state, f"A bed costs {REST_COST_KETER} keter."

    new_inventory = copy_inventory(state.player.inventory)
    new_inventory.remove(ItemId.KETER, REST_COST_KETER)
    max_hp, _, _ = effective_stats(state.player)
    new_player = replace(state.player, inventory=new_inventory, hp=max_hp)
    wake_minutes = state.minutes + minutes_until_hour(state.minutes, WAKE_HOUR)
    new_state = replace(
        state, player=new_player, enemies=create_initial_enemies(), minutes=wake_minutes
    )
    return new_state, (
        f"You sleep until morning ({REST_COST_KETER} keter). HP restored. "
        f"The wilds stir again. {format_clock(wake_minutes)}"
    )


def sell_item(state: GameState, item_id: ItemId, amount: int) -> Tuple[GameState, str]:
    item_def = ITEM_DEFS[item_id]
    if item_def.kind in (ItemKind.CURRENCY, ItemKind.QUEST_ITEM) or item_def.value <= 0:
        return state, f"Nobody will buy the {item_def.name}."
    npcs_here = state.npcs_here()
    if not any(npc.shop_inventory for npc in npcs_here):
        return state, "Nobody here is buying."
    if state.player.inventory.count(item_id) < amount:
        return state, f"You don't have {amount}x {item_def.name}."

    payout = max(1, item_def.value // 2) * amount
    new_inventory = copy_inventory(state.player.inventory)
    new_inventory.remove(item_id, amount)
    new_inventory.add(ItemId.KETER, payout)
    new_player = replace(state.player, inventory=new_inventory)
    return replace(state, player=new_player), f"You sell {amount}x {item_def.name} for {payout} keter."
