"""
Traductions qui complètent config/translations.py : les mots-clés de départ anglais qui n'avaient pas
encore de version en espagnol, français, allemand et russe, et les formules de titre.

MORE_TOPICS : pour chaque marché, les sujets anglais au-delà du 4e (même ordre que config/markets.py).
FORMULAS    : chaque formule de titre anglaise -> es, fr, de, ru. Les requêtes "sujet + formule" des
              autres langues se construisent comme en anglais (voir config/queries.py).

Ce sont des expressions de recherche (ce que les gens tapent ou mettent dans leurs titres), pas des
traductions mot à mot.
"""

MORE_TOPICS = {
    "history": {
        "es": ["segunda guerra mundial", "primera guerra mundial", "imperio romano", "antiguo egipto",
               "documental de historia", "historia olvidada", "misterios históricos", "guerra fría",
               "historia financiera", "historia alternativa"],
        "fr": ["seconde guerre mondiale", "première guerre mondiale", "empire romain", "égypte antique",
               "documentaire histoire", "histoire oubliée", "mystères historiques", "guerre froide",
               "histoire de la finance", "histoire alternative"],
        "de": ["Zweiter Weltkrieg", "Erster Weltkrieg", "Römisches Reich", "Antikes Ägypten",
               "Geschichtsdokumentation", "vergessene Geschichte", "historische Rätsel", "Kalter Krieg",
               "Finanzgeschichte", "alternative Geschichte"],
        "ru": ["вторая мировая война", "первая мировая война", "Римская империя", "древний Египет",
               "исторический документальный фильм", "забытая история", "исторические загадки", "холодная война",
               "история финансов", "альтернативная история"],
    },
    "finance": {
        "es": ["bases de la inversión", "colapso económico", "errores con el dinero", "puntaje crediticio",
               "inversión inmobiliaria", "ingresos extra", "cómo salir de deudas", "historia económica"],
        "fr": ["bases de l'investissement", "effondrement économique", "erreurs d'argent", "score de crédit",
               "investissement immobilier", "revenu complémentaire", "rembourser ses dettes", "histoire économique"],
        "de": ["Grundlagen des Investierens", "Wirtschaftskollaps", "Geldfehler", "Kreditscore",
               "Immobilieninvestition", "Nebenverdienst", "Schulden abbezahlen", "Wirtschaftsgeschichte"],
        "ru": ["основы инвестирования", "экономический коллапс", "ошибки с деньгами", "кредитный рейтинг",
               "инвестиции в недвижимость", "подработка", "как погасить долги", "экономическая история"],
    },
    "military": {
        "es": ["estrategia militar explicada", "documental de la segunda guerra mundial",
               "tecnología militar explicada", "historia de las fuerzas especiales",
               "serie documental de la segunda guerra mundial", "la tecnología militar más avanzada",
               "historia de un grupo de fuerzas especiales", "fuerzas especiales del Reino Unido"],
        "fr": ["stratégie militaire expliquée", "documentaire seconde guerre mondiale",
               "technologie militaire expliquée", "histoire des forces spéciales",
               "série documentaire seconde guerre mondiale", "la technologie militaire la plus avancée",
               "histoire d'un groupe de forces spéciales", "forces spéciales britanniques"],
        "de": ["Militärstrategie erklärt", "Dokumentation Zweiter Weltkrieg", "Militärtechnologie erklärt",
               "Geschichte der Spezialeinheiten", "Dokuserie Zweiter Weltkrieg", "modernste Militärtechnologie",
               "Geschichte einer Spezialeinheit", "britische Spezialeinheiten"],
        "ru": ["военная стратегия объяснение", "документальный фильм о второй мировой войне",
               "военные технологии объяснение", "история спецназа",
               "документальный сериал о второй мировой войне", "самые передовые военные технологии",
               "история подразделения спецназа", "британский спецназ"],
    },
    "fitness": {
        "es": ["bases del entrenamiento de fuerza", "ejercicios con peso corporal"],
        "fr": ["bases de la musculation", "exercices au poids du corps"],
        "de": ["Krafttraining Grundlagen", "Übungen mit dem eigenen Körpergewicht"],
        "ru": ["основы силовых тренировок", "упражнения с собственным весом"],
    },
    "health": {
        "es": ["misterios médicos resueltos", "datos curiosos del cuerpo humano"],
        "fr": ["mystères médicaux résolus", "faits sur le corps humain"],
        "de": ["gelöste medizinische Rätsel", "Fakten über den menschlichen Körper"],
        "ru": ["разгаданные медицинские загадки", "факты о человеческом теле"],
    },
    "psychology": {
        "es": ["experimentos psicológicos"],
        "fr": ["expériences psychologiques"],
        "de": ["psychologische Experimente"],
        "ru": ["психологические эксперименты"],
    },
    "true_crime": {
        "es": ["caso de personas desaparecidas"],
        "fr": ["affaire de disparition"],
        "de": ["Vermisstenfall"],
        "ru": ["дело о пропавших без вести"],
    },
}

