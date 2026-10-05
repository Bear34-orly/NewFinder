"""
Script ponctuel : récupère l'avatar, la bannière, la description, et
les miniatures récentes pour toutes les chaînes déjà en base qui n'en
ont pas encore, sans relancer un run complet de recherche.
"""

import json
import os

from dotenv import load_dotenv

from discovery.channel_activity import check_channel_age_and_activity
from discovery.channel_stats import get_channel_stats
from discovery.database import get_connection, init_db, list_all_channels

load_dotenv()


if __name__ == "__main__":
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise SystemExit("YOUTUBE_API_KEY manquant dans .env")

    init_db()
    channels = list_all_channels()

    missing = [
        c for c in channels
        if not c.get("channel_thumbnail_url")
        or not c.get("channel_description")
        or not c.get("recent_video_ids")
    ]
    print(f"{len(channels)} chaînes en base, {len(missing)} à compléter.\n")

    if not missing:
        print("Rien à faire, toutes les chaînes sont déjà complètes.")
        raise SystemExit(0)

    channel_ids = [c["channel_id"] for c in missing]
    stats = get_channel_stats(channel_ids, api_key)

    conn = get_connection()
    updated_count = 0

    for c in missing:
        cid = c["channel_id"]
        data = stats.get(cid, {})

        # Pour les miniatures récentes, on a besoin de la playlist
        # uploads -> un appel supplémentaire par chaîne (coût: ~1 unité).
        recent_ids = []
        uploads_playlist_id = data.get("uploads_playlist_id")
        if uploads_playlist_id:
            activity = check_channel_age_and_activity(uploads_playlist_id, api_key)
            if activity["status"] == "OK":
                recent_ids = activity["video_ids"][:4]

        conn.execute(
            """UPDATE channels
               SET channel_thumbnail_url = ?, channel_banner_url = ?,
                   channel_description = ?, recent_video_ids = ?
               WHERE channel_id = ?""",
            (
                data.get("channel_thumbnail_url"),
                data.get("channel_banner_url"),
                data.get("channel_description"),
                json.dumps(recent_ids),
                cid,
            ),
        )
        updated_count += 1
        print(f"  [{updated_count}/{len(missing)}] {c['channel_title']} complété")

    conn.commit()
    conn.close()

    print(f"\n{updated_count} chaînes mises à jour.")