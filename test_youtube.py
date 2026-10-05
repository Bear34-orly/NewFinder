import os
from dotenv import load_dotenv
from googleapiclient.discovery import build

# Charger explicitement le .env situé dans le dossier actuel
load_dotenv(".env", override=True)

api_key = os.getenv("YOUTUBE_API_KEY")

print("Clé trouvée :", bool(api_key))
print("Longueur de la clé :", len(api_key) if api_key else 0)

if not api_key:
    raise RuntimeError(
        "YOUTUBE_API_KEY n'a pas été trouvée dans .env"
    )

youtube = build(
    "youtube",
    "v3",
    developerKey=api_key
)

response = youtube.search().list(
    part="snippet",
    q="History",
    type="video",
    maxResults=3
).execute()

print("\nRésultats YouTube :")

for item in response.get("items", []):
    print(
        item["snippet"]["title"],
        "—",
        item["snippet"]["channelTitle"]
    )