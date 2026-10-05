"""
Script de test isolé : vérifie l'ORDRE des dates retournées par la
playlist "uploads" (récent -> ancien, ou l'inverse ?) sur UNE seule
chaîne, avant de faire confiance à detect_activity_start().

Usage: modifie CHANNEL_HANDLE ci-dessous, puis lance :
    python -m discovery.test_single_channel
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("YOUTUBE_API_KEY")

# <<< MODIFIE ICI avec le handle d'une chaîne trouvée précédemment >>>
CHANNEL_HANDLE = "HistoricDave"


def get_channel_id_and_uploads_playlist(handle: str) -> tuple[str, str]:
    resp = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={
            "part": "contentDetails",
            "forHandle": handle,
            "key": API_KEY,
        },
        timeout=15,
    )
    data = resp.json()
    items = data.get("items", [])
    if not items:
        raise SystemExit(f"Chaîne introuvable pour le handle '{handle}'. Vérifie l'orthographe.")
    channel_id = items[0]["id"]
    uploads_playlist_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    return channel_id, uploads_playlist_id


def print_first_page_dates(uploads_playlist_id: str):
    resp = requests.get(
        "https://www.googleapis.com/youtube/v3/playlistItems",
        params={
            "part": "contentDetails,snippet",
            "playlistId": uploads_playlist_id,
            "maxResults": 15,
            "key": API_KEY,
        },
        timeout=15,
    )
    data = resp.json()
    items = data.get("items", [])

    print(f"\n{len(items)} vidéos récupérées (première page) :\n")
    for item in items:
        title = item["snippet"]["title"]
        published = item["contentDetails"]["videoPublishedAt"]
        print(f"  {published}  |  {title}")


if __name__ == "__main__":
    if not API_KEY:
        raise SystemExit("YOUTUBE_API_KEY manquant dans .env")

    channel_id, uploads_playlist_id = get_channel_id_and_uploads_playlist("historicdave1")
    print(f"Channel ID: {channel_id}")
    print(f"Uploads playlist ID: {uploads_playlist_id}")

    print_first_page_dates(uploads_playlist_id)