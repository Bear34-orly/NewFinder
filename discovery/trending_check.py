"""
Interroge l'endpoint officiel "Trending" de YouTube Data API
(videos.list avec chart=mostPopular), filtré par région et catégorie.

Coût quota minime : 1 unité par appel (contre 100 pour search.list),
donc quasi gratuit à utiliser souvent.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

# Catégories les plus pertinentes pour nos marchés faceless
CATEGORIES = {
    "1": "Film & Animation",
    "22": "People & Blogs",
    "24": "Entertainment",
    "25": "News & Politics",
    "27": "Education",
    "28": "Science & Technology",
}


def get_trending_videos(api_key: str, region_code: str = "US",
                         category_id: str | None = None, max_results: int = 25) -> list[dict]:
    params = {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": min(max_results, 50),
        "key": api_key,
    }
    if category_id:
        params["videoCategoryId"] = category_id

    resp = requests.get(YOUTUBE_VIDEOS_URL, params=params, timeout=15)
    if resp.status_code != 200:
        print(f"  [!] Erreur API ({resp.status_code}): {resp.text[:200]}")
        return []

    data = resp.json()
    results = []
    for item in data.get("items", []):
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        results.append({
            "video_id": item.get("id"),
            "title": snippet.get("title"),
            "channel_title": snippet.get("channelTitle"),
            "channel_id": snippet.get("channelId"),
            "category_id": snippet.get("categoryId"),
            "view_count": int(stats.get("viewCount", 0)),
            "published_at": snippet.get("publishedAt"),
        })
    return results


if __name__ == "__main__":
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise SystemExit("YOUTUBE_API_KEY manquant dans .env")

    REGION = "US"

    for cat_id, cat_name in CATEGORIES.items():
        print(f"\n{'=' * 60}")
        print(f"TENDANCES US — {cat_name} (catégorie {cat_id})")
        print(f"{'=' * 60}\n")

        videos = get_trending_videos(api_key, region_code=REGION, category_id=cat_id, max_results=15)

        if not videos:
            print("  (aucun résultat pour cette catégorie)")
            continue

        for v in videos:
            print(f"  {v['view_count']:>12,} vues | {v['title']} (chaîne: {v['channel_title']})")