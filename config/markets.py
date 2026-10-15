"""
Vocabulaire initial par marché + formules de titre "incognito".

title_formulas : formules de titre plausibles pour amorcer chaque
marché, en attendant que extract_patterns.py détecte les vrais
formats émergents à partir de nos propres résultats. Volontairement
génériques et non figées — à ajuster/enrichir dès que des patterns
réels ressortent pour un marché donné.
"""

MARKETS = {
    "history": {
        "topics": [
            "ancient civilizations",
            "ancient empires",
            "lost civilizations",
            "medieval history",
            "world war 2",
            "world war 1",
            "roman empire",
            "ancient egypt",
            "history documentary",
            "forgotten history",
            "historical mysteries",
            "cold war",
            "financial history",
            "alternate history",
        ],
        "title_formulas": [
            "explained",
            "the true story of",
            "what really happened",
            "vs reality",
            "the rise and fall of",
            "the history of",
        ],
    },
    "finance": {
        "topics": [
            "personal finance",
            "stock market",
            "passive income",
            "financial independence",
            "investing basics",
            "economic collapse",
            "money mistakes",
            "credit score",
            "real estate investing",
            "side hustle",
            "debt payoff",
            "economic history",
        ],
        "title_formulas": [
            "explained",
            "the truth about",
            "why you're broke",
            "what nobody tells you about",
            "the math behind",
            "how to actually",
        ],
    },
    "military": {
        "topics": [
            "declassified military",
            "military history",
            "military history documentary",
            "cold war military",
            "military strategy explained",
            "world war 2 documentary",
            "military technology explained",
            "special forces history",
            "world war 2 documentary series",
            "most advanced military technology",
            "special forces group history",
            "uk special forces",
        ],
        "title_formulas": [
            "explained",
            "the true story of",
            "declassified",
            "what really happened",
        ],
    },
    "fitness": {
        "topics": [
            "calisthenics training",
            "home workout guide",
            "muscle building science",
            "fitness transformation story",
            "strength training basics",
            "bodyweight exercises",
        ],
        "title_formulas": [
            "explained",
            "the science of",
            "before and after",
            "the truth about",
        ],
    },
    "health": {
        "topics": [
            "nutrition science explained",
            "sleep science",
            "gut health explained",
            "longevity research",
            "medical mysteries solved",
            "human body facts",
        ],
        "title_formulas": [
            "explained",
            "the science of",
            "what nobody tells you about",
            "the truth about",
        ],
    },
    "psychology": {
        "topics": [
            "psychology facts explained",
            "cognitive bias explained",
            "human behavior science",
            "mind tricks explained",
            "psychological experiments",
        ],
        "title_formulas": [
            "explained",
            "the psychology of",
            "why you",
            "what it really means when",
        ],
    },
    "relationships": {
        "topics": [
            "relationship psychology",
            "attachment styles explained",
            "dating red flags explained",
            "breakup psychology",
        ],
        "title_formulas": [
            "explained",
            "signs that",
            "the truth about",
            "why he/she",
        ],
    },
    "true_crime": {
        "topics": [
            "unsolved murder cases",
            "true crime documentary",
            "cold case solved",
            "serial killer case files",
            "missing persons case",
        ],
        "title_formulas": [
            "the true story of",
            "solved",
            "what really happened",
            "the disappearance of",
        ],
    },
    "gaming": {
        "topics": [
            "gaming history documentary",
            "video game facts explained",
            "gaming industry secrets",
            "retro gaming history",
        ],
        "title_formulas": [
            "explained",
            "the rise and fall of",
            "the true story of",
            "what happened to",
        ],
    },
    "sports": {
        "topics": [
            "sports history documentary",
            "sports records explained",
            "athlete documentary",
            "sports science explained",
        ],
        "title_formulas": [
            "explained",
            "the true story of",
            "the rise and fall of",
            "what happened to",
        ],
    },
    "food": {
        "topics": [
            "food science explained",
            "food history documentary",
            "culinary secrets explained",
            "food industry facts",
        ],
        "title_formulas": [
            "explained",
            "the secret behind",
            "the true story of",
            "what nobody tells you about",
        ],
    },
    "travel": {
        "topics": [
            "abandoned places documentary",
            "hidden places explained",
            "travel documentary",
            "unusual destinations explained",
        ],
        "title_formulas": [
            "explained",
            "the mystery of",
            "the true story of",
            "why nobody visits",
        ],
    },
    "science": {
        "topics": [
            "science facts explained",
            "physics explained simply",
            "scientific discoveries",
            "science mysteries solved",
        ],
        "title_formulas": [
            "explained",
            "the science behind",
            "what really happens when",
            "solved",
        ],
    },
    "space": {
        "topics": [
            "space facts explained",
            "space exploration documentary",
            "astronomy explained",
            "space mysteries",
        ],
        "title_formulas": [
            "explained",
            "what really happens when",
            "the mystery of",
            "the true story of",
        ],
    },
    "technology": {
        "topics": [
            "technology explained",
            "tech history documentary",
            "how technology works",
            "future technology explained",
        ],
        "title_formulas": [
            "explained",
            "how it actually works",
            "the true story of",
            "the rise and fall of",
        ],
    },
    "ai": {
        "topics": [
            "ai explained",
            "artificial intelligence documentary",
            "ai facts explained",
            "machine learning explained simply",
        ],
        "title_formulas": [
            "explained",
            "how it actually works",
            "what nobody tells you about",
            "the truth about",
        ],
    },
    "cars": {
        "topics": [
            "car engineering explained",
            "automotive history documentary",
            "car facts explained",
            "supercar engineering",
        ],
        "title_formulas": [
            "explained",
            "how it actually works",
            "the true story of",
            "the rise and fall of",
        ],
    },
    "animals": {
        "topics": [
            "animal documentary",
            "wildlife facts explained",
            "animal behavior science",
            "extreme animal survival",
        ],
        "title_formulas": [
            "explained",
            "how they survive",
            "the true story of",
            "what really happens when",
        ],
    },
    "nature": {
        "topics": [
            "nature documentary",
            "natural phenomena explained",
            "earth science facts",
            "nature mysteries explained",
        ],
        "title_formulas": [
            "explained",
            "the mystery of",
            "how it actually works",
            "what really happens when",
        ],
    },
    "business": {
        "topics": [
            "business history documentary",
            "company success story",
            "business strategy explained",
            "startup story explained",
        ],
        "title_formulas": [
            "explained",
            "the rise and fall of",
            "the true story of",
            "what happened to",
        ],
    },
    "real_estate": {
        "topics": [
            "real estate investing explained",
            "real estate market explained",
            "property investment facts",
            "housing market documentary",
        ],
        "title_formulas": [
            "explained",
            "the truth about",
            "what nobody tells you about",
            "why you're broke",
        ],
    },
    "crypto": {
        "topics": [
            "crypto explained",
            "bitcoin documentary",
            "blockchain explained simply",
            "crypto history",
        ],
        "title_formulas": [
            "explained",
            "the truth about",
            "the rise and fall of",
            "what nobody tells you about",
        ],
    },
    "celebrities": {
        "topics": [
            "celebrity documentary",
            "celebrity net worth explained",
            "celebrity life story",
            "celebrity facts explained",
        ],
        "title_formulas": [
            "the true story of",
            "the rise and fall of",
            "what happened to",
            "the truth about",
        ],
    },
    "luxury": {
        "topics": [
            "luxury lifestyle documentary",
            "luxury brand history",
            "expensive things explained",
            "luxury industry secrets",
        ],
        "title_formulas": [
            "explained",
            "the true story of",
            "what nobody tells you about",
            "the rise and fall of",
        ],
    },
}


def build_queries(market: str) -> list[str]:
    """
    Combine topics + title formulas pour générer la liste de requêtes
    à envoyer à YouTube Data API pour un marché donné.
    """
    if market not in MARKETS:
        raise ValueError(f"Marché inconnu: {market}")

    cfg = MARKETS[market]
    queries = []

    queries.extend(cfg["topics"])

    for topic in cfg["topics"][:4]:
        for formula in cfg["title_formulas"][:3]:
            queries.append(f"{topic} {formula}")

    return queries



# --- Mots-clés supplémentaires + 3 nouveaux marchés (disasters, geopolitics, mythology) ---
from config.extra_topics import register as _register_extra  # noqa: E402

_register_extra(MARKETS)