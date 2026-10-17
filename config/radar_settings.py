"""
Réglages du radar (vidéos fortes sans mot-clé, par catégorie YouTube).

Tout se règle ici. Le radar ne cherche pas avec des mots-clés : il explore les
vidéos les plus vues des 60 derniers jours, catégorie par catégorie, par petites
tranches de dates, et se souvient de ce qu'il a déjà exploré.
"""

# ---------- Ce qu'on explore ----------

LANGUAGE = "en"                 # anglais seul pour l'instant

# Catégories YouTube explorées (numéro officiel -> nom). Musique (10) est retirée.
CATEGORIES = {
    "1": "Film et animation",
    "2": "Autos et véhicules",
    "15": "Animaux",
    "17": "Sport",
    "19": "Voyages et événements",
    "20": "Jeux vidéo",
    "22": "Gens et blogs",
    "23": "Comédie",
    "24": "Divertissement",
    "25": "Actualités et politique",
    "26": "Conseils et style",
    "27": "Éducation",
    "28": "Science et technologie",
    "29": "Associations et activisme",
}

DURATIONS = ("medium", "long")  # 4 à 20 minutes, plus de 20 minutes (exclut les Shorts)

WINDOW_DAYS = 60                # on ne regarde que les vidéos publiées dans les 60 derniers jours
SLICE_DAYS = 5                  # taille d'une tranche de dates (une "case" = catégorie + durée + tranche)
MIN_SLICE_DAYS = 1              # une case saturée est coupée en deux, jamais en dessous de cette taille

# ---------- Quota ----------

SEARCH_BUDGET_UNITS = 6000      # quota maximum dépensé en recherches par passage (100 unités par appel)
MAX_PAGES_PER_CELL = 10         # YouTube ne donne pas plus de ~500 résultats (10 pages de 50) par recherche

# ---------- Vidéos et chaînes ----------

MIN_VIEWS = 100_000             # une vidéo compte à partir de ce nombre de vues
MAX_CHANNELS_TO_VALIDATE = 150  # nombre maximum de chaînes validées par passage
RECENT_CHANNEL_DAYS = 170       # une chaîne créée il y a moins de 170 jours passe forcément la règle des 6 mois : elle est testée en premier
                                # (puis le tri se fait par vues croissantes, les moins vues d'abord)
MAX_STRONG_AGE_DAYS = 60        # une chaîne est rejetée si elle a une vidéo >= MIN_VIEWS publiée il y a plus longtemps

# ---------- Revisite des cases (les vues continuent de monter) ----------

RECHECK_YOUNGER_THAN_DAYS = 30  # seules les cases dont la tranche a moins de 30 jours sont refaites
RECHECK_AFTER_DAYS = 7          # ... 7 jours après la fin de leur exploration

# ---------- Marché des chaînes ----------

MIN_MARKET_WORDS = 2            # un marché est attribué s'il a au moins 2 mots dans les titres de la chaîne
UNCLASSIFIED_MARKET = "radar"   # marché donné aux chaînes qu'on ne sait pas classer

# ---------- Mots-clés du radar ----------

RADAR_MIN_CHANNELS = 2          # une expression doit venir d'au moins 2 chaînes radar différentes
RADAR_REQUIRE_MARKET_WORD = True

# ---------- Chaînes hors cible : musique et enfants ----------
# Une chaîne est écartée AVANT la validation (donc sans dépenser de quota) si son nom, le titre de sa
# vidéo forte ou le début de sa description contient un de ces mots (mot entier, majuscules ignorées).
# Pour laisser passer un mot, enlève-le de la liste ; pour en écarter un autre, ajoute-le.
OFF_TARGET_WORDS = (
    # enfants
    "kids", "kid", "children", "childrens", "toddler", "toddlers", "nursery", "rhymes", "preschool",
    "kindergarten", "baby", "babies", "cocomelon", "lullaby", "lullabies", "cartoons", "coloring",
    # musique
    "music", "song", "songs", "lyrics", "lyric", "remix", "instrumental", "karaoke", "playlist",
    "soundtrack", "beats", "lofi", "singer", "concert", "dj",
)
OFF_TARGET_PHRASES = (
    "for kids", "baby shark", "official video", "official audio", "music video", "full album",
)

# ---------- Classement dans les marchés ----------
LEARN_VOCAB_MIN_CHANNELS = 3    # un mot est "appris" pour un marché s'il apparaît chez au moins 3 chaînes de ce marché
LEARN_VOCAB_MIN_SHARE = 0.5     # ... et si ce marché l'emploie plus que tous les autres ensemble (part >= 50 % des chaînes qui l'emploient, taille du marché corrigée)
CATEGORY_HINT_BONUS = 1         # point en plus pour le marché suggéré par la catégorie YouTube de la vidéo

# Catégorie YouTube -> marché du site qu'elle suggère (un coup de pouce, pas une décision).
CATEGORY_MARKET_HINT = {
    "2": "cars",
    "15": "animals",
    "17": "sports",
    "19": "travel",
    "20": "gaming",
    "25": "geopolitics",
    "28": "technology",
}
