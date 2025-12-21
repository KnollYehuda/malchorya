from dataclasses import dataclass
from core.state import GameState

@dataclass(frozen=True)
class CommandResult:
    state: GameState
    message: str = ""
