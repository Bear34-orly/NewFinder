"""
Calcule les indices "visage" des chaînes DÉJÀ enregistrées en base
(les nouvelles chaînes sont analysées pendant la découverte).

Deux indices, tous deux gratuits (aucun quota YouTube) :
  - texte  : part des titres qui ressemblent à une interview / un format avec visage
             (mots comme "guest", numéros d'épisode, mots censurés...)
  - images : visages sur les miniatures (OpenCV, voir face_detect.py)

Chaque chaîne est enregistrée dès qu'elle est analysée : si le programme
s'arrête, ce qui est fait est conservé et la relance reprend où il en était.

Usage :
    python -m discovery.rescan_faces                 (chaînes jamais analysées : texte + images)
    python -m discovery.rescan_faces --text-only     (seulement le texte, toutes les chaînes, sans OpenCV)
    python -m discovery.rescan_faces --refresh       (tout réanalyser)
    python -m discovery.rescan_faces --market history
    python -m discovery.rescan_faces --limit 50      (seulement 50 chaînes)
"""

import argparse

from config.face_settings import FACE_TAG_SAME_RATIO
from config.faceless_signals import DOUBTFUL_RATIO
from discovery.database import list_channels_for_face_scan, update_face_scores
from discovery.faceless_filter import text_face_score


def main():
    parser = argparse.ArgumentParser(description="Analyse des visages sur les chaînes déjà en base")
    parser.add_argument("--refresh", action="store_true", help="réanalyser aussi les chaînes déjà analysées")
    parser.add_argument("--text-only", action="store_true",
                        help="seulement le score de texte (toutes les chaînes, sans images ni OpenCV)")
    parser.add_argument("--market", default=None, help="un seul marché")
    parser.add_argument("--limit", type=int, default=None, help="nombre maximum de chaînes")
    args = parser.parse_args()

    channels = list_channels_for_face_scan(refresh=args.refresh or args.text_only, market=args.market)
    if args.limit:
        channels = channels[:args.limit]
    print(f"{len(channels)} chaîne(s) à analyser.")
    if not channels:
        return

    analyzer = None
    analyze_channel = None
    if not args.text_only:
        from discovery.face_detect import FaceAnalyzer, analyze_channel
        analyzer = FaceAnalyzer()

    flagged_text = flagged_face = done = 0
    for i, ch in enumerate(channels, 1):
        label = f"  [{i}/{len(channels)}] {ch['channel_title'][:40]:<40}"

        # 1) Texte
        text = text_face_score(ch["titles"], ch["channel_title"], ch["language"])
        update_face_scores(ch["channel_id"], text_ratio=text["ratio"])
        text_mark = text["ratio"] >= DOUBTFUL_RATIO and text["total"] >= 3
        if text_mark:
            flagged_text += 1
        line = f"{label} titres={text['ratio']:.2f}{' (signal)' if text_mark else ''}"

        # 2) Miniatures
        if analyzer is not None:
            try:
                res = analyze_channel(ch["video_ids"], analyzer)
            except Exception as e:
                print(f"{line}  miniatures : analyse impossible ({type(e).__name__})")
                done += 1
                continue
            if res["images"] == 0:
                print(f"{line}  miniatures : aucune récupérée")
                done += 1
                continue
            update_face_scores(ch["channel_id"], res["face_ratio"], res["same_face_ratio"])
            face_mark = res["same_face_ratio"] >= FACE_TAG_SAME_RATIO
            if face_mark:
                flagged_face += 1
            line += (f"  images={res['images']} visage={res['face_ratio']:.2f} "
                     f"même_visage={res['same_face_ratio']:.2f}{' -> Visage ?' if face_mark else ''}")
        print(line)
        done += 1

    print(f"\n{done} chaîne(s) analysée(s).")
    print(f"  Signal de texte (>= {DOUBTFUL_RATIO:.0%} des titres) : {flagged_text}")
    if analyzer is not None:
        print(f"  Même visage (>= {FACE_TAG_SAME_RATIO:.0%} des miniatures) : {flagged_face}")


if __name__ == "__main__":
    main()