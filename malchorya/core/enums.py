from enum import Enum
from dataclasses import dataclass


class Race(Enum):
    HUMAN = "human"
    ELF = "elf"
    DWARF = "dwarf"
    ORC = "orc"


class CombatClass(Enum):
    MAGE = "mage"
    ASSASSIN = "assassin"
    KNIGHT = "knight"


class WindDirection(Enum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"


@dataclass(frozen=True)
class ParsedCommand:
    cmd: "Command"
    args: list[str]


class Command(Enum):
    _ignore_ = ("_ParsedCommand",)
    LOOK = ("look", 0, "")
    TALK = ("talk", 0, "")
    STATUS = ("status", 0, "")
    MOVE = ("move", 1, "<direction>")
    INVENTORY = ("inventory", 0, "")
    BUY = ("buy", 1, "<item_id> [amount]")
    TAKE = ("take", 1, "<item_id>")
    QUESTS = ("quests", 0, "")
    ATTACK = ("attack", 0, "[enemy_id]")
    EQUIP = ("equip", 1, "<item_id>")
    UNEQUIP = ("unequip", 1, "<weapon|armor>")
    USE = ("use", 1, "<item_id>")
    SELL = ("sell", 1, "<item_id> [amount]")
    REST = ("rest", 0, "")
    TIME = ("time", 0, "")
    WAIT = ("wait", 0, "[hours]")
    HELP = ("help", 0, "")

    def __init__(self, value: str, min_args: int, usage_suffix: str):
        self._value_ = value
        self.min_args = min_args
        self.usage_suffix = usage_suffix

    @classmethod
    def parse(cls, raw: str) -> ParsedCommand | None:
        parts = raw.strip().split()
        if not parts:
            return None

        name = parts[0].lower()
        for cmd in cls:
            if cmd.value == name:
                return ParsedCommand(cmd=cmd, args=parts[1:])
        return None

    @classmethod
    def help_text(cls) -> str:
        lines: list[str] = ["Commands:"]
        for cmd in cls:
            suffix = f" {cmd.usage_suffix}" if cmd.usage_suffix else ""
            lines.append(f"  {cmd.value}{suffix}")
        lines.append("  quit")
        return "\n".join(lines)

    def usage_line(self) -> str:
        suffix = f" {self.usage_suffix}" if self.usage_suffix else ""
        return f"{self.value}{suffix}"
