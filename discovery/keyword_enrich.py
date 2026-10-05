"""
Enrichissement automatisé des mots‑clés (topics & title_formulas)
en s’appuyant sur les suggestions de recherche YouTube.
Aucune clé API supplémentaire n’est requise.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

import requests

# ----------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------
MARKETS_FILE = Path("config/markets.py")
# Si vous voulez garder vos entrées de base, créez un fichier de surcharge
# (ex. config/markets_extended.py) et importez‑le à la place.
# Ici, on écrase directement les sections title_formulas et topics.
# ----------------------------------------------------------------------

YT_SUGGEST_URL = "https://suggestqueries.google.com/complete/search"
YT_SUGGEST_PARAMS = {
    "client": "firefox",   # YouTube utilise ce client
    "ds": "yt",
    # "hl": "fr",          # décommentez pour forcer la langue française
}

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for",
    "is", "are", "was", "were", "this", "that", "you", "your", "i", "my",
    "how", "why", "what", "with", "from", "at", "by", "it", "its", "be",
    "do", "did", "does", "can", "will", "not", "no", "yes", "if", "so",
    "just", "here", "now", "up", "out", "about", "into", "all", "as",
}

# Mots qui apparaissent souvent dans les titres et qui signalent un
# « format » plutôt que le sujet lui‑même.
FORMAT_SEEDS = {
    "explained", "secret", "secrets", "truth", "lies", "myth", "myths",
    "story", "stories", "guide", "tutorial", "how", "what", "why",
    "when", "where", "who", "versus", "vs", "before", "after",
    "rise", "fall", "history", "of", "the", "a", "an",
}

def _clean(text: str) -> str:
    """Minuscule, suppression ponctuation, espaces multiples."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def _is_likely_topic(phrase: str) -> bool:
    """Heuristique très simple : un topic contient au moins un nom
    (ici on accepte toute phrase de 2‑4 mots qui n’est pas uniquement
    composée de mots vides ou de mots de format)."""
    words = _clean(phrase).split()
    if not (2 <= len(words) <= 4):
        return False
    # Au moins un mot qui n’est ni un stopword ni un format seed
    return any(w not in STOPWORDS and w not in FORMAT_SEEDS for w in words)

def _extract_formula(phrase: str) -> str | None:
    """
    Transforme une suggestion en formule de titre, en remplaçant les
    groupes de mots qui semblent être le sujet par {X}.
    Retourne None si aucune structure détectable.
    """
    clean_phrase = _clean(phrase)
    words = clean_phrase.split()
    if len(words) < 2:
        return None

    # On remplace tout mot qui n’est ni un stopword ni un format seed
    # par un joker {X}. Cela donne des squelettes du type
    # “how {X} works”, “the truth about {X}”, …
    skeleton = []
    for w in words:
        if w in STOPWORDS or w in FORMAT_SEEDS:
            skeleton.append(w)
        else:
            skeleton.append("{X}")
    # On nettoie les doublons de joker consécutifs
    joined = " ".join(skeleton)
    joined = re.sub(r"(\{\s*X\s*\}\s*){2,}", "{X} ", joined).strip()
    # On ne garde que les squelettes contenant réellement un joker
    return joined if "{X}" in joined else None

