"""
Script ponctuel : insère dans la base les 43 chaînes déjà validées lors
du dernier run complet (copiées manuellement depuis la sortie terminal),
sans consommer de quota API.

À lancer une seule fois pour ce lot. Les prochains runs de search.py
alimenteront la base automatiquement au fil de l'eau.
"""

from discovery.database import save_validated_channels

# Données copiées depuis la sortie du dernier run complet.
CHANNELS = [
    {"channel_title": "Nils", "channel_id": "UC-CzFjDbVlqH_mHK-oBy45Q", "subscriber_count": 43100, "strong_video_count": 4, "total_videos_checked": 6, "density_score": 0.67},
    {"channel_title": "Paint Maniac", "channel_id": "UCdi-rTleLSNBYEVOWuAic5w", "subscriber_count": 41900, "strong_video_count": 10, "total_videos_checked": 15, "density_score": 0.67},
    {"channel_title": "S Rao", "channel_id": "UCc52cvjjgPzrnxq2bdV5-UA", "subscriber_count": 122, "strong_video_count": 5, "total_videos_checked": 8, "density_score": 0.62},
    {"channel_title": "StickOrbit", "channel_id": "UCWYoLAeg56FJKxYEkaNsRIg", "subscriber_count": 1640, "strong_video_count": 3, "total_videos_checked": 5, "density_score": 0.60},
    {"channel_title": "Ink Explainer", "channel_id": "UCpgrEMx8diLrw7YNQ6r3uUw", "subscriber_count": 92200, "strong_video_count": 9, "total_videos_checked": 15, "density_score": 0.60},
    {"channel_title": "ExplainTory", "channel_id": "UCfqJsOXexvOvaDe-KJSi09w", "subscriber_count": 6200, "strong_video_count": 7, "total_videos_checked": 15, "density_score": 0.47},
    {"channel_title": "Switching Lives", "channel_id": "UCMSe_mQ_9xKuEAUAnaKgW-A", "subscriber_count": 519, "strong_video_count": 3, "total_videos_checked": 7, "density_score": 0.43},
    {"channel_title": "Odd Machines", "channel_id": "UCisGyGEvclQ9H5nkzu5YrlQ", "subscriber_count": 2370, "strong_video_count": 7, "total_videos_checked": 18, "density_score": 0.39},
    {"channel_title": "Bridgehead", "channel_id": "UC13oiUQQochn-nKvM9tBOYg", "subscriber_count": 595, "strong_video_count": 5, "total_videos_checked": 13, "density_score": 0.38},
    {"channel_title": "Real Farmers", "channel_id": "UCIP_eqovDAZVLwMW0R7vDGQ", "subscriber_count": 15000, "strong_video_count": 6, "total_videos_checked": 17, "density_score": 0.35},
    {"channel_title": "Ancient Secrets", "channel_id": "UCDkB3dzU-X83jTzQiSypkmQ", "subscriber_count": 2160, "strong_video_count": 4, "total_videos_checked": 13, "density_score": 0.31},
    {"channel_title": "The Forgotten Gentleman", "channel_id": "UC9rZrcxfzuVtq7SP11XHn5A", "subscriber_count": 1810, "strong_video_count": 5, "total_videos_checked": 17, "density_score": 0.29},
    {"channel_title": "Wrongly Assumed", "channel_id": "UClVmPVF1AxBkx-hcA371RoQ", "subscriber_count": 7310, "strong_video_count": 7, "total_videos_checked": 24, "density_score": 0.29},
    {"channel_title": "Tactical Genius", "channel_id": "UCElMKzapdJqiKvRBO-Aterg", "subscriber_count": 9920, "strong_video_count": 3, "total_videos_checked": 12, "density_score": 0.25},
    {"channel_title": "Ambrose Discovery", "channel_id": "UCAVxoa11gRHcit9_onvTkMQ", "subscriber_count": 48400, "strong_video_count": 7, "total_videos_checked": 28, "density_score": 0.25},
    {"channel_title": "HinExp", "channel_id": "UCytiKJcsuKFARvAeUABvRBA", "subscriber_count": 57200, "strong_video_count": 11, "total_videos_checked": 45, "density_score": 0.24},
    {"channel_title": "Zoxi", "channel_id": "UCjpUuL5eXu8QeuiqPE8XaIQ", "subscriber_count": 3640, "strong_video_count": 4, "total_videos_checked": 17, "density_score": 0.24},
    {"channel_title": "Professor Historian", "channel_id": "UC35fL9KdO0OSC9CoQk5MLfg", "subscriber_count": 37700, "strong_video_count": 8, "total_videos_checked": 36, "density_score": 0.22},
    {"channel_title": "Ten Minute Historian", "channel_id": "UCs9_VXTXc5IkncksrGyBNvw", "subscriber_count": 591, "strong_video_count": 4, "total_videos_checked": 19, "density_score": 0.21},
    {"channel_title": "GoDocs", "channel_id": "UC771k8zqZmmIsRTvENq-voA", "subscriber_count": 30000, "strong_video_count": 12, "total_videos_checked": 59, "density_score": 0.20},
    {"channel_title": "Global Life Lens", "channel_id": "UCarhEwIqdYAmLTFamSTYbNg", "subscriber_count": 14800, "strong_video_count": 5, "total_videos_checked": 26, "density_score": 0.19},
    {"channel_title": "Lost Appalachian Towns & Coal Country", "channel_id": "UCgwf-pL16bs3uO4qID4w0Hw", "subscriber_count": 1310, "strong_video_count": 4, "total_videos_checked": 22, "density_score": 0.18},
    {"channel_title": "Blitzkrieg", "channel_id": "UCPNro6-pzlC4koUqQB7r6uw", "subscriber_count": 3260, "strong_video_count": 6, "total_videos_checked": 35, "density_score": 0.17},
    {"channel_title": "WUFO TV", "channel_id": "UCaSfbjZReHoweptNU3XiIUw", "subscriber_count": 5430, "strong_video_count": 6, "total_videos_checked": 38, "density_score": 0.16},
    {"channel_title": "Max Edge", "channel_id": "UCxcRUaURwolndbnyExToyhw", "subscriber_count": 9980, "strong_video_count": 3, "total_videos_checked": 20, "density_score": 0.15},
    {"channel_title": "Ancient Romans", "channel_id": "UCYHyaQ1f4PRBJa9um_KXexQ", "subscriber_count": 1190, "strong_video_count": 3, "total_videos_checked": 22, "density_score": 0.14},
    {"channel_title": "Diario de un Guerrero Estoico", "channel_id": "UCD4JEvhPS-Vn7tIXxy0X02w", "subscriber_count": 6850, "strong_video_count": 4, "total_videos_checked": 31, "density_score": 0.13},
    {"channel_title": "Whyologica", "channel_id": "UC_j4fjvV74qM5NtRd1PKw3Q", "subscriber_count": 629, "strong_video_count": 5, "total_videos_checked": 40, "density_score": 0.12},
    {"channel_title": "Ancient Egyptians", "channel_id": "UCUAy7-6tGMZz_Wy8SKeDTbg", "subscriber_count": 13500, "strong_video_count": 3, "total_videos_checked": 24, "density_score": 0.12},
    {"channel_title": "The Kashmiri", "channel_id": "UC-JEtN_v7p_MPSQnLgi6qCg", "subscriber_count": 11100, "strong_video_count": 3, "total_videos_checked": 24, "density_score": 0.12},
    {"channel_title": "history mick", "channel_id": "UCip7yKHhFM8hgUmKPj3GZww", "subscriber_count": 2690, "strong_video_count": 3, "total_videos_checked": 27, "density_score": 0.11},
    {"channel_title": "CloverSHORT", "channel_id": "UC47eS_wDckFoaQLZz5AmqHQ", "subscriber_count": 53000, "strong_video_count": 14, "total_videos_checked": 127, "density_score": 0.11},
    {"channel_title": "Markets of the Past", "channel_id": "UCPDCiU00ugujWP8H2HMbiFA", "subscriber_count": 71000, "strong_video_count": 7, "total_videos_checked": 74, "density_score": 0.09},
    {"channel_title": "Underwater Earth 4K", "channel_id": "UCiK9ODIN1_AEte6eV7m7jZA", "subscriber_count": 25500, "strong_video_count": 5, "total_videos_checked": 101, "density_score": 0.05},
    {"channel_title": "FreeStream Movies", "channel_id": "UCV8sMLn3QmOhc3Y1PACHIoA", "subscriber_count": 10400, "strong_video_count": 5, "total_videos_checked": 109, "density_score": 0.05},
    {"channel_title": "Past Unsealed", "channel_id": "UCQ2ZeVkfAYyGT1MesxOS9cQ", "subscriber_count": 27100, "strong_video_count": 9, "total_videos_checked": 216, "density_score": 0.04},
    {"channel_title": "DNA Mystery", "channel_id": "UCpHg1zp_mwDbJQgEmbJcaFQ", "subscriber_count": 10900, "strong_video_count": 3, "total_videos_checked": 73, "density_score": 0.04},
    {"channel_title": "Easy History Explained", "channel_id": "UCVyxl_CZvl-FTNYBhkQki-A", "subscriber_count": 2670, "strong_video_count": 4, "total_videos_checked": 103, "density_score": 0.04},
    {"channel_title": "History Tales", "channel_id": "UCpzeNvCynwgZGNu5vb9_r7g", "subscriber_count": 1270, "strong_video_count": 3, "total_videos_checked": 98, "density_score": 0.03},
    {"channel_title": "Orca Planet TV", "channel_id": "UCPp2r-IwCHHnj96OABcUcOQ", "subscriber_count": 9720, "strong_video_count": 4, "total_videos_checked": 142, "density_score": 0.03},
    {"channel_title": "Focus Short Drama", "channel_id": "UCDu1tNugqnIS3phNLEVeJew", "subscriber_count": 36700, "strong_video_count": 8, "total_videos_checked": 304, "density_score": 0.03},
    {"channel_title": "EYE MATRIX", "channel_id": "UCD8cK-tEgVvN4Dm-8R7fDGQ", "subscriber_count": 490, "strong_video_count": 3, "total_videos_checked": 153, "density_score": 0.02},
    {"channel_title": "DoveDrama", "channel_id": "UCt8IDART25_t3lq1NC9ZgHg", "subscriber_count": 22000, "strong_video_count": 3, "total_videos_checked": 228, "density_score": 0.01},
]

if __name__ == "__main__":
    for c in CHANNELS:
        c["channel_url"] = f"https://www.youtube.com/channel/{c['channel_id']}"

    save_validated_channels(CHANNELS, market="history")