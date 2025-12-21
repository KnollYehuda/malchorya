from typing import Callable, Dict, Optional
from core.enums import Command, WindDirection
from core.items import ItemId
from core.state import GameState
from core.dialogue import DIALOGUE_BY_NPC_ID, DIALOGUE_BY_KIND

Handler = Callable[[GameState, list[str]], str]

def cmd_look(state: GameState, option: Optional[str] = None) -> str:
    npcs = []
    location = state.world.get_location(state.player.location_id)
    npcs = ", ".join(npcs) if npcs else "none"
    lines = [
        f"You are in {location.name}.",
        location.description,
    ]
    npcs_here = state.world.get_npcs_in_location(location.id)
    if npcs_here:
        lines.append(
            "You see: " + ", ".join(f"{n.name} ({n.id}). {n.name} is a {n.kind.value}" for n in npcs_here)
        )
    exits = ", ".join(sorted(direction.value for direction in location.exits.keys())) or "none"
    lines.append(f"Exits: {exits}")
    return "\n".join(lines)

def cmd_talk(state: GameState, option: Optional[str] = None) -> str:
    npc_id = option.strip()
    npc = state.world.npcs.get(npc_id)
    if npc is None:
        return "Unknown npc id."

    if npc.location_id != state.player.location_id:
        return "They are not here."

    if npc.sentient:
        return DIALOGUE_BY_NPC_ID.get(npc.id, DIALOGUE_BY_KIND.get(npc.kind, "..."))
    else:
        return "Only the rustling of birds and the buzzing of flies can be heard..."

def cmd_status(state: GameState, option: Optional[str] = None) -> str:
    return (
        f"Name: {state.player.name}\n"
        f"Race: {state.player.race.value}\n"
        f"Class: {state.player.combat_class.value}\n"
        f"Keter: {state.player.inventory.count(ItemId.KETER)}\n"
        f"Location: {state.world.get_location(state.player.location_id)}"
    )

def parse_direction(raw: str) -> WindDirection | None:
    v = raw.lower().strip()
    for d in WindDirection:
        if d.value == v:
            return d
    return None

def cmd_move(state: GameState, option: Optional[str] = None) -> str:
    direction = parse_direction(option)
    if direction is None:
        return "Unknown direction. Use: north/south/east/west"

    location = state.world.get_location(state.player.location_id)
    if direction not in location.exits:
        return f"You can't go '{direction.value}' from here."

    state.player.location_id = location.exits[direction]
    new_location = state.world.get_location(state.player.location_id)
    return f"You move {direction.value} to {new_location.name}."


def cmd_inventory(state: GameState, option: Optional[str] = None) -> str:
    inventory = state.player.inventory
    if inventory.is_empty():
        return "Your inventory is empty."

    lines = ["Inventory:"]
    for item_id, amount in inventory.items.items():
        lines.append(f"{item_id.value}: {amount}")
    return "\n".join(lines)


def cmd_help(state: GameState, option: Optional[str] = None) -> str:
    return Command.help_text()


HANDLERS: Dict[Command, Handler] = {
    Command.LOOK: cmd_look,
    Command.TALK: cmd_talk,
    Command.STATUS: cmd_status,
    Command.MOVE: cmd_move,
    Command.INVENTORY: cmd_inventory,
    Command.HELP: cmd_help,
}


def handle_command(state: GameState, raw: str) -> str:
    parsed = Command.parse(raw)
    if parsed is None:
        return "Unknown command. Type 'help'."

    if len(parsed.args) < parsed.cmd.min_args:
        return f"Usage: {parsed.cmd.usage_line()}"

    handler = HANDLERS.get(parsed.cmd)
    if handler is None:
        return "Command not implemented yet."

    return handler(state, parsed.args[-1] if parsed.args else "")

