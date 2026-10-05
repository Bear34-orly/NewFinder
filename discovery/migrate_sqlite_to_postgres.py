"""
Script ponctuel : copie toutes les chaînes de data/channels.db (SQLite)
vers la base PostgreSQL (Supabase). Les chaînes déjà présentes dans
PostgreSQL ne sont pas écrasées.
"""

import sqlite3
from pathlib import Path

from discovery.database import get_connection, init_db

SQLITE_PATH = Path(__file__).parent.parent / "data" / "channels.db"

COLUMNS = [
    "channel_id", "channel_title", "channel_url", "channel_thumbnail_url",
    "channel_banner_url", "channel_description", "recent_video_ids",
    "channel_status", "market", "subscriber_count", "video_count",
    "strong_video_count", "proven_video_count", "total_videos_checked",
    "density_score", "view_sub_ratio", "detected_language",
    "best_video_title", "best_video_id", "first_discovered_at",
    "last_checked_at",
]


if __name__ == "__main__":
    if not SQLITE_PATH.exists():
        raise SystemExit(f"Fichier introuvable : {SQLITE_PATH}")

    src = sqlite3.connect(SQLITE_PATH)
    src.row_factory = sqlite3.Row
    existing_cols = {r["name"] for r in src.execute("PRAGMA table_info(channels)")}
    cols = [c for c in COLUMNS if c in existing_cols]

    rows = src.execute(f"SELECT {', '.join(cols)} FROM channels").fetchall()
    print(f"{len(rows)} chaînes trouvées dans SQLite.")

    init_db()
    dst = get_connection()
    placeholders = ", ".join(["%s"] * len(cols))
    sql = (
        f"INSERT INTO channels ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT (channel_id) DO NOTHING"
    )

    inserted = 0
    with dst.cursor() as cur:
        for r in rows:
            cur.execute(sql, tuple(r[c] for c in cols))
            inserted += cur.rowcount
    dst.commit()
    dst.close()
    src.close()

    print(f"{inserted} chaînes copiées vers PostgreSQL ({len(rows) - inserted} déjà présentes).")