"""
Stockage du module Concurrence (PostgreSQL, même base que le Niche Finder).

Tables :
  access_codes       un code d'accès par personne (créé par toi)
  my_channels        les chaînes que chaque personne veut analyser
  analyses           chaque analyse (statut, résultat en JSON)
  channel_snapshots  mesures datées d'une chaîne : permet de voir l'évolution
"""

import json
import secrets
from datetime import datetime, timedelta, timezone

import psycopg2.extras

from discovery.database import get_connection, pooled_connection

_initialized = False


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_tables():
    global _initialized
    if _initialized:
        return
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS access_codes (
                code TEXT PRIMARY KEY,
                name TEXT,
                daily_limit INTEGER DEFAULT 3,
                created_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS my_channels (
                id SERIAL PRIMARY KEY,
                owner_code TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                channel_title TEXT,
                channel_url TEXT,
                thumbnail TEXT,
                market TEXT,
                added_at TEXT,
                UNIQUE (owner_code, channel_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id SERIAL PRIMARY KEY,
                owner_code TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                status TEXT,
                progress TEXT,
                error TEXT,
                units_used INTEGER DEFAULT 0,
                data TEXT,
                created_at TEXT,
                finished_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS channel_snapshots (
                id SERIAL PRIMARY KEY,
                channel_id TEXT NOT NULL,
                taken_at TEXT,
                subscribers BIGINT,
                total_views BIGINT,
                video_count INTEGER,
                median_views DOUBLE PRECISION
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_snap_channel ON channel_snapshots (channel_id, taken_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_analyses_owner ON analyses (owner_code, created_at)")
    conn.commit()
    conn.close()
    _initialized = True


# ---------------------------------------------------------------- codes d'accès

def create_code(name: str, daily_limit: int = 3) -> str:
    init_tables()
    code = secrets.token_urlsafe(8)
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO access_codes (code, name, daily_limit, created_at) VALUES (%s, %s, %s, %s)",
                (code, name, daily_limit, now_iso()),
            )
        conn.commit()
    return code


def get_code(code: str):
    if not code:
        return None
    init_tables()
    with pooled_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM access_codes WHERE code = %s", (code,))
            row = cur.fetchone()
    return dict(row) if row else None


def list_codes() -> list:
    init_tables()
    with pooled_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT code, name, daily_limit, created_at FROM access_codes ORDER BY created_at")
            return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------- mes chaînes

def add_channel(owner: str, info: dict, market):
    init_tables()
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO my_channels (owner_code, channel_id, channel_title, channel_url, thumbnail, market, added_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (owner_code, channel_id) DO UPDATE SET
                    channel_title = EXCLUDED.channel_title,
                    thumbnail = EXCLUDED.thumbnail,
                    market = EXCLUDED.market
            """, (owner, info["channel_id"], info["title"], info["url"], info.get("thumbnail"), market, now_iso()))
        conn.commit()


def list_channels(owner: str) -> list:
    init_tables()
    with pooled_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM my_channels WHERE owner_code = %s ORDER BY added_at DESC", (owner,))
            return [dict(r) for r in cur.fetchall()]


def get_channel(owner: str, channel_id: str):
    init_tables()
    with pooled_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM my_channels WHERE owner_code = %s AND channel_id = %s", (owner, channel_id)
            )
            row = cur.fetchone()
    return dict(row) if row else None


def delete_channel(owner: str, channel_id: str) -> bool:
    init_tables()
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM my_channels WHERE owner_code = %s AND channel_id = %s", (owner, channel_id))
            deleted = cur.rowcount > 0
            cur.execute("DELETE FROM analyses WHERE owner_code = %s AND channel_id = %s", (owner, channel_id))
        conn.commit()
    return deleted


# ---------------------------------------------------------------- analyses

def create_analysis(owner: str, channel_id: str) -> int:
    init_tables()
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO analyses (owner_code, channel_id, status, progress, created_at)
                VALUES (%s, %s, 'running', 'Démarrage...', %s) RETURNING id
            """, (owner, channel_id, now_iso()))
            new_id = cur.fetchone()[0]
        conn.commit()
    return new_id


def update_analysis(analysis_id: int, **fields):
    """Champs autorisés : status, progress, error, units_used, data (dict), finished_at."""
    allowed = {"status", "progress", "error", "units_used", "data", "finished_at"}
    sets, values = [], []
    for k, v in fields.items():
        if k not in allowed:
            raise ValueError(k)
        if k == "data" and v is not None:
            v = json.dumps(v, ensure_ascii=False)
        sets.append(f"{k} = %s")
        values.append(v)
    if not sets:
        return
    values.append(analysis_id)
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE analyses SET {', '.join(sets)} WHERE id = %s", values)
        conn.commit()


def get_analysis(owner: str, analysis_id: int):
    init_tables()
    with pooled_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM analyses WHERE id = %s AND owner_code = %s", (analysis_id, owner))
            row = cur.fetchone()
    if not row:
        return None
    d = dict(row)
    d["data"] = json.loads(d["data"]) if d.get("data") else None
    return d


def list_analyses(owner: str, channel_id: str, limit: int = 10) -> list:
    init_tables()
    with pooled_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, status, progress, error, units_used, created_at, finished_at
                FROM analyses WHERE owner_code = %s AND channel_id = %s
                ORDER BY id DESC LIMIT %s
            """, (owner, channel_id, limit))
            return [dict(r) for r in cur.fetchall()]


def count_analyses_today(owner: str) -> int:
    init_tables()
    start = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM analyses WHERE owner_code = %s AND created_at >= %s", (owner, start)
            )
            return cur.fetchone()[0]


def has_running(owner: str) -> bool:
    init_tables()
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM analyses WHERE owner_code = %s AND status = 'running' LIMIT 1", (owner,))
            return cur.fetchone() is not None


def mark_stale_running(max_minutes: int = 15):
    """Une analyse restée 'running' trop longtemps (serveur redémarré) passe en erreur."""
    init_tables()
    limit = (datetime.now(timezone.utc) - timedelta(minutes=max_minutes)).isoformat()
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE analyses SET status = 'error',
                    error = 'Analyse interrompue (le serveur a redémarré). Relance-la.'
                WHERE status = 'running' AND created_at < %s
            """, (limit,))
        conn.commit()


# ---------------------------------------------------------------- snapshots

def previous_snapshot(channel_id: str, older_than_hours: float = 1.0):
    init_tables()
    limit = (datetime.now(timezone.utc) - timedelta(hours=older_than_hours)).isoformat()
    with pooled_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM channel_snapshots WHERE channel_id = %s AND taken_at < %s
                ORDER BY taken_at DESC LIMIT 1
            """, (channel_id, limit))
            row = cur.fetchone()
    return dict(row) if row else None


def add_snapshot(profile: dict):
    init_tables()
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO channel_snapshots (channel_id, taken_at, subscribers, total_views, video_count, median_views)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (profile["channel_id"], now_iso(), profile.get("subscribers"),
                  profile.get("total_views"), profile.get("video_count"), profile.get("median_views")))
        conn.commit()
