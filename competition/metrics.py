"""
Calcul du profil chiffré d'une chaîne à partir de ses dernières vidéos.

Règles :
- seules les vidéos longues (> 3 min) comptent ;
- les vidéos de moins de 3 jours sont ignorées (elles n'ont pas encore leurs vues) ;
- chaque valeur est soit OBSERVÉE (donnée brute de l'API), soit CALCULÉE.
"""

import re
import statistics
from collections import Counter
from datetime import datetime, timezone

from competition.yt import LONG_MIN_SECONDS

EXCLUDE_RECENT_DAYS = 3
BREAKOUT_MULTIPLIER = 3.0

CURIOSITY_WORDS = {
    "secret", "secrets", "truth", "nobody", "never", "hidden", "mystery", "mysteries",
    "shocking", "untold", "real", "really", "why", "what happens", "revealed",
    "unknown", "forgotten", "dark", "terrifying", "insane", "worst", "best",
    "secreto", "verdad", "nadie", "nunca", "oculto", "misterio",
    "secret", "vérité", "personne", "jamais", "caché", "mystère",
}
QUESTION_STARTS = (
    "how ", "why ", "what ", "who ", "when ", "where ", "can ", "do ", "does ",
    "is ", "are ", "will ", "should ", "comment ", "pourquoi ", "que ", "qui ",
    "como ", "cómo ", "por qué ", "qué ",
)

STOPWORDS = set("""
the and for with that this from your you are was were has have had not but they their them
what when where which who whom why how can will would could should about into over under
after before than then just only more most some such very much many been being does did
its it's our out off all any each every both few other another own same too also still
his her she him hers himself herself his one two get got make made way ways new
les des une que qui pour dans sur avec sont pas plus cette ces aux par mais
los las del por con una que para como pero sus este esta esto
der die das und ist nicht mit von den ein eine
""".split())


# Mots de "format de titre" : ils décrivent la façon de titrer, pas le sujet.
# On les retire pour que la proximité de sujet ne soit pas faussée.
TITLE_FILLER = set("""
explained explain explains truth secret secrets really actually happened happen happens story stories
real never ever everything nothing changed revealed behind inside ultimate complete full guide
simple video videos documentary shocking untold hidden mystery mysteries worst best amazing
""".split())


def tokens(title: str) -> list:
    words = re.findall(r"[^\W\d_]{4,}", (title or "").lower())
    return [w for w in words if w not in STOPWORDS and w not in TITLE_FILLER]


