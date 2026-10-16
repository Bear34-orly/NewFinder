"""
Étape 4 — Moteur de mots-clés.

Il lit les titres des vidéos fortes déjà trouvées et propose deux sortes de nouvelles recherches :
  - des expressions collées de 2-3 mots qui reviennent chez plusieurs chaînes ;
  - des mélanges : un mot-clé de départ + un mot fréquent qui apparaît avec lui dans les titres.
Celles qui ramènent de NOUVELLES chaînes validées sont gardées ("actif"), les autres
sont abandonnées ("retiré").

Cycle de vie d'un mot-clé (table keywords, colonne status) :
    test    -> en essai (relancé à chaque passe, jusqu'à RETIRE_AFTER_RUNS passes)
    active  -> a ramené au moins PROMOTE_MIN_VALIDATED nouvelle(s) chaîne(s) : relancé à chaque passe
    retired -> RETIRE_AFTER_RUNS passes sans nouvelle chaîne : ne reviendra plus
    banned  -> interdit à la main (discovery.keywords_report ban ...)

Les seeds (mots-clés de config/markets.py, translations.py, extra_topics.py) ne sont
jamais modifiés ni stockés ici.

Tout le calcul des expressions est local : aucun quota YouTube. Seules les
recherches de test en consomment (2 recherches par expression, comme les seeds).
"""

import re

from config.keyword_settings import (
    GENERIC_WORDS, MAX_ACTIVE_PER_MARKET, MIN_CHANNELS_PER_MIX, MIN_CHANNELS_PER_PARTIAL_MIX,
    MIN_CHANNELS_PER_PHRASE, MIN_CORPUS_CHANNELS, MIX_ALLOW_PARTIAL_SEED,
    MIN_CORPUS_TITLES, MIN_SEED_SHARE, NEGATIVE_SHARE_MAX, NEW_TESTS_PER_PASS, PHRASE_SIZES,
    PROMOTE_MIN_VALIDATED, REQUIRE_MARKET_WORD, RETIRE_AFTER_RUNS, STOPWORDS, TEST_QUOTA_SHARE,
)

SUPPORTED_LANGUAGES = tuple(STOPWORDS.keys())

# Ponctuation qui coupe une phrase : on n'assemble jamais deux mots séparés par elle.
_SEGMENT_SPLIT = re.compile(r"[|:;,.!?()\[\]{}\"“”«»„…—–/\\#@*&+=<>~•·]|\s-\s")
_TOKEN = re.compile(r"[^\W_]+(?:'[^\W_]+)*")


# ---------------------------------------------------------------------------
# Découpage en mots
# ---------------------------------------------------------------------------

def _segments(text: str, language: str) -> list[list]:
    """Découpe un texte en segments de mots. Un mot contenant un chiffre devient None (barrière)."""
    t = (text or "").lower().replace("’", "'").replace("‘", "'").replace("`", "'")
    if language == "fr":
        t = t.replace("'", " ")          # l'empire -> l empire
    segments = []
    for seg in _SEGMENT_SPLIT.split(t):
        tokens = []
        for m in _TOKEN.finditer(seg):
            word = m.group(0)
            tokens.append(None if any(ch.isdigit() for ch in word) else word)
        if tokens:
            segments.append(tokens)
    return segments


def _is_stop(word: str, language: str) -> bool:
    return len(word) == 1 or word in STOPWORDS.get(language, ())


def _eligible(words: tuple, language: str) -> bool:
    """Une expression valable : ni début ni fin sur un mot vide ou générique, au moins 2 mots utiles."""
    generic = GENERIC_WORDS.get(language, ())
    first, last = words[0], words[-1]
    if _is_stop(first, language) or _is_stop(last, language):
        return False
    if first in generic or last in generic:
        return False
    if len(set(words)) < len(words):
        return False
    useful = [w for w in words if not _is_stop(w, language)]
    return len(useful) >= 2


def title_phrases(title: str, language: str) -> set:
    """Toutes les expressions valables (tuples de mots) d'un titre."""
    found = set()
    for tokens in _segments(title, language):
        for n in PHRASE_SIZES:
            for i in range(len(tokens) - n + 1):
                window = tokens[i:i + n]
                if None in window:
                    continue
                words = tuple(window)
                if _eligible(words, language):
                    found.add(words)
    return found


def phrase_words(text: str, language: str) -> tuple:
    """Une requête ou une expression écrite à la main -> tuple de mots (chiffres = None)."""
    words = []
    for seg in _segments(text, language):
        words.extend(seg)
    return tuple(words)


