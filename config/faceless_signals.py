"""
Signaux de contenu "avec visage / on-camera", par langue.

Chaque entrée est un mot ou une expression. Le filtre compare des MOTS ENTIERS
(après normalisation : minuscules, sans accents, ё -> е, apostrophes droites),
donc "vlog" ne matche pas "vlogger" et "ft." ne matche pas dans un autre mot.

Pour ajouter un signal : ajouter une ligne dans la bonne langue, rien d'autre.
Éviter les mots isolés ambigus (ex: "live" seul, "show" seul).
"""

SIGNALS = {
    "en": [
        "podcast", "interview", "reacts", "reaction", "reacting", "reacts to",
        "vlog", "with me", "ft.", "feat.", "my thoughts", "q&a", "ask me",
        "storytime", "story time", "day in my life", "livestream", "live stream",
        "unboxing", "meet the", "behind the scenes", "my story", "my journey",
        "my experience", "i tried", "i bought", "i quit", "i tested",
        "get ready with me", "grwm", "haul", "hey guys",
        "guest", "guests",
    ],
    "es": [
        "podcast", "entrevista", "reaccion", "reacciono", "reaccionando",
        "vlog", "conmigo", "mi historia", "mi experiencia", "mi opinion",
        "preguntas y respuestas", "en vivo", "en directo", "unboxing",
        "detras de camaras", "tras bambalinas", "un dia en mi vida",
        "probe", "compre", "ft.", "feat.",
    ],
    "fr": [
        "podcast", "interview", "reaction", "je reagis", "reagis", "vlog",
        "avec moi", "ma vie", "mon histoire", "mon experience", "mon avis",
        "en direct", "unboxing", "questions reponses", "coulisses",
        "une journee avec moi", "j'ai teste", "j'ai essaye", "j'ai achete",
        "ft.", "feat.",
    ],
    "de": [
        "podcast", "interview", "reaktion", "ich reagiere", "reagiert auf",
        "vlog", "mit mir", "meine geschichte", "meine erfahrung",
        "meine meinung", "livestream", "im livestream", "unboxing",
        "fragen und antworten", "hinter den kulissen",
        "ein tag in meinem leben", "ich habe getestet", "ich teste",
        "ft.", "feat.",
    ],
    "ru": [
        "подкаст", "интервью", "реакция", "реагирую", "влог", "со мной",
        "моя история", "мой опыт", "мое мнение", "прямой эфир", "стрим",
        "распаковка", "вопросы и ответы", "закулисье",
        "день из моей жизни", "я попробовал", "я купил", "я проверил",
    ],
}

# Motifs de FORME de titre (expressions régulières), valables pour toutes les langues.
# Appliqués au titre normalisé (minuscules, sans accents). Chaque motif est
# rare chez les chaînes faceless, mais fréquent chez les interviews/podcasts.
PATTERN_SIGNALS = [
    # mot censuré avec une astérisque : "r*tards", "f*cks"
    ("mot censuré avec *", r"[^\W\d_]\*+"),
    # numéro d'épisode après une barre : "... | chs #36"
    ("numéro d'épisode après une barre", r"\|[^|#]{1,15}#\s?\d+"),
]

# Seuils du score de texte, calculé sur l'ensemble des titres d'une chaîne
# (part des titres qui contiennent au moins un signal).
MIN_TITLES_TO_JUDGE = 3     # en dessous, on ne juge pas (verdict "ok")
DOUBTFUL_RATIO = 0.30       # >= : chaîne marquée "douteuse"
FACE_RATIO = 0.60           # >= : chaîne rejetée comme non-faceless