from dataclasses import replace
from typing import Callable, Dict, Optional
from core.enums import Command, WindDirection
from core.items import ItemId
from core.state import GameState
from core.dialogue import DIALOGUE_BY_NPC_ID, DIALOGUE_BY_KIND
from logic.result import CommandResult

Handler = Callable[[GameState, list[str]], str]

def cmd_look(state: GameState, args: list[str]) -> CommandResult:
    loc = state.world.get_location(state.player.location_id)
    exits = ", ".join([d.value for d in loc.exits.keys()]) or "none"
    return CommandResult(state, f"{loc.name}\n{loc.description}\nExits: {exits}")

def cmd_talk(state: GameState, args: list[str]) -> CommandResult:
    npc_id = args[0].strip() if args else ""
    if not npc_id:
        return CommandResult(state=state, message="Usage: talk <npc_id>")

    npc = state.world.npcs.get(npc_id)
    if npc is None:
        return CommandResult(state=state, message="Unknown npc id.")

    if npc.location_id != state.player.location_id:
        return CommandResult(state=state, message="They are not here.")

    if npc.sentient:
        msg = DIALOGUE_BY_NPC_ID.get(npc.id, DIALOGUE_BY_KIND.get(npc.kind, "..."))
        return CommandResult(state=state, message=msg)

    return CommandResult(
        state=state,
        message="Only the rustling of birds and the buzzing of flies can be heard...",
    )

def cmd_status(state: GameState, args: list[str]) -> CommandResult:
    p = state.player
    loc = state.world.get_location(p.location_id)
    return CommandResult(state, f"{p.name} at {loc.name}.")


def parse_direction(raw: str) -> WindDirection | None:
    v = raw.lower().strip()
    for d in WindDirection:
        if d.value == v:
            return d
    return None


def cmd_inventory(state: GameState, args: list[str]) -> CommandResult:
    inv = state.player.inventory
    if inv.is_empty():
        return CommandResult(state, "Your inventory is empty.")

    lines = ["Inventory:"]
    for item_id, amount in inv.items.items():
        lines.append(f"{item_id.value}: {amount}")
    return CommandResult(state, "\n".join(lines))


def cmd_move(state: GameState, args: list[str]) -> CommandResult:
    option = args[0] if args else ""
    direction = parse_direction(option)
    if direction is None:
        return CommandResult(state=state, message="Unknown direction. Use: north/south/east/west")

    location = state.world.get_location(state.player.location_id)
    if direction not in location.exits:
        return CommandResult(state=state, message=f"You can't go '{direction.value}' from here.")

    next_location_id = location.exits[direction]
    new_player = replace(state.player, location_id=next_location_id)
    new_state = replace(state, player=new_player)

    new_location = new_state.world.get_location(new_player.location_id)
    return CommandResult(state=new_state, message=f"You move {direction.value} to {new_location.name}.")


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


def handle_command(state: GameState, raw: str) -> CommandResult:
    parsed = Command.parse(raw)
    if parsed is None:
        return CommandResult(state=state, message="Unknown command. Type 'help'.")

    if len(parsed.args) < parsed.cmd.min_args:
        return CommandResult(state=state, message=f"Usage: {parsed.cmd.usage_line()}")

    handler = HANDLERS.get(parsed.cmd)
    if handler is None:
        return CommandResult(state=state, message="Command not implemented yet.")

    return handler(state, parsed.args)