def normalize_phrase(text: str, language: str) -> str:
    """Forme enregistrée dans la table keywords : mots en minuscules séparés par un espace."""
    return " ".join(w if w is not None else "#" for w in phrase_words(text, language))


def _contains(big: tuple, small: tuple) -> bool:
    n = len(small)
    if n == 0 or n > len(big):
        return False
    return any(big[i:i + n] == small for i in range(len(big) - n + 1))


def _overlaps(phrase: tuple, known: list) -> bool:
    """Vrai si l'expression est la même qu'une connue, ou contient / est contenue dans une de 2+ mots."""
    for k in known:
        if phrase == k:
            return True
        if len(k) >= 2 and (_contains(phrase, k) or _contains(k, phrase)):
            return True
    return False


def market_vocabulary(market: str, language: str, seeds: list[str]) -> set:
    """
    Mots du sujet d'un marché : les mots utiles de ses mots-clés de départ
    (liste de base + réserve + recherches de la semaine).
    """
    from config.extra_topics import EXTRA_TOPICS, EXTRA_TRANSLATED
    from config.markets import MARKETS
    from config.translations import TRANSLATED_TOPICS

    texts = list(seeds)
    if language == "en":
        texts += MARKETS.get(market, {}).get("topics", [])
        texts += EXTRA_TOPICS.get(market, [])
    else:
        texts += TRANSLATED_TOPICS.get(market, {}).get(language, [])
        texts += EXTRA_TRANSLATED.get(market, {}).get(language, [])

    generic = GENERIC_WORDS.get(language, ())
    words = set()
    for t in texts:
        for w in phrase_words(t, language):
            if w and not _is_stop(w, language) and w not in generic and len(w) >= 3:
                words.add(w)
    return words


# ---------------------------------------------------------------------------
# Comptage et choix des expressions
# ---------------------------------------------------------------------------

def count_phrases(rows: list[dict], language: str) -> dict:
    """rows : [{channel_id, title, views}] -> {expression: {channels, views, titles, example}}"""
    stats = {}
    for r in rows:
        title = r.get("title") or ""
        for ph in title_phrases(title, language):
            s = stats.get(ph)
            if s is None:
                s = stats[ph] = {"channels": set(), "views": 0, "titles": 0, "example": title}
            s["channels"].add(r.get("channel_id"))
            s["views"] += r.get("views") or 0
            s["titles"] += 1
    return stats


def propose_candidates(positives: list[dict], negatives: list[dict], language: str,
                       known: list, banned: list, market_words: set | None = None) -> dict:
    """
    Classe les expressions candidates.

    known        : mots-clés déjà existants (seeds + tous ceux de la table) sous forme de tuples de mots
    banned       : expressions interdites (tuples de mots)
    market_words : vocabulaire du marché (voir market_vocabulary) ; si REQUIRE_MARKET_WORD est vrai,
                   une expression doit contenir au moins un de ces mots
    Retourne {"candidates": [...], "info": {...}} — candidates triées de la meilleure à la moins bonne.
    """
    pos_channels = {r.get("channel_id") for r in positives}
    info = {"channels": len(pos_channels), "titles": len(positives),
            "too_few_channels": 0, "excluded_refused": 0, "excluded_known": 0, "excluded_banned": 0,
            "excluded_off_market": 0, "enough_data": True}
    if len(pos_channels) < MIN_CORPUS_CHANNELS or len(positives) < MIN_CORPUS_TITLES:
        info["enough_data"] = False
        return {"candidates": [], "info": info}

    pos = count_phrases(positives, language)
    neg = count_phrases(negatives, language) if negatives else {}

    candidates = []
    for ph, s in pos.items():
        n = len(s["channels"])
        if n < MIN_CHANNELS_PER_PHRASE:
            info["too_few_channels"] += 1
            continue
        neg_n = len(neg[ph]["channels"]) if ph in neg else 0
        if neg_n and neg_n / (neg_n + n) >= NEGATIVE_SHARE_MAX:
            info["excluded_refused"] += 1
            continue
        if any(_contains(ph, b) for b in banned if b):
            info["excluded_banned"] += 1
            continue
        if _overlaps(ph, known):
            info["excluded_known"] += 1
            continue
        if REQUIRE_MARKET_WORD and market_words is not None and not any(w in market_words for w in ph):
            info["excluded_off_market"] += 1
            continue
        candidates.append({"words": ph, "phrase": " ".join(ph), "channels": n,
                           "views": s["views"], "titles": s["titles"], "example": s["example"],
                           "refused_channels": neg_n})
    candidates.sort(key=lambda c: (-c["channels"], -c["views"], c["phrase"]))
    return {"candidates": candidates, "info": info}


