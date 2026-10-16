"""
Filtre faceless v2 — apprentissage des motifs de titres des chaînes "Visage".

Compare les titres de tes chaînes SUPPRIMÉES avec la raison "Visage"
(interviews, podcasts, talk-shows... dont la miniature ne montre pas de visage)
aux titres de tes chaînes GARDÉES, puis liste :
  1. des MOTIFS DE FORME (numéro d'épisode, "guest", mots censurés avec *, ...)
  2. des MOTS et EXPRESSIONS de 2 mots qui reviennent chez les chaînes "Visage"
     et presque jamais chez les gardées.

Tout est compté PAR CHAÎNE (un mot compte une fois par chaîne, même s'il est
répété dans 40 titres), pour qu'une seule chaîne ne fausse pas la liste.

Rien n'est modifié : le script affiche seulement des propositions. Tu relis la
liste, tu retires ce qui n'a pas de sens, puis on ajoute le reste aux signaux.

Usage :
    python -m discovery.learn_face_titles
    python -m discovery.learn_face_titles --lang en     (défaut : en)
    python -m discovery.learn_face_titles --lang all
    python -m discovery.learn_face_titles --top 60
"""

import argparse
import re
from collections import defaultdict

from discovery.database import get_connection, init_db

MIN_FACE_CHANNELS = 2   # un terme doit apparaître chez au moins 2 chaînes "Visage"
SMOOTH = 0.02           # lissage du rapport de fréquences

# Motifs de FORME de titre. Chaque motif est testé sur chaque titre.
STRUCTURE_PATTERNS = {
    "numéro d'épisode après une barre (| XXX #36)": re.compile(r"\|\s*[^|#]{1,15}#\s?\d+"),
    "numéro avec # (#36)": re.compile(r"#\s?\d+"),
    "Ep./Episode + numéro": re.compile(r"\b(?:ep|episode|ep\.)\s*\.?\s*\d+", re.I),
    "mot 'guest(s)'": re.compile(r"\bguests?\b", re.I),
    "mot censuré avec * (ex: m*t)": re.compile(r"\w\*+\w?"),
    "barre verticale |": re.compile(r"\|"),
    "tiret long ou ' - ' séparateur": re.compile(r"\s[-–—]\s"),
    "guillemets": re.compile(r"[\"“”«»]"),
    "MOT EN MAJUSCULES (3+ lettres)": re.compile(r"\b[A-Z]{3,}\b"),
    "'with' + nom": re.compile(r"\bwith\s+[A-Z][a-z]+", re.I),
    "point d'exclamation": re.compile(r"!"),
}

STOP = set("""a an and are as at be but by for from has have he her his how i in is it its
me my not of on or our she so than that the their them they this to up was we were what when
where which who why will with you your de la le les des du un une et en que qui pour pas sur
par dans est son sa ses au aux el los las del por con para una es und der die das ein eine
ist nicht mit von zu den dem im на и в не что это как по из за для с от или так же вы он она""".split())

WORD = re.compile(r"[^\W\d_]{3,}(?:'[^\W\d_]+)?", re.U)


def tokens(title: str) -> list[str]:
    return [w.lower() for w in WORD.findall(title) if w.lower() not in STOP]


def terms_of_title(title: str) -> set[str]:
    toks = tokens(title)
    out = set(toks)
    out.update(f"{a} {b}" for a, b in zip(toks, toks[1:]))
    return out


def channel_terms(titles: list[str]) -> set[str]:
    t = set()
    for title in titles:
        t |= terms_of_title(title)
    return t


def load_titles(language: str):
    """Retourne (titres des chaînes 'face', titres des chaînes gardées) : {channel_id: [titres]}."""
    init_db()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            params = ()
            lang_sql = ""
            if language != "all":
                lang_sql = " AND v.language = %s"
                params = (language,)
            cur.execute(
                "SELECT v.channel_id, v.title FROM video_titles v "
                "JOIN rejected_channels r ON r.channel_id = v.channel_id "
                "WHERE r.reject_reason = 'face'" + lang_sql, params)
            face = defaultdict(list)
            for cid, title in cur.fetchall():
                if title:
                    face[cid].append(title)
            cur.execute(
                "SELECT v.channel_id, v.title FROM video_titles v "
                "JOIN channels c ON c.channel_id = v.channel_id "
                "WHERE TRUE" + lang_sql, params)
            kept = defaultdict(list)
            for cid, title in cur.fetchall():
                if title:
                    kept[cid].append(title)
            return dict(face), dict(kept)
    finally:
        conn.close()


