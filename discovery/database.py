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
        # Requête de recherche qui a trouvé la chaîne (pour juger les mots-clés)
        cur.execute("ALTER TABLE channels ADD COLUMN IF NOT EXISTS query_source TEXT")

        # Chaînes supprimées par l'utilisateur : refus définitif + exemples négatifs
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rejected_channels (
                channel_id TEXT PRIMARY KEY,
                channel_title TEXT,
                market TEXT,
                detected_language TEXT,
                best_video_title TEXT,
                query_source TEXT,
                rejected_at TEXT,
                reject_reason TEXT
            )
        """)
        # Raison du refus : 'face' (a un visage), 'topic' (sujet sans intérêt), 'unknown'
        cur.execute("ALTER TABLE rejected_channels ADD COLUMN IF NOT EXISTS reject_reason TEXT")

        # Indices "visage" (filtre faceless v2) : part des miniatures avec un grand visage,
        # part des miniatures montrant la même personne, part des titres avec un signal de texte.
        for table in ("channels", "rejected_channels"):
            cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS face_ratio DOUBLE PRECISION")
            cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS same_face_ratio DOUBLE PRECISION")
            cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS face_text_ratio DOUBLE PRECISION")
            cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS face_checked_at TEXT")

        # Titres des vidéos fortes (matière première de l'apprentissage des mots-clés)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS video_titles (
                video_id TEXT PRIMARY KEY,
                channel_id TEXT,
                market TEXT,
                language TEXT,
                title TEXT,
                views BIGINT,
                recorded_at TEXT
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_video_titles_channel ON video_titles (channel_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_video_titles_market_lang ON video_titles (market, language)")

        # Mots-clés de recherche par marché et par langue (utilisée à l'étape 4)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS keywords (
                market TEXT NOT NULL,
                language TEXT NOT NULL,
                query TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'seed',
                source TEXT,
                times_run INTEGER NOT NULL DEFAULT 0,
                channels_found INTEGER NOT NULL DEFAULT 0,
                validated_found INTEGER NOT NULL DEFAULT 0,
                created_at TEXT,
                last_run_at TEXT,
                PRIMARY KEY (market, language, query)
            )
        """)

        # Carte du radar : une ligne par "case" (catégorie + durée + tranche de dates)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS radar_cells (
                category TEXT NOT NULL,
                duration TEXT NOT NULL,
                slice_start TEXT NOT NULL,
                slice_end TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'open',
                pages_done INTEGER NOT NULL DEFAULT 0,
                page_token TEXT,
                videos_seen INTEGER NOT NULL DEFAULT 0,
                videos_qualifying INTEGER NOT NULL DEFAULT 0,
                created_at TEXT,
                finished_at TEXT,
                last_run_at TEXT,
                PRIMARY KEY (category, duration, slice_start, slice_end)
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
        cur.execute("SELECT channel_id FROM rejected_channels")
        rejected = {r[0] for r in cur.fetchall()}
        skipped = 0
        saved = 0

        for c in channels:
            if c["channel_id"] in rejected:
                skipped += 1
                continue
            saved += 1
            recent_ids = json.dumps(c.get("recent_thumbnail_ids", []))

            cur.execute("""
                INSERT INTO channels (
                    channel_id, channel_title, channel_url, channel_thumbnail_url,
                    channel_banner_url, channel_description, recent_video_ids,
                    channel_status, market, subscriber_count, video_count,
                    strong_video_count, proven_video_count, total_videos_checked,
                    density_score, view_sub_ratio, detected_language,
                    best_video_title, best_video_id, first_discovered_at,
                    last_checked_at, query_source,
                    face_ratio, same_face_ratio, face_text_ratio, face_checked_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (channel_id) DO UPDATE SET
                    face_ratio = COALESCE(EXCLUDED.face_ratio, channels.face_ratio),
                    same_face_ratio = COALESCE(EXCLUDED.same_face_ratio, channels.same_face_ratio),
                    face_text_ratio = COALESCE(EXCLUDED.face_text_ratio, channels.face_text_ratio),
                    face_checked_at = COALESCE(EXCLUDED.face_checked_at, channels.face_checked_at),
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
                    last_checked_at = EXCLUDED.last_checked_at,
                    query_source = COALESCE(channels.query_source, EXCLUDED.query_source)
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
                now, now, c.get("query_source"),
                c.get("face_ratio"), c.get("same_face_ratio"),
                c.get("face_text_ratio"), c.get("face_checked_at"),
            ))

            _insert_titles(cur, c["channel_id"], market, c.get("detected_language"),
                           (c.get("strong_videos") or []) + (c.get("proven_videos") or []), now)

    conn.commit()
    conn.close()
    msg = f"\n{saved} chaînes enregistrées dans la base PostgreSQL."
    if skipped:
        msg += f" ({skipped} ignorée(s) car refusées.)"
    print(msg)


def _insert_titles(cur, channel_id, market, language, videos, now):
    """Enregistre (ou met à jour) les titres de vidéos fortes d'une chaîne."""
    seen = set()
    for v in videos:
        vid, title = v.get("video_id"), v.get("title")
        if not vid or not title or vid in seen:
            continue
        seen.add(vid)
        cur.execute("""
            INSERT INTO video_titles (video_id, channel_id, market, language, title, views, recorded_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (video_id) DO UPDATE SET
                views = EXCLUDED.views, title = EXCLUDED.title, recorded_at = EXCLUDED.recorded_at
        """, (vid, channel_id, market, language, title, v.get("view_count"), now))


def save_video_titles(channel_id: str, market: str, language: str, videos: list) -> int:
    """Utilisée par refresh.py : enregistre les titres de vidéos fortes d'une chaîne."""
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            _insert_titles(cur, channel_id, market, language, videos, now)
        conn.commit()
    return len({v.get("video_id") for v in videos if v.get("video_id") and v.get("title")})


def list_rejected_ids() -> set:
    """Identifiants des chaînes supprimées par l'utilisateur (refus définitif)."""
    init_db()
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT channel_id FROM rejected_channels")
            return {r[0] for r in cur.fetchall()}


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


def delete_channel(channel_id: str, reason: str = "unknown") -> bool:
    """
    Supprime la chaîne ET la note comme refusée : elle ne reviendra plus jamais.
    reason : 'face' (la chaîne a un visage), 'topic' (sujet sans intérêt) ou 'unknown'.
    """
    if reason not in ("face", "topic"):
        reason = "unknown"
    init_db()
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO rejected_channels (channel_id, channel_title, market, detected_language,
                                               best_video_title, query_source, rejected_at, reject_reason,
                                               face_ratio, same_face_ratio, face_text_ratio, face_checked_at)
                SELECT channel_id, channel_title, market, detected_language,
                       best_video_title, query_source, %s, %s,
                       face_ratio, same_face_ratio, face_text_ratio, face_checked_at
                FROM channels WHERE channel_id = %s
                ON CONFLICT (channel_id) DO NOTHING
            """, (datetime.now(timezone.utc).isoformat(), reason, channel_id))
            cur.execute("DELETE FROM channels WHERE channel_id = %s", (channel_id,))
            deleted = cur.rowcount > 0
        conn.commit()
    return deleted


def list_channel_refs(market: str | None = None) -> list[dict]:
    """Liste légère des chaînes (id, titre, marché, abonnés) pour le rafraîchissement."""
    init_db()
    with pooled_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if market:
                cur.execute("SELECT channel_id, channel_title, market, detected_language, subscriber_count "
                            "FROM channels WHERE market = %s ORDER BY last_checked_at ASC NULLS FIRST", (market,))
            else:
                cur.execute("SELECT channel_id, channel_title, market, detected_language, subscriber_count "
                            "FROM channels ORDER BY last_checked_at ASC NULLS FIRST")
            return [dict(r) for r in cur.fetchall()]


def update_channel_stats(channel_id: str, stats: dict) -> bool:
    """
    Met à jour uniquement les chiffres d'une chaîne déjà enregistrée.
    N'efface rien et ne change ni le marché, ni la date de découverte, ni le titre de la meilleure vidéo.
    """
    init_db()
    recent_ids = json.dumps(stats.get("recent_thumbnail_ids", []))
    now = datetime.now(timezone.utc).isoformat()
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE channels SET
                    subscriber_count = %s,
                    video_count = %s,
                    strong_video_count = %s,
                    proven_video_count = %s,
                    total_videos_checked = %s,
                    density_score = %s,
                    channel_status = %s,
                    recent_video_ids = %s,
                    last_checked_at = %s
                WHERE channel_id = %s
            """, (
                stats.get("subscriber_count"), stats.get("video_count"),
                stats.get("strong_video_count"), stats.get("proven_video_count"),
                stats.get("total_videos_checked"), stats.get("density_score"),
                stats.get("channel_status"), recent_ids, now, channel_id,
            ))
            updated = cur.rowcount > 0
        conn.commit()
    return updated