def _parse_dt(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def title_features(title: str) -> dict:
    t = (title or "").strip()
    low = t.lower()
    words = re.findall(r"\w+", low)
    caps_words = [w for w in re.findall(r"[^\W\d_]{3,}", t) if w.isupper()]
    return {
        "has_number": bool(re.search(r"\d", t)),
        "is_question": "?" in t or low.startswith(QUESTION_STARTS),
        "has_curiosity": any((" " in w and w in low) or w in words for w in CURIOSITY_WORDS),
        "length": len(t),
        "has_caps_word": bool(caps_words),
    }


def duration_bucket(seconds: int) -> str:
    m = seconds / 60
    if m < 8:
        return "3-8 min"
    if m < 15:
        return "8-15 min"
    if m < 30:
        return "15-30 min"
    return "30 min +"


def _median(values):
    return statistics.median(values) if values else None


def _mean(values):
    return statistics.fmean(values) if values else None


def _share(flags):
    return (sum(1 for f in flags if f) / len(flags)) if flags else None


def build_profile(channel: dict, videos: list) -> dict:
    """
    channel : infos de yt.get_channels / resolve_channel
    videos  : liste brute de yt.get_recent_videos
    """
    now = datetime.now(timezone.utc)

    clean = []
    for v in videos:
        dt = _parse_dt(v.get("published_at"))
        if not dt or v.get("duration_s", 0) < LONG_MIN_SECONDS:
            continue
        age_days = (now - dt).total_seconds() / 86400
        item = dict(v)
        item["age_days"] = round(age_days, 1)
        item["published_dt"] = dt
        clean.append(item)

    clean.sort(key=lambda v: v["published_dt"], reverse=True)

    # Dernier upload (toutes vidéos longues, même très récentes)
    last_upload_days = clean[0]["age_days"] if clean else None

    # Vidéos qui ont eu le temps d'accumuler leurs vues
    mature = [v for v in clean if v["age_days"] >= EXCLUDE_RECENT_DAYS]
    views = [v["views"] for v in mature]

    subs = channel.get("subscribers")
    med = _median(views)

    # Fréquence : vidéos longues publiées sur les 90 derniers jours
    created = _parse_dt(channel.get("published_at"))
    channel_age_days = (now - created).days if created else None
    window = 90
    if channel_age_days is not None:
        window = min(90, max(channel_age_days, 14))
    in_window = [v for v in clean if v["age_days"] <= window]
    videos_per_month = round(len(in_window) / (window / 30), 2) if clean else 0.0
    sample_capped = len(videos) >= 50 and len(in_window) == len(clean)

    # Tendance : 10 dernières vs 10 précédentes
    recent10 = [v["views"] for v in mature[:10]]
    prev10 = [v["views"] for v in mature[10:20]]
    recent_median = _median(recent10)
    trend_ratio = None
    if len(recent10) >= 5 and len(prev10) >= 5 and _median(prev10):
        trend_ratio = round(_median(recent10) / _median(prev10), 2)

    # Breakouts
    breakout_rate = None
    top_ratio = None
    if med and len(views) >= 5:
        breakout_rate = round(sum(1 for x in views if x >= BREAKOUT_MULTIPLIER * med) / len(views), 3)
        top_ratio = round(max(views) / med, 2)

    feats = [title_features(v["title"]) for v in clean]
    weekdays = Counter(v["published_dt"].strftime("%A") for v in clean)
    top_weekday = weekdays.most_common(1)[0][0] if weekdays else None

    likes = sum(v["likes"] for v in mature)
    total_views = sum(views)
    likes_per_1k = round(likes / total_views * 1000, 1) if total_views else None

    best = sorted(mature, key=lambda v: v["views"], reverse=True)[:5]

    return {
        "channel_id": channel["channel_id"],
        "title": channel.get("title"),
        "url": channel.get("url"),
        "thumbnail": channel.get("thumbnail"),
        "subscribers": subs,
        "total_views": channel.get("total_views"),
        "video_count": channel.get("video_count"),
        "channel_age_days": channel_age_days,
        "country": channel.get("country"),
        "sample_size": len(clean),
        "mature_size": len(mature),
        "last_upload_days": last_upload_days,
        "videos_per_month": videos_per_month,
        "sample_capped": sample_capped,
        "median_views": med,
        "mean_views": round(_mean(views)) if views else None,
        "views_per_sub": round(med / subs, 3) if (med and subs) else None,
        "recent_median": recent_median,
        "trend_ratio": trend_ratio,
        "breakout_rate": breakout_rate,
        "top_ratio": top_ratio,
        "median_duration_min": round(_median([v["duration_s"] for v in clean]) / 60, 1) if clean else None,
        "likes_per_1k_views": likes_per_1k,
        "share_number": _round(_share([f["has_number"] for f in feats])),
        "share_question": _round(_share([f["is_question"] for f in feats])),
        "share_curiosity": _round(_share([f["has_curiosity"] for f in feats])),
        "share_caps": _round(_share([f["has_caps_word"] for f in feats])),
        "avg_title_length": round(_mean([f["length"] for f in feats]), 1) if feats else None,
        "top_weekday": top_weekday,
        "best_videos": [{
            "id": v["id"], "title": v["title"], "views": v["views"],
            "duration_min": round(v["duration_s"] / 60, 1),
            "published_at": v["published_at"],
        } for v in best],
        # Échantillon compact, utilisé pour les associations et la similarité
        "videos": [{
            "id": v["id"], "title": v["title"], "views": v["views"],
            "duration_s": v["duration_s"], "age_days": v["age_days"],
        } for v in clean],
    }


def _round(x):
    return None if x is None else round(x, 3)
