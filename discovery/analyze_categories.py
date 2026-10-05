"""
Script d'analyse : vérifie la catégorie YouTube réelle des chaînes déjà
validées et stockées, pour savoir où chercher en priorité avant d'ajouter
la recherche par catégorie au pipeline.

Coût quota : quasi nul (1 appel videos.list par lot de 50 IDs).
"""

import os
from collections import Counter

import requests
from dotenv import load_dotenv

from discovery.database import list_all_channels

load_dotenv()

YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

# Table de correspondance des catégories YouTube les plus courantes
CATEGORY_NAMES = {
    "1": "Film & Animation",
    "2": "Autos & Vehicles",
    "10": "Music",
    "15": "Pets & Animals",
    "17": "Sports",
    "19": "Travel & Events",
    "20": "Gaming",
    "22": "People & Blogs",
    "23": "Comedy",
    "24": "Entertainment",
    "25": "News & Politics",
    "26": "Howto & Style",
    "27": "Education",
    "28": "Science & Technology",
}


def get_categories(video_ids: list[str], api_key: str) -> dict[str, str]:
    """Retourne {video_id: categoryId} pour une liste de vidéos, en batch de 50."""
    results = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        params = {"part": "snippet", "id": ",".join(batch), "key": api_key}
        resp = requests.get(YOUTUBE_VIDEOS_URL, params=params, timeout=15)
        if resp.status_code != 200:
            print(f"  [!] Erreur ({resp.status_code}): {resp.text[:150]}")
            continue
        data = resp.json()
        for item in data.get("items", []):
            cat_id = item.get("snippet", {}).get("categoryId")
            results[item["id"]] = cat_id
    return results


if __name__ == "__main__":
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise SystemExit("YOUTUBE_API_KEY manquant dans .env")

    channels = list_all_channels()
    print(f"{len(channels)} chaînes trouvées dans la base.\n")

    video_ids = [c["best_video_id"] for c in channels if c.get("best_video_id")]
    categories = get_categories(video_ids, api_key)

    print(f"{len(categories)} catégories récupérées.\n")

    counter = Counter(categories.values())

    print("=== Répartition des catégories ===\n")
    for cat_id, count in counter.most_common():
        name = CATEGORY_NAMES.get(cat_id, f"Catégorie inconnue ({cat_id})")
        pct = count / len(categories) * 100
        print(f"  {name} (id={cat_id}): {count} chaînes ({pct:.0f}%)")

    print("\n=== Détail par chaîne ===\n")
    for c in channels:
        vid = c.get("best_video_id")
        cat_id = categories.get(vid, "?")
        cat_name = CATEGORY_NAMES.get(cat_id, f"id={cat_id}")
        print(f"  {c['channel_title']:<40} -> {cat_name}")