def list_channels_for_face_scan(refresh: bool = False, market: str | None = None,
                                max_videos: int = 6) -> list[dict]:
    """
    Chaînes à analyser pour les visages : par défaut celles jamais analysées.
    Pour chaque chaîne : ses vidéos les plus vues (table video_titles), sinon ses
    vidéos récentes, et tous ses titres (pour le score de texte).
    Retourne [{channel_id, channel_title, language, titles, video_ids}].
    """
    init_db()
    with pooled_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            sql = ("SELECT channel_id, channel_title, detected_language, best_video_title, "
                   "recent_video_ids FROM channels WHERE TRUE")
            params = []
            if not refresh:
                sql += " AND face_checked_at IS NULL"
            if market:
                sql += " AND market = %s"
                params.append(market)
            cur.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]
            if not rows:
                return []

            ids = [r["channel_id"] for r in rows]
            cur.execute("""
                SELECT channel_id, video_id, title FROM (
                    SELECT channel_id, video_id, title,
                           ROW_NUMBER() OVER (PARTITION BY channel_id ORDER BY views DESC NULLS LAST) AS rn
                    FROM video_titles WHERE channel_id = ANY(%s)
                ) t ORDER BY channel_id, rn
            """, (ids,))
            top, titles = {}, {}
            for r in cur.fetchall():
                titles.setdefault(r["channel_id"], []).append(r["title"])
                if len(top.setdefault(r["channel_id"], [])) < max_videos:
                    top[r["channel_id"]].append(r["video_id"])

    result = []
    for r in rows:
        vids = top.get(r["channel_id"])
        if not vids:
            try:
                vids = json.loads(r.get("recent_video_ids") or "[]")
            except (json.JSONDecodeError, TypeError):
                vids = []
        all_titles = list(titles.get(r["channel_id"], []))
        if r.get("best_video_title"):
            all_titles.append(r["best_video_title"])
        result.append({"channel_id": r["channel_id"], "channel_title": r["channel_title"] or r["channel_id"],
                       "language": r.get("detected_language"), "titles": all_titles,
                       "video_ids": (vids or [])[:max_videos]})
    return result


