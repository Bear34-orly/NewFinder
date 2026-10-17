"""
Radar : découverte de chaînes par les vidéos fortes des 60 derniers jours, SANS mot-clé.

Le radar explore YouTube catégorie par catégorie, par petites tranches de dates ("cases"),
dans l'ordre des vues décroissantes, et descend tant que les vidéos ont encore au moins
MIN_VIEWS vues. Il se souvient des cases déjà explorées (table radar_cells) : chaque passage
reprend là où le précédent s'est arrêté (limite de quota), puis revisite les cases récentes
(les vues continuent de monter).

Les chaînes trouvées passent par les MÊMES critères que la découverte habituelle
(<= 100K abonnés, langue, faceless, activité, vidéos fortes), plus une règle : une chaîne est
rejetée si elle a une vidéo >= MIN_VIEWS vues publiée il y a plus de MAX_STRONG_AGE_DAYS jours.

Les chaînes retenues sont classées dans un marché (ou "radar" si on ne sait pas), enregistrées
avec leurs titres, et le moteur de mots-clés en tire des mots-clés "radar" (piste séparée).

Usage :
    python -m discovery.radar                  (un passage, budget de recherche = SEARCH_BUDGET_UNITS)
    python -m discovery.radar --budget 3000    (budget de recherche plus petit pour ce passage)
    python -m discovery.radar --dry-run        (montre le plan sans rien appeler ni enregistrer)
    python -m discovery.radar --status         (état de la carte : cases terminées, ouvertes...)
    python -m discovery.radar --reclassify     (range les chaînes restées dans 'radar' dans un vrai marché)
    python -m discovery.radar --reclassify-all (revoit aussi les chaînes déjà rangées)
"""

import argparse
import math
import time
from collections import Counter, deque
from datetime import date, datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

from config import radar_settings as cfg
from discovery.youtube_client import QuotaExhaustedError, has_keys, key_count, youtube_get

load_dotenv()

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
CATEGORIES_URL = "https://www.googleapis.com/youtube/v3/videoCategories"
SEARCH_COST = 100

ANCHOR = date(2024, 1, 1)           # les tranches sont alignées sur cette date : elles ne bougent jamais d'un jour à l'autre

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 3
REQUEST_TIMEOUT = 20
REQUEST_TIMEOUT_MIN = 30   # délai minimum accordé à Google pour répondre (secondes)


# ---------------------------------------------------------------------------
# Appels réseau
# ---------------------------------------------------------------------------

_COUNTER = None          # compteur de quota du passage en cours (voir run)


def _api_get(url: str, params: dict):
    if _COUNTER is not None:
        _COUNTER.add(url)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return youtube_get(url, params, timeout=REQUEST_TIMEOUT)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f"    [!] Erreur réseau (tentative {attempt}/{MAX_RETRIES}): {type(e).__name__}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
    return None


def _rfc3339(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _midnight(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


class UnitCounter:
    """Compte les appels (et le quota) de ce passage."""

    def __init__(self):
        self.calls = Counter()

    def add(self, url: str):
        self.calls[url.rsplit("/", 1)[-1]] += 1

    @property
    def units(self) -> int:
        return sum(n * (SEARCH_COST if name == "search" else 1) for name, n in self.calls.items())

    @property
    def search_units(self) -> int:
        return self.calls.get("search", 0) * SEARCH_COST


# ---------------------------------------------------------------------------
# Cases (catégorie + durée + tranche de dates)
# ---------------------------------------------------------------------------

def build_slices(today: date) -> list:
    """Tranches [début, fin[ alignées sur ANCHOR qui couvrent les WINDOW_DAYS derniers jours."""
    first = today - timedelta(days=cfg.WINDOW_DAYS)
    idx = (first - ANCHOR).days // cfg.SLICE_DAYS
    slices = []
    while True:
        start = ANCHOR + timedelta(days=idx * cfg.SLICE_DAYS)
        if start > today:
            break
        slices.append((start, start + timedelta(days=cfg.SLICE_DAYS)))
        idx += 1
    return slices


def cell_key(category: str, duration: str, start, end) -> tuple:
    return (str(category), duration, str(start), str(end))


def merge_cells(saved: list, slices: list, categories: list) -> tuple:
    """
    Fusionne les cases enregistrées et les cases attendues.
    Retourne ({clé: case}, [cases nouvelles à créer]).
    """
    cells = {}
    for c in saved:
        cells[cell_key(c["category"], c["duration"], c["slice_start"], c["slice_end"])] = dict(c)
    new = []
    for (start, end) in slices:
        for cat in categories:
            for dur in cfg.DURATIONS:
                key = cell_key(cat, dur, start, end)
                if key not in cells:
                    cells[key] = {"category": str(cat), "duration": dur, "slice_start": str(start),
                                  "slice_end": str(end), "state": "open", "pages_done": 0, "page_token": None,
                                  "videos_seen": 0, "videos_qualifying": 0, "created_at": None,
                                  "finished_at": None, "last_run_at": None}
                    new.append(cells[key])
    return cells, new


def _parse_iso(value):
    if not value:
        return None
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def plan_work(cells: dict, now: datetime, categories: list) -> list:
    """
    Ordre de travail : 1) cases commencées, 2) cases jamais explorées (tranches récentes d'abord),
    3) revisites des cases récentes terminées depuis plus de RECHECK_AFTER_DAYS.
    """
    window_start = (now - timedelta(days=cfg.WINDOW_DAYS)).date()
    recent_limit = (now - timedelta(days=cfg.RECHECK_YOUNGER_THAN_DAYS)).date()
    recheck_limit = now - timedelta(days=cfg.RECHECK_AFTER_DAYS)
    cat_order = {str(c): i for i, c in enumerate(categories)}
    dur_order = {d: i for i, d in enumerate(cfg.DURATIONS)}

    opened, rechecks = [], []
    for c in cells.values():
        if c["category"] not in cat_order:
            continue
        end = date.fromisoformat(c["slice_end"])
        if end <= window_start:
            continue
        if c["state"] == "open":
            opened.append(c)
        elif c["state"] == "done":
            finished = _parse_iso(c.get("finished_at"))
            if end > recent_limit and finished is not None and finished <= recheck_limit:
                rechecks.append(c)

    opened.sort(key=lambda c: (0 if (c["pages_done"] or 0) > 0 else 1,
                               -date.fromisoformat(c["slice_start"]).toordinal(),
                               cat_order[c["category"]], dur_order.get(c["duration"], 9)))
    rechecks.sort(key=lambda c: c.get("finished_at") or "")
    return opened + rechecks


# ---------------------------------------------------------------------------
# Catégories officielles
# ---------------------------------------------------------------------------

def valid_categories() -> list:
    """Catégories de cfg.CATEGORIES reconnues par YouTube (liste officielle, 1 unité)."""
    wanted = [str(c) for c in cfg.CATEGORIES]
    resp = _api_get(CATEGORIES_URL, {"part": "snippet", "regionCode": "US"})
    if resp is None or resp.status_code != 200:
        print("  (liste officielle des catégories indisponible : on garde celles du fichier de réglages)")
        return wanted
    assignable = {item["id"] for item in resp.json().get("items", [])
                  if item.get("snippet", {}).get("assignable", True)}
    missing = [c for c in wanted if c not in assignable]
    if missing:
        print("  Catégories ignorées (inconnues de YouTube) : " + ", ".join(f"{c} ({cfg.CATEGORIES[c]})" for c in missing))
    return [c for c in wanted if c in assignable]


# ---------------------------------------------------------------------------
# Exploration d'une case
# ---------------------------------------------------------------------------

_PENDING = None          # cases à enregistrer à la FIN du passage (voir run) ; None = on écrit tout de suite


def _save_cell(cell: dict, dry: bool = False):
    """
    Pendant un passage, les cases ne sont pas écrites tout de suite : elles sont gardées en mémoire et
    enregistrées seulement quand leurs vidéos ont été traitées. Si le passage plante, aucune case n'est
    marquée terminée et on peut simplement relancer, sans perdre de chaînes.
    """
    if dry:
        return
    if _PENDING is not None:
        _PENDING[cell_key(cell["category"], cell["duration"], cell["slice_start"], cell["slice_end"])] = dict(cell)
        return
    from discovery.database import radar_save_cell
    radar_save_cell(cell)


def _flush_cells() -> int:
    """Écrit en base les cases gardées en mémoire. Retourne leur nombre."""
    from discovery.database import radar_save_cell

    n = 0
    if _PENDING:
        for cell in _PENDING.values():
            radar_save_cell(cell)
            n += 1
        _PENDING.clear()
    return n


def _with_retries(func, url, params, timeout):
    """Appelle youtube_get en réessayant si le réseau ne répond pas (délai dépassé, connexion coupée)."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return func(url, params, timeout=max(timeout, REQUEST_TIMEOUT_MIN))
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt == MAX_RETRIES:
                raise
            print(f"    [!] Réseau lent ({type(e).__name__}), nouvel essai {attempt + 1}/{MAX_RETRIES}...")
            time.sleep(RETRY_DELAY_SECONDS)


def explore_cell(cell: dict, now: datetime, budget: dict, collected: dict, stats: dict, queue: deque, dry: bool = False) -> str:
    """
    Explore une case page par page. Retourne l'état : 'done', 'split', 'open' (budget épuisé) ou 'error'.
    collected : {video_id: vidéo qualifiante}. stats : compteurs de l'entonnoir.
    """
    import discovery.video_stats as vs

    start_d = date.fromisoformat(cell["slice_start"])
    end_d = date.fromisoformat(cell["slice_end"])
    after = max(_midnight(start_d), now - timedelta(days=cfg.WINDOW_DAYS))
    before = min(_midnight(end_d), now)
    if after >= before:
        cell.update(state="done", finished_at=now.isoformat(), page_token=None)
        _save_cell(cell, dry)
        return "done"

    if cell["state"] == "done":                      # revisite : on repart de zéro
        cell.update(state="open", pages_done=0, page_token=None, videos_seen=0, videos_qualifying=0)

    while True:
        if budget["calls_left"] <= 0:
            cell["last_run_at"] = now.isoformat()
            _save_cell(cell, dry)
            return "open"

        params = {
            "part": "snippet", "type": "video", "order": "viewCount",
            "publishedAfter": _rfc3339(after), "publishedBefore": _rfc3339(before),
            "videoCategoryId": cell["category"], "videoDuration": cell["duration"],
            "relevanceLanguage": cfg.LANGUAGE, "safeSearch": "moderate", "maxResults": 50,
        }
        if cell.get("page_token"):
            params["pageToken"] = cell["page_token"]

        resp = _api_get(SEARCH_URL, params)
        budget["calls_left"] -= 1
        budget["calls_used"] += 1
        stats["pages"] += 1

        if resp is None:
            print("    [!] Réseau indisponible : case laissée ouverte.")
            _save_cell(cell, dry)
            return "error"
        if resp.status_code != 200:
            if cell.get("page_token"):
                print(f"    [!] Page refusée ({resp.status_code}) : la case recommencera à la page 1.")
                cell.update(page_token=None, pages_done=0, videos_seen=0, videos_qualifying=0)
            else:
                print(f"    [!] Erreur API ({resp.status_code}) : {resp.text[:150]}")
            _save_cell(cell, dry)
            return "error"

        data = resp.json()
        items = data.get("items", [])
        token = data.get("nextPageToken")

        rows = {}
        for it in items:
            vid = it.get("id", {}).get("videoId")
            if not vid:
                continue
            sn = it.get("snippet", {})
            rows[vid] = {"video_id": vid, "title": sn.get("title"), "channel_id": sn.get("channelId"),
                         "channel_title": sn.get("channelTitle"), "published_at": sn.get("publishedAt"),
                         "query_source": "radar", "category": cell["category"]}

        views_by_id = vs.get_video_stats(list(rows.keys()), "") if rows else {}
        page_views = []
        qualifying = 0
        for vid, row in rows.items():
            st = views_by_id.get(vid)
            if not st:
                continue
            page_views.append(st["view_count"])
            if st["view_count"] >= cfg.MIN_VIEWS and vid not in collected:
                collected[vid] = {**row, **st}
                qualifying += 1
        page_min = min(page_views) if page_views else 0

        cell["pages_done"] = (cell.get("pages_done") or 0) + 1
        cell["videos_seen"] = (cell.get("videos_seen") or 0) + len(rows)
        cell["videos_qualifying"] = (cell.get("videos_qualifying") or 0) + qualifying
        cell["page_token"] = token
        cell["last_run_at"] = now.isoformat()

        if not token or page_min < cfg.MIN_VIEWS:
            cell.update(state="done", finished_at=now.isoformat(), page_token=None)
            _save_cell(cell, dry)
            stats["cells_done"] += 1
            return "done"

        if cell["pages_done"] >= cfg.MAX_PAGES_PER_CELL:
            length = (end_d - start_d).days
            if length > cfg.MIN_SLICE_DAYS:
                mid = start_d + timedelta(days=max(1, length // 2))
                children = []
                for (a, b) in ((start_d, mid), (mid, end_d)):
                    child = {"category": cell["category"], "duration": cell["duration"],
                             "slice_start": str(a), "slice_end": str(b), "state": "open", "pages_done": 0,
                             "page_token": None, "videos_seen": 0, "videos_qualifying": 0,
                             "created_at": None, "finished_at": None, "last_run_at": None}
                    _save_cell(child, dry)
                    children.append(child)
                cell.update(state="split", page_token=None, finished_at=now.isoformat())
                _save_cell(cell, dry)
                for child in reversed(children):
                    queue.appendleft(child)
                stats["cells_split"] += 1
                return "split"
            cell.update(state="done", finished_at=now.isoformat(), page_token=None)
            _save_cell(cell, dry)
            stats["cells_done"] += 1
            stats["cells_saturated"] += 1
            return "done"

        _save_cell(cell, dry)           # on continue avec la page suivante (ou on reprendra demain)


# ---------------------------------------------------------------------------
# Marché d'une chaîne
# ---------------------------------------------------------------------------

_OFF_TARGET_RE = None


def is_off_target(*texts) -> bool:
    """Vrai si un des textes contient un mot ou une expression de musique / enfants (voir radar_settings)."""
    global _OFF_TARGET_RE
    import re

    if _OFF_TARGET_RE is None:
        parts = [re.escape(w) for w in cfg.OFF_TARGET_WORDS] + [re.escape(p) for p in cfg.OFF_TARGET_PHRASES]
        _OFF_TARGET_RE = re.compile(r"(?<!\w)(?:" + "|".join(parts) + r")(?!\w)", re.IGNORECASE)
    return any(t and _OFF_TARGET_RE.search(t) for t in texts)


def build_market_vocabularies() -> tuple:
    """
    ({marché: mots}, mots partagés par 3 marchés ou plus, ignorés pour le classement).
    Vocabulaire d'un marché = ses mots-clés de départ + les mots qui reviennent dans les titres
    des chaînes que le site a DÉJÀ classées dans ce marché (le vocabulaire grandit avec la base).
    """
    from config.markets import MARKETS
    from discovery.database import load_market_corpus
    from discovery.keyword_engine import _useful_words, market_vocabulary

    vocabs = {m: set(market_vocabulary(m, cfg.LANGUAGE, [])) for m in MARKETS}

    try:
        corpus = load_market_corpus(cfg.LANGUAGE)
    except Exception as e:                                    # la base est facultative pour le classement
        print(f"  (vocabulaire appris ignoré : {type(e).__name__}: {e})")
        corpus = []
    channels_of_word = {}                                     # (marché, mot) -> chaînes
    size = {}                                                 # marché -> nombre de chaînes dans le corpus
    for r in corpus:
        if r["market"] not in vocabs:
            continue
        size.setdefault(r["market"], set()).add(r["channel_id"])
        for w in set(_useful_words(r["title"], cfg.LANGUAGE)):
            channels_of_word.setdefault((r["market"], w), set()).add(r["channel_id"])
    # Un mot est "appris" pour un marché seulement s'il lui est vraiment PROPRE : on compare la part
    # de chaînes qui l'emploient dans chaque marché (un gros marché ne gagne pas juste parce qu'il est gros).
    rate = {}
    for (m, w), chans in channels_of_word.items():
        rate.setdefault(w, {})[m] = len(chans) / max(1, len(size[m]))
    for (m, w), chans in channels_of_word.items():
        if len(chans) < cfg.LEARN_VOCAB_MIN_CHANNELS:
            continue
        if rate[w][m] / sum(rate[w].values()) >= cfg.LEARN_VOCAB_MIN_SHARE:
            vocabs[m].add(w)

    counts = Counter(w for words in vocabs.values() for w in words)
    shared = {w for w, n in counts.items() if n >= 3}
    return {m: words - shared for m, words in vocabs.items()}, shared


def classify_market(titles: list, vocabs: dict, hint_market: str | None = None) -> str:
    """
    Marché dont le vocabulaire apparaît le plus dans les titres ; 'radar' si on ne sait pas.
    hint_market : marché suggéré par la catégorie YouTube (donne un point en plus).
    """
    from discovery.keyword_engine import _useful_words

    words = set()
    for t in titles:
        words.update(_useful_words(t or "", cfg.LANGUAGE))
    scored = []
    for m, v in vocabs.items():
        score = len(v & words)
        if hint_market == m and score > 0:                    # le coup de pouce ne crée jamais un marché seul
            score += cfg.CATEGORY_HINT_BONUS
        scored.append((score, m))
    scored.sort(reverse=True)
    if not scored:
        return cfg.UNCLASSIFIED_MARKET
    best, market = scored[0]
    second = scored[1][0] if len(scored) > 1 else 0
    if best >= cfg.MIN_MARKET_WORDS and best > second:
        return market
    return cfg.UNCLASSIFIED_MARKET


# ---------------------------------------------------------------------------
# Des vidéos aux chaînes validées
# ---------------------------------------------------------------------------

def process_videos(videos: list, funnel: dict) -> tuple:
    """Applique les critères de chaînes. Retourne (chaînes validées, quota_épuisé)."""
    import discovery.channel_activity as ca
    import discovery.channel_stats as cs
    from discovery.database import existing_channel_ids, list_rejected_ids
    from discovery.faceless_filter import pre_filter_faceless, score_channel_result
    from discovery.language_filter import filter_and_prioritize_by_language

    funnel["videos"] = len(videos)

    # Une ligne par chaîne : sa vidéo la plus vue.
    best = {}
    for v in videos:
        cur = best.get(v["channel_id"])
        if cur is None or v["view_count"] > cur["view_count"]:
            best[v["channel_id"]] = v
    funnel["channels"] = len(best)

    rejected = list_rejected_ids()
    known = existing_channel_ids(list(best.keys()))
    fresh = [v for cid, v in best.items() if cid not in rejected and cid not in known]
    funnel["already_known"] = len(best) - len(fresh)
    funnel["new_channels"] = len(fresh)

    # Musique et enfants : écartés tout de suite (gratuit, avant de demander les stats de chaîne).
    kept = [v for v in fresh if not is_off_target(v.get("channel_title"), v.get("title"))]
    funnel["off_target"] = len(fresh) - len(kept)
    fresh = kept

    print("\nStats de chaîne (abonnés)...")
    with_channels = cs.enrich_with_channel_data(fresh, "", max_subscribers=100_000)
    funnel["small_channels"] = len(with_channels)
    kept = [v for v in with_channels if not is_off_target((v.get("channel_description") or "")[:300])]
    funnel["off_target"] += len(with_channels) - len(kept)
    with_channels = kept

    lang_filtered = [v for v in filter_and_prioritize_by_language(with_channels)
                     if v.get("detected_language") == cfg.LANGUAGE]
    funnel["language_ok"] = len(lang_filtered)

    candidates = pre_filter_faceless(lang_filtered)
    funnel["faceless_text_ok"] = len(candidates)

    # Ordre de test : 1) chaînes créées récemment (elles passent forcément la règle d'âge),
    # 2) puis les moins vues d'abord. La limite coupe la fin de la liste.
    recent_limit = datetime.now(timezone.utc) - timedelta(days=cfg.RECENT_CHANNEL_DAYS)

    def _is_recent(v):
        created = _parse_iso(v.get("channel_created_at"))
        return created is not None and created >= recent_limit

    funnel["recent_channels"] = sum(1 for v in candidates if _is_recent(v))
    candidates.sort(key=lambda v: (not _is_recent(v), v["view_count"]))
    candidates = candidates[:cfg.MAX_CHANNELS_TO_VALIDATE]
    funnel["to_validate"] = len(candidates)

    print(f"\nValidation de l'activité ({len(candidates)} chaînes, règle des {cfg.MAX_STRONG_AGE_DAYS} jours)...")
    validated = []
    statuses = Counter()
    quota_stopped = False
    for i, channel in enumerate(candidates, 1):
        print(f"  [{i}/{len(candidates)}] {channel['channel_title']}...", end=" ")
        try:
            result = ca.validate_channel_activity(channel, "", strong_max_age_days=cfg.MAX_STRONG_AGE_DAYS,
                                                  strong_min_views=cfg.MIN_VIEWS)
        except QuotaExhaustedError:
            print("\n  [!] Toutes les clés sont épuisées : arrêt de la validation.")
            quota_stopped = True
            break
        status = result["activity_status"]
        statuses[status] += 1
        print(status + (f" ({result['channel_status']})" if status == "VALID" else ""))
        if status != "VALID":
            continue
        text_score = score_channel_result(result)
        if text_score["verdict"] == "face":
            statuses["REJECTED_TEXT_FACE"] += 1
            print(f"    -> rejetée (texte non-faceless : {text_score['hits']}/{text_score['total']} titres)")
            continue
        result["face_text_ratio"] = text_score["ratio"]
        result["face_text_verdict"] = text_score["verdict"]
        result["density_score"] = result["strong_video_count"] / result["total_videos_checked"]
        result["channel_url"] = f"https://www.youtube.com/channel/{result['channel_id']}"
        validated.append(result)

    funnel["statuses"] = dict(statuses)
    funnel["validated"] = len(validated)
    validated.sort(key=lambda v: (v["channel_status"] != "PROVEN", -v["density_score"]))
    return validated, quota_stopped


def save_by_market(validated: list) -> dict:
    """Classe chaque chaîne dans un marché et l'enregistre. Retourne {marché: [chaînes]}."""
    from discovery.database import save_validated_channels

    vocabs, _ = build_market_vocabularies()
    groups = {}
    for ch in validated:
        titles = [ch.get("title")] + [v.get("title") for v in (ch.get("strong_videos") or [])] \
                 + [v.get("title") for v in (ch.get("proven_videos") or [])] + [ch.get("channel_title")]
        hint = cfg.CATEGORY_MARKET_HINT.get(str(ch.get("category")))
        market = classify_market([t for t in titles if t], vocabs, hint)
        ch["query_source"] = "radar"
        groups.setdefault(market, []).append(ch)
    for market, chs in groups.items():
        save_validated_channels(chs, market=market)
    return groups


# ---------------------------------------------------------------------------
# Passage complet
# ---------------------------------------------------------------------------

def _print_plan(work: list, budget_calls: int, categories: list):
    resume = sum(1 for c in work if c["state"] == "open" and (c["pages_done"] or 0) > 0)
    fresh = sum(1 for c in work if c["state"] == "open" and not (c["pages_done"] or 0))
    rechecks = sum(1 for c in work if c["state"] == "done")
    print(f"Plan : {len(categories)} catégories x {len(cfg.DURATIONS)} durées, tranches de {cfg.SLICE_DAYS} jours "
          f"sur {cfg.WINDOW_DAYS} jours.")
    print(f"  Cases à travailler : {len(work)} ({resume} à reprendre, {fresh} jamais explorées, {rechecks} à revisiter).")
    print(f"  Budget : {budget_calls} appels de recherche = {budget_calls * SEARCH_COST} unités "
          f"(au moins 1 appel par case ; les cases fortes en demandent plusieurs).")
    covered = min(len(work), budget_calls)
    print(f"  Au minimum {covered} case(s) seront touchées dans ce passage.")


def run(budget_units: int | None = None, dry_run: bool = False) -> None:
    import discovery.channel_activity as ca
    import discovery.channel_stats as cs
    import discovery.video_stats as vs
    from discovery.database import radar_load_cells

    now = datetime.now(timezone.utc)
    budget_units = cfg.SEARCH_BUDGET_UNITS if budget_units is None else budget_units
    budget_calls = max(0, budget_units // SEARCH_COST)

    print(f"{'#' * 60}\n# RADAR (langue : {cfg.LANGUAGE}) — {now:%Y-%m-%d %H:%M} UTC\n{'#' * 60}\n")

    global _COUNTER, _PENDING
    counter = UnitCounter()
    originals = {}
    if not dry_run:
        _COUNTER = counter
        _PENDING = {}
        # Compte aussi les appels des modules existants, sans les modifier.
        for mod in (vs, cs, ca):
            originals[mod] = mod.youtube_get

            def wrapped(url, params, timeout=20, _orig=mod.youtube_get):
                counter.add(url)
                return _with_retries(_orig, url, params, timeout)

            mod.youtube_get = wrapped

    try:
        categories = [str(c) for c in cfg.CATEGORIES] if dry_run else valid_categories()
        slices = build_slices(now.date())
        saved = radar_load_cells()
        cells, _new = merge_cells(saved, slices, categories)
        work = plan_work(cells, now, categories)
        _print_plan(work, budget_calls, categories)
        if dry_run:
            return

        collected, stats = {}, Counter()
        budget = {"calls_left": budget_calls, "calls_used": 0}
        queue = deque(work)
        quota_stopped = False
        print("\nExploration des cases...")
        try:
            while queue and budget["calls_left"] > 0:
                cell = queue.popleft()
                label = f"{cfg.CATEGORIES.get(cell['category'], cell['category'])} / {cell['duration']} / " \
                        f"{cell['slice_start']} -> {cell['slice_end']}"
                before_q = len(collected)
                state = explore_cell(cell, now, budget, collected, stats, queue)
                print(f"  {label}: page(s) {cell['pages_done']}, +{len(collected) - before_q} vidéo(s) >= "
                      f"{cfg.MIN_VIEWS:,} vues -> {state}")
        except QuotaExhaustedError:
            print("\n  [!] Toutes les clés sont épuisées pendant la recherche : on traite ce qui est déjà trouvé.")
            quota_stopped = True

        videos = list(collected.values())
        per_category = Counter(v["category"] for v in videos)
        funnel = {}
        validated, q2 = ([], False)
        if videos:
            validated, q2 = process_videos(videos, funnel)
            quota_stopped = quota_stopped or q2
        else:
            print("\nAucune vidéo qualifiante dans ce passage.")

        groups = {}
        if validated:
            print("\nAnalyse des visages sur les miniatures...")
            try:
                import discovery.face_detect as fd
                fd.attach_face_scores(validated)
            except ImportError as e:
                print(f"  (analyse des miniatures ignorée : {e})")
            groups = save_by_market(validated)
        n_cells = _flush_cells()
        print(f"\n{n_cells} case(s) enregistrée(s) dans la carte du radar.")

        created = []
        try:
            from discovery.keyword_engine import create_radar_keywords
            created = create_radar_keywords(cfg.LANGUAGE)
        except Exception as e:
            print(f"  (mots-clés radar ignorés : {type(e).__name__}: {e})")

        # ---------------- Résumé ----------------
        print(f"\n{'=' * 60}\nRÉSUMÉ DU RADAR\n{'=' * 60}")
        print(f"Cases explorées : {stats['cells_done']} terminées, {stats['cells_split']} coupées en deux, "
              f"{stats['cells_saturated']} saturées (1 jour), {stats['pages']} page(s) lue(s).")
        if funnel:
            print("\nEntonnoir :")
            print(f"  vidéos >= {cfg.MIN_VIEWS:,} vues ............ {funnel['videos']}")
            print(f"  chaînes ......................... {funnel['channels']}")
            print(f"  déjà connues ou refusées ........ {funnel['already_known']}")
            print(f"  nouvelles chaînes ............... {funnel['new_channels']}")
            print(f"  écartées (musique / enfants) .... {funnel.get('off_target', 0)}")
            print(f"  <= 100K abonnés ................. {funnel['small_channels']}")
            print(f"  langue {cfg.LANGUAGE} ........................ {funnel['language_ok']}")
            print(f"  faceless (texte) ................ {funnel['faceless_text_ok']}")
            print(f"  dont créées il y a < {cfg.RECENT_CHANNEL_DAYS} jours ...... {funnel.get('recent_channels', 0)}  (testées en premier)")
            print(f"  validées (activité + règle) ..... {funnel['validated']}  (sur {funnel['to_validate']} testées)")
            if funnel.get("statuses"):
                print("  détail des refus : " + ", ".join(f"{k}={v}" for k, v in sorted(funnel["statuses"].items())
                                                          if k != "VALID"))
            print("\nVidéos qualifiantes par catégorie : " + ", ".join(
                f"{cfg.CATEGORIES.get(c, c)}={n}" for c, n in per_category.most_common()))
        if groups:
            print("\nChaînes enregistrées par marché : " + ", ".join(f"{m}={len(c)}" for m, c in sorted(groups.items())))
        if created:
            print("\nMots-clés radar créés :")
            for k in created:
                print(f"  + [{k['market']}] {k['query']}  ({k['channels']} chaînes radar)")
        print(f"\nQuota dépensé : {counter.units:,} unités "
              f"(dont recherches : {counter.search_units:,}) — appels : "
              + ", ".join(f"{k}={v}" for k, v in sorted(counter.calls.items())))
        if quota_stopped:
            print("[!] Quota épuisé : le prochain passage reprendra là où celui-ci s'est arrêté.")
    finally:
        if _PENDING:
            print("\n[!] Passage interrompu avant la fin : aucune case n'a été marquée terminée. "
                  "Relance la commande, rien n'est perdu.")
        _COUNTER = None
        _PENDING = None
        for mod, orig in originals.items():
            mod.youtube_get = orig


def reclassify(review_all: bool = False) -> None:
    """
    Range dans un vrai marché les chaînes restées dans le marché 'radar', quand le vocabulaire
    (de départ + appris) le permet. Ne déplace JAMAIS une chaîne qui a déjà un vrai marché
    (celui-ci peut venir de l'indice de catégorie, que ce calcul n'a plus).
    review_all=True (--reclassify-all) : revoit aussi les chaînes déjà rangées, et peut les remettre
    dans 'radar'. Ne supprime rien : les chaînes musique / enfants sont seulement listées pour que tu
    les supprimes toi-même sur le site.
    """
    from discovery.database import list_unclassified_channels, set_channel_market

    vocabs, _ = build_market_vocabularies()
    chans = list_unclassified_channels(cfg.LANGUAGE)
    if not review_all:
        chans = [c for c in chans if c["market"] == cfg.UNCLASSIFIED_MARKET]
        print(f"{len(chans)} chaîne(s) restée(s) dans le marché 'radar'.")
    else:
        print(f"{len(chans)} chaîne(s) trouvée(s) par le radar (toutes revues, même celles déjà rangées).")
    moved = 0
    final = Counter()
    off_target = []
    for ch in chans:
        titles = ch["titles"] + [ch.get("best_video_title"), ch.get("channel_title")]
        titles = [t for t in titles if t]
        if is_off_target(ch.get("channel_title"), ch.get("best_video_title"), (ch.get("channel_description") or "")[:300]):
            off_target.append(ch["channel_title"])
        market = classify_market(titles, vocabs)
        final[market] += 1
        if market != ch["market"]:
            set_channel_market(ch["channel_id"], market)
            moved += 1
            print(f"  {ch['channel_title']}: {ch['market']} -> {market}")
    print(f"\n{moved} chaîne(s) changée(s) de marché.")
    print("Répartition finale : " + ", ".join(f"{m}={n}" for m, n in sorted(final.items())))
    if off_target:
        print("\nChaînes musique / enfants déjà dans la base (à supprimer sur le site si tu n'en veux pas) :")
        for t in off_target:
            print(f"  - {t}")
    try:
        from discovery.keyword_engine import create_radar_keywords
        created = create_radar_keywords(cfg.LANGUAGE)
        if created:
            print("\nMots-clés radar créés :")
            for k in created:
                print(f"  + [{k['market']}] {k['query']}  ({k['channels']} chaînes radar)")
    except Exception as e:
        print(f"  (mots-clés radar ignorés : {type(e).__name__}: {e})")


def print_status() -> None:
    from discovery.database import radar_load_cells

    now = datetime.now(timezone.utc)
    categories = [str(c) for c in cfg.CATEGORIES]
    cells, new = merge_cells(radar_load_cells(), build_slices(now.date()), categories)
    window_start = (now - timedelta(days=cfg.WINDOW_DAYS)).date()
    live = [c for c in cells.values()
            if date.fromisoformat(c["slice_end"]) > window_start and c["state"] != "split"
            and c["category"] in categories]
    states = Counter(c["state"] for c in live)
    total = len(live)
    done = states.get("done", 0)
    print(f"Cases de la fenêtre de {cfg.WINDOW_DAYS} jours : {total}")
    print(f"  terminées : {done} ({done / total:.0%})" if total else "  aucune")
    print(f"  ouvertes (à explorer ou à reprendre) : {states.get('open', 0)}")
    started = sum(1 for c in live if c["state"] == "open" and (c["pages_done"] or 0) > 0)
    print(f"  dont déjà commencées : {started}")
    work = plan_work(cells, now, categories)
    rechecks = sum(1 for c in work if c["state"] == "done")
    print(f"  revisites dues : {rechecks}")
    per_cat = {}
    for c in live:
        d = per_cat.setdefault(c["category"], [0, 0])
        d[1] += 1
        d[0] += 1 if c["state"] == "done" else 0
    print("\nPar catégorie (terminées / total) :")
    for cat in categories:
        if cat in per_cat:
            a, b = per_cat[cat]
            print(f"  {cfg.CATEGORIES[cat]:<28} {a}/{b}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Radar : vidéos fortes sans mot-clé, par catégorie.")
    parser.add_argument("--budget", type=int, default=None,
                        help=f"budget de recherche en unités pour ce passage (défaut : {cfg.SEARCH_BUDGET_UNITS})")
    parser.add_argument("--dry-run", action="store_true", help="montre le plan sans appeler YouTube ni écrire")
    parser.add_argument("--status", action="store_true", help="montre l'état de la carte")
    parser.add_argument("--reclassify", action="store_true",
                        help="range dans un vrai marché les chaînes restées dans 'radar' (sans appeler YouTube)")
    parser.add_argument("--reclassify-all", action="store_true",
                        help="revoit TOUTES les chaînes du radar, même celles déjà rangées (peut les remettre dans 'radar')")
    args = parser.parse_args()

    if args.status:
        print_status()
    elif args.reclassify or args.reclassify_all:
        reclassify(review_all=args.reclassify_all)
    else:
        if not args.dry_run and not has_keys():
            raise SystemExit("Aucune clé API trouvée : renseigne YOUTUBE_API_KEYS (ou YOUTUBE_API_KEY) dans .env.")
        if not args.dry_run:
            print(f"{key_count()} clé(s) API chargée(s).")
        run(args.budget, args.dry_run)
