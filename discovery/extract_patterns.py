"""
Extracteur de patterns, version affinée : squelette plus précis, qui
généralise uniquement les éléments qui varient réellement (nombres,
sujets spécifiques) en gardant la structure de phrase (verbes, mots
de liaison) intacte.

Inclut maintenant : liste de mots-bruit à exclure, utilitaire pour
retrouver quels titres contiennent un mot donné (debug), et exécution
sur plusieurs marchés à la suite.
"""

import re
from collections import Counter

from discovery.database import list_all_channels

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for",
    "is", "are", "was", "were", "this", "that", "you", "your", "i", "my",
    "how", "why", "what", "with", "from", "at", "by", "it", "its", "be",
    "do", "did", "does", "can", "will", "not", "no", "yes", "if", "so",
    "just", "here", "now", "up", "out", "about", "into", "all", "as",
}

FORMAT_WORDS = {
    "explained", "truth", "secret", "secrets", "mistake", "mistakes",
    "story", "stories", "reveal", "reveals", "revealed", "really",
    "actually", "happened", "wrong", "right", "worst", "best", "never",
    "always", "everyone", "nobody", "everything", "guide", "history",
    "vs", "versus", "before", "after", "way", "ways",
}

# Mots identifiés comme bruit de recherche (hors-sujet, faux positifs
# de matching) — à exclure des mots fréquents ET des squelettes.
# Alimenté au fil des runs quand on repère un faux positif.
NOISE_WORDS = {
    "movie", "film", "bigfoot", "fantasy",
}


def clean_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r"[^\w\s]", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def find_titles_with_word(titles: list[str], word: str) -> list[str]:
    """Utilitaire de debug : retrouve quels titres contiennent un mot donné."""
    word = word.lower()
    return [t for t in titles if word in clean_title(t).split()]


def extract_frequent_words(titles: list[str], min_length: int = 4, top_n: int = 25) -> list[tuple[str, int]]:
    counter = Counter()
    for title in titles:
        words = clean_title(title).split()
        for w in words:
            if len(w) >= min_length and w not in STOPWORDS and w not in NOISE_WORDS:
                counter[w] += 1
    return counter.most_common(top_n)


def extract_title_skeletons(titles: list[str], top_n: int = 20) -> list[tuple[str, int]]:
    counter = Counter()
    for title in titles:
        cleaned = clean_title(title)
        words = cleaned.split()
        skeleton_words = []
        for w in words:
            if w in NOISE_WORDS:
                continue  # on retire carrément le mot-bruit du squelette
            if w.isdigit():
                skeleton_words.append("{x}")
            elif w in FORMAT_WORDS:
                skeleton_words.append(w)
            elif len(w) >= 6 and w not in STOPWORDS:
                skeleton_words.append("{x}")
            else:
                skeleton_words.append(w)
        skeleton = " ".join(skeleton_words)
        if skeleton and skeleton.count("{x}") < len(skeleton_words) and "{x}" in skeleton:
            counter[skeleton] += 1
    return counter.most_common(top_n)


def analyze_market(market: str, all_channels: list[dict], show_debug_for: list[str] | None = None):
    """
    Lance l'analyse complète pour UN marché, avec affichage debug
    optionnel des titres contenant certains mots suspects.
    """
    market_channels = [c for c in all_channels if c.get("market") == market]
    titles = [c["best_video_title"] for c in market_channels if c.get("best_video_title")]

    print(f"\n{'=' * 60}")
    print(f"MARCHÉ : {market.upper()}")
    print(f"{'=' * 60}")
    print(f"{len(market_channels)} chaînes en base, {len(titles)} avec un titre exploitable.\n")

    if not titles:
        print("Aucun titre disponible pour ce marché. Rien à analyser.")
        return

    print("--- Mots fréquents (candidats 'topics') ---\n")
    for word, count in extract_frequent_words(titles):
        print(f"  {word}: {count}")

    print("\n--- Squelettes de titre fréquents (candidats 'title_formulas') ---\n")
    found_any = False
    for skeleton, count in extract_title_skeletons(titles):
        if count >= 2:
            found_any = True
            print(f"  [{count}x] {skeleton}")
    if not found_any:
        print("  (aucun squelette répété au moins 2 fois)")

    if show_debug_for:
        print("\n--- Debug : titres contenant des mots suspects ---\n")
        for word in show_debug_for:
            matches = find_titles_with_word(titles, word)
            if matches:
                print(f"  '{word}' ({len(matches)} titre(s)) :")
                for t in matches:
                    print(f"    - {t}")


if __name__ == "__main__":
    all_channels = list_all_channels()

    MARKETS_TO_ANALYZE = ["history", "finance", "military"]

    # Mots à inspecter en debug pour chaque marché, si on veut comprendre
    # d'où vient un mot suspect repéré dans un run précédent.
    DEBUG_WORDS = {
        "history": [],
        "finance": [],
        "military": ["bigfoot", "movie", "film", "fantasy"],
    }

    for market in MARKETS_TO_ANALYZE:
        analyze_market(market, all_channels, show_debug_for=DEBUG_WORDS.get(market))