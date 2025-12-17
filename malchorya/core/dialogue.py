from core.npcs import NpcKind

DIALOGUE_BY_NPC_ID: dict[str, str] = {
    "merchant_eron": "Keter for goods. Goods for Keter.",
    "lysa_wanderer": "They say Malchorya remembers every footstep.",
    "borin_guard": "Keep your weapon close. The pines are not as empty as they look.",
    "silent_one": "...",
}

DIALOGUE_BY_KIND: dict[NpcKind, str] = {
    NpcKind.MERCHANT: "Interested in trading?",
    NpcKind.CITIZEN: "Hello, traveler.",
    NpcKind.GUARD: "Move along.",
    NpcKind.MYSTERIOUS: "...",
}
