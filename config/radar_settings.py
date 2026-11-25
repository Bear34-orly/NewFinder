"""
Réglages du radar (vidéos fortes sans mot-clé, par catégorie YouTube).

Tout se règle ici. Le radar ne cherche pas avec des mots-clés : il explore les
vidéos les plus vues des 90 derniers jours, catégorie par catégorie, par petites
tranches de dates, et se souvient de ce qu'il a déjà exploré (une carte par langue).

Il n'y a plus de marchés : toutes les chaînes retenues sont rangées sous le même nom (MARKET_LABEL).
"""

# ---------- Ce qu'on explore ----------

LANGUAGE = "en"                 # langue par défaut ; le robot en donne une autre chaque jour (--language)
LANGUAGES = ("en", "es", "fr", "de", "ru")

# Catégories YouTube explorées (numéro officiel -> nom). Musique (10) est retirée.
# L'ORDRE COMPTE : avec un budget limité, le radar explore d'abord les catégories du haut de la liste.
# Les catégories où les chaînes faceless sont les plus fréquentes sont en premier ; celles où l'on voit
# surtout des gens à l'écran (blogs, comédie) ou des films sont en dernier. Toutes restent explorées
# quand le budget le permet.
CATEGORIES = {
    "27": "Éducation",
    "28": "Science et technologie",
    "24": "Divertissement",
    "25": "Actualités et politique",
    "26": "Conseils et style",
    "19": "Voyages et événements",
    "15": "Animaux",
    "2": "Autos et véhicules",
    "17": "Sport",
    "20": "Jeux vidéo",
    "29": "Associations et activisme",
    "22": "Gens et blogs",
    "23": "Comédie",
    "1": "Film et animation",
}

DURATIONS = ("medium", "long")  # 4 à 20 minutes, plus de 20 minutes (exclut les Shorts)

WINDOW_DAYS = 90                # on ne regarde que les vidéos publiées dans les 90 derniers jours (3 mois)
SLICE_DAYS = 5                  # taille d'une tranche de dates (une "case" = catégorie + durée + tranche)
MIN_SLICE_DAYS = 1              # une case saturée est coupée en deux, jamais en dessous de cette taille

# ---------- Quota ----------

SEARCH_BUDGET_UNITS = 6000      # quota maximum dépensé en recherches par passage (100 unités par appel)
MAX_PAGES_PER_CELL = 10         # YouTube ne donne pas plus de ~500 résultats (10 pages de 50) par recherche

# ---------- Critères d'une chaîne ----------

MIN_VIEWS = 100_000             # une vidéo "forte" a au moins ce nombre de vues
MIN_STRONG_VIDEOS = 1           # la chaîne doit avoir au moins 1 vidéo à MIN_VIEWS vues (pas de maximum)
MIN_VIDEOS = 3                  # la chaîne doit avoir au moins 3 vidéos publiées
ACTIVE_WITHIN_DAYS = 7          # sa vidéo la plus récente doit avoir moins de 7 jours
MAX_VIDEO_AGE_DAYS = 90         # la chaîne est rejetée si elle a UNE vidéo de plus de 90 jours (3 mois)
# Il n'y a plus de limite d'abonnés.

MAX_CHANNELS_TO_VALIDATE = None  # None = AUCUNE limite : toutes les chaînes trouvées sont validées (les plus récentes d'abord)
SAVE_EVERY = 25                 # les chaînes validées sont enregistrées par paquets de 25 (rien n'est perdu si le robot s'arrête)

# ---------- Revisite des cases (les vues continuent de monter) ----------

RECHECK_YOUNGER_THAN_DAYS = 30  # seules les cases dont la tranche a moins de 30 jours sont refaites
RECHECK_AFTER_DAYS = 7          # ... 7 jours après la fin de leur exploration

# ---------- Nom unique donné aux chaînes du radar (il n'y a plus de marchés) ----------

MARKET_LABEL = "radar"

# ---------- Chaînes hors cible : musique et enfants ----------
# Une chaîne est écartée AVANT la validation (donc sans dépenser de quota) si son nom, le titre de sa
# vidéo forte ou le début de sa description contient un de ces mots (mot entier, majuscules ignorées).
# Pour laisser passer un mot, enlève-le de la liste ; pour en écarter un autre, ajoute-le.
OFF_TARGET_WORDS = (
    # enfants (anglais)
    "kids", "kid", "children", "childrens", "toddler", "toddlers", "nursery", "rhymes", "preschool",
    "kindergarten", "baby", "babies", "cocomelon", "lullaby", "lullabies", "cartoons", "coloring",
    # musique (anglais)
    "music", "song", "songs", "lyrics", "lyric", "remix", "instrumental", "karaoke", "playlist",
    "soundtrack", "beats", "lofi", "singer", "concert", "dj",
    # espagnol
    "niños", "niñas", "infantil", "infantiles", "bebé", "bebés", "canciones", "canción", "música",
    "musica", "letra", "letras", "cantante", "dibujos",
    # français
    "enfants", "enfant", "bébé", "bébés", "comptines", "comptine", "chanson", "chansons", "musique",
    "paroles", "chanteur", "dessins",
    # allemand
    "kinder", "kinderlieder", "kinderlied", "baby", "babys", "lied", "lieder", "musik", "liedtext",
    "sänger", "zeichentrick",
    # russe
    "детям", "детские", "детская", "малышей", "малыши", "мультики", "мультфильмы", "песни", "песня",
    "музыка", "клип", "караоке", "колыбельная", "колыбельные",
)
OFF_TARGET_PHRASES = (
    "for kids", "baby shark", "official video", "official audio", "music video", "full album",
    "para niños", "clip officiel", "pour enfants", "für kinder", "для детей", "музыкальный клип",
)