def pick_non_overlapping(candidates: list[dict], count: int, known: list, language: str = "en") -> list[dict]:
    """
    Prend les `count` meilleures expressions qui ne se recouvrent pas entre elles :
    ni l'une dans l'autre, ni avec un mot nouveau en commun (pour tester des sujets différents).
    Deux mélanges ne partent jamais du même mot-clé de départ dans la même passe.
    """
    picked = []
    taken = list(known)
    used_words = set()
    used_seeds = set()
    for c in candidates:
        if len(picked) >= count:
            break
        if c.get("kind") != "mixed" and _overlaps(c["words"], taken):
            continue
        if c.get("kind") == "mixed" and _overlaps(c["words"], [t for t in taken if t not in known]):
            continue
        novel = c.get("novel_words")
        if novel is None:
            novel = {w for w in c["words"] if w and not _is_stop(w, language)}
        if novel & used_words:
            continue
        seed_key = c.get("seed_key")
        if seed_key is not None and seed_key in used_seeds:
            continue
        picked.append(c)
        taken.append(c["words"])
        used_words |= novel
        if seed_key is not None:
            used_seeds.add(seed_key)
    return picked


# ---------------------------------------------------------------------------
# Mélanges : mot-clé de départ + mot fréquent des titres
# ---------------------------------------------------------------------------

def _useful_words(text: str, language: str) -> list:
    generic = GENERIC_WORDS.get(language, ())
    out = []
    for seg in _segments(text, language):
        for w in seg:
            if w and not _is_stop(w, language) and w not in generic and len(w) >= 3:
                out.append(w)
    return out


def base_seeds(seeds: list[str], language: str) -> list[dict]:
    """
    Mots-clés de départ "de base" : on écarte ceux qui sont une variante d'un autre
    (ex : 'ancient civilizations explained' vient de 'ancient civilizations').
    Retourne [{"text", "words" (tuple), "core" (frozenset)}].
    """
    items = []
    seen = set()
    for sd in seeds:
        core = frozenset(_useful_words(sd, language))
        if not core or core in seen:
            continue
        seen.add(core)
        items.append({"text": sd.strip().lower(), "words": phrase_words(sd, language), "core": core})
    return [a for a in items if not any(b["core"] < a["core"] for b in items)]


def _count_mixed(rows: list[dict], bases: list[dict], language: str) -> dict:
    """
    {(index du seed, mot): {"full": {...}, "partial": {...}}}
      full    : titres qui contiennent TOUS les mots du mot-clé de départ
      partial : titres qui contiennent AU MOINS UN mot du mot-clé de départ (les "full" y sont inclus)
    chaque entrée : {channels, views, titles, example}
    """
    stats = {}

    def add(entry, r, title):
        if entry is None:
            entry = {"channels": set(), "views": 0, "titles": 0, "example": title}
        entry["channels"].add(r.get("channel_id"))
        entry["views"] += r.get("views") or 0
        entry["titles"] += 1
        return entry

    for r in rows:
        title = r.get("title") or ""
        tw = set(_useful_words(title, language))
        if not tw:
            continue
        for i, b in enumerate(bases):
            hit = b["core"] & tw
            if not hit:
                continue
            is_full = b["core"] <= tw
            for w in tw - b["core"]:
                slot = stats.setdefault((i, w), {"full": None, "partial": None})
                if is_full:
                    slot["full"] = add(slot["full"], r, title)
                if MIX_ALLOW_PARTIAL_SEED:
                    slot["partial"] = add(slot["partial"], r, title)
    return stats


def _best_mode(slot: dict | None):
    """Mode retenu pour un couple : 'full' (>= MIN_CHANNELS_PER_MIX) sinon 'partial' (>= MIN_CHANNELS_PER_PARTIAL_MIX)."""
    if not slot:
        return None
    if slot.get("full") and len(slot["full"]["channels"]) >= MIN_CHANNELS_PER_MIX:
        return "full"
    if slot.get("partial") and len(slot["partial"]["channels"]) >= MIN_CHANNELS_PER_PARTIAL_MIX:
        return "partial"
    return None


