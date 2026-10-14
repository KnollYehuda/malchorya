from dataclasses import replace
from typing import Callable, Dict, Optional, Tuple

from core.enums import Command, WindDirection
from core.inventory import Inventory
from core.items import ItemId, ItemDef, ItemKind, ITEM_DEFS
from core.quests import QUESTS, QuestStatus, quest_is_completable
from core.state import GameState
from core.dialogue import (
    DIALOGUE_BY_NPC_ID,
    DIALOGUE_BY_KIND,
    QUEST_OFFER,
    QUEST_REMINDER,
    QUEST_COMPLETE,
)
from core.clock import format_clock, is_night, MINUTES_PER_DAY
from core.enemies import ENEMY_DEFS
from core.mapping import ascii_map
from core.progression import effective_stats, grant_xp, xp_needed_for_next_level
from logic.combat import (
    attack_enemy,
    copy_inventory,
    enemy_retaliation,
    equip_item,
    find_item_id,
    rest_at_inn,
    resolve_death,
    sell_item,
    unequip_item,
    use_item,
)
from logic.result import CommandResult

Handler = Callable[[GameState, list[str]], CommandResult]


def _complete_quest(state: GameState, quest) -> Tuple[GameState, str]:
    new_quest_log = {**state.quest_log, quest.id: QuestStatus.COMPLETE}
    new_inventory = copy_inventory(state.player.inventory)

    if quest.required_item is not None:
        new_inventory.remove(quest.required_item, quest.required_amount)

    if quest.reward_keter > 0:
        new_inventory.add(ItemId.KETER, quest.reward_keter)
    if quest.reward_item is not None:
        new_inventory.add(quest.reward_item, quest.reward_item_amount)

    new_player = replace(state.player, inventory=new_inventory)
    level_messages: list[str] = []
    if quest.reward_xp:
        new_player, level_messages = grant_xp(new_player, quest.reward_xp)
    new_state = replace(state, quest_log=new_quest_log, player=new_player)

    reward_parts = []
    if quest.reward_xp:
        reward_parts.append(f"{quest.reward_xp} xp")
    if quest.reward_keter:
        reward_parts.append(f"{quest.reward_keter} keter")
    if quest.reward_item is not None:
        item_name = ITEM_DEFS[quest.reward_item].name
        reward_parts.append(f"{quest.reward_item_amount}x {item_name}")

    reward_str = " and ".join(reward_parts) if reward_parts else "nothing"
    return new_state, " ".join([f"[Quest complete! Received: {reward_str}]", *level_messages])


def cmd_look(state: GameState, args: list[str]) -> CommandResult:
    loc = state.world.get_location(state.player.location_id)
    exits = ", ".join([direction.value for direction in loc.exits.keys()]) or "none"

    loc_items = state.location_items.get(state.player.location_id, {})
    item_parts = []
    for item_id, amount in loc_items.items():
        item_parts.append(f"{ITEM_DEFS[item_id].name} x{amount}")

    message = f"{loc.name}\n{loc.description}\nExits: {exits}"
    if item_parts:
        message += f"\nItems on ground: {', '.join(item_parts)}"
    people = [f"{npc.name} ({npc.id})" for npc in state.npcs_here()]
    if people:
        message += f"\nPresent: {', '.join(people)}"
    enemies_here = state.enemies.get(state.player.location_id, [])
    if enemies_here:
        enemy_parts = [
            f"{ENEMY_DEFS[enemy.def_id].name} [{enemy.instance_id}] HP {enemy.hp}"
            for enemy in enemies_here
        ]
        message += f"\nHostile: {', '.join(enemy_parts)}"
    return CommandResult(state, message)


