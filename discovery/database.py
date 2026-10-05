"""
Stockage des chaînes validées dans PostgreSQL (Supabase).
L'adresse de connexion est lue dans DATABASE_URL (fichier .env en local,
variable d'environnement sur Render).

Les fonctions utilisées par le site (lecture, suppression) réutilisent des
connexions déjà ouvertes (pool) pour éviter la latence d'une nouvelle
connexion à chaque clic.
"""

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

_initialized = False
_pool = None


def get_connection():
    """Connexion directe (utilisée par les scripts ponctuels)."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL manquant (fichier .env ou variable d'environnement).")
    return psycopg2.connect(DATABASE_URL, connect_timeout=15)


def _get_pool():
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL manquant (fichier .env ou variable d'environnement).")
        _pool = pool.ThreadedConnectionPool(1, 5, DATABASE_URL, connect_timeout=15)
    return _pool


@contextmanager
def pooled_connection():
    """Emprunte une connexion du pool et la rend à la fin."""
    p = _get_pool()
    conn = p.getconn()
    broken = False
    try:
        yield conn
    except psycopg2.OperationalError:
        broken = True
        raise
    finally:
        if broken or conn.closed:
            p.putconn(conn, close=True)
        else:
            try:
                conn.rollback()
            except Exception:
                pass
            p.putconn(conn)


def init_db():
    global _initialized
    if _initialized:
        return
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
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
                subscriber_count BIGINT,
                video_count INTEGER,
                strong_video_count INTEGER,
                proven_video_count INTEGER,
                total_videos_checked INTEGER,
                density_score DOUBLE PRECISION,
                view_sub_ratio DOUBLE PRECISION,
                detected_language TEXT,
                best_video_title TEXT,
                best_video_id TEXT,
                first_discovered_at TEXT,
                last_checked_at TEXT
            )
        """)
    conn.commit()
    conn.close()
    _initialized = True


def save_validated_channels(channels: list[dict], market: str):
    init_db()
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()

    with conn.cursor() as cur:
        for c in channels:
            recent_ids = json.dumps(c.get("recent_thumbnail_ids", []))

            cur.execute("""
                INSERT INTO channels (
                    channel_id, channel_title, channel_url, channel_thumbnail_url,
                    channel_banner_url, channel_description, recent_video_ids,
                    channel_status, market, subscriber_count, video_count,
                    strong_video_count, proven_video_count, total_videos_checked,
                    density_score, view_sub_ratio, detected_language,
                    best_video_title, best_video_id, first_discovered_at,
                    last_checked_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                          %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (channel_id) DO UPDATE SET
                    subscriber_count = EXCLUDED.subscriber_count,
                    video_count = EXCLUDED.video_count,
                    strong_video_count = EXCLUDED.strong_video_count,
                    proven_video_count = EXCLUDED.proven_video_count,
                    total_videos_checked = EXCLUDED.total_videos_checked,
                    density_score = EXCLUDED.density_score,
                    view_sub_ratio = EXCLUDED.view_sub_ratio,
                    channel_thumbnail_url = EXCLUDED.channel_thumbnail_url,
                    channel_banner_url = EXCLUDED.channel_banner_url,
                    channel_description = EXCLUDED.channel_description,
                    recent_video_ids = EXCLUDED.recent_video_ids,
                    channel_status = EXCLUDED.channel_status,
                    last_checked_at = EXCLUDED.last_checked_at
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
    print(f"\n{len(channels)} chaînes enregistrées dans la base PostgreSQL.")


def list_all_channels() -> list[dict]:
    init_db()
    with pooled_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM channels ORDER BY density_score DESC NULLS LAST")
            rows = cur.fetchall()

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
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM channels WHERE channel_id = %s", (channel_id,))
            deleted = cur.rowcount > 0
        conn.commit()
    return deleted