def structure_report(face: dict, kept: dict) -> list[tuple]:
    """Pour chaque motif : part des chaînes de chaque groupe où le motif apparaît
    sur au moins 30 % des titres."""
    rows = []
    for name, rx in STRUCTURE_PATTERNS.items():
        def share(group):
            if not group:
                return 0.0
            n = 0
            for titles in group.values():
                hit = sum(1 for t in titles if rx.search(t))
                if titles and hit / len(titles) >= 0.30:
                    n += 1
            return n / len(group)
        rows.append((name, share(face), share(kept)))
    rows.sort(key=lambda r: r[1] - r[2], reverse=True)
    return rows


def term_report(face: dict, kept: dict, top: int) -> list[dict]:
    n_face, n_kept = len(face), len(kept)
    face_counts, kept_counts = defaultdict(int), defaultdict(int)
    example = {}
    for cid, titles in face.items():
        for term in channel_terms(titles):
            face_counts[term] += 1
            if term not in example:
                for t in titles:
                    if term in terms_of_title(t):
                        example[term] = t
                        break
    for titles in kept.values():
        for term in channel_terms(titles):
            kept_counts[term] += 1

    rows = []
    for term, fc in face_counts.items():
        if fc < MIN_FACE_CHANNELS:
            continue
        kc = kept_counts.get(term, 0)
        f_rate = fc / n_face
        k_rate = kc / n_kept if n_kept else 0.0
        lift = (f_rate + SMOOTH) / (k_rate + SMOOTH)
        if lift < 2.0:
            continue
        rows.append({"term": term, "face": fc, "kept": kc, "lift": lift, "example": example.get(term, "")})
    rows.sort(key=lambda r: (r["lift"], r["face"]), reverse=True)
    return rows[:top]


def main():
    parser = argparse.ArgumentParser(description="Motifs de titres des chaînes 'Visage'")
    parser.add_argument("--lang", default="en", help="langue des titres : en (défaut), es, fr, de, ru, all")
    parser.add_argument("--top", type=int, default=40, help="nombre de termes affichés")
    args = parser.parse_args()

    face, kept = load_titles(args.lang)
    n_face_titles = sum(len(v) for v in face.values())
    n_kept_titles = sum(len(v) for v in kept.values())
    print(f"Langue : {args.lang}")
    print(f"Chaînes 'Visage' : {len(face)} ({n_face_titles} titres)")
    print(f"Chaînes gardées  : {len(kept)} ({n_kept_titles} titres)")
    if len(face) < 5 or not kept:
        print("[!] Peu de données : les résultats seront peu fiables.")
    if not face or not kept:
        return

    print("\n=== 1. MOTIFS DE FORME (part des chaînes où le motif est sur 30 %+ des titres) ===")
    print(f"{'motif':<48} | {'Visage':>7} | {'gardées':>8}")
    for name, f, k in structure_report(face, kept):
        print(f"{name:<48} | {f:>6.0%} | {k:>7.0%}")

    print(f"\n=== 2. MOTS ET EXPRESSIONS typiques des chaînes 'Visage' (top {args.top}) ===")
    print("(chaînes 'Visage' contenant le terme / chaînes gardées contenant le terme)")
    rows = term_report(face, kept, args.top)
    if not rows:
        print("  Aucun terme ne ressort assez clairement.")
    for r in rows:
        print(f"  {r['term']:<28} {r['face']:>2}/{len(face)} vs {r['kept']:>2}/{len(kept)}   ex: {r['example'][:70]}")

    print("\nRelis la liste : retire ce qui parle du SUJET (pas du format), et dis-moi ce qu'on garde.")


if __name__ == "__main__":
    main()