def cmd_talk(state: GameState, args: list[str]) -> CommandResult:
    npc_id = args[0].strip() if args else ""
    if not npc_id:
        return CommandResult(state=state, message="Usage: talk <npc_id>")

    npc = state.world.npcs.get(npc_id)
    if npc is None:
        return CommandResult(state=state, message="Unknown npc id.")

    if npc.location_at(state.hour) != state.player.location_id:
        return CommandResult(state=state, message="They are not here.")

    if not npc.sentient:
        return CommandResult(
            state=state,
            message="Only the rustling of birds and the buzzing of flies can be heard...",
        )

    if state.enemies.get(state.player.location_id):
        return CommandResult(state=state, message=f"{npc.name} can't talk with enemies nearby.")

    # Quest giver interactions
    for quest in [quest for quest in QUESTS.values() if quest.giver_id == npc_id]:
        quest_status = state.quest_log.get(quest.id, QuestStatus.NOT_STARTED)

        if quest_status == QuestStatus.NOT_STARTED:
            new_quest_log = {**state.quest_log, quest.id: QuestStatus.IN_PROGRESS}
            new_state = replace(state, quest_log=new_quest_log)
            return CommandResult(new_state, f"{npc.name}: {QUEST_OFFER[quest.id]}")

        if quest_status == QuestStatus.IN_PROGRESS and quest.completion_npc_id == npc_id:
            if quest_is_completable(quest.id, state):
                new_state, reward_msg = _complete_quest(state, quest)
                return CommandResult(
                    new_state, f"{npc.name}: {QUEST_COMPLETE[quest.id]} {reward_msg}"
                )
            return CommandResult(state, f"{npc.name}: {QUEST_REMINDER[quest.id]}")

    # Quest completion target (NPC that completes another NPC's quest)
    for quest in [
        quest
        for quest in QUESTS.values()
        if quest.completion_npc_id == npc_id and quest.giver_id != npc_id
    ]:
        quest_status = state.quest_log.get(quest.id, QuestStatus.NOT_STARTED)
        if quest_status == QuestStatus.IN_PROGRESS and quest_is_completable(quest.id, state):
            new_state, reward_msg = _complete_quest(state, quest)
            return CommandResult(
                new_state, f"{npc.name}: {QUEST_COMPLETE[quest.id]} {reward_msg}"
            )

    msg = DIALOGUE_BY_NPC_ID.get(npc.id, DIALOGUE_BY_KIND.get(npc.kind, "..."))
    return CommandResult(state, f"{npc.name}: {msg}")


def cmd_status(state: GameState, args: list[str]) -> CommandResult:
    player = state.player
    loc = state.world.get_location(player.location_id)
    max_hp, attack, defense = effective_stats(player)
    equipped = ", ".join(
        f"{slot.value}: {ITEM_DEFS[item_id].name}" for slot, item_id in player.equipment.items()
    ) or "nothing"
    lines = [
        f"{player.name} ({player.race.value} {player.combat_class.value}) at {loc.name}.",
        f"Level {player.level}  XP {player.xp}/{xp_needed_for_next_level(player.level)}",
        f"HP {player.hp}/{max_hp}  Attack {attack}  Defense {defense}",
        f"Equipped: {equipped}",
        format_clock(state.minutes),
    ]
    return CommandResult(state, "\n".join(lines))


def cmd_inventory(state: GameState, args: list[str]) -> CommandResult:
    inv = state.player.inventory
    if inv.is_empty():
        return CommandResult(state, "Your inventory is empty.")

    lines = ["Inventory:"]
    for item_id, amount in inv.items.items():
        item_name = ITEM_DEFS[item_id].name
        lines.append(f"  {item_name}: {amount}")
    return CommandResult(state, "\n".join(lines))


def cmd_move(state: GameState, args: list[str]) -> CommandResult:
    direction_str = args[0] if args else ""
    direction = None
    for wind_direction in WindDirection:
        if wind_direction.value == direction_str.lower():
            direction = wind_direction
            break

    if direction is None:
        return CommandResult(state=state, message="Unknown direction. Use: north/south/east/west")

    location = state.world.get_location(state.player.location_id)
    if direction not in location.exits:
        return CommandResult(state=state, message=f"You can't go '{direction.value}' from here.")

    retreat_messages: list[str] = []
    if state.enemies.get(state.player.location_id):
        state, retreat_messages = enemy_retaliation(state, state.player.location_id)
        retreat_messages.insert(0, "Enemies strike as you turn your back!")
        if state.player.hp <= 0:
            state, death_message = resolve_death(state)
            retreat_messages.append(death_message)
            return CommandResult(state=state, message="\n".join(retreat_messages))

    next_location_id = location.exits[direction]
    new_player = replace(state.player, location_id=next_location_id)
    new_state = replace(state, player=new_player)

    new_location = new_state.world.get_location(new_player.location_id)
    move_message = f"You move {direction.value} to {new_location.name}."
    hostile_here = new_state.enemies.get(next_location_id, [])
    if hostile_here:
        move_message += " Hostile creatures are here!"
    return CommandResult(state=new_state, message="\n".join([*retreat_messages, move_message]))