# anglais -> (es, fr, de, ru)
_FORMULAS = {
    "explained": ("explicado", "expliqué", "erklärt", "объяснение"),
    "the true story of": ("la verdadera historia de", "la véritable histoire de", "die wahre Geschichte von", "правдивая история"),
    "what really happened": ("lo que realmente pasó", "ce qui s'est vraiment passé", "was wirklich geschah", "что произошло на самом деле"),
    "vs reality": ("vs la realidad", "vs la réalité", "vs Realität", "против реальности"),
    "the rise and fall of": ("auge y caída de", "ascension et chute de", "Aufstieg und Fall von", "взлёт и падение"),
    "the history of": ("la historia de", "l'histoire de", "die Geschichte von", "история"),
    "the truth about": ("la verdad sobre", "la vérité sur", "die Wahrheit über", "правда о"),
    "why you're broke": ("por qué estás en la ruina", "pourquoi tu es fauché", "warum du pleite bist", "почему у тебя нет денег"),
    "what nobody tells you about": ("lo que nadie te cuenta sobre", "ce que personne ne te dit sur", "was dir niemand erzählt", "о чём никто не говорит"),
    "the math behind": ("las matemáticas detrás de", "les maths derrière", "die Mathematik hinter", "математика за"),
    "how to actually": ("cómo realmente", "comment vraiment", "wie man wirklich", "как на самом деле"),
    "declassified": ("desclasificado", "déclassifié", "freigegeben", "рассекречено"),
    "the science of": ("la ciencia de", "la science de", "die Wissenschaft von", "наука о"),
    "before and after": ("antes y después", "avant et après", "vorher und nachher", "до и после"),
    "the psychology of": ("la psicología de", "la psychologie de", "die Psychologie von", "психология"),
    "why you": ("por qué tú", "pourquoi tu", "warum du", "почему ты"),
    "what it really means when": ("lo que realmente significa cuando", "ce que ça veut vraiment dire quand", "was es wirklich bedeutet wenn", "что на самом деле значит когда"),
    "signs that": ("señales de que", "signes que", "Anzeichen dafür dass", "признаки что"),
    "why he/she": ("por qué él/ella", "pourquoi il/elle", "warum er/sie", "почему он/она"),
    "solved": ("resuelto", "résolu", "gelöst", "раскрыто"),
    "the disappearance of": ("la desaparición de", "la disparition de", "das Verschwinden von", "исчезновение"),
    "what happened to": ("qué pasó con", "ce qui est arrivé à", "was geschah mit", "что случилось с"),
    "the secret behind": ("el secreto detrás de", "le secret derrière", "das Geheimnis hinter", "секрет"),
    "the mystery of": ("el misterio de", "le mystère de", "das Rätsel um", "тайна"),
    "why nobody visits": ("por qué nadie visita", "pourquoi personne ne visite", "warum niemand besucht", "почему туда никто не ездит"),
    "the science behind": ("la ciencia detrás de", "la science derrière", "die Wissenschaft hinter", "наука за"),
    "what really happens when": ("qué pasa realmente cuando", "ce qui se passe vraiment quand", "was wirklich passiert wenn", "что на самом деле происходит когда"),
    "how it actually works": ("cómo funciona realmente", "comment ça marche vraiment", "wie es wirklich funktioniert", "как это работает на самом деле"),
    "how they survive": ("cómo sobreviven", "comment ils survivent", "wie sie überleben", "как они выживают"),
    "the final minutes": ("los últimos minutos", "les dernières minutes", "die letzten Minuten", "последние минуты"),
    "documentary": ("documental", "documentaire", "Dokumentation", "документальный фильм"),
    "investigation": ("investigación", "enquête", "Ermittlung", "расследование"),
    "why": ("por qué", "pourquoi", "warum", "почему"),
    "map": ("mapa", "carte", "Karte", "карта"),
    "collapse": ("colapso", "effondrement", "Zusammenbruch", "коллапс"),
    "the real reason": ("la verdadera razón", "la vraie raison", "der wahre Grund", "настоящая причина"),
    "who really controls": ("quién controla realmente", "qui contrôle vraiment", "wer wirklich kontrolliert", "кто на самом деле контролирует"),
    "origins of": ("orígenes de", "origines de", "Ursprünge von", "происхождение"),
    "mythology": ("mitología", "mythologie", "Mythologie", "мифология"),
    "the dark side of": ("el lado oscuro de", "le côté obscur de", "die dunkle Seite von", "тёмная сторона"),
    "full story": ("historia completa", "histoire complète", "die ganze Geschichte", "полная история"),
}

FORMULAS = {
    en: dict(zip(("es", "fr", "de", "ru"), tr)) for en, tr in _FORMULAS.items()
}