def propose_mixed(positives: list[dict], negatives: list[dict], language: str,
                  seeds: list[str], learned: list, banned: list) -> dict:
    """
    Candidats "mélangés" : un mot-clé de départ + un mot qui apparaît avec lui dans les titres.
    Un couple est retenu si :
      - des titres contenant TOUS les mots du mot-clé de départ viennent d'au moins MIN_CHANNELS_PER_MIX chaînes, ou
      - des titres contenant AU MOINS UN de ses mots viennent d'au moins MIN_CHANNELS_PER_PARTIAL_MIX chaînes
        (si MIX_ALLOW_PARTIAL_SEED).
    learned : mots-clés déjà dans la table (tuples de mots) ; banned : interdits (tuples).
    """
    info = {"mixed_too_few": 0, "mixed_refused": 0, "mixed_known": 0, "mixed_banned": 0}
    bases = base_seeds(seeds, language)
    if not bases:
        return {"candidates": [], "info": info}
    pos = _count_mixed(positives, bases, language)
    neg = _count_mixed(negatives, bases, language) if negatives else {}
    seed_words = {phrase_words(sd, language) for sd in seeds}
    all_core = set().union(*(b["core"] for b in bases))     # mots déjà présents dans un mot-clé de départ

    candidates = []
    for key, slot in pos.items():
        i, w = key
        if w in all_core:                                    # éviter 'ancient egypt civilizations'
            continue
        mode = _best_mode(slot)
        if mode is None:
            info["mixed_too_few"] += 1
            continue
        st = slot[mode]
        n = len(st["channels"])
        neg_slot = neg.get(key)
        neg_n = len(neg_slot[mode]["channels"]) if neg_slot and neg_slot.get(mode) else 0
        if neg_n and neg_n / (neg_n + n) >= NEGATIVE_SHARE_MAX:
            info["mixed_refused"] += 1
            continue
        b = bases[i]
        words = b["words"] + (w,)
        if words in seed_words or _overlaps(words, learned):
            info["mixed_known"] += 1
            continue
        if any(_contains(words, bb) for bb in banned if bb):
            info["mixed_banned"] += 1
            continue
        candidates.append({"words": words, "phrase": f"{b['text']} {w}", "channels": n,
                           "views": st["views"], "titles": st["titles"], "example": st["example"],
                           "refused_channels": neg_n, "kind": "mixed", "mix_mode": mode,
                           "novel_words": {w}, "seed_key": i})
    candidates.sort(key=lambda c: (-c["channels"], c["mix_mode"] != "full", -c["views"], c["phrase"]))
    return {"candidates": candidates, "info": info}


def propose_all(positives: list[dict], negatives: list[dict], language: str, seeds: list[str],
                learned: list, banned: list, market_words: set | None = None) -> dict:
    """
    Expressions collées (propose_candidates) et mélanges (propose_mixed), en alternance :
    meilleure expression, meilleur mélange, deuxième expression, deuxième mélange...
    """
    known = [phrase_words(s, language) for s in seeds] + list(learned)
    res = propose_candidates(positives, negatives, language, known, banned, market_words)
    info = dict(res["info"])
    info.update({"mixed_too_few": 0, "mixed_refused": 0, "mixed_known": 0, "mixed_banned": 0})
    if not info["enough_data"]:
        return {"candidates": [], "info": info}
    mixed = propose_mixed(positives, negatives, language, seeds, learned, banned)
    info.update(mixed["info"])
    phrases, mixes = res["candidates"], mixed["candidates"]
    merged = []
    for k in range(max(len(phrases), len(mixes))):
        if k < len(phrases):
            merged.append(phrases[k])
        if k < len(mixes):
            merged.append(mixes[k])
    return {"candidates": merged, "info": info}


# ---------------------------------------------------------------------------
# Plan d'une passe
# ---------------------------------------------------------------------------

def slot_budget(n_seed: int) -> dict:
    """
    Nombre de places pour les mots-clés appris, selon le nombre de seeds du marché.
      test_slots   : recherches de test (plafond TEST_QUOTA_SHARE du total, 1 minimum, NEW_TESTS_PER_PASS maximum)
      active_slots : mots-clés actifs relancés (les seeds restent au moins MIN_SEED_SHARE du total)
    """
    share = TEST_QUOTA_SHARE
    test_slots = int(n_seed * share / (1 - share))
    test_slots = max(1, min(NEW_TESTS_PER_PASS, test_slots))
    max_learned = int(n_seed * (1 - MIN_SEED_SHARE) / MIN_SEED_SHARE)
    active_slots = max(0, min(MAX_ACTIVE_PER_MARKET, max_learned - test_slots))
    return {"test_slots": test_slots, "active_slots": active_slots}


def _yield_of(row: dict) -> float:
    return (row.get("validated_found") or 0) / max(row.get("times_run") or 0, 1)