def cmd_buy(state: GameState, args: list[str]) -> CommandResult:
    item_id_str = args[0].lower()
    amount = 1
    if len(args) > 1:
        try:
            amount = int(args[1])
        except ValueError:
            return CommandResult(state, "Amount must be a number.")
    if amount <= 0:
        return CommandResult(state, "Amount must be positive.")

    item_id = find_item_id(item_id_str)
    if item_id is None:
        return CommandResult(state, f"Unknown item: {item_id_str}")

    item_def = ITEM_DEFS[item_id]

    npcs_here = state.npcs_here()
    seller = None
    for npc in npcs_here:
        if npc.shop_inventory.get(item_id, 0) >= amount:
            seller = npc
            break

    if seller is None:
        return CommandResult(state, f"Nobody here sells {item_def.name}.")

    total_cost = item_def.value * amount
    keter_held = state.player.inventory.count(ItemId.KETER)
    if keter_held < total_cost:
        return CommandResult(
            state, f"Need {total_cost} keter. You have {keter_held}."
        )

    new_inventory = copy_inventory(state.player.inventory)
    new_inventory.remove(ItemId.KETER, total_cost)
    new_inventory.add(item_id, amount)

    new_player = replace(state.player, inventory=new_inventory)
    new_state = replace(state, player=new_player)
    message = f"You buy {amount}x {item_def.name} for {total_cost} keter."

    if item_def.kind in (ItemKind.WEAPON, ItemKind.ARMOR) and item_def.kind not in new_player.equipment:
        new_state, equip_message = equip_item(new_state, item_id)
        message += f" {equip_message}"

    return CommandResult(new_state, message)


def cmd_take(state: GameState, args: list[str]) -> CommandResult:
    item_id_str = args[0].lower()

    item_id = find_item_id(item_id_str)
    if item_id is None:
        return CommandResult(state, f"Unknown item: {item_id_str}")

    item_def = ITEM_DEFS[item_id]
    loc_items = state.location_items.get(state.player.location_id, {})
    available = loc_items.get(item_id, 0)

    if available <= 0:
        return CommandResult(state, f"There's no {item_def.name} here.")
    if item_def.night_only and not is_night(state.hour):
        return CommandResult(
            state, f"The {item_def.name}s are shut tight. They open only after dark."
        )

    new_location_items = {
        location_id: dict(items)
        for location_id, items in state.location_items.items()
    }
    new_location_items[state.player.location_id][item_id] -= 1
    if new_location_items[state.player.location_id][item_id] <= 0:
        del new_location_items[state.player.location_id][item_id]

    new_inventory = copy_inventory(state.player.inventory)
    new_inventory.add(item_id, 1)

    new_player = replace(state.player, inventory=new_inventory)
    new_state = replace(state, player=new_player, location_items=new_location_items)

    remaining = new_location_items.get(state.player.location_id, {}).get(item_id, 0)
    suffix = f" ({remaining} left here)" if remaining > 0 else ""
    return CommandResult(new_state, f"You pick up a {item_def.name}.{suffix}")


def cmd_quests(state: GameState, args: list[str]) -> CommandResult:
    if not state.quest_log:
        return CommandResult(state, "No quests yet. Talk to NPCs to find work.")

    lines = []
    for quest_id, status in state.quest_log.items():
        quest = QUESTS[quest_id]
        status_label = "DONE" if status == QuestStatus.COMPLETE else "active"
        progress = ""
        if quest.kill_target is not None and status != QuestStatus.COMPLETE:
            progress = f" ({state.quest_progress.get(quest_id, 0)}/{quest.kill_count})"
        lines.append(f"[{status_label}] {quest.name}: {quest.objective}{progress}")

    return CommandResult(state, "\n".join(lines))


def _require_item(state: GameState, raw: str):
    item_id = find_item_id(raw)
    if item_id is None:
        return None, CommandResult(state, f"Unknown item: {raw}")
    return item_id, None


def cmd_attack(state: GameState, args: list[str]) -> CommandResult:
    new_state, message = attack_enemy(state, args[0] if args else None)
    return CommandResult(new_state, message)


