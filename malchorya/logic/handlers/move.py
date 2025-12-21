from core.enums import WindDirection
from logic.result import CommandResult

def handle_move(state, args) -> CommandResult:
    if not args:
        return CommandResult(state=state, message="Usage: move <north|south|east|west>")

    raw_dir = args[0].lower()
    direction = {
        "north": WindDirection.NORTH,
        "south": WindDirection.SOUTH,
        "east": WindDirection.EAST,
        "west": WindDirection.WEST,
    }.get(raw_dir)

    if direction is None:
        return CommandResult(state=state, message="Invalid direction.")

    world = state.world
    player = state.player
    loc = world.locations[player.location_id]

    next_id = loc.exits.get(direction)
    if not next_id:
        return CommandResult(state=state, message=f"No exit to the {raw_dir}.")

    new_player = type(player)(
        **{**player.__dict__, "location_id": next_id}
    )

    new_state = type(state)(
        **{**state.__dict__, "player": new_player}
    )

    next_loc = world.locations[next_id]
    return CommandResult(state=new_state, message=f"You moved to {next_loc.name}.")
