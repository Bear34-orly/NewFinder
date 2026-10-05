"""
Étape 5 (temporaire) : stockage simple des chaînes validées dans une
base SQLite locale.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "channels.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            channel_id TEXT PRIMARY KEY,
            channel_title TEXT,
            channel_url TEXT,
            channel_thumbnail_url TEXT,
            channel_banner_url TEXT,
            channel_description TEXT,
            recent_video_ids TEXT,
            channel_status TEXT,
            market TEXT,
            subscriber_count INTEGER,
            video_count INTEGER,
            strong_video_count INTEGER,
            proven_video_count INTEGER,
            total_videos_checked INTEGER,
            density_score REAL,
            view_sub_ratio REAL,
            detected_language TEXT,
            best_video_title TEXT,
            best_video_id TEXT,
            first_discovered_at TEXT,
            last_checked_at TEXT
        )
    """)
    for column in ("channel_thumbnail_url", "channel_banner_url",
                   "channel_description", "recent_video_ids",
                   "channel_status", "proven_video_count"):
        try:
            col_type = "INTEGER" if column == "proven_video_count" else "TEXT"
            conn.execute(f"ALTER TABLE channels ADD COLUMN {column} {col_type}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()


def save_validated_channels(channels: list[dict], market: str):
    init_db()
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()

    for c in channels:
        recent_ids = json.dumps(c.get("recent_thumbnail_ids", []))

        conn.execute("""
            INSERT INTO channels (
                channel_id, channel_title, channel_url, channel_thumbnail_url,
                channel_banner_url, channel_description, recent_video_ids,
                channel_status, market, subscriber_count, video_count,
                strong_video_count, proven_video_count, total_videos_checked,
                density_score, view_sub_ratio, detected_language,
                best_video_title, best_video_id, first_discovered_at,
                last_checked_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(channel_id) DO UPDATE SET
                subscriber_count = excluded.subscriber_count,
                video_count = excluded.video_count,
                strong_video_count = excluded.strong_video_count,
                proven_video_count = excluded.proven_video_count,
                total_videos_checked = excluded.total_videos_checked,
                density_score = excluded.density_score,
                view_sub_ratio = excluded.view_sub_ratio,
                channel_thumbnail_url = excluded.channel_thumbnail_url,
                channel_banner_url = excluded.channel_banner_url,
                channel_description = excluded.channel_description,
                recent_video_ids = excluded.recent_video_ids,
                channel_status = excluded.channel_status,
                last_checked_at = excluded.last_checked_at
        """, (
            c["channel_id"], c["channel_title"], c["channel_url"],
            c.get("channel_thumbnail_url"), c.get("channel_banner_url"),
            c.get("channel_description"), recent_ids,
            c.get("channel_status", "WATCHLIST"),
            market, c.get("subscriber_count"), c.get("video_count"),
            c.get("strong_video_count"), c.get("proven_video_count", 0),
            c.get("total_videos_checked"),
            c.get("density_score"), c.get("view_sub_ratio"),
            c.get("detected_language"), c.get("title"), c.get("video_id"),
            now, now,
        ))

    conn.commit()
    conn.close()
    print(f"\n{len(channels)} chaînes enregistrées dans {DB_PATH}")


def list_all_channels() -> list[dict]:
    init_db()
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM channels ORDER BY density_score DESC").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["recent_video_ids"] = json.loads(d.get("recent_video_ids") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["recent_video_ids"] = []
        result.append(d)
    return result


def delete_channel(channel_id: str) -> bool:
    init_db()
    conn = get_connection()
    cursor = conn.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted