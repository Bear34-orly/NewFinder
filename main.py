import os
import re
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# ============================================================
# CONFIGURATION
# ============================================================

MARKETS = [
    "History",
    "Finance",
    "Fitness",
    "Health",
]


# ============================================================
# DISCOVERY
# ============================================================

# On recherche les vidéos publiées dans les 60 derniers jours.
DISCOVERY_DAYS = 60

# Une vidéo doit avoir au moins 200K vues pour devenir
# une vidéo candidate.
MIN_DISCOVERY_VIDEO_VIEWS = 200_000

# Une vidéo doit être PLUS LONGUE que 3 minutes.
#
# 3 minutes = 180 secondes.
#
# Donc :
# 180 secondes exactement -> rejet
# 181 secondes             -> accepté
#
# Ce filtre permet d'écarter les Shorts de notre discovery.
MIN_LONG_VIDEO_SECONDS = 180


# ============================================================
# FILTRES CHAÎNE
# ============================================================

# Une chaîne avec plus de 50 vidéos est rejetée.
MAX_CHANNEL_VIDEOS = 50

# La chaîne doit avoir au moins 1 million de vues totales.
MIN_CHANNEL_VIEWS = 1_000_000

# La dernière vidéo doit dater de 15 jours maximum.
MAX_LAST_UPLOAD_DAYS = 15


# ============================================================
# FILTRE VIRALITÉ
# ============================================================

# La chaîne doit posséder au moins 3 vidéos ayant
# 200K vues ou plus.
MIN_VIRAL_VIDEOS = 3
MIN_VIRAL_VIDEO_VIEWS = 200_000


# ============================================================
# RECHERCHE
# ============================================================

SEARCH_MAX_RESULTS = 50


# ============================================================
# INITIALISATION YOUTUBE API
# ============================================================

load_dotenv(".env", override=True)

API_KEY = os.getenv("YOUTUBE_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "YOUTUBE_API_KEY introuvable dans .env"
    )

youtube = build(
    "youtube",
    "v3",
    developerKey=API_KEY
)


# ============================================================
# UTILITAIRES
# ============================================================

def parse_youtube_date(date_string):
    """
    Convertit une date YouTube ISO 8601 en datetime UTC.
    """

    return datetime.fromisoformat(
        date_string.replace("Z", "+00:00")
    )


def format_number(number):
    """
    Affichage lisible des grands nombres.
    """

    return f"{number:,}"


def days_since(date):
    """
    Nombre de jours écoulés depuis une date.
    """

    now = datetime.now(timezone.utc)

    return (now - date).days


def parse_duration(duration):
    """
    Convertit une durée ISO 8601 YouTube en secondes.

    Exemples :

    PT30S       -> 30
    PT3M        -> 180
    PT3M25S     -> 205
    PT1H5M10S   -> 3910
    """

    if not duration:
        return 0

    pattern = re.compile(
        r"PT"
        r"(?:(\d+)H)?"
        r"(?:(\d+)M)?"
        r"(?:(\d+)S)?"
    )

    match = pattern.fullmatch(duration)

    if not match:
        return 0

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return (
        hours * 3600
        + minutes * 60
        + seconds
    )


def format_duration(seconds):
    """
    Transforme les secondes en affichage lisible.
    """

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:

        return (
            f"{hours}:{minutes:02d}:{secs:02d}"
        )

    return (
        f"{minutes}:{secs:02d}"
    )


# ============================================================
# 1. DISCOVERY
# ============================================================

def search_market_videos(market):
    """
    Recherche les vidéos du marché publiées dans les
    60 derniers jours.

    Une vidéo devient candidate uniquement si :

        vues >= 200K
        ET
        durée > 180 secondes

    Les statistiques et la durée sont récupérées dans
    le même videos.list().
    """

    print("\n" + "=" * 70)
    print(f"DISCOVERY : {market}")
    print("=" * 70)

    now = datetime.now(timezone.utc)

    published_after = (
        now - timedelta(
            days=DISCOVERY_DAYS
        )
    ).isoformat()

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    response = youtube.search().list(
        part="snippet",
        q=market,
        type="video",
        order="viewCount",
        publishedAfter=published_after,
        maxResults=SEARCH_MAX_RESULTS
    ).execute()

    search_items = response.get(
        "items",
        []
    )

    print(
        f"Vidéos découvertes : "
        f"{len(search_items)}"
    )

    if not search_items:
        return [], {}

    # --------------------------------------------------------
    # VIDEO IDS
    # --------------------------------------------------------

    video_ids = []

    for item in search_items:

        video_id = item.get(
            "id",
            {}
        ).get(
            "videoId"
        )

        if video_id:

            video_ids.append(
                video_id
            )

    if not video_ids:

        return [], {}

    # --------------------------------------------------------
    # VIDEO DETAILS
    #
    # Un seul appel pour :
    #
    # - titre
    # - chaîne
    # - date
    # - vues
    # - durée
    # --------------------------------------------------------

    stats_response = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        id=",".join(video_ids)
    ).execute()

    viral_videos = []

    # Cache global des vidéos
    video_cache = {}

    # Compteurs pour comprendre ce que la discovery
    # élimine.
    videos_over_200k = 0
    long_videos_over_200k = 0

    for item in stats_response.get(
        "items",
        []
    ):

        video_id = item["id"]

        snippet = item.get(
            "snippet",
            {}
        )

        statistics = item.get(
            "statistics",
            {}
        )

        content_details = item.get(
            "contentDetails",
            {}
        )

        # ----------------------------------------------------
        # VUES
        # ----------------------------------------------------

        views = int(
            statistics.get(
                "viewCount",
                0
            )
        )

        # ----------------------------------------------------
        # DATE
        # ----------------------------------------------------

        published_at_string = snippet.get(
            "publishedAt"
        )

        if not published_at_string:

            continue

        published_at = parse_youtube_date(
            published_at_string
        )

        # ----------------------------------------------------
        # CHAÎNE
        # ----------------------------------------------------

        channel_id = snippet.get(
            "channelId"
        )

        channel_title = snippet.get(
            "channelTitle",
            "Unknown"
        )

        # ----------------------------------------------------
        # TITRE
        # ----------------------------------------------------

        title = snippet.get(
            "title",
            ""
        )

        # ----------------------------------------------------
        # DURÉE
        # ----------------------------------------------------

        duration_iso = content_details.get(
            "duration"
        )

        duration_seconds = parse_duration(
            duration_iso
        )

        # ----------------------------------------------------
        # CACHE
        # ----------------------------------------------------

        video_cache[video_id] = {
            "video_id": video_id,
            "views": views,
            "published_at": published_at,
            "channel_id": channel_id,
            "channel_title": channel_title,
            "title": title,
            "duration_seconds": duration_seconds,
        }

        # ----------------------------------------------------
        # FILTRE 1 : 200K VUES
        # ----------------------------------------------------

        if views < MIN_DISCOVERY_VIDEO_VIEWS:

            continue

        videos_over_200k += 1

        # ----------------------------------------------------
        # FILTRE 2 : VIDÉO LONGUE
        #
        # IMPORTANT :
        #
        # > 180 secondes
        #
        # 180 secondes exactement = rejet
        # ----------------------------------------------------

        if duration_seconds <= MIN_LONG_VIDEO_SECONDS:

            continue

        long_videos_over_200k += 1

        # ----------------------------------------------------
        # CANDIDAT DISCOVERY
        # ----------------------------------------------------

        viral_videos.append(
            video_cache[video_id]
        )

    # --------------------------------------------------------
    # RÉSULTATS DISCOVERY
    # --------------------------------------------------------

    print(
        f"Vidéos >= "
        f"{format_number(MIN_DISCOVERY_VIDEO_VIEWS)} vues : "
        f"{videos_over_200k}"
    )

    print(
        f"Vidéos >= "
        f"{format_number(MIN_DISCOVERY_VIDEO_VIEWS)} "
        f"ET > 3 minutes : "
        f"{long_videos_over_200k}"
    )

    return viral_videos, video_cache


# ============================================================
# 2. RÉCUPÉRER LES CHAÎNES PAR LOTS
# ============================================================

def get_channels_batch(channel_ids):
    """
    Récupère les informations des chaînes.

    Maximum 50 IDs par requête.
    """

    channels = {}

    unique_ids = list(
        dict.fromkeys(
            channel_ids
        )
    )

    for start in range(
        0,
        len(unique_ids),
        50
    ):

        batch = unique_ids[
            start:start + 50
        ]

        response = youtube.channels().list(
            part="snippet,contentDetails,statistics",
            id=",".join(batch)
        ).execute()

        for item in response.get(
            "items",
            []
        ):

            channel_id = item["id"]

            statistics = item.get(
                "statistics",
                {}
            )

            snippet = item.get(
                "snippet",
                {}
            )

            content_details = item.get(
                "contentDetails",
                {}
            )

            total_views = int(
                statistics.get(
                    "viewCount",
                    0
                )
            )

            video_count = int(
                statistics.get(
                    "videoCount",
                    0
                )
            )

            uploads_playlist = (
                content_details
                .get(
                    "relatedPlaylists",
                    {}
                )
                .get(
                    "uploads"
                )
            )

            channels[channel_id] = {
                "id": channel_id,
                "title": snippet.get(
                    "title",
                    "Unknown"
                ),
                "total_views": total_views,
                "video_count": video_count,
                "uploads_playlist": uploads_playlist,
            }

    return channels


# ============================================================
# 3. RÉCUPÉRER LES UPLOADS
# ============================================================

def get_channel_uploads(
    uploads_playlist_id
):
    """
    Récupère les uploads d'une chaîne.

    Cette fonction n'est appelée qu'après :

        videoCount <= 50

    Donc une seule page de 50 vidéos suffit normalement.
    """

    if not uploads_playlist_id:

        return []

    response = youtube.playlistItems().list(
        part="contentDetails,snippet",
        playlistId=uploads_playlist_id,
        maxResults=50
    ).execute()

    items = response.get(
        "items",
        []
    )

    videos = []

    for item in items:

        content_details = item.get(
            "contentDetails",
            {}
        )

        snippet = item.get(
            "snippet",
            {}
        )

        video_id = content_details.get(
            "videoId"
        )

        published_at_string = (
            content_details.get(
                "videoPublishedAt"
            )
            or snippet.get(
                "publishedAt"
            )
        )

        if (
            not video_id
            or not published_at_string
        ):

            continue

        published_at = parse_youtube_date(
            published_at_string
        )

        videos.append({
            "video_id": video_id,
            "published_at": published_at,
            "title": snippet.get(
                "title",
                ""
            ),
        })

    # Plus récent → plus ancien
    videos.sort(
        key=lambda x: x["published_at"],
        reverse=True
    )

    return videos


# ============================================================
# 4. STATISTIQUES DES VIDÉOS
# ============================================================

def get_video_statistics(
    video_ids,
    video_cache=None
):
    """
    Récupère les statistiques des vidéos.

    Réutilise les données déjà présentes dans le cache.
    """

    if video_cache is None:

        video_cache = {}

    results = {}

    missing_ids = []

    # --------------------------------------------------------
    # CACHE
    # --------------------------------------------------------

    for video_id in video_ids:

        if video_id in video_cache:

            results[video_id] = (
                video_cache[video_id]["views"]
            )

        else:

            missing_ids.append(
                video_id
            )

    # --------------------------------------------------------
    # Rien à demander
    # --------------------------------------------------------

    if not missing_ids:

        return results

    # --------------------------------------------------------
    # BATCHS DE 50
    # --------------------------------------------------------

    for start in range(
        0,
        len(missing_ids),
        50
    ):

        batch = missing_ids[
            start:start + 50
        ]

        response = youtube.videos().list(
            part="statistics",
            id=",".join(batch)
        ).execute()

        for item in response.get(
            "items",
            []
        ):

            views = int(
                item.get(
                    "statistics",
                    {}
                ).get(
                    "viewCount",
                    0
                )
            )

            results[
                item["id"]
            ] = views

    return results


# ============================================================
# 5. ANALYSE D'UNE CHAÎNE
# ============================================================

def analyze_channel(
    channel,
    discovery_videos,
    video_cache
):
    """
    Applique les conditions finales.

    Ordre :

        1. <= 50 vidéos
        2. >= 1M vues chaîne
        3. dernière vidéo <= 15 jours
        4. >= 3 vidéos à 200K
    """

    channel_name = channel["title"]

    print(
        f"\n→ Analyse : "
        f"{channel_name}"
    )

    # ========================================================
    # CONDITION 1
    # MAX 50 VIDÉOS
    # ========================================================

    video_count = channel[
        "video_count"
    ]

    print(
        f"   Nombre de vidéos : "
        f"{video_count}"
    )

    if video_count > MAX_CHANNEL_VIDEOS:

        print(
            f"   ❌ REJECT — plus de "
            f"{MAX_CHANNEL_VIDEOS} vidéos"
        )

        return None

    print(
        "   ✓ Condition 1 — <= 50 vidéos"
    )

    # ========================================================
    # CONDITION 2
    # VUES TOTALES >= 1M
    # ========================================================

    total_views = channel[
        "total_views"
    ]

    print(
        f"   Vues chaîne : "
        f"{format_number(total_views)}"
    )

    if total_views < MIN_CHANNEL_VIEWS:

        print(
            "   ❌ REJECT — moins de 1M vues"
        )

        return None

    print(
        "   ✓ Condition 2 — >= 1M vues"
    )

    # ========================================================
    # RÉCUPÉRATION DES UPLOADS
    # ========================================================

    uploads = get_channel_uploads(
        channel["uploads_playlist"]
    )

    if not uploads:

        print(
            "   ❌ REJECT — aucun upload accessible"
        )

        return None

    # ========================================================
    # CONDITION 3
    # DERNIÈRE VIDÉO <= 15 JOURS
    # ========================================================

    latest_video = uploads[0]

    latest_date = latest_video[
        "published_at"
    ]

    latest_age_days = days_since(
        latest_date
    )

    print(
        f"   Dernière vidéo : "
        f"{latest_age_days} jour(s)"
    )

    if latest_age_days > MAX_LAST_UPLOAD_DAYS:

        print(
            "   ❌ REJECT — dernière vidéo trop ancienne"
        )

        return None

    print(
        "   ✓ Condition 3 — vidéo récente"
    )

    # ========================================================
    # CONDITION 4
    # AU MOINS 3 VIDÉOS >= 200K
    # ========================================================

    video_ids = [
        video["video_id"]
        for video in uploads
    ]

    statistics = get_video_statistics(
        video_ids,
        video_cache
    )

    viral_videos = []

    for video in uploads:

        video_id = video[
            "video_id"
        ]

        views = statistics.get(
            video_id,
            0
        )

        if views >= MIN_VIRAL_VIDEO_VIEWS:

            viral_videos.append({
                "video_id": video_id,
                "title": video["title"],
                "views": views,
                "published_at": video[
                    "published_at"
                ],
            })

    viral_count = len(
        viral_videos
    )

    print(
        f"   Vidéos >= "
        f"{format_number(MIN_VIRAL_VIDEO_VIEWS)} : "
        f"{viral_count}"
    )

    if viral_count < MIN_VIRAL_VIDEOS:

        print(
            f"   ❌ REJECT — seulement "
            f"{viral_count}/"
            f"{MIN_VIRAL_VIDEOS} vidéos à "
            f">={format_number(MIN_VIRAL_VIDEO_VIEWS)}"
        )

        return None

    # ========================================================
    # VALIDATED
    # ========================================================

    print(
        "   ✅ CHANNEL VALIDATED"
    )

    viral_videos.sort(
        key=lambda x: x["views"],
        reverse=True
    )

    return {
        "channel_id": channel["id"],
        "channel_name": channel_name,
        "total_views": total_views,
        "video_count": video_count,
        "latest_video_date": latest_date,
        "viral_count": viral_count,
        "viral_videos": viral_videos,
    }


# ============================================================
# 6. MAIN
# ============================================================