def cmd_equip(state: GameState, args: list[str]) -> CommandResult:
    item_id, error = _require_item(state, args[0])
    if error:
        return error
    new_state, message = equip_item(state, item_id)
    return CommandResult(new_state, message)


def cmd_unequip(state: GameState, args: list[str]) -> CommandResult:
    new_state, message = unequip_item(state, args[0])
    return CommandResult(new_state, message)


def cmd_use(state: GameState, args: list[str]) -> CommandResult:
    item_id, error = _require_item(state, args[0])
    if error:
        return error
    new_state, message = use_item(state, item_id)
    return CommandResult(new_state, message)


def cmd_sell(state: GameState, args: list[str]) -> CommandResult:
    item_id, error = _require_item(state, args[0])
    if error:
        return error
    amount = 1
    if len(args) > 1:
        try:
            amount = int(args[1])
        except ValueError:
            return CommandResult(state, "Amount must be a number.")
    if amount <= 0:
        return CommandResult(state, "Amount must be positive.")
    new_state, message = sell_item(state, item_id, amount)
    return CommandResult(new_state, message)


def cmd_rest(state: GameState, args: list[str]) -> CommandResult:
    new_state, message = rest_at_inn(state)
    return CommandResult(new_state, message)


def cmd_time(state: GameState, args: list[str]) -> CommandResult:
    return CommandResult(state, format_clock(state.minutes))


def cmd_wait(state: GameState, args: list[str]) -> CommandResult:
    hours = 1
    if args:
        try:
            hours = int(args[0])
        except ValueError:
            return CommandResult(state, "Hours must be a number.")
    if not 1 <= hours <= 8:
        return CommandResult(state, "You can wait between 1 and 8 hours.")
    if state.enemies.get(state.player.location_id):
        return CommandResult(state, "You can't wait with enemies nearby.")
    new_state = replace(state, minutes=state.minutes + hours * 60)
    return CommandResult(new_state, f"You wait {hours} hour(s). {format_clock(new_state.minutes)}")


def cmd_map(state: GameState, args: list[str]) -> CommandResult:
    return CommandResult(state, ascii_map(state))


def cmd_help(state: GameState, args: list[str]) -> CommandResult:
    return CommandResult(state, Command.help_text())


HANDLERS: Dict[Command, Handler] = {
    Command.LOOK: cmd_look,
    Command.TALK: cmd_talk,
    Command.STATUS: cmd_status,
    Command.MOVE: cmd_move,
    Command.INVENTORY: cmd_inventory,
    Command.BUY: cmd_buy,
    Command.TAKE: cmd_take,
    Command.QUESTS: cmd_quests,
    Command.ATTACK: cmd_attack,
    Command.EQUIP: cmd_equip,
    Command.UNEQUIP: cmd_unequip,
    Command.USE: cmd_use,
    Command.SELL: cmd_sell,
    Command.REST: cmd_rest,
    Command.TIME: cmd_time,
    Command.MAP: cmd_map,
    Command.WAIT: cmd_wait,
    Command.HELP: cmd_help,
}


# Minutes of game time a successful command consumes (rest/wait/death manage time themselves).
TIME_COST_MINUTES: Dict[Command, int] = {
    Command.MOVE: 30,
    Command.TALK: 10,
    Command.ATTACK: 5,
    Command.BUY: 5,
    Command.SELL: 5,
    Command.TAKE: 5,
    Command.EQUIP: 5,
    Command.USE: 5,
}


def handle_command(state: GameState, raw: str) -> CommandResult:
    parsed = Command.parse(raw)
    if parsed is None:
        return CommandResult(state=state, message="Unknown command. Type 'help'.")

    if len(parsed.args) < parsed.cmd.min_args:
        return CommandResult(state=state, message=f"Usage: {parsed.cmd.usage_line()}")

    handler = HANDLERS.get(parsed.cmd)
    if handler is None:
        return CommandResult(state=state, message="Command not implemented yet.")

    result = handler(state, parsed.args)
    if result.state.player.location_id not in result.state.visited:
        result = CommandResult(
            replace(result.state, visited=result.state.visited | {result.state.player.location_id}),
            result.message,
        )
    minutes_spent = TIME_COST_MINUTES.get(parsed.cmd, 0)
    if minutes_spent and result.state is not state:
        result = CommandResult(
            replace(result.state, minutes=result.state.minutes + minutes_spent), result.message
        )
    return result
