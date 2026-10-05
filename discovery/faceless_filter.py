"""
Étape 4 (AVANT activité de chaîne) : filtre faceless.

V1 = heuristique textuelle low-cost (gratuite, aucun appel API) +
affichage de la miniature pour validation visuelle rapide par l'humain.
Une vraie détection visuelle automatique sera ajoutée plus tard.
"""

# Mots qui trahissent typiquement un format "on-camera" / non-faceless
NON_FACELESS_KEYWORDS = [
    "podcast", "interview", "reacts", "reaction", "vlog", "with me",
    "ft.", "feat.", "my thoughts", "q&a", "ask me", "storytime",
    "day in my life", "livestream", "live stream", "unboxing",
    "meet the", "behind the scenes",
]


def looks_non_faceless(video: dict) -> bool:
    """
    Retourne True si le titre/chaîne contient un signal fort de format
    on-camera. Ne prouve rien à 100%, sert juste à écarter les cas
    évidents avant la validation humaine.
    """
    text = f"{video.get('title', '')} {video.get('channel_title', '')}".lower()
    return any(keyword in text for keyword in NON_FACELESS_KEYWORDS)


def get_thumbnail_url(video_id: str) -> str:
    """
    URL de la miniature haute qualité, pour vérification visuelle rapide.
    """
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"


def pre_filter_faceless(videos: list[dict]) -> list[dict]:
    """
    Écarte les cas évidents de non-faceless via mots-clés, ajoute l'URL
    de la miniature à chaque vidéo restante pour validation manuelle
    avant de lancer l'étape (coûteuse) d'analyse d'activité de chaîne.
    """
    survivors = []
    excluded_count = 0

    for v in videos:
        if looks_non_faceless(v):
            excluded_count += 1
            continue
        survivors.append({**v, "thumbnail_url": get_thumbnail_url(v["video_id"])})

    print(f"  Filtre mots-clés : {excluded_count} exclues, {len(survivors)} restantes à valider visuellement.")
    return survivors