def plan_learned_queries(market: str, language: str, seeds: list[str]) -> dict:
    """
    Choisit les mots-clés appris à ajouter aux seeds pour cette passe.

    Retourne {"queries": [...], "active": [...], "tests": [...], "new": [...], "info": {...}}.
    Écrit dans la table keywords les NOUVEAUX mots-clés mis en test.
    """
    from discovery.database import add_keyword, list_keywords, load_keyword_corpus

    result = {"queries": [], "active": [], "tests": [], "new": [], "info": None}
    if language not in SUPPORTED_LANGUAGES:
        return result

    rows = list_keywords(market, language)
    budget = slot_budget(len(seeds))

    # Mots-clés actifs : les plus rentables d'abord, puis les moins récemment lancés
    actives = [r for r in rows if r["status"] == "active"]
    actives.sort(key=lambda r: (-_yield_of(r), r.get("last_run_at") or ""))
    actives = actives[:budget["active_slots"]]

    # Mots-clés en essai : les plus anciens d'abord
    in_test = [r for r in rows if r["status"] == "test"]
    in_test.sort(key=lambda r: r.get("created_at") or "")
    in_test = in_test[:budget["test_slots"]]

    free = budget["test_slots"] - len(in_test)
    new_count = min(NEW_TESTS_PER_PASS, free)

    new_rows = []
    if new_count > 0:
        learned = [phrase_words(r["query"], language) for r in rows]
        known = [phrase_words(s, language) for s in seeds] + learned
        banned = [phrase_words(r["query"], language) for r in rows if r["status"] == "banned"]
        positives, negatives = load_keyword_corpus(market, language)
        vocab = market_vocabulary(market, language, seeds)
        proposal = propose_all(positives, negatives, language, seeds, learned, banned, vocab)
        result["info"] = proposal["info"]
        for c in pick_non_overlapping(proposal["candidates"], new_count, known, language):
            if add_keyword(market, language, c["phrase"], status="test", source=c.get("kind", "learned")):
                new_rows.append({"query": c["phrase"], "status": "test", "times_run": 0,
                                 "channels_found": 0, "validated_found": 0,
                                 "channels": c["channels"], "example": c["example"]})

    result["active"] = actives
    result["tests"] = in_test
    result["new"] = new_rows
    seen = set()
    for r in actives + in_test + new_rows:
        q = r["query"]
        if q not in seen:
            seen.add(q)
            result["queries"].append(q)
    return result


# ---------------------------------------------------------------------------
# Jugement d'une passe
# ---------------------------------------------------------------------------

def _sources(channel: dict) -> set:
    """Recherches qui ont trouvé la meilleure vidéo d'une chaîne (query_source : 'a, b, c')."""
    return {s.strip().lower() for s in (channel.get("query_source") or "").split(", ") if s.strip()}


def decide_status(status: str, times_run: int, validated_total: int) -> str:
    """Nouveau statut d'un mot-clé après une passe (times_run et validated_total incluent cette passe)."""
    if status == "test":
        if validated_total >= PROMOTE_MIN_VALIDATED:
            return "active"
        if times_run >= RETIRE_AFTER_RUNS:
            return "retired"
    return status


def record_pass_results(market: str, language: str, plan: dict, seeds: list[str],
                        candidates: list[dict], validated: list[dict], known_before: set) -> list[dict]:
    """
    Met à jour les mots-clés utilisés pendant une passe terminée normalement.

    candidates   : chaînes trouvées par la recherche (<= 100K abonnés), avec leur query_source
    validated    : chaînes validées de la passe
    known_before : identifiants de chaînes déjà en base AVANT l'enregistrement de la passe

    Une chaîne compte comme "nouvelle chaîne validée" d'un mot-clé si elle est validée, absente de
    la base avant la passe, ET n'a été trouvée par aucun seed (sinon le mot-clé n'a rien apporté).
    """
    from discovery.database import record_keyword_run

    seed_set = {s.strip().lower() for s in seeds}
    summary = []
    for kw in plan["active"] + plan["tests"] + plan["new"]:
        q = kw["query"].lower()
        found = [c for c in candidates if q in _sources(c)]
        fresh = [v for v in validated
                 if q in _sources(v) and v["channel_id"] not in known_before and not (_sources(v) & seed_set)]
        times_run = (kw.get("times_run") or 0) + 1
        validated_total = (kw.get("validated_found") or 0) + len(fresh)
        old_status = kw["status"]
        new_status = decide_status(old_status, times_run, validated_total)
        record_keyword_run(market, language, kw["query"], len(found), len(fresh), new_status)
        summary.append({"query": kw["query"], "found": len(found), "fresh": len(fresh),
                        "old_status": old_status, "new_status": new_status, "times_run": times_run})
    return summary