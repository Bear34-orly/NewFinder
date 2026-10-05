"""
Étape 3bis : filtrage/priorisation par langue.

Utilise en priorité "declared_language" (defaultAudioLanguage de YouTube,
récupéré dans video_stats.py) car c'est fiable même pour des titres en
alphabet latin qui transcrivent une autre langue (ex: hindi romanisé).

Si "declared_language" est absent (créateur ne l'a pas renseigné),
on retombe sur une détection depuis le titre via langdetect, en dernier
recours seulement.
"""

from langdetect import detect, DetectorFactory, LangDetectException

DetectorFactory.seed = 0

ALLOWED_LANGUAGES = {"en", "es", "fr", "de", "ru"}

LANGUAGE_PRIORITY = {
    "en": 0,
    "es": 1,
    "fr": 2,
    "de": 3,
    "ru": 3,
}


def _normalize_lang_code(code: str) -> str:
    """ 'en-US' -> 'en', 'fr-FR' -> 'fr' """
    return code.split("-")[0].lower()


def detect_title_language(title: str) -> str | None:
    if not title or len(title.strip()) < 5:
        return None
    try:
        return detect(title)
    except LangDetectException:
        return None


def resolve_language(video: dict) -> tuple[str | None, str]:
    """
    Retourne (code_langue, source) où source est "declared" ou "title_guess".
    Priorité absolue au champ déclaré par YouTube.
    """
    declared = video.get("declared_language")
    if declared:
        return _normalize_lang_code(declared), "declared"

    guessed = detect_title_language(video.get("title", ""))
    return guessed, "title_guess"


def filter_and_prioritize_by_language(videos: list[dict]) -> list[dict]:
    """
    Ajoute "detected_language" et "language_source", exclut les langues
    hors ALLOWED_LANGUAGES, trie par priorité de langue.
    """
    tagged = []
    for v in videos:
        lang, source = resolve_language(v)
        if lang not in ALLOWED_LANGUAGES:
            continue
        tagged.append({**v, "detected_language": lang, "language_source": source})

    tagged.sort(key=lambda v: LANGUAGE_PRIORITY.get(v["detected_language"], 99))
    return tagged