def update_face_scores(channel_id: str, face_ratio: float | None = None,
                       same_face_ratio: float | None = None,
                       text_ratio: float | None = None) -> bool:
    """
    Enregistre les indices "visage" d'une chaîne déjà enregistrée (ne touche à rien d'autre).
    Les valeurs absentes (None) ne modifient rien. Les indices de miniatures
    (face_ratio, same_face_ratio) posent aussi la date d'analyse.
    """
    init_db()
    sets, params = [], []
    if face_ratio is not None and same_face_ratio is not None:
        sets += ["face_ratio = %s", "same_face_ratio = %s", "face_checked_at = %s"]
        params += [face_ratio, same_face_ratio, datetime.now(timezone.utc).isoformat()]
    if text_ratio is not None:
        sets.append("face_text_ratio = %s")
        params.append(text_ratio)
    if not sets:
        return False
    params.append(channel_id)
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE channels SET {', '.join(sets)} WHERE channel_id = %s", params)
            updated = cur.rowcount > 0
        conn.commit()
    return updated


# ---------------------------------------------------------------------------
# Moteur de mots-clés (étape 4)
# ---------------------------------------------------------------------------

def existing_channel_ids(channel_ids: list[str]) -> set:
    """Parmi ces identifiants, ceux qui sont DÉJÀ dans la table channels."""
    if not channel_ids:
        return set()
    init_db()
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT channel_id FROM channels WHERE channel_id = ANY(%s)", (list(channel_ids),))
            return {r[0] for r in cur.fetchall()}


