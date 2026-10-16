"""
Filtre faceless v2 — partie A : score de texte multilingue (en, es, fr, de, ru).

Deux niveaux, tous deux gratuits (aucun appel API) :

1) pre_filter_faceless(videos)  -> AVANT l'analyse d'activité.
   Écarte les cas évidents : un signal dans le titre de la meilleure vidéo
   ou dans le nom de la chaîne, dans la langue détectée de la chaîne.

2) text_face_score(...)         -> APRÈS l'analyse d'activité.
   Calcule la part des titres de la chaîne qui contiennent un signal.
   Verdict : "ok" | "doubtful" | "face".

La comparaison se fait sur des MOTS ENTIERS, après normalisation.
"""

import re
import unicodedata

from config.faceless_signals import (
    SIGNALS, PATTERN_SIGNALS, MIN_TITLES_TO_JUDGE, DOUBTFUL_RATIO, FACE_RATIO,
)


def normalize(text: str) -> str:
    """Minuscules, sans accents, ё->е, apostrophes droites, espaces simples."""
    if not text:
        return ""
    text = text.casefold()
    text = text.replace("’", "'").replace("‘", "'").replace("`", "'")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = unicodedata.normalize("NFC", text)
    return " ".join(text.split())


def _compile(signals: list[str]):
    parts = [re.escape(normalize(s)) for s in signals if s.strip()]
    if not parts:
        return None
    # Mots entiers : ni lettre/chiffre juste avant, ni juste après.
    return re.compile(r"(?<!\w)(?:" + "|".join(parts) + r")(?!\w)")


_PATTERNS = {lang: _compile(words) for lang, words in SIGNALS.items()}
_SHAPE_PATTERNS = [(name, re.compile(rx)) for name, rx in PATTERN_SIGNALS]


def find_signal(text: str, language: str | None) -> str | None:
    """Retourne le premier signal trouvé dans le texte, ou None.
    Langue inconnue ou non gérée : aucun jugement (None)."""
    pattern = _PATTERNS.get((language or "").split("-")[0].lower())
    if pattern is None:
        return None
    norm = normalize(text)
    m = pattern.search(norm)
    if m:
        return m.group(0)
    for name, rx in _SHAPE_PATTERNS:
        if rx.search(norm):
            return name
    return None


def looks_non_faceless(video: dict) -> bool:
    """Signal dans le titre de la meilleure vidéo ou le nom de la chaîne."""
    lang = video.get("detected_language")
    return (find_signal(video.get("title", ""), lang) is not None
            or find_signal(video.get("channel_title", ""), lang) is not None)


def get_thumbnail_url(video_id: str) -> str:
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"


def pre_filter_faceless(videos: list[dict]) -> list[dict]:
    """Écarte les cas évidents, ajoute l'URL de miniature aux survivants."""
    survivors = []
    excluded = 0
    for v in videos:
        if looks_non_faceless(v):
            excluded += 1
            continue
        survivors.append({**v, "thumbnail_url": get_thumbnail_url(v["video_id"])})
    print(f"  Filtre texte multilingue : {excluded} exclues, {len(survivors)} restantes.")
    return survivors


def text_face_score(titles: list[str], channel_title: str, language: str | None) -> dict:
    """
    Part des titres de la chaîne qui contiennent un signal "visage".

    Retourne {"ratio", "hits", "total", "examples", "verdict"}.
    Moins de MIN_TITLES_TO_JUDGE titres : verdict "ok" (pas assez de données).
    """
    seen = set()
    all_titles = []
    for t in list(titles) + [channel_title]:
        key = normalize(t or "")
        if key and key not in seen:
            seen.add(key)
            all_titles.append(t)

    hits = []
    for t in all_titles:
        sig = find_signal(t, language)
        if sig:
            hits.append((t, sig))

    total = len(all_titles)
    ratio = len(hits) / total if total else 0.0

    if total < MIN_TITLES_TO_JUDGE:
        verdict = "ok"
    elif ratio >= FACE_RATIO:
        verdict = "face"
    elif ratio >= DOUBTFUL_RATIO:
        verdict = "doubtful"
    else:
        verdict = "ok"

    return {
        "ratio": round(ratio, 3),
        "hits": len(hits),
        "total": total,
        "examples": [f"{sig} <- {t[:60]}" for t, sig in hits[:3]],
        "verdict": verdict,
    }


def score_channel_result(result: dict) -> dict:
    """Applique text_face_score à un résultat de validate_channel_activity."""
    titles = [v.get("title", "") for v in result.get("strong_videos", [])]
    titles.append(result.get("title", ""))  # meilleure vidéo trouvée par la recherche
    return text_face_score(titles, result.get("channel_title", ""),
                           result.get("detected_language"))