def main():

    # ========================================================
    # CACHE GLOBAL
    # ========================================================

    global_video_cache = {}

    discovered_channels = {}

    validated_channels = {}

    # ========================================================
    # PHASE 1
    # DISCOVERY DES VIDÉOS LONGUES ET VIRALES
    # ========================================================

    for market in MARKETS:

        try:

            (
                viral_videos,
                video_cache
            ) = search_market_videos(
                market
            )

            # Ajouter au cache
            global_video_cache.update(
                video_cache
            )

            # ------------------------------------------------
            # CHAÎNES DÉCOUVERTES
            # ------------------------------------------------

            for video in viral_videos:

                channel_id = video[
                    "channel_id"
                ]

                if not channel_id:

                    continue

                if (
                    channel_id
                    not in discovered_channels
                ):

                    discovered_channels[
                        channel_id
                    ] = {
                        "channel_id":
                            channel_id,

                        "channel_name":
                            video[
                                "channel_title"
                            ],

                        "markets":
                            set(),

                        "discovery_videos":
                            [],
                    }

                discovered_channels[
                    channel_id
                ]["markets"].add(
                    market
                )

                discovered_channels[
                    channel_id
                ]["discovery_videos"].append(
                    video
                )

        except HttpError as error:

            print(
                f"\n❌ API ERROR pendant "
                f"la recherche {market}"
            )

            print(error)

    # ========================================================
    # RÉSUMÉ DISCOVERY
    # ========================================================

    print(
        "\n\n"
        + "=" * 70
    )

    print(
        "DISCOVERY TERMINÉE"
    )

    print(
        "=" * 70
    )

    print(
        f"Chaînes uniques découvertes : "
        f"{len(discovered_channels)}"
    )

    if not discovered_channels:

        print(
            "\nAucune chaîne découverte."
        )

        return

    # ========================================================
    # PHASE 2
    # INFORMATIONS CHAÎNES
    # ========================================================

    channel_ids = list(
        discovered_channels.keys()
    )

    try:

        channels_data = get_channels_batch(
            channel_ids
        )

    except HttpError as error:

        print(
            "\n❌ Erreur lors de la récupération "
            "des chaînes."
        )

        print(error)

        return

    print(
        f"Informations récupérées pour "
        f"{len(channels_data)} chaînes."
    )

    # ========================================================
    # PHASE 3
    # FILTRAGE FINAL
    # ========================================================

    for (
        channel_id,
        discovery_data
    ) in discovered_channels.items():

        channel = channels_data.get(
            channel_id
        )

        if not channel:

            continue

        try:

            result = analyze_channel(
                channel,

                discovery_data[
                    "discovery_videos"
                ],

                global_video_cache
            )

            if result:

                result["markets"] = sorted(
                    discovery_data[
                        "markets"
                    ]
                )

                validated_channels[
                    channel_id
                ] = result

        except HttpError as error:

            print(
                f"\n❌ API ERROR pour "
                f"{channel['title']}"
            )

            print(error)

        except Exception as error:

            print(
                f"\n❌ ERROR pour "
                f"{channel['title']}"
            )

            print(error)

    # ========================================================
    # RÉSULTATS
    # ========================================================

    print(
        "\n\n"
        + "=" * 70
    )

    print(
        "CHAÎNES VALIDÉES"
    )

    print(
        "=" * 70
    )

    if not validated_channels:

        print(
            "Aucune chaîne ne satisfait "
            "toutes les conditions."
        )

        return

    for channel in (
        validated_channels.values()
    ):

        print(
            f"\n📺 "
            f"{channel['channel_name']}"
        )

        print(
            f"   Marché(s) : "
            f"{', '.join(channel['markets'])}"
        )

        print(
            f"   Vues chaîne : "
            f"{format_number(channel['total_views'])}"
        )

        print(
            f"   Nombre de vidéos : "
            f"{channel['video_count']}"
        )

        print(
            f"   Vidéos >= 200K : "
            f"{channel['viral_count']}"
        )

        print(
            "\n   Vidéos virales :"
        )

        for video in channel[
            "viral_videos"
        ][:10]:

            print(
                f"      • "
                f"{format_number(video['views'])} vues "
                f"| "
                f"{format_duration(video.get('duration_seconds', 0))} "
                f"| "
                f"{video['title']}"
            )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except HttpError as error:

        print(
            "\n❌ YouTube API Error:"
        )

        print(error)

    except KeyboardInterrupt:

        print(
            "\n\n⏹️ Recherche arrêtée par l'utilisateur."
        )