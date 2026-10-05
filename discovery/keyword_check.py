"""
Outil de vérification avant d'ajouter un sous-thème à config/markets.py.
Interroge l'autocomplete YouTube (gratuit, aucune clé API nécessaire)
pour voir quelles vraies recherches les internautes associent à un
sous-thème candidat, avant de l'utiliser dans notre pipeline.
"""

import json

import requests


def get_youtube_suggestions(query: str) -> list[str]:
    resp = requests.get(
        "https://suggestqueries.google.com/complete/search",
        params={"client": "youtube", "ds": "yt", "q": query},
        timeout=10,
    )
    text = resp.text
    start = text.find("[")
    data = json.loads(text[start:-1] if text.endswith(")") else text[start:])
    return [item[0] for item in data[1]]


if __name__ == "__main__":
    from config.markets import MARKETS

    MARKET = "history"
    candidates = MARKETS[MARKET]["topics"]

    for candidate in candidates:
        print(f"\n'{candidate}' →")
        try:
            suggestions = get_youtube_suggestions(candidate)
            for s in suggestions[:8]:
                print(f"  - {s}")
        except Exception as e:
            print(f"  [!] Erreur: {e}")