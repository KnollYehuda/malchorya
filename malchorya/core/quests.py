from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

from core.items import ItemId


class QuestStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


@dataclass(frozen=True)
class Quest:
    id: str
    name: str
    giver_id: str
    completion_npc_id: str
    description: str
    objective: str
    reward_keter: int
    reward_item: Optional[ItemId] = None
    reward_item_amount: int = 1
    reward_xp: int = 0
    kill_target: Optional[str] = None
    kill_count: int = 0
    required_item: Optional[ItemId] = None
    required_amount: int = 0


QUESTS: Dict[str, Quest] = {
    "borin_errand": Quest(
        id="borin_errand",
        name="Borin's Errand",
        giver_id="borin_guard",
        completion_npc_id="borin_guard",
        description="Borin Stonehand needs pine cones from the Forest Depths.",
        objective="Collect 3 pine cones and return to Borin in the Pinewood.",
        reward_keter=25,
        reward_xp=10,
        required_item=ItemId.PINE_CONE,
        required_amount=3,
    ),
    "borin_wolves": Quest(
        id="borin_wolves",
        name="Wolves at the Gate",
        giver_id="borin_guard",
        completion_npc_id="borin_guard",
        description="Wolves in the Forest Depths threaten travelers.",
        objective="Slay 2 grey wolves in the Forest Depths and report to Borin.",
        reward_keter=30,
        reward_xp=25,
        kill_target="wolf",
        kill_count=2,
    ),
    "borin_bandits": Quest(
        id="borin_bandits",
        name="Smoke on the Hill",
        giver_id="borin_guard",
        completion_npc_id="borin_guard",
        description="Bandits have occupied the Ruined Watchtower east of the Pinewood.",
        objective="Defeat 2 bandits at the Ruined Watchtower and report to Borin.",
        reward_keter=50,
        reward_xp=40,
        kill_target="bandit",
        kill_count=2,
    ),
    "maren_moonpetal": Quest(
        id="maren_moonpetal",
        name="Flowers for the Flame",
        giver_id="maren_priest",
        completion_npc_id="maren_priest",
        description="Maren needs moonpetals, which bloom in the marsh only after dark.",
        objective="Pick 2 moonpetals in Blackwater Marsh at night and bring them to Maren.",
        reward_keter=15,
        reward_item=ItemId.HEALTH_POTION,
        reward_item_amount=3,
        reward_xp=30,
        required_item=ItemId.MOONPETAL,
        required_amount=2,
    ),
    "lysa_message": Quest(
        id="lysa_message",
        name="Lysa's Message",
        giver_id="lysa_wanderer",
        completion_npc_id="vorn_innkeeper",
        description="Lysa wants you to carry her greeting to Vorn the Innkeeper.",
        objective="Speak with Vorn at the Rusted Flagon (town, south).",
        reward_keter=0,
        reward_item=ItemId.HEALTH_POTION,
        reward_item_amount=2,
    ),
    "eron_supply": Quest(
        id="eron_supply",
        name="Eron's Inquiry",
        giver_id="merchant_eron",
        completion_npc_id="elara_blacksmith",
        description="Eron wants to know if Elara the Blacksmith has sword stock.",
        objective="Speak with Elara at the forge (town, north of square).",
        reward_keter=15,
    ),
}


def quest_is_completable(quest_id: str, state) -> bool:
    quest = QUESTS[quest_id]
    if quest.required_item is not None:
        return state.player.inventory.count(quest.required_item) >= quest.required_amount
    if quest.kill_target is not None:
        return state.quest_progress.get(quest_id, 0) >= quest.kill_count
    if quest_id in ("lysa_message", "eron_supply"):
        return True
    return False
