from core.npcs import NpcKind

DIALOGUE_BY_NPC_ID: dict[str, str] = {
    "merchant_eron": "Keter for goods. Try 'buy health_potion'.",
    "lysa_wanderer": "They say Malchorya remembers every footstep.",
    "borin_guard": "Keep your weapon close. The pines are not as empty as they look.",
    "silent_one": "...",
    "elara_blacksmith": "Finest steel this side of the river. Try 'buy iron_sword' or 'buy leather_armor'.",
    "vorn_innkeeper": "Welcome to the Rusted Flagon. 'buy health_potion' if you need it.",
    "maren_priest": "The Quiet Flame asks nothing of you. Potions, though, are four keter... ask and see.",
    "oren_hermit": "Moonpetal blooms in the marsh only after dark. Mind the lurkers; they hunt by the same moon.",
    "ferryman_tol": "The river runs east, if you have coin enough.",
}

DIALOGUE_BY_KIND: dict[NpcKind, str] = {
    NpcKind.MERCHANT: "Interested in trading?",
    NpcKind.CITIZEN: "Hello, traveler.",
    NpcKind.GUARD: "Move along.",
    NpcKind.MYSTERIOUS: "...",
    NpcKind.BLACKSMITH: "What do you need forged?",
    NpcKind.INNKEEPER: "Rest your feet, traveler.",
    NpcKind.PRIEST: "Peace be with you.",
    NpcKind.HERMIT: "Hm. Visitors.",
    NpcKind.FERRYMAN: "Crossing costs keter.",
}

QUEST_OFFER: dict[str, str] = {
    "borin_errand": (
        "The forest depths hold what I need — pine cones, three of them. "
        "Bring them back and I'll make it worth your while. "
        "[Quest started: Borin's Errand]"
    ),
    "maren_moonpetal": (
        "The flame dims without moonpetal oil. The flowers grow in Blackwater Marsh, "
        "south of the crossroads, but open only at night. Bring me two. "
        "[Quest started: Flowers for the Flame]"
    ),
    "borin_wolves": (
        "Wolves have been dragging off travelers from the depths. Kill two of them "
        "and I'll pay you. Mind your health. [Quest started: Wolves at the Gate]"
    ),
    "borin_bandits": (
        "Smoke on the hill east of here. Bandits, a dozen at least once. "
        "Two are left. Clear them out. Bring potions. [Quest started: Smoke on the Hill]"
    ),
    "lysa_message": (
        "Traveler, would you carry word to Vorn at the tavern? "
        "Tell him Lysa sends her regards. He'll know what it means. "
        "[Quest started: Lysa's Message]"
    ),
    "eron_supply": (
        "I need sword stock but can't leave the dock. Go see if Elara at the forge "
        "has blades to sell, then report back. "
        "[Quest started: Eron's Inquiry]"
    ),
}

QUEST_REMINDER: dict[str, str] = {
    "maren_moonpetal": "Two moonpetals, picked in the marsh after dark. Do be careful.",
    "borin_wolves": "The wolves still hunt. Two of them, in the forest depths.",
    "borin_bandits": "The watchtower is east of the pinewood. Two bandits remain.",
    "borin_errand": "Have you gathered three pine cones yet? The forest depths lie north of the pinewood.",
    "lysa_message": "Did you speak to Vorn yet? He's at the Rusted Flagon in the town square.",
    "eron_supply": "Go speak with Elara at the forge — north of the town square.",
}

QUEST_COMPLETE: dict[str, str] = {
    "maren_moonpetal": "They are perfect. The flame will burn bright again. Thank you.",
    "borin_wolves": "The roads are safer already. Take this.",
    "borin_bandits": "You cleared the watchtower? Malchorya owes you.",
    "borin_errand": "Ah, three pine cones! Exactly what I needed.",
    "lysa_message": "Lysa's regards? I'm glad to hear it. Here, take this for your trouble.",
    "eron_supply": "Eron sent you? Good — tell him I've got blades. Here's something for the errand.",
}
