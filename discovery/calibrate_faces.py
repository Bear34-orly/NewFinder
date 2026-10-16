"""
Filtre faceless v2 — partie C : calibration du seuil "Visage ?".

Compare deux groupes avec les chiffres de face_detect.py :
  - tes chaînes SUPPRIMÉES avec la raison "Visage"  (rejected_channels.reject_reason = 'face')
  - tes chaînes GARDÉES                              (table channels)

Pour chaque chaîne, on prend ses vidéos les plus vues (table video_titles),
on télécharge leurs miniatures (gratuit, aucun quota YouTube) et on calcule
face_ratio et same_face_ratio. Puis on cherche le seuil qui sépare le mieux
les deux groupes.

Usage :
    python -m discovery.calibrate_faces
    python -m discovery.calibrate_faces --kept 80      (nombre de chaînes gardées testées)
    python -m discovery.calibrate_faces --refresh      (ignore le cache, retélécharge tout)

Les résultats sont gardés dans data/face_calibration.json : relancer le script
ne retélécharge que les chaînes nouvelles.
"""

import argparse
import json
import random
from pathlib import Path

from config.face_settings import FACE_TAG_SAME_RATIO, MAX_THUMBNAILS
from discovery.database import get_connection, init_db

CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "face_calibration.json"
MIN_IMAGES = 3  # en dessous, la chaîne n'a pas assez de miniatures pour être jugée


def _top_video_ids(cur, channel_id: str) -> list[str]:
    cur.execute(
        "SELECT video_id FROM video_titles WHERE channel_id = %s "
        "ORDER BY views DESC NULLS LAST LIMIT %s",
        (channel_id, MAX_THUMBNAILS),
    )
    return [r[0] for r in cur.fetchall()]


def load_groups(kept_sample: int, seed: int = 7):
    """Retourne (chaînes 'face', chaînes gardées) sous forme de [(id, titre, [video_ids])]."""
    init_db()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT channel_id, channel_title FROM rejected_channels WHERE reject_reason = 'face'")
            face_rows = cur.fetchall()
            cur.execute("SELECT channel_id, channel_title FROM channels")
            kept_rows = cur.fetchall()
            random.Random(seed).shuffle(kept_rows)
            kept_rows = kept_rows[:kept_sample]

            def attach(rows):
                out = []
                for cid, title in rows:
                    vids = _top_video_ids(cur, cid)
                    if vids:
                        out.append((cid, title or cid, vids))
                return out

            return attach(face_rows), attach(kept_rows)
    finally:
        conn.close()


def load_cache() -> dict:
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_cache(cache: dict):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


def measure(channels, cache, analyzer, refresh: bool, label: str) -> list[dict]:
    from discovery.face_detect import analyze_channel
    results = []
    for i, (cid, title, vids) in enumerate(channels, 1):
        if cid in cache and not refresh:
            res = cache[cid]
            tag = "(cache)"
        else:
            res = analyze_channel(vids, analyzer)
            cache[cid] = res
            tag = ""
        print(f"  [{label} {i}/{len(channels)}] {title[:40]:<40} images={res['images']} "
              f"visage={res['face_ratio']:.2f} même_visage={res['same_face_ratio']:.2f} {tag}")
        if res["images"] >= MIN_IMAGES:
            results.append({"id": cid, "title": title, **res})
    return results


def rate_at(values: list[float], t: float) -> float:
    return sum(1 for v in values if v >= t) / len(values) if values else 0.0


def suggest_threshold(face_vals: list[float], kept_vals: list[float]):
    """
    Seuil qui maximise (chaînes 'face' attrapées - chaînes gardées marquées à tort).
    Retourne (seuil, taux_attrapé, taux_faux) ou None s'il manque des données.
    """
    if not face_vals or not kept_vals:
        return None
    best = None
    for k in range(10, 100, 5):
        t = k / 100
        recall = rate_at(face_vals, t)
        false_rate = rate_at(kept_vals, t)
        score = recall - false_rate
        if best is None or score > best[0] + 1e-9:
            best = (score, t, recall, false_rate)
    _, t, recall, false_rate = best
    return t, recall, false_rate


def print_table(name: str, face: list[dict], kept: list[dict], key: str):
    fv = [r[key] for r in face]
    kv = [r[key] for r in kept]
    print(f"\n--- Seuil sur '{name}' ---")
    print(f"{'seuil':>6} | {'Visage attrapées':>17} | {'gardées marquées à tort':>24}")
    for k in range(10, 100, 10):
        t = k / 100
        print(f"{t:>6.2f} | {rate_at(fv, t):>16.0%} | {rate_at(kv, t):>23.0%}")
    sug = suggest_threshold(fv, kv)
    if sug:
        t, recall, false_rate = sug
        print(f"=> Meilleur seuil : {t:.2f}  ({recall:.0%} des 'Visage' attrapées, "
              f"{false_rate:.0%} des gardées marquées à tort)")
    return sug


def main():
    parser = argparse.ArgumentParser(description="Calibration du seuil Visage ?")
    parser.add_argument("--kept", type=int, default=60, help="nombre de chaînes gardées à tester")
    parser.add_argument("--refresh", action="store_true", help="ignorer le cache")
    args = parser.parse_args()

    face_channels, kept_channels = load_groups(args.kept)
    print(f"{len(face_channels)} chaîne(s) supprimées 'Visage', {len(kept_channels)} chaîne(s) gardées à tester.")
    if len(face_channels) < 5:
        print("[!] Moins de 5 chaînes 'Visage' avec des titres en base : la calibration sera peu fiable.")

    from discovery.face_detect import FaceAnalyzer
    analyzer = FaceAnalyzer()
    cache = {} if args.refresh else load_cache()

    face = measure(face_channels, cache, analyzer, args.refresh, "visage")
    save_cache(cache)
    kept = measure(kept_channels, cache, analyzer, args.refresh, "gardée")
    save_cache(cache)

    print(f"\n{len(face)} chaîne(s) 'Visage' et {len(kept)} gardée(s) exploitables "
          f"(au moins {MIN_IMAGES} miniatures).")
    if not face or not kept:
        print("Pas assez de données pour proposer un seuil.")
        return

    sug_same = print_table("même_visage", face, kept, "same_face_ratio")
    print_table("visage (n'importe qui)", face, kept, "face_ratio")

    if sug_same:
        t = sug_same[0]
        flagged = [r for r in kept if r["same_face_ratio"] >= t]
        missed = [r for r in face if r["same_face_ratio"] < t]
        print(f"\nChaînes GARDÉES qui seraient marquées 'Visage ?' au seuil {t:.2f} "
              f"(à vérifier : vrais visages que tu n'as pas encore supprimés, ou fausses alertes) :")
        for r in flagged:
            print(f"  - {r['title']}  (même_visage={r['same_face_ratio']:.2f})")
        if not flagged:
            print("  (aucune)")
        print(f"\nChaînes 'Visage' NON attrapées au seuil {t:.2f} :")
        for r in missed:
            print(f"  - {r['title']}  (même_visage={r['same_face_ratio']:.2f}, visage={r['face_ratio']:.2f})")
        if not missed:
            print("  (aucune)")
        print(f"\nSeuil actuel dans config/face_settings.py : FACE_TAG_SAME_RATIO = {FACE_TAG_SAME_RATIO}")
        print(f"Pour appliquer le seuil proposé, mets FACE_TAG_SAME_RATIO = {t:.2f}")


if __name__ == "__main__":
    main()