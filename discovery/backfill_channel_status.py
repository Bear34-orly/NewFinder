"""
Script ponctuel : recalcule channel_status (PROVEN/WATCHLIST) et
proven_video_count pour toutes les chaînes déjà en base qui n'ont pas
encore ce statut, sans refaire toute la recherche depuis le début.

Réutilise l'historique de vidéos déjà validé — relit juste les
statistiques de vues des vidéos de chaque chaîne pour appliquer le
nouveau critère (>=100K vues absolu).
"""

import os

from dotenv import load_dotenv

from discovery.channel_activity import (
    check_channel_age_and_activity,
    classify_videos,
    get_video_stats_batch,
)
from discovery.channel_stats import get_channel_stats
from discovery.database import get_connection, init_db, list_all_channels

load_dotenv()


if __name__ == "__main__":
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise SystemExit("YOUTUBE_API_KEY manquant dans .env")

    init_db()
    channels = list_all_channels()

    missing = [c for c in channels if not c.get("channel_status")]
    print(f"{len(channels)} chaînes en base, {len(missing)} sans statut à recalculer.\n")

    if not missing:
        print("Rien à faire, toutes les chaînes ont déjà un statut.")
        raise SystemExit(0)

    # On a besoin de la playlist uploads pour chaque chaîne (pas
    # stockée directement en base) -> on la redemande via channels.list.
    channel_ids = [c["channel_id"] for c in missing]
    fresh_stats = get_channel_stats(channel_ids, api_key)

    conn = get_connection()
    updated_count = 0

    for c in missing:
        cid = c["channel_id"]
        uploads_playlist_id = fresh_stats.get(cid, {}).get("uploads_playlist_id")

        if not uploads_playlist_id:
            print(f"  [!] {c['channel_title']}: playlist introuvable, ignorée")
            continue

        activity = check_channel_age_and_activity(uploads_playlist_id, api_key)
        if activity["status"] != "OK":
            # La chaîne ne passerait plus le critère d'âge aujourd'hui,
            # mais on ne la supprime pas (elle a été validée à l'époque) :
            # on lui donne juste un statut neutre.
            print(f"  [!] {c['channel_title']}: ne repasse plus le critère d'âge ({activity['status']}), statut = WATCHLIST par défaut")
            conn.execute(
                "UPDATE channels SET channel_status = 'WATCHLIST', proven_video_count = 0 WHERE channel_id = ?",
                (cid,),
            )
            updated_count += 1
            continue

        video_stats = get_video_stats_batch(activity["video_ids"], api_key)
        classified = classify_videos(video_stats, c.get("subscriber_count"))

        channel_status = "PROVEN" if len(classified["proven"]) >= 3 else "WATCHLIST"

        conn.execute(
            "UPDATE channels SET channel_status = ?, proven_video_count = ? WHERE channel_id = ?",
            (channel_status, len(classified["proven"]), cid),
        )
        updated_count += 1
        print(f"  [{updated_count}/{len(missing)}] {c['channel_title']} -> {channel_status} "
              f"({len(classified['proven'])} vidéos >=100K)")

    conn.commit()
    conn.close()

    print(f"\n{updated_count} chaînes mises à jour.")