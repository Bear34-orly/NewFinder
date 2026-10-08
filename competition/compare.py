"""
Comparaison chiffrée entre ta chaîne et chaque concurrent.

Aucune opinion : chaque ligne est une mesure, un calcul, et l'écart entre les deux.
Niveaux de vérité affichés dans l'interface :
  OBSERVÉ  = donnée brute de YouTube (abonnés, âge de la chaîne...)
  CALCULÉ  = résultat d'un calcul sur ces données (médiane, ratio...)
  INFÉRÉ   = association constatée dans l'échantillon, qui n'est PAS une preuve de cause
"""

import math
import statistics

from competition.metrics import EXCLUDE_RECENT_DAYS, duration_bucket, title_features

DIFF_THRESHOLD = 1.15  # un écart de moins de 15 % est considéré comme égalité

# key, label, niveau, "high" si plus haut = mieux (None = simple différence), groupe, format
METRICS = [
    ("subscribers", "Abonnés", "observed", None, "scale", "int"),
    ("channel_age_days", "Âge de la chaîne", "observed", None, "scale", "days"),
    ("video_count", "Vidéos publiées (total)", "observed", None, "scale", "int"),
    ("median_views", "Vues médianes par vidéo", "calculated", "high", "performance", "int"),
    ("mean_views", "Vues moyennes par vidéo", "calculated", "high", "performance", "int"),
    ("recent_median", "Vues médianes (10 dernières vidéos)", "calculated", "high", "performance", "int"),
    ("views_per_sub", "Vues médianes par abonné", "calculated", "high", "performance", "dec"),
    ("breakout_rate", "Part de vidéos à 3× la médiane ou plus", "calculated", "high", "performance", "pct"),
    ("top_ratio", "Meilleure vidéo / médiane", "calculated", "high", "performance", "ratio"),
    ("trend_ratio", "Tendance (10 dernières / 10 précédentes)", "calculated", "high", "performance", "ratio"),
    ("likes_per_1k_views", "J'aime pour 1000 vues", "calculated", "high", "performance", "dec"),
    ("videos_per_month", "Vidéos longues par mois", "calculated", "high", "rhythm", "dec"),
    ("last_upload_days", "Jours depuis la dernière vidéo", "calculated", "low", "rhythm", "dec"),
    ("median_duration_min", "Durée médiane (minutes)", "calculated", None, "style", "dec"),
    ("avg_title_length", "Longueur moyenne des titres", "calculated", None, "style", "dec"),
    ("share_number", "Titres avec un chiffre", "calculated", None, "style", "pct"),
    ("share_question", "Titres en question", "calculated", None, "style", "pct"),
    ("share_curiosity", "Titres avec mot de curiosité", "calculated", None, "style", "pct"),
    ("share_caps", "Titres avec un mot en MAJUSCULES", "calculated", None, "style", "pct"),
]
PERFORMANCE_KEYS = ["median_views", "views_per_sub", "breakout_rate", "recent_median"]
LABELS = {m[0]: m[1] for m in METRICS}
FORMATS = {m[0]: m[5] for m in METRICS}


def fmt_value(key: str, v) -> str:
    if v is None:
        return "n/d"
    kind = FORMATS.get(key, "dec")
    if kind == "int":
        return f"{round(v):,}".replace(",", " ")
    if kind == "pct":
        return f"{v * 100:.0f} %"
    if kind == "ratio":
        return f"{v:.1f}×"
    if kind == "days":
        return f"{round(v)} j"
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _row(mine: dict, other: dict, spec: tuple) -> dict:
    key, label, level, better, group, _ = spec
    a, b = mine.get(key), other.get(key)
    row = {
        "key": key, "label": label, "level": level, "group": group,
        "mine": a, "other": b,
        "mine_text": fmt_value(key, a), "other_text": fmt_value(key, b),
        "ratio": None, "verdict": "n/a",
    }
    if a is None or b is None:
        return row

    if a == 0 and b == 0:
        row["verdict"] = "equal"
        return row
    # Publier il y a 2 jours ou il y a 5 jours ne change rien : on ne compare
    # la "fraîcheur" que si l'une des deux chaînes est vraiment à l'arrêt.
    if key == "last_upload_days" and max(a, b) <= 14:
        row["verdict"] = "equal"
        return row
    if a == 0 or b == 0:
        ratio = None
        bigger_other = b > a
    else:
        ratio = b / a
        bigger_other = ratio >= 1
        row["ratio"] = round(ratio, 2)

    if better is None:
        row["verdict"] = "neutral"
        return row

    significant = ratio is None or ratio >= DIFF_THRESHOLD or ratio <= 1 / DIFF_THRESHOLD
    if not significant:
        row["verdict"] = "equal"
        return row

    other_better = bigger_other if better == "high" else not bigger_other
    row["verdict"] = "other" if other_better else "mine"
    return row


def _sentence(row: dict, who: str) -> str:
    """Phrase factuelle pour un écart. who = 'other' (il te dépasse) ou 'mine' (tu le dépasses)."""
    label = row["label"]
    if row["ratio"]:
        mult = row["ratio"] if row["ratio"] >= 1 else 1 / row["ratio"]
        suffix = f" ({mult:.1f}×)"
    else:
        suffix = ""
    if who == "other":
        return f"{label} : {row['other_text']} chez lui contre {row['mine_text']} chez toi{suffix}"
    return f"{label} : {row['mine_text']} chez toi contre {row['other_text']} chez lui{suffix}"


def _gap_size(row: dict) -> float:
    if not row["ratio"]:
        return 0.0
    return abs(math.log(row["ratio"]))


def compare_pair(mine: dict, other: dict) -> dict:
    rows = [_row(mine, other, spec) for spec in METRICS]

    other_rows = sorted([r for r in rows if r["verdict"] == "other"], key=_gap_size, reverse=True)
    mine_rows = sorted([r for r in rows if r["verdict"] == "mine"], key=_gap_size, reverse=True)

    perf_other = [r for r in other_rows if r["key"] in PERFORMANCE_KEYS]
    perf_mine = [r for r in mine_rows if r["key"] in PERFORMANCE_KEYS]

    return {
        "rows": rows,
        "other_ahead": [_sentence(r, "other") for r in other_rows],
        "mine_ahead": [_sentence(r, "mine") for r in mine_rows],
        "main_gap": _sentence(perf_other[0], "other") if perf_other else None,
        "main_advantage": _sentence(perf_mine[0], "mine") if perf_mine else None,
        "best_videos": {"mine": mine.get("best_videos", [])[:3], "other": other.get("best_videos", [])[:3]},
    }


def associations(profiles: list) -> list:
    """
    Pour chaque caractéristique de titre / durée : comparaison de la performance
    des vidéos qui l'ont et de celles qui ne l'ont pas, chacune rapportée à la
    médiane de SA chaîne (pour pouvoir mélanger des chaînes de tailles différentes).
    C'est une association constatée, pas une preuve de cause.
    """
    items = []
    for p in profiles:
        med = p.get("median_views")
        if not med:
            continue
        for v in p.get("videos", []):
            if v.get("age_days", 0) < EXCLUDE_RECENT_DAYS:
                continue
            f = title_features(v["title"])
            items.append({
                "ratio": v["views"] / med,
                "has_number": f["has_number"],
                "is_question": f["is_question"],
                "has_curiosity": f["has_curiosity"],
                "has_caps_word": f["has_caps_word"],
                "bucket": duration_bucket(v["duration_s"]),
            })

    tests = [
        ("Titre avec un chiffre", lambda i: i["has_number"]),
        ("Titre en question", lambda i: i["is_question"]),
        ("Titre avec mot de curiosité", lambda i: i["has_curiosity"]),
        ("Titre avec un mot en MAJUSCULES", lambda i: i["has_caps_word"]),
    ]
    for bucket in ("3-8 min", "8-15 min", "15-30 min", "30 min +"):
        tests.append((f"Durée {bucket}", (lambda b: lambda i: i["bucket"] == b)(bucket)))

    out = []
    for label, fn in tests:
        yes = [i["ratio"] for i in items if fn(i)]
        no = [i["ratio"] for i in items if not fn(i)]
        if len(yes) < 5 or len(no) < 5:
            continue
        my, mn = statistics.median(yes), statistics.median(no)
        out.append({
            "label": label,
            "n_with": len(yes), "n_without": len(no),
            "with_ratio": round(my, 2), "without_ratio": round(mn, 2),
            "lift": round(my / mn, 2) if mn else None,
        })
    out.sort(key=lambda a: abs(math.log(a["lift"])) if a["lift"] else 0, reverse=True)
    return out


def build_report(data: dict) -> dict:
    """Assemble tout ce que l'interface affiche pour une analyse terminée."""
    mine = data["mine"]
    competitors = data.get("competitors", [])

    out_comps = []
    for c in competitors:
        cmp = compare_pair(mine, c["profile"])
        out_comps.append({
            "profile": {k: v for k, v in c["profile"].items() if k != "videos"},
            "similarity": c.get("similarity"),
            "source": c.get("source"),
            "comparison": cmp,
        })

    out_comps.sort(key=lambda c: (c["similarity"] or {}).get("score", 0), reverse=True)

    return {
        "mine": {k: v for k, v in mine.items() if k != "videos"},
        "competitors": out_comps,
        "associations": associations([mine] + [c["profile"] for c in competitors]),
        "queries": data.get("queries", []),
        "units_used": data.get("units_used"),
        "generated_at": data.get("generated_at"),
        "notes": data.get("notes", []),
    }