def load_keyword_corpus(market: str, language: str) -> tuple[list[dict], list[dict]]:
    """
    Titres servant à apprendre des mots-clés pour un marché et une langue.

    Retourne (positifs, négatifs) :
      - positifs : titres des vidéos fortes des chaînes ENCORE en base ;
      - négatifs : titres des chaînes supprimées par l'utilisateur pour 'face' ou 'topic'
        (on ne veut pas apprendre ce qui ramène ce type de chaînes).
    Chaque ligne : {channel_id, title, views}. Les chaînes supprimées sans raison ('unknown')
    sont ignorées des deux côtés.
    """
    init_db()
    with pooled_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT vt.channel_id, vt.title, vt.views
                FROM video_titles vt
                JOIN channels c ON c.channel_id = vt.channel_id
                WHERE vt.market = %s AND vt.language = %s AND vt.title IS NOT NULL
            """, (market, language))
            positives = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT vt.channel_id, vt.title, vt.views
                FROM video_titles vt
                JOIN rejected_channels r ON r.channel_id = vt.channel_id
                WHERE vt.market = %s AND vt.language = %s AND vt.title IS NOT NULL
                  AND r.reject_reason IN ('face', 'topic')
            """, (market, language))
            negatives = [dict(r) for r in cur.fetchall()]

            # Meilleure vidéo des chaînes refusées (au cas où leurs titres n'aient pas été enregistrés)
            cur.execute("""
                SELECT channel_id, best_video_title AS title, 0 AS views
                FROM rejected_channels
                WHERE market = %s AND detected_language = %s AND best_video_title IS NOT NULL
                  AND reject_reason IN ('face', 'topic')
            """, (market, language))
            negatives += [dict(r) for r in cur.fetchall()]
    return positives, negatives


def list_keywords(market: str | None = None, language: str | None = None,
                  statuses: list[str] | None = None) -> list[dict]:
    """Mots-clés appris, bannis ou retirés (les seeds sont dans la configuration, pas ici)."""
    init_db()
    sql = ("SELECT market, language, query, status, source, times_run, channels_found, "
           "validated_found, created_at, last_run_at FROM keywords WHERE TRUE")
    params = []
    if market:
        sql += " AND market = %s"
        params.append(market)
    if language:
        sql += " AND language = %s"
        params.append(language)
    if statuses:
        sql += " AND status = ANY(%s)"
        params.append(list(statuses))
    sql += " ORDER BY market, language, status, created_at"
    with pooled_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]


def add_keyword(market: str, language: str, query: str, status: str = "test",
                source: str = "learned") -> bool:
    """Ajoute un mot-clé (sans rien écraser s'il existe déjà). Retourne True si ajouté."""
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO keywords (market, language, query, status, source, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (market, language, query) DO NOTHING
            """, (market, language, query, status, source, now))
            added = cur.rowcount > 0
        conn.commit()
    return added


def ban_keyword(market: str, language: str, query: str) -> None:
    """Interdit un mot-clé : il ne sera plus jamais proposé ni testé."""
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO keywords (market, language, query, status, source, created_at)
                VALUES (%s, %s, %s, 'banned', 'manual', %s)
                ON CONFLICT (market, language, query) DO UPDATE SET status = 'banned'
            """, (market, language, query, now))
        conn.commit()


def unban_keyword(market: str, language: str, query: str) -> bool:
    """Lève l'interdiction (la ligne est supprimée : le mot-clé pourra être reproposé)."""
    init_db()
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM keywords WHERE market = %s AND language = %s AND query = %s "
                        "AND status = 'banned'", (market, language, query))
            removed = cur.rowcount > 0
        conn.commit()
    return removed


