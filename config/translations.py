"""
Sujets de recherche dans les 4 autres langues (es, fr, de, ru) pour chacun des
24 marchés. Chaque liste correspond aux 4 premiers sujets anglais de
config/markets.py, dans le même ordre. L'anglais reste dans markets.py.

Ces listes ne sont qu'un point de départ : à l'étape 4, le moteur de
mots-clés en apprendra de nouveaux à partir des titres des vidéos qui
marchent, dans chaque langue.
"""

TRANSLATED_TOPICS = {
    "history": {
        "es": ["civilizaciones antiguas", "imperios antiguos", "civilizaciones perdidas", "historia medieval"],
        "fr": ["civilisations antiques", "empires antiques", "civilisations perdues", "histoire médiévale"],
        "de": ["antike Zivilisationen", "antike Reiche", "verlorene Zivilisationen", "Geschichte des Mittelalters"],
        "ru": ["древние цивилизации", "древние империи", "потерянные цивилизации", "история средневековья"],
    },
    "finance": {
        "es": ["finanzas personales", "mercado de valores", "ingresos pasivos", "independencia financiera"],
        "fr": ["finances personnelles", "bourse", "revenus passifs", "indépendance financière"],
        "de": ["persönliche Finanzen", "Aktienmarkt", "passives Einkommen", "finanzielle Unabhängigkeit"],
        "ru": ["личные финансы", "фондовый рынок", "пассивный доход", "финансовая независимость"],
    },
    "military": {
        "es": ["militar desclasificado", "historia militar", "documental de historia militar", "ejército guerra fría"],
        "fr": ["militaire déclassifié", "histoire militaire", "documentaire histoire militaire", "armée guerre froide"],
        "de": ["freigegebene Militärakten", "Militärgeschichte", "Dokumentation Militärgeschichte", "Militär im Kalten Krieg"],
        "ru": ["рассекреченные военные материалы", "военная история", "документальный фильм военная история", "армия холодной войны"],
    },
    "fitness": {
        "es": ["entrenamiento de calistenia", "guía de ejercicio en casa", "ciencia del aumento muscular", "historia de transformación física"],
        "fr": ["entraînement de callisthénie", "guide d'entraînement à la maison", "science de la prise de muscle", "histoire de transformation physique"],
        "de": ["Calisthenics Training", "Heimtraining Anleitung", "Wissenschaft des Muskelaufbaus", "Fitness Transformation Geschichte"],
        "ru": ["тренировки калистеники", "домашние тренировки руководство", "наука о росте мышц", "история преображения тела"],
    },
    "health": {
        "es": ["ciencia de la nutrición explicada", "ciencia del sueño", "salud intestinal explicada", "investigación sobre longevidad"],
        "fr": ["science de la nutrition expliquée", "science du sommeil", "santé intestinale expliquée", "recherche sur la longévité"],
        "de": ["Ernährungswissenschaft erklärt", "Schlafforschung", "Darmgesundheit erklärt", "Langlebigkeitsforschung"],
        "ru": ["наука о питании", "наука о сне", "здоровье кишечника", "исследования долголетия"],
    },
    "psychology": {
        "es": ["datos de psicología explicados", "sesgos cognitivos explicados", "ciencia del comportamiento humano", "trucos mentales explicados"],
        "fr": ["faits de psychologie expliqués", "biais cognitifs expliqués", "science du comportement humain", "astuces mentales expliquées"],
        "de": ["Psychologie Fakten erklärt", "kognitive Verzerrungen erklärt", "menschliches Verhalten Wissenschaft", "Gedankentricks erklärt"],
        "ru": ["факты психологии", "когнитивные искажения", "наука о поведении человека", "психологические уловки"],
    },
    "relationships": {
        "es": ["psicología de las relaciones", "estilos de apego explicados", "señales de alerta en citas", "psicología de las rupturas"],
        "fr": ["psychologie des relations", "styles d'attachement expliqués", "signaux d'alerte en couple", "psychologie de la rupture"],
        "de": ["Beziehungspsychologie", "Bindungsstile erklärt", "Warnsignale beim Dating", "Psychologie der Trennung"],
        "ru": ["психология отношений", "типы привязанности", "тревожные сигналы в отношениях", "психология расставания"],
    },
    "true_crime": {
        "es": ["casos de asesinato sin resolver", "documental de crímenes reales", "caso archivado resuelto", "expedientes de asesinos en serie"],
        "fr": ["affaires de meurtre non résolues", "documentaire faits divers", "affaire classée résolue", "dossiers de tueurs en série"],
        "de": ["ungelöste Mordfälle", "True Crime Dokumentation", "Cold Case gelöst", "Fallakten Serienmörder"],
        "ru": ["нераскрытые убийства", "документальный фильм о преступлениях", "раскрытое старое дело", "дела серийных убийц"],
    },
    "gaming": {
        "es": ["documental historia de los videojuegos", "datos de videojuegos explicados", "secretos de la industria del gaming", "historia de los juegos retro"],
        "fr": ["documentaire histoire du jeu vidéo", "faits sur les jeux vidéo expliqués", "secrets de l'industrie du jeu vidéo", "histoire du jeu rétro"],
        "de": ["Dokumentation Geschichte der Videospiele", "Videospiel Fakten erklärt", "Geheimnisse der Gaming Industrie", "Retro Gaming Geschichte"],
        "ru": ["документальный фильм история видеоигр", "факты о видеоиграх", "секреты игровой индустрии", "история ретро игр"],
    },
    "sports": {
        "es": ["documental historia del deporte", "récords deportivos explicados", "documental de atletas", "ciencia del deporte explicada"],
        "fr": ["documentaire histoire du sport", "records sportifs expliqués", "documentaire sur un athlète", "science du sport expliquée"],
        "de": ["Dokumentation Sportgeschichte", "Sportrekorde erklärt", "Sportler Dokumentation", "Sportwissenschaft erklärt"],
        "ru": ["документальный фильм история спорта", "спортивные рекорды", "документальный фильм о спортсмене", "наука о спорте"],
    },
    "food": {
        "es": ["ciencia de los alimentos explicada", "documental historia de la comida", "secretos culinarios explicados", "datos de la industria alimentaria"],
        "fr": ["science de l'alimentation expliquée", "documentaire histoire de la cuisine", "secrets culinaires expliqués", "faits sur l'industrie alimentaire"],
        "de": ["Lebensmittelwissenschaft erklärt", "Dokumentation Geschichte des Essens", "Kochgeheimnisse erklärt", "Fakten zur Lebensmittelindustrie"],
        "ru": ["наука о еде", "документальный фильм история кулинарии", "кулинарные секреты", "факты о пищевой индустрии"],
    },
    "travel": {
        "es": ["documental lugares abandonados", "lugares ocultos explicados", "documental de viajes", "destinos inusuales explicados"],
        "fr": ["documentaire lieux abandonnés", "lieux cachés expliqués", "documentaire de voyage", "destinations insolites expliquées"],
        "de": ["Dokumentation verlassene Orte", "versteckte Orte erklärt", "Reisedokumentation", "ungewöhnliche Reiseziele erklärt"],
        "ru": ["документальный фильм заброшенные места", "скрытые места мира", "документальный фильм о путешествиях", "необычные места для путешествий"],
    },
    "science": {
        "es": ["datos científicos explicados", "física explicada de forma sencilla", "descubrimientos científicos", "misterios de la ciencia resueltos"],
        "fr": ["faits scientifiques expliqués", "physique expliquée simplement", "découvertes scientifiques", "mystères scientifiques résolus"],
        "de": ["Wissenschaft Fakten erklärt", "Physik einfach erklärt", "wissenschaftliche Entdeckungen", "wissenschaftliche Rätsel gelöst"],
        "ru": ["научные факты", "физика простыми словами", "научные открытия", "разгаданные тайны науки"],
    },
    "space": {
        "es": ["datos del espacio explicados", "documental exploración espacial", "astronomía explicada", "misterios del espacio"],
        "fr": ["faits sur l'espace expliqués", "documentaire exploration spatiale", "astronomie expliquée", "mystères de l'espace"],
        "de": ["Weltraum Fakten erklärt", "Dokumentation Raumfahrt", "Astronomie erklärt", "Rätsel des Weltalls"],
        "ru": ["факты о космосе", "документальный фильм освоение космоса", "астрономия простыми словами", "тайны космоса"],
    },
    "technology": {
        "es": ["tecnología explicada", "documental historia de la tecnología", "cómo funciona la tecnología", "tecnología del futuro explicada"],
        "fr": ["technologie expliquée", "documentaire histoire de la technologie", "comment fonctionne la technologie", "technologie du futur expliquée"],
        "de": ["Technologie erklärt", "Dokumentation Technikgeschichte", "wie Technologie funktioniert", "Zukunftstechnologie erklärt"],
        "ru": ["технологии простыми словами", "документальный фильм история технологий", "как работают технологии", "технологии будущего"],
    },
    "ai": {
        "es": ["inteligencia artificial explicada", "documental inteligencia artificial", "datos de IA explicados", "aprendizaje automático explicado de forma sencilla"],
        "fr": ["intelligence artificielle expliquée", "documentaire intelligence artificielle", "faits sur l'IA expliqués", "apprentissage automatique expliqué simplement"],
        "de": ["künstliche Intelligenz erklärt", "Dokumentation künstliche Intelligenz", "KI Fakten erklärt", "maschinelles Lernen einfach erklärt"],
        "ru": ["искусственный интеллект простыми словами", "документальный фильм об искусственном интеллекте", "факты об ИИ", "машинное обучение простыми словами"],
    },
    "cars": {
        "es": ["ingeniería automotriz explicada", "documental historia del automóvil", "datos de coches explicados", "ingeniería de superdeportivos"],
        "fr": ["ingénierie automobile expliquée", "documentaire histoire de l'automobile", "faits sur les voitures expliqués", "ingénierie des supercars"],
        "de": ["Automobiltechnik erklärt", "Dokumentation Automobilgeschichte", "Auto Fakten erklärt", "Supersportwagen Technik"],
        "ru": ["устройство автомобиля", "документальный фильм история автомобилей", "факты об автомобилях", "инженерия суперкаров"],
    },
    "animals": {
        "es": ["documental de animales", "datos de fauna salvaje", "ciencia del comportamiento animal", "supervivencia animal extrema"],
        "fr": ["documentaire animalier", "faits sur la faune sauvage", "science du comportement animal", "survie animale extrême"],
        "de": ["Tierdokumentation", "Fakten über Wildtiere", "Wissenschaft des Tierverhaltens", "extremes Überleben der Tiere"],
        "ru": ["документальный фильм о животных", "факты о диких животных", "наука о поведении животных", "экстремальное выживание животных"],
    },
    "nature": {
        "es": ["documental de naturaleza", "fenómenos naturales explicados", "datos de ciencias de la Tierra", "misterios de la naturaleza explicados"],
        "fr": ["documentaire nature", "phénomènes naturels expliqués", "faits sur les sciences de la Terre", "mystères de la nature expliqués"],
        "de": ["Naturdokumentation", "Naturphänomene erklärt", "Fakten zur Geowissenschaft", "Rätsel der Natur erklärt"],
        "ru": ["документальный фильм о природе", "природные явления", "факты о науках о Земле", "загадки природы"],
    },
    "business": {
        "es": ["documental historia empresarial", "historia de éxito de una empresa", "estrategia empresarial explicada", "historia de una startup explicada"],
        "fr": ["documentaire histoire d'entreprise", "histoire de réussite d'une entreprise", "stratégie d'entreprise expliquée", "histoire d'une startup expliquée"],
        "de": ["Dokumentation Unternehmensgeschichte", "Erfolgsgeschichte eines Unternehmens", "Unternehmensstrategie erklärt", "Startup Geschichte erklärt"],
        "ru": ["документальный фильм история бизнеса", "история успеха компании", "бизнес стратегия простыми словами", "история стартапа"],
    },
    "real_estate": {
        "es": ["inversión inmobiliaria explicada", "mercado inmobiliario explicado", "datos de inversión en propiedades", "documental mercado de la vivienda"],
        "fr": ["investissement immobilier expliqué", "marché immobilier expliqué", "faits sur l'investissement locatif", "documentaire marché du logement"],
        "de": ["Immobilieninvestition erklärt", "Immobilienmarkt erklärt", "Fakten zur Immobilienanlage", "Dokumentation Wohnungsmarkt"],
        "ru": ["инвестиции в недвижимость", "рынок недвижимости простыми словами", "факты об инвестициях в недвижимость", "документальный фильм о рынке жилья"],
    },
    "crypto": {
        "es": ["criptomonedas explicadas", "documental bitcoin", "blockchain explicado de forma sencilla", "historia de las criptomonedas"],
        "fr": ["cryptomonnaies expliquées", "documentaire bitcoin", "blockchain expliquée simplement", "histoire des cryptomonnaies"],
        "de": ["Kryptowährungen erklärt", "Bitcoin Dokumentation", "Blockchain einfach erklärt", "Geschichte der Kryptowährungen"],
        "ru": ["криптовалюты простыми словами", "документальный фильм о биткоине", "блокчейн простыми словами", "история криптовалют"],
    },
    "celebrities": {
        "es": ["documental de famosos", "patrimonio de famosos explicado", "historia de vida de un famoso", "datos de famosos explicados"],
        "fr": ["documentaire sur une célébrité", "fortune des célébrités expliquée", "histoire de vie d'une célébrité", "faits sur les célébrités expliqués"],
        "de": ["Promi Dokumentation", "Vermögen von Prominenten erklärt", "Lebensgeschichte eines Prominenten", "Promi Fakten erklärt"],
        "ru": ["документальный фильм о знаменитости", "состояние знаменитостей", "история жизни знаменитости", "факты о знаменитостях"],
    },
    "luxury": {
        "es": ["documental estilo de vida de lujo", "historia de marcas de lujo", "cosas caras explicadas", "secretos de la industria del lujo"],
        "fr": ["documentaire vie de luxe", "histoire des marques de luxe", "objets chers expliqués", "secrets de l'industrie du luxe"],
        "de": ["Dokumentation Luxusleben", "Geschichte der Luxusmarken", "teure Dinge erklärt", "Geheimnisse der Luxusindustrie"],
        "ru": ["документальный фильм роскошная жизнь", "история люксовых брендов", "дорогие вещи", "секреты индустрии роскоши"],
    },
}