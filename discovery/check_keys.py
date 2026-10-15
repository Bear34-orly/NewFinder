"""
Vérifie les clés API YouTube de .env (YOUTUBE_API_KEYS).

Chaque clé fait un seul appel très léger (1 unité de quota) et le résultat est :
  OK            : la clé marche et il reste du quota
  QUOTA ÉPUISÉ  : la clé est bonne mais plus de quota aujourd'hui (revient demain)
  INVALIDE      : clé fausse, mal copiée ou restreinte
  API NON ACTIVÉE : YouTube Data API v3 n'est pas activée dans le projet de la clé
  ERREUR        : autre problème (réseau, etc.)

Les clés ne sont jamais affichées en entier (seulement les 4 derniers caractères).

Usage:
    python -m discovery.check_keys
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

TEST_URL = "https://www.googleapis.com/youtube/v3/videos"
TEST_PARAMS = {"part": "id", "id": "dQw4w9WgXcQ"}


def _load_keys() -> list[str]:
    raw = os.environ.get("YOUTUBE_API_KEYS", "")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        single = os.environ.get("YOUTUBE_API_KEY", "").strip()
        if single:
            keys = [single]
    return keys


def check_key(key: str) -> tuple[str, str]:
    try:
        resp = requests.get(TEST_URL, params={**TEST_PARAMS, "key": key}, timeout=20)
    except requests.exceptions.RequestException as e:
        return "ERREUR", type(e).__name__

    if resp.status_code == 200:
        return "OK", ""

    text = resp.text.lower()
    if resp.status_code in (403, 429) and "quota" in text:
        return "QUOTA ÉPUISÉ", ""
    if resp.status_code == 403 and ("has not been used" in text or "accessnotconfigured" in text or "disabled" in text):
        return "API NON ACTIVÉE", "active YouTube Data API v3 dans ce projet"
    if resp.status_code in (400, 403) and ("api key not valid" in text or "api_key_invalid" in text or "keyinvalid" in text):
        return "INVALIDE", ""
    if resp.status_code == 403:
        return "INVALIDE", "clé refusée (restriction ou projet suspendu ?)"
    return "ERREUR", f"code {resp.status_code}"


def main():
    keys = _load_keys()
    if not keys:
        raise SystemExit("Aucune clé trouvée : renseigne YOUTUBE_API_KEYS dans .env.")

    unique = list(dict.fromkeys(keys))
    duplicates = len(keys) - len(unique)

    print(f"{len(keys)} clé(s) dans .env" + (f" ({duplicates} en double)" if duplicates else "") + "\n")

    counts = {}
    for i, key in enumerate(keys, 1):
        status, detail = check_key(key)
        counts[status] = counts.get(status, 0) + 1
        suffix = f"  ({detail})" if detail else ""
        print(f"  n°{i:>2}  ...{key[-4:]}  {status}{suffix}")

    ok = counts.get("OK", 0)
    print("\nRésumé :")
    for status, n in counts.items():
        print(f"  {status}: {n}")
    print(f"\nClés utilisables maintenant : {ok} sur {len(keys)} (≈ {ok * 10_000:,} unités de quota par jour)")


if __name__ == "__main__":
    main()