def record_keyword_run(market: str, language: str, query: str, channels_found: int,
                       validated_found: int, new_status: str, new_source: str | None = None) -> None:
    """Ajoute les résultats d'une passe à un mot-clé et met à jour son statut (et son origine si demandé)."""
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE keywords SET
                    times_run = times_run + 1,
                    channels_found = channels_found + %s,
                    validated_found = validated_found + %s,
                    status = %s,
                    source = COALESCE(%s, source),
                    last_run_at = %s
                WHERE market = %s AND language = %s AND query = %s
            """, (channels_found, validated_found, new_status, new_source, now, market, language, query))
        conn.commit()


def load_radar_corpus(language: str) -> list[dict]:
    """
    Titres des vidéos fortes des chaînes trouvées par le radar (channels.query_source = 'radar'),
    pour une langue. Chaque ligne : {channel_id, market, title, views}.
    """
    init_db()
    with pooled_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT vt.channel_id, c.market AS market, vt.title, vt.views
                FROM video_titles vt
                JOIN channels c ON c.channel_id = vt.channel_id
                WHERE c.query_source = 'radar' AND vt.language = %s AND vt.title IS NOT NULL
            """, (language,))
            return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Radar : carte des cases explorées
# ---------------------------------------------------------------------------

_CELL_COLS = ("category", "duration", "slice_start", "slice_end", "state", "pages_done", "page_token",
              "videos_seen", "videos_qualifying", "created_at", "finished_at", "last_run_at")


def radar_load_cells() -> list[dict]:
    init_db()
    with pooled_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT " + ", ".join(_CELL_COLS) + " FROM radar_cells")
            return [dict(r) for r in cur.fetchall()]


def radar_save_cell(cell: dict) -> None:
    """Crée ou met à jour une case (clé : category, duration, slice_start, slice_end)."""
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    values = {
        "category": cell["category"], "duration": cell["duration"],
        "slice_start": cell["slice_start"], "slice_end": cell["slice_end"],
        "state": cell.get("state", "open"), "pages_done": cell.get("pages_done", 0),
        "page_token": cell.get("page_token"), "videos_seen": cell.get("videos_seen", 0),
        "videos_qualifying": cell.get("videos_qualifying", 0),
        "created_at": cell.get("created_at") or now, "finished_at": cell.get("finished_at"),
        "last_run_at": cell.get("last_run_at"),
    }
    cols = list(values.keys())
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols
                        if c not in ("category", "duration", "slice_start", "slice_end", "created_at"))
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO radar_cells (" + ", ".join(cols) + ") VALUES (" + ", ".join(["%s"] * len(cols)) + ") "
                "ON CONFLICT (category, duration, slice_start, slice_end) DO UPDATE SET " + updates,
                [values[c] for c in cols])
        conn.commit()


# ---------------------------------------------------------------------------
# Radar : classement des chaînes dans les marchés
# ---------------------------------------------------------------------------

def load_market_corpus(language: str) -> list[dict]:
    """Titres des vidéos fortes des chaînes classées dans un vrai marché par la découverte habituelle (pas par le radar)."""
    init_db()
    with pooled_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT c.market AS market, vt.channel_id, vt.title
                FROM video_titles vt
                JOIN channels c ON c.channel_id = vt.channel_id
                WHERE c.market IS NOT NULL AND c.market <> 'radar'
                  AND COALESCE(c.query_source, '') <> 'radar'
                  AND vt.language = %s AND vt.title IS NOT NULL
            """, (language,))
            return [dict(r) for r in cur.fetchall()]


def list_unclassified_channels(language: str) -> list[dict]:
    """Chaînes trouvées par le radar (quel que soit leur marché actuel), avec tous leurs titres connus."""
    init_db()
    with pooled_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT channel_id, channel_title, best_video_title, channel_description, market
                FROM channels WHERE query_source = 'radar' AND detected_language = %s
            """, (language,))
            chans = [dict(r) for r in cur.fetchall()]
            ids = [c["channel_id"] for c in chans]
            titles = {}
            if ids:
                cur.execute("SELECT channel_id, title FROM video_titles WHERE channel_id = ANY(%s)", (ids,))
                for r in cur.fetchall():
                    titles.setdefault(r["channel_id"], []).append(r["title"])
    for c in chans:
        c["titles"] = titles.get(c["channel_id"], [])
    return chans


def set_channel_market(channel_id: str, market: str) -> None:
    """Déplace une chaîne (et ses titres de vidéos) vers un autre marché."""
    init_db()
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE channels SET market = %s WHERE channel_id = %s", (market, channel_id))
            cur.execute("UPDATE video_titles SET market = %s WHERE channel_id = %s", (market, channel_id))
        conn.commit()
