"""
Orchestration d'une analyse de concurrence :

  1. lecture de ta chaîne et de ses dernières vidéos
  2. recherche de concurrents :
       - dans la base du Niche Finder (même marché, taille proche)
       - par recherche YouTube avec les mots de tes propres titres
  3. profil chiffré de chaque candidat, score de proximité, tri
  4. enregistrement du résultat (le site compare ensuite à la volée)

Une analyse complète coûte environ 200 à 260 unités de quota (2 recherches = 200).
"""

import math
import traceback
from datetime import datetime, timezone

from langdetect import DetectorFactory, detect

from competition import store
from competition.metrics import build_profile
from competition.similarity import search_queries, similarity
from competition.yt import (
    ChannelNotFound,
    Tracker,
    get_channels,
    get_recent_videos,
    resolve_channel,
    search_videos,
)
from discovery.youtube_client import QuotaExhaustedError

DetectorFactory.seed = 0

MAX_PROFILED = 10      # candidats profilés en détail (2 unités chacun)
KEEP = 5               # concurrents gardés dans le résultat
MAX_INACTIVE_DAYS = 120
MIN_VIDEOS_TOTAL = 8
MIN_LONG_VIDEOS = 5
MIN_COMMON_KEYWORDS = 3


def detect_language(profile: dict, default: str = "en") -> str:
    titles = [v["title"] for v in profile.get("videos", [])[:20]]
    text = ". ".join(titles)
    if len(text) < 30:
        return default
    try:
        return detect(text)
    except Exception:
        return default


def _db_candidates(my_info: dict, market):
    """Chaînes du Niche Finder du même marché et de taille proche."""
    if not market:
        return []
    from discovery.database import list_all_channels
    subs = my_info.get("subscribers") or 0
    out = []
    for c in list_all_channels():
        if (c.get("market") or "").lower() != market.lower():
            continue
        if c["channel_id"] == my_info["channel_id"]:
            continue
        s = c.get("subscriber_count") or 0
        if subs and not (subs / 10 <= s <= subs * 10):
            continue
        out.append(c["channel_id"])
    return out


def _size_score(a, b) -> float:
    if not a or not b:
        return 0.5
    return max(0.0, 1.0 - abs(math.log(a / b)) / math.log(30))


def _within_size(my_subs, subs) -> bool:
    if subs is None:
        return False
    hi = max((my_subs or 0) * 10, 5000)
    lo = (my_subs or 0) / 10
    return lo <= subs <= hi


def _set_progress(analysis_id: int, text: str, tracker: Tracker):
    store.update_analysis(analysis_id, progress=text, units_used=tracker.units)


def _attach_history(profile: dict):
    """Ajoute l'évolution depuis la dernière mesure enregistrée (s'il y en a une)."""
    prev = store.previous_snapshot(profile["channel_id"])
    store.add_snapshot(profile)
    if not prev or profile.get("subscribers") is None or prev.get("subscribers") is None:
        return
    try:
        then = datetime.fromisoformat(prev["taken_at"])
        days = max(1, round((datetime.now(timezone.utc) - then).total_seconds() / 86400))
    except ValueError:
        return
    profile["history"] = {
        "days": days,
        "subs_change": profile["subscribers"] - prev["subscribers"],
        "median_views_before": prev.get("median_views"),
    }


