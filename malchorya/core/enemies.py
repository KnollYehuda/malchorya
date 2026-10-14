from dataclasses import dataclass
from typing import Dict, List, Optional

from core.items import ItemId


@dataclass(frozen=True)
class EnemyDef:
    id: str
    name: str
    max_hp: int
    attack: int
    defense: int
    xp_reward: int
    keter_reward: int = 0
    loot_item: Optional[ItemId] = None


@dataclass(frozen=True)
class EnemyInstance:
    instance_id: str
    def_id: str
    hp: int


ENEMY_DEFS: Dict[str, EnemyDef] = {
    "wolf": EnemyDef(
        id="wolf",
        name="Grey Wolf",
        max_hp=14,
        attack=5,
        defense=1,
        xp_reward=8,
        loot_item=ItemId.WOLF_PELT,
    ),
    "bog_lurker": EnemyDef(
        id="bog_lurker",
        name="Bog Lurker",
        max_hp=28,
        attack=8,
        defense=2,
        xp_reward=20,
        keter_reward=6,
    ),
    "bandit": EnemyDef(
        id="bandit",
        name="Bandit",
        max_hp=22,
        attack=7,
        defense=2,
        xp_reward=15,
        keter_reward=12,
    ),
}

ENEMY_SPAWNS: Dict[str, List[str]] = {
    "forest_depths": ["wolf", "wolf"],
    "watchtower": ["bandit", "bandit"],
    "marsh": ["bog_lurker", "bog_lurker"],
}


def create_initial_enemies() -> Dict[str, List[EnemyInstance]]:
    enemies: Dict[str, List[EnemyInstance]] = {}
    for location_id, enemy_def_ids in ENEMY_SPAWNS.items():
        enemies[location_id] = [
            EnemyInstance(
                instance_id=f"{def_id}_{index + 1}",
                def_id=def_id,
                hp=ENEMY_DEFS[def_id].max_hp,
            )
            for index, def_id in enumerate(enemy_def_ids)
        ]
    return enemies
