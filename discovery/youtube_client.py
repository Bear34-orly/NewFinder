"""
Client YouTube avec rotation automatique des clés API.

Les clés sont lues dans YOUTUBE_API_KEYS (séparées par des virgules).
Quand une clé renvoie une erreur de quota, la suivante prend le relais.
Quand toutes sont épuisées, QuotaExhaustedError est levée.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()


class QuotaExhaustedError(Exception):
    """Toutes les clés API ont atteint leur quota."""


def _load_keys() -> list[str]:
    raw = os.environ.get("YOUTUBE_API_KEYS", "")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        single = os.environ.get("YOUTUBE_API_KEY", "").strip()
        if single:
            keys = [single]
    return keys


_KEYS = _load_keys()
_exhausted: set[int] = set()
_current = 0


def has_keys() -> bool:
    return len(_KEYS) > 0


def key_count() -> int:
    return len(_KEYS)


def _is_quota_error(resp: requests.Response) -> bool:
    if resp.status_code == 429:
        return True
    if resp.status_code == 403:
        return "quota" in resp.text.lower()
    return False


def youtube_get(url: str, params: dict, timeout: int = 20) -> requests.Response:
    """
    GET vers YouTube Data API. Le paramètre "key" est géré ici :
    toute valeur passée dans params est remplacée par la clé active.
    """
    global _current

    if not _KEYS:
        raise RuntimeError("Aucune clé API trouvée (YOUTUBE_API_KEYS ou YOUTUBE_API_KEY dans .env).")

    while True:
        if len(_exhausted) >= len(_KEYS):
            raise QuotaExhaustedError("Toutes les clés API sont épuisées.")

        key = _KEYS[_current]
        resp = requests.get(url, params={**params, "key": key}, timeout=timeout)

        if _is_quota_error(resp):
            _exhausted.add(_current)
            print(f"  [!] Clé n°{_current + 1} épuisée ({len(_exhausted)}/{len(_KEYS)} épuisées).")
            for step in range(1, len(_KEYS) + 1):
                idx = (_current + step) % len(_KEYS)
                if idx not in _exhausted:
                    _current = idx
                    print(f"  -> passage à la clé n°{_current + 1}")
                    break
            continue

        return resp