def run_analysis(analysis_id: int, owner: str, my_channel_id: str, market):
    tracker = Tracker()
    notes = []
    try:
        # ---- 1. ta chaîne
        _set_progress(analysis_id, "Lecture de ta chaîne...", tracker)
        infos = get_channels([my_channel_id], tracker)
        if my_channel_id not in infos:
            raise ChannelNotFound("Ta chaîne est introuvable (supprimée ou privée ?).")
        my_info = infos[my_channel_id]
        mine = build_profile(my_info, get_recent_videos(my_info["uploads_playlist"], tracker))
        if mine["mature_size"] < MIN_LONG_VIDEOS:
            notes.append(
                f"Ta chaîne n'a que {mine['mature_size']} vidéo(s) longue(s) assez anciennes : "
                "les médianes et pourcentages sont peu fiables."
            )
        if my_info.get("subscribers") is None:
            notes.append("Le nombre d'abonnés de ta chaîne est caché : la taille ne peut pas être comparée.")

        language = detect_language(mine)
        queries = search_queries(mine)
        if not queries:
            notes.append("Pas assez de titres pour construire une recherche.")

        # ---- 2. candidats
        candidates = {}  # channel_id -> {"hits": int, "sources": set}

        _set_progress(analysis_id, "Recherche dans la base du Niche Finder...", tracker)
        for cid in _db_candidates(mine, market):
            candidates.setdefault(cid, {"hits": 0, "sources": set()})["sources"].add("base")

        for i, q in enumerate(queries, 1):
            _set_progress(analysis_id, f"Recherche YouTube {i}/{len(queries)} : « {q} »", tracker)
            for hit in search_videos(q, language[:2], tracker):
                if hit["channel_id"] == my_channel_id:
                    continue
                entry = candidates.setdefault(hit["channel_id"], {"hits": 0, "sources": set()})
                entry["hits"] += 1
                entry["sources"].add("youtube")

        if not candidates:
            notes.append("Aucun concurrent candidat trouvé.")

        # ---- 3. tri préliminaire sur la taille
        _set_progress(analysis_id, f"Mesure de {len(candidates)} chaînes candidates...", tracker)
        cand_infos = get_channels(list(candidates), tracker)

        my_subs = mine.get("subscribers")
        scored = []
        for cid, info in cand_infos.items():
            if info["video_count"] < MIN_VIDEOS_TOTAL:
                continue
            if my_subs and not _within_size(my_subs, info["subscribers"]):
                continue
            pre = _size_score(my_subs, info["subscribers"]) + 0.15 * min(candidates[cid]["hits"], 4)
            if "base" in candidates[cid]["sources"]:
                pre += 0.3
            scored.append((pre, cid))
        scored.sort(reverse=True)
        to_profile = [cid for _, cid in scored[:MAX_PROFILED]]

        # marché des candidats connus de la base
        db_markets = {}
        if market:
            from discovery.database import list_all_channels
            db_markets = {c["channel_id"]: (c.get("market") or "").lower() for c in list_all_channels()}

        # ---- 4. profils détaillés
        profiled = []
        for n, cid in enumerate(to_profile, 1):
            info = cand_infos[cid]
            _set_progress(analysis_id, f"Analyse du concurrent {n}/{len(to_profile)} : {info['title']}", tracker)
            profile = build_profile(info, get_recent_videos(info["uploads_playlist"], tracker))

            if profile["mature_size"] < MIN_LONG_VIDEOS:
                continue
            if profile["last_upload_days"] is None or profile["last_upload_days"] > MAX_INACTIVE_DAYS:
                continue
            if detect_language(profile, default=language) != language:
                continue

            db_market = db_markets.get(cid)
            same_market = (db_market == market.lower()) if (market and db_market) else None
            sim = similarity(mine, profile, same_market)
            source = "base" if "base" in candidates[cid]["sources"] else "youtube"
            # Un candidat trouvé par recherche doit partager au moins 3 mots-clés de sujet
            # avec ta chaîne, sinon il est hors sujet.
            if source == "youtube" and sim["common_count"] < MIN_COMMON_KEYWORDS:
                continue
            profiled.append({"profile": profile, "similarity": sim, "source": source})

        profiled.sort(key=lambda c: c["similarity"]["score"], reverse=True)
        competitors = profiled[:KEEP]
        if not competitors and candidates:
            notes.append("Des candidats ont été trouvés mais aucun ne passe les filtres "
                         "(langue, activité récente, taille). Ajoute un concurrent à la main.")

        # ---- 5. historique + enregistrement
        _set_progress(analysis_id, "Enregistrement...", tracker)
        _attach_history(mine)
        for c in competitors:
            _attach_history(c["profile"])

        data = {
            "mine": mine,
            "competitors": competitors,
            "queries": queries,
            "language": language,
            "market": market,
            "units_used": tracker.units,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "notes": notes,
        }
        store.update_analysis(
            analysis_id, status="done", progress="Terminé", data=data,
            units_used=tracker.units, finished_at=store.now_iso(),
        )

    except QuotaExhaustedError:
        store.update_analysis(
            analysis_id, status="error", units_used=tracker.units, finished_at=store.now_iso(),
            error="Le quota YouTube est épuisé pour aujourd'hui. Réessaie demain.",
        )
    except ChannelNotFound as e:
        store.update_analysis(analysis_id, status="error", error=str(e), finished_at=store.now_iso())
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        store.update_analysis(
            analysis_id, status="error", units_used=tracker.units, finished_at=store.now_iso(),
            error=f"Erreur pendant l'analyse : {str(e)[:200]}",
        )


def add_manual_competitor(owner: str, analysis_id: int, url: str):
    """Ajoute un concurrent choisi par l'utilisateur à une analyse terminée."""
    analysis = store.get_analysis(owner, analysis_id)
    if not analysis or analysis["status"] != "done" or not analysis["data"]:
        raise ValueError("Analyse introuvable ou pas terminée.")

    data = analysis["data"]
    tracker = Tracker()
    info = resolve_channel(url, tracker)

    if info["channel_id"] == data["mine"]["channel_id"]:
        raise ValueError("C'est ta propre chaîne.")
    if any(c["profile"]["channel_id"] == info["channel_id"] for c in data["competitors"]):
        raise ValueError("Ce concurrent est déjà dans la liste.")

    profile = build_profile(info, get_recent_videos(info["uploads_playlist"], tracker))
    sim = similarity(data["mine"], profile, None)
    _attach_history(profile)
    data["competitors"].append({"profile": profile, "similarity": sim, "source": "manuel"})
    data["units_used"] = (data.get("units_used") or 0) + tracker.units
    store.update_analysis(analysis_id, data=data, units_used=data["units_used"])
    return profile["channel_id"]


def remove_competitor(owner: str, analysis_id: int, channel_id: str) -> bool:
    analysis = store.get_analysis(owner, analysis_id)
    if not analysis or not analysis["data"]:
        return False
    data = analysis["data"]
    before = len(data["competitors"])
    data["competitors"] = [c for c in data["competitors"] if c["profile"]["channel_id"] != channel_id]
    if len(data["competitors"]) == before:
        return False
    store.update_analysis(analysis_id, data=data)
    return True