def fetch_suggestions(seed: str, limit: int = 10) -> List[str]:
    """
    Interroge l’endpoint de suggestion YouTube pour un semence donnée.
    Retourne une liste de suggestions brutes (déjà nettoyées).
    """
    params = YT_SUGGEST_PARAMS.copy()
    params["q"] = seed
    try:
        resp = requests.get(YT_SUGGEST_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # data est généralement [[seed], [suggestion1, suggestion2, ...]]
        suggestions = data[1] if isinstance(data, list) and len(data) > 1 else []
        return [_clean(s) for s in suggestions if s][:limit]
    except Exception as e:
        print(f"[!] Erreur suggestion pour '{seed}': {e}")
        return []

def enrich_market(market_name: str, base_topics: List[str]) -> Tuple[List[str], List[str]]:
    """
    À partir d’une liste de topics de base, génère :
    - une nouvelle liste de topics (sujets fréquents)
    - une nouvelle liste de title_formulas (structures récurrentes)
    """
    all_topics = set(base_topics)
    all_formulas = set()

    for topic in base_topics:
        # 1️⃣ Recherche directe du topic (pour capter les variantes longues)
        suggs = fetch_suggestions(topic, limit=15)
        all_topics.update(suggs)

        # 2️⃣ Recherche autour de chaque mot du topic (pour élargir)
        for word in topic.split():
            if len(word) > 3:  # on n’élargit pas les mots trop courts
                suggs = fetch_suggestions(word, limit=10)
                all_topics.update(suggs)

        # 3️⃣ Génération de formules à partir des suggestions obtenues
        for phrase in list(all_topics):
            formula = _extract_formula(phrase)
            if formula:
                all_formulas.add(formula)

    # Nettoyage final
    topics_clean = sorted({t for t in all_topics if _is_likely_topic(t)})
    formulas_clean = sorted({f for f in all_formulas if f.count("{X}") >= 1})
    return topics_clean, formulas_clean

def update_markets_file(market: str, topics: List[str], formulas: List[str]):
    """
    Écrase les sections `topics` et `title_formulas` du marché donné
    dans le fichier config/markets.py.
    """
    if not MARKETS_FILE.exists():
        raise FileNotFoundError(f"Le fichier {MARKETS_FILE} est introuvable.")

    content = MARKETS_FILE.read_text(encoding="utf-8")
    lines = content.splitlines()

    # We'll rebuild the file line by line, replacing the two lists when we find them.
    inside_market = False
    inside_topics = False
    inside_formulas = False
    out_lines = []

    for line in lines:
        stripped = line.strip()

        # Detect start of market block
        if stripped.startswith(f'"{market}"':):
            inside_market = True
            out_lines.append(line)
            continue

        if inside_market:
            # Detect start of topics list
            if stripped.startswith("topics"):
                inside_topics = True
                out_lines.append("        [")
                for t in topics:
                    out_lines.append(f'            "{t}",')
                out_lines.append("        ],")
                continue
            # Detect start of title_formulas list
            if stripped.startswith("title_formulas"):
                inside_formulas = True
                out_lines.append("        [")
                for f in formulas:
                    out_lines.append(f'            "{f}",')
                out_lines.append("        ],")
                continue

            # If we are inside one of the lists, we skip until we see the closing bracket line.
            # Simpler: we just skip any line that belongs to the list until we encounter a line that ends with '],'
            # but we have already replaced the list above, so we need to skip until we exit the list.
            # We'll use a bracket counter approach.
            # However, since we already emitted the replacement, we need to skip the original list lines.
            # We'll just set a flag to skip lines until we see a line that contains ']' and not inside a nested structure.
            # For simplicity, we'll just skip lines until we see a line that starts with a closing brace '}' or a comma after the market block?
            # This is getting messy. Instead, let's adopt a different strategy: we will reconstruct the whole file using regex replacement.
            # Given the file is small, we can do regex substitution.
            # We'll break out of line-by-line processing and do regex after the loop.
            # For now, we'll just collect lines and later apply regex.
            # To avoid overcomplicating, we'll abort the line-by-line and just do regex replacement at the end.
            pass
        # If not inside market or we are inside market but not in a list we are replacing, keep line.
        out_lines.append(line)

    # Since the line-by-line approach is error-prone, we'll instead use regex to replace the lists.
    # Let's restart with regex method.

def update_markets_file_regex(market: str, topics: List[str], formulas: List[str]):
    if not MARKETS_FILE.exists():
        raise FileNotFoundError(f"Le fichier {MARKETS_FILE} est introuvable.")

    content = MARKETS_FILE.read_text(encoding="utf-8")

    # Build replacement strings
    topics_replacement = "        [\n" + "\n".join([f'            "{t}",' for t in topics]) + "\n        ]"
    formulas_replacement = "        [\n" + "\n".join([f'            "{f}",' for f in formulas]) + "\n        ]"

    # Replace topics list for the given market
    # Pattern: "market": { ... "topics": [ ... ], ... }
    # We'll use regex with DOTALL to capture inside the market block.
    import re

    # Pattern to find the market block
    market_pattern = rf'("{re.escape(market)"}\s*:\s*\{{[^}}]*)(?P<topics>"topics"\s*:\s*$$[^$$]*$$)([^}}]*)'}}'
    # However, doing nested braces regex is complex. Simpler: replace line by line but with a small state machine.
    # Given time, let's do a simple approach: we know the file structure is stable; we can replace between lines.
    # We'll read lines and when we are inside the market and see "topics": we replace until the closing ].
    # We'll implement a proper state machine.

    lines = content.splitlines()
    inside_market = False
    inside_topics = False
    inside_formulas = False
    out = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith(f'"{market}"':):
            inside_market = True
            out.append(line)
            i += 1
            continue

        if inside_market:
            if stripped.startswith("topics"):
                # Replace the whole list line(s) until we find a line that ends with '],' (closing bracket)
                out.append("        [")
                for t in topics:
                    out.append(f'            "{t}",')
                out.append("        ],")
                # Skip the original lines until we pass the closing bracket of the original list
                i += 1
                while i < len(lines):
                    if lines[i].strip().endswith('],'):
                        i += 1
                        break
                    i += 1
                continue
            if stripped.startswith("title_formulas"):
                out.append("        [")
                for f in formulas:
                    out.append(f'            "{f}",')
                out.append("        ],")
                i += 1
                while i < len(lines):
                    if lines[i].strip().endswith('],'):
                        i += 1
                        break
                    i += 1
                continue

        out.append(line)
        i += 1

    new_content = "\n".join(out)
    MARKETS_FILE.write_text(new_content, encoding="utf-8")
    print(f"[✓] {MARKETS_FILE} mis à jour pour le marché '{market}'")
    print(f"    topics      : {len(topics)} entrées")
    print(f"    title_formulas: {len(formulas)} entrées")

def main():
    # ------------------------------------------------------------------
    # 1️⃣ Charger votre configuration actuelle (pour garder les topics de base)
    # ------------------------------------------------------------------
    sys.path.append(str(Path(__file__).parent.parent))  # ajouter la racine du projet
    try:
        from config import markets
    except Exception as e:
        print(f"[!] Impossible d’importer config/markets.py : {e}")
        return

    markets_to_update = ["history", "finance"]

    for mkt in markets_to_update:
        base_topics = getattr(markets.MARKETS[mkt], "topics", [])
        if not base_topics:
            print(f"[!] Aucun topic de base trouvé pour le marché '{mkt}'. On passe.")
            continue
        print(f"\n--- Enrichissement du marché '{mkt}' ---")
        topics, formulas = enrich_market(mkt, base_topics)
        update_markets_file_regex(mkt, topics, formulas)

if __name__ == "__main__":
    main()