from __future__ import annotations
from dataclasses import replace, is_dataclass
from logic.result import CommandResult

def ok(state, message: str = "") -> CommandResult:
    return CommandResult(state=state, message=message)

def fail(state, message: str) -> CommandResult:
    return CommandResult(state=state, message=message)

def set_player_location(state, location_id: str):
    # עובד רק אם player/state הם dataclass
    return replace(state, player=replace(state.player, location_id=location_id))
