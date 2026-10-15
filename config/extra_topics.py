"""
Mots-clés supplémentaires (trouvés avec TubeLab) + 3 nouveaux marchés.

Chaque ligne = (anglais, espagnol, français, allemand, russe).
Ces mots-clés servent de réserve : à chaque passage, seule une partie
tourne (EXTRA_PER_RUN par marché et par langue, en rotation chaque semaine),
pour ne pas dépasser le quota YouTube. Au bout de quelques semaines tout
a été testé. À l'étape 4, le moteur de mots-clés gardera ceux qui rapportent.
"""

from config.translations import TRANSLATED_TOPICS

EXTRA_PER_RUN = 3

# Nouveaux marchés : formules de titre (les mots-clés sont plus bas)
NEW_MARKET_FORMULAS = {
    "disasters": ["what really happened", "explained", "the final minutes", "documentary", "investigation", "the true story of"],
    "geopolitics": ["explained", "why", "map", "collapse", "the real reason", "who really controls"],
    "mythology": ["explained", "the true story of", "origins of", "mythology", "the dark side of", "full story"],
}

KEYWORDS = {
    "relationships": [
        ("toxic relationship signs", "señales de relación tóxica", "signes d'une relation toxique", "Anzeichen einer toxischen Beziehung", "признаки токсичных отношений"),
        ("dating advice for men", "consejos de citas para hombres", "conseils de séduction pour hommes", "Dating-Tipps für Männer", "советы по знакомствам для мужчин"),
        ("attachment styles explained", "estilos de apego explicados", "styles d'attachement expliqués", "Bindungstypen erklärt", "типы привязанности объяснение"),
        ("signs he is losing interest", "señales de que pierde el interés", "signes qu'il perd intérêt", "Anzeichen für nachlassendes Interesse", "признаки что он теряет интерес"),
        ("breakup recovery", "superar una ruptura", "se remettre d'une rupture", "Trennung überwinden", "как пережить расставание"),
        ("dark psychology of love", "psicología oscura del amor", "psychologie sombre de l'amour", "dunkle Psychologie der Liebe", "тёмная психология любви"),
        ("marriage problems", "problemas de matrimonio", "problèmes de couple", "Eheprobleme", "проблемы в браке"),
        ("narcissist relationship", "relación con un narcisista", "relation avec un narcissique", "Beziehung mit einem Narzissten", "отношения с нарциссом"),
        ("how to be attractive", "cómo ser atractivo", "comment être attirant", "wie man attraktiv wird", "как быть привлекательным"),
        ("loneliness and friendship", "soledad y amistad", "solitude et amitié", "Einsamkeit und Freundschaft", "одиночество и дружба"),
    ],
    "gaming": [
        ("retro gaming history", "historia de los videojuegos retro", "histoire du jeu vidéo rétro", "Geschichte der Retro-Spiele", "история ретро игр"),
        ("console wars", "guerra de consolas", "guerre des consoles", "Konsolenkrieg", "война консолей"),
        ("video game industry rise and fall", "auge y caída de la industria del videojuego", "essor et chute de l'industrie du jeu vidéo", "Aufstieg und Fall der Spieleindustrie", "взлёт и падение игровой индустрии"),
        ("indie game development story", "historia de un juego indie", "histoire d'un jeu indépendant", "Geschichte eines Indie-Spiels", "история создания инди игры"),
        ("lost video games", "videojuegos perdidos", "jeux vidéo perdus", "verlorene Videospiele", "потерянные видеоигры"),
        ("game studio collapse", "cierre de estudio de videojuegos", "chute d'un studio de jeux vidéo", "Spielestudio Pleite", "крах игровой студии"),
        ("gaming controversies", "polémicas de videojuegos", "polémiques du jeu vidéo", "Gaming-Skandale", "скандалы в играх"),
        ("minecraft lore", "historia de minecraft", "histoire de minecraft", "Minecraft Geschichte", "история майнкрафта"),
        ("unsolved video game mysteries", "misterios sin resolver de videojuegos", "mystères non résolus des jeux vidéo", "ungelöste Videospiel-Rätsel", "нерешённые загадки видеоигр"),
        ("best selling games of all time", "videojuegos más vendidos de la historia", "jeux vidéo les plus vendus de l'histoire", "meistverkaufte Spiele aller Zeiten", "самые продаваемые игры в истории"),
    ],
    "sports": [
        ("forgotten stadiums", "estadios olvidados", "stades oubliés", "vergessene Stadien", "забытые стадионы"),
        ("rise and fall of football clubs", "auge y caída de clubes de fútbol", "essor et chute de clubs de football", "Aufstieg und Fall von Fußballvereinen", "взлёт и падение футбольных клубов"),
        ("1970s nfl history", "historia de la nfl de los años 70", "histoire de la nfl des années 70", "NFL Geschichte der 70er", "история НФЛ 70-х"),
        ("greatest athletes of all time", "los mejores atletas de la historia", "les plus grands athlètes de l'histoire", "größte Athleten aller Zeiten", "величайшие спортсмены в истории"),
        ("sports scandals", "escándalos deportivos", "scandales sportifs", "Sportskandale", "спортивные скандалы"),
        ("tragic sports stories", "historias trágicas del deporte", "histoires tragiques du sport", "tragische Sportgeschichten", "трагические истории в спорте"),
        ("boxing history", "historia del boxeo", "histoire de la boxe", "Boxgeschichte", "история бокса"),
        ("olympic games history", "historia de los juegos olímpicos", "histoire des jeux olympiques", "Geschichte der Olympischen Spiele", "история олимпийских игр"),
        ("greatest comebacks in sports", "las mejores remontadas del deporte", "les plus grandes remontadas du sport", "größte Comebacks im Sport", "величайшие камбэки в спорте"),
        ("football transfers explained", "fichajes de fútbol explicados", "transferts de football expliqués", "Fußball-Transfers erklärt", "трансферы в футболе объяснение"),
    ],
    "food": [
        ("banned foods", "alimentos prohibidos", "aliments interdits", "verbotene Lebensmittel", "запрещённые продукты"),
        ("foods invented by accident", "alimentos inventados por accidente", "aliments inventés par accident", "zufällig erfundene Lebensmittel", "продукты изобретённые случайно"),
        ("every food explained", "todos los alimentos explicados", "tous les aliments expliqués", "alle Lebensmittel erklärt", "все продукты объяснение"),
        ("history of fast food", "historia de la comida rápida", "histoire du fast food", "Geschichte von Fast Food", "история фастфуда"),
        ("food industry secrets", "secretos de la industria alimentaria", "secrets de l'industrie alimentaire", "Geheimnisse der Lebensmittelindustrie", "секреты пищевой индустрии"),
        ("street food around the world", "comida callejera del mundo", "street food dans le monde", "Streetfood weltweit", "уличная еда мира"),
        ("origin of famous dishes", "origen de platos famosos", "origine des plats célèbres", "Ursprung berühmter Gerichte", "происхождение известных блюд"),
        ("food that is not what you think", "alimentos que no son lo que crees", "aliments qui ne sont pas ce que vous croyez", "Lebensmittel die nicht sind wofür man sie hält", "еда не то чем кажется"),
        ("ancient recipes", "recetas antiguas", "recettes anciennes", "antike Rezepte", "древние рецепты"),
        ("restaurant chains collapse", "quiebra de cadenas de restaurantes", "chute des chaînes de restaurants", "Pleite von Restaurantketten", "крах сетей ресторанов"),
    ],
    "travel": [
        ("abandoned places", "lugares abandonados", "lieux abandonnés", "verlassene Orte", "заброшенные места"),
        ("abandoned roads and infrastructure", "carreteras e infraestructuras abandonadas", "routes et infrastructures abandonnées", "verlassene Straßen und Infrastruktur", "заброшенные дороги и инфраструктура"),
        ("haunted places", "lugares embrujados", "lieux hantés", "Spukorte", "места с привидениями"),
        ("ghost towns", "pueblos fantasma", "villes fantômes", "Geisterstädte", "города-призраки"),
        ("most dangerous places on earth", "los lugares más peligrosos de la tierra", "les endroits les plus dangereux de la terre", "gefährlichste Orte der Erde", "самые опасные места на земле"),
        ("hidden places nobody visits", "lugares ocultos que nadie visita", "endroits cachés que personne ne visite", "versteckte Orte die niemand besucht", "скрытые места куда никто не ездит"),
        ("forbidden islands", "islas prohibidas", "îles interdites", "verbotene Inseln", "запретные острова"),
        ("world's strangest places", "los lugares más extraños del mundo", "les endroits les plus étranges du monde", "seltsamste Orte der Welt", "самые странные места мира"),
        ("lost cities", "ciudades perdidas", "villes perdues", "verlorene Städte", "потерянные города"),
        ("underground cities", "ciudades subterráneas", "villes souterraines", "unterirdische Städte", "подземные города"),
    ],
    "science": [
        ("physics explained simply", "física explicada de forma sencilla", "la physique expliquée simplement", "Physik einfach erklärt", "физика простыми словами"),
        ("unsolved mysteries of science", "misterios sin resolver de la ciencia", "mystères non résolus de la science", "ungelöste Rätsel der Wissenschaft", "нерешённые загадки науки"),
        ("how the human body works", "cómo funciona el cuerpo humano", "comment fonctionne le corps humain", "wie der menschliche Körper funktioniert", "как работает человеческое тело"),
        ("quantum mechanics explained", "mecánica cuántica explicada", "la mécanique quantique expliquée", "Quantenmechanik erklärt", "квантовая механика объяснение"),
        ("deep sea mysteries", "misterios del fondo del mar", "mystères des profondeurs de la mer", "Rätsel der Tiefsee", "тайны морских глубин"),
        ("strange science facts", "datos científicos extraños", "faits scientifiques étranges", "seltsame wissenschaftliche Fakten", "странные научные факты"),
        ("geology and earth's interior", "geología y el interior de la tierra", "géologie et intérieur de la terre", "Geologie und Erdinneres", "геология и недра земли"),
        ("history of scientific discoveries", "historia de los descubrimientos científicos", "histoire des découvertes scientifiques", "Geschichte wissenschaftlicher Entdeckungen", "история научных открытий"),
        ("extinct species", "especies extintas", "espèces disparues", "ausgestorbene Arten", "вымершие виды"),
        ("chemistry in everyday life", "química en la vida cotidiana", "la chimie du quotidien", "Chemie im Alltag", "химия в повседневной жизни"),
    ],
    "space": [
        ("black holes explained", "agujeros negros explicados", "les trous noirs expliqués", "Schwarze Löcher erklärt", "чёрные дыры объяснение"),
        ("nasa missions history", "historia de las misiones de la nasa", "histoire des missions de la nasa", "Geschichte der NASA-Missionen", "история миссий НАСА"),
        ("mars colonization", "colonización de marte", "colonisation de mars", "Marskolonisierung", "колонизация марса"),
        ("james webb telescope discoveries", "descubrimientos del telescopio james webb", "découvertes du télescope james webb", "Entdeckungen des James-Webb-Teleskops", "открытия телескопа джеймс уэбб"),
        ("space disasters", "desastres espaciales", "catastrophes spatiales", "Weltraumkatastrophen", "космические катастрофы"),
        ("how big is the universe", "qué tan grande es el universo", "quelle est la taille de l'univers", "wie groß ist das Universum", "насколько велика вселенная"),
        ("alien life search", "búsqueda de vida extraterrestre", "recherche de vie extraterrestre", "Suche nach außerirdischem Leben", "поиск внеземной жизни"),
        ("solar system planets facts", "datos de los planetas del sistema solar", "faits sur les planètes du système solaire", "Fakten über die Planeten des Sonnensystems", "факты о планетах солнечной системы"),
        ("end of the universe", "el fin del universo", "la fin de l'univers", "das Ende des Universums", "конец вселенной"),
        ("apollo missions untold stories", "historias no contadas de las misiones apolo", "histoires inédites des missions apollo", "unerzählte Geschichten der Apollo-Missionen", "нерассказанные истории миссий аполлон"),
    ],
    "technology": [
        ("history of the internet", "historia de internet", "histoire d'internet", "Geschichte des Internets", "история интернета"),
        ("tech companies rise and fall", "auge y caída de empresas tecnológicas", "essor et chute des entreprises technologiques", "Aufstieg und Fall von Tech-Unternehmen", "взлёт и падение технологических компаний"),
        ("how computers work", "cómo funcionan los ordenadores", "comment fonctionnent les ordinateurs", "wie Computer funktionieren", "как работают компьютеры"),
        ("future technology predictions", "predicciones de tecnología del futuro", "prédictions des technologies du futur", "Zukunftstechnologien Vorhersagen", "прогнозы технологий будущего"),
        ("failed tech products", "productos tecnológicos fracasados", "produits technologiques ratés", "gescheiterte Tech-Produkte", "провальные технологические продукты"),
        ("cybersecurity stories", "historias de ciberseguridad", "histoires de cybersécurité", "Cybersicherheit Geschichten", "истории кибербезопасности"),
        ("how smartphones changed the world", "cómo los teléfonos inteligentes cambiaron el mundo", "comment les smartphones ont changé le monde", "wie Smartphones die Welt veränderten", "как смартфоны изменили мир"),
        ("semiconductor industry explained", "industria de semiconductores explicada", "l'industrie des semi-conducteurs expliquée", "Halbleiterindustrie erklärt", "полупроводниковая индустрия объяснение"),
        ("old technology forgotten", "tecnología antigua olvidada", "technologies anciennes oubliées", "vergessene alte Technologie", "забытые старые технологии"),
        ("social media history", "historia de las redes sociales", "histoire des réseaux sociaux", "Geschichte der sozialen Medien", "история социальных сетей"),
    ],
    "ai": [
        ("artificial intelligence explained", "inteligencia artificial explicada", "l'intelligence artificielle expliquée", "künstliche Intelligenz erklärt", "искусственный интеллект объяснение"),
        ("ai taking jobs", "la ia quitando empleos", "l'ia qui supprime des emplois", "KI nimmt Jobs weg", "ИИ отнимает работу"),
        ("future of ai", "futuro de la ia", "futur de l'ia", "Zukunft der KI", "будущее ИИ"),
        ("ai tools for beginners", "herramientas de ia para principiantes", "outils d'ia pour débutants", "KI-Tools für Anfänger", "инструменты ИИ для начинающих"),
        ("dangers of ai", "peligros de la ia", "dangers de l'ia", "Gefahren der KI", "опасности ИИ"),
        ("history of artificial intelligence", "historia de la inteligencia artificial", "histoire de l'intelligence artificielle", "Geschichte der künstlichen Intelligenz", "история искусственного интеллекта"),
        ("ai makes money online", "ganar dinero con ia", "gagner de l'argent avec l'ia", "mit KI Geld verdienen", "заработок с помощью ИИ"),
        ("which ai is the best", "cuál es la mejor ia", "quelle est la meilleure ia", "welche KI ist die beste", "какой ИИ лучший"),
        ("ai robots humanoid", "robots humanoides con ia", "robots humanoïdes avec ia", "humanoide KI-Roboter", "человекоподобные роботы с ИИ"),
        ("ai generated stories", "historias generadas por ia", "histoires générées par ia", "von KI generierte Geschichten", "истории созданные ИИ"),
    ],
    "cars": [
        ("engine engineering explained", "ingeniería del motor explicada", "ingénierie du moteur expliquée", "Motortechnik erklärt", "устройство двигателя объяснение"),
        ("classic cars history", "historia de los coches clásicos", "histoire des voitures classiques", "Geschichte der Oldtimer", "история классических автомобилей"),
        ("car brand collapse", "caída de marcas de coches", "chute des marques automobiles", "Untergang von Automarken", "крах автомобильных брендов"),
        ("worst cars ever made", "los peores coches jamás fabricados", "les pires voitures jamais fabriquées", "schlechteste Autos aller Zeiten", "худшие автомобили в истории"),
        ("electric cars explained", "coches eléctricos explicados", "les voitures électriques expliquées", "Elektroautos erklärt", "электромобили объяснение"),
        ("supercars history", "historia de los superdeportivos", "histoire des supercars", "Geschichte der Supersportwagen", "история суперкаров"),
        ("car recalls and scandals", "retiradas y escándalos de coches", "rappels et scandales automobiles", "Autorückrufe und Skandale", "отзывы и скандалы автомобилей"),
        ("forgotten car brands", "marcas de coches olvidadas", "marques de voitures oubliées", "vergessene Automarken", "забытые автомобильные бренды"),
        ("how cars are made", "cómo se fabrican los coches", "comment sont fabriquées les voitures", "wie Autos gebaut werden", "как делают автомобили"),
        ("motorcycles history", "historia de las motos", "histoire des motos", "Geschichte der Motorräder", "история мотоциклов"),
    ],
    "animals": [
        ("wildlife survival documentary", "documental de supervivencia animal", "documentaire de survie animale", "Tierdokumentation Überleben", "документальный фильм о выживании животных"),
        ("predator vs prey", "depredador contra presa", "prédateur contre proie", "Raubtier gegen Beute", "хищник против жертвы"),
        ("animal life cycle egg to survivor", "ciclo de vida animal del huevo al superviviente", "cycle de vie animal de l'œuf à la survie", "Lebenszyklus vom Ei zum Überlebenden", "жизненный цикл животного от яйца до выжившего"),
        ("strangest animals on earth", "los animales más extraños de la tierra", "les animaux les plus étranges de la terre", "seltsamste Tiere der Erde", "самые странные животные земли"),
        ("deadliest animals", "los animales más letales", "les animaux les plus mortels", "tödlichste Tiere", "самые смертоносные животные"),
        ("deep sea creatures", "criaturas de las profundidades", "créatures des abysses", "Tiefseekreaturen", "существа глубин океана"),
        ("animal intelligence", "inteligencia animal", "intelligence animale", "Tierintelligenz", "интеллект животных"),
        ("extinct animals and prehistoric creatures", "animales extintos y criaturas prehistóricas", "animaux disparus et créatures préhistoriques", "ausgestorbene Tiere und prähistorische Kreaturen", "вымершие животные и доисторические существа"),
        ("big cats hunting", "grandes felinos cazando", "grands félins à la chasse", "Großkatzen bei der Jagd", "охота больших кошек"),
        ("birds of prey", "aves rapaces", "oiseaux de proie", "Greifvögel", "хищные птицы"),
    ],
    "nature": [
        ("natural disasters explained", "desastres naturales explicados", "catastrophes naturelles expliquées", "Naturkatastrophen erklärt", "природные катастрофы объяснение"),
        ("rare earth phenomena", "fenómenos raros de la tierra", "phénomènes rares de la terre", "seltene Naturphänomene", "редкие явления природы"),
        ("isolated islands documentary", "documental de islas aisladas", "documentaire sur les îles isolées", "Dokumentation über isolierte Inseln", "документальный фильм об изолированных островах"),
        ("volcano eruptions", "erupciones volcánicas", "éruptions volcaniques", "Vulkanausbrüche", "извержения вулканов"),
        ("tsunami and earthquakes", "tsunamis y terremotos", "tsunamis et séismes", "Tsunamis und Erdbeben", "цунами и землетрясения"),
        ("rainforest secrets", "secretos de la selva tropical", "secrets de la forêt tropicale", "Geheimnisse des Regenwaldes", "тайны тропического леса"),
        ("mountains and glaciers", "montañas y glaciares", "montagnes et glaciers", "Berge und Gletscher", "горы и ледники"),
        ("deserts of the world", "desiertos del mundo", "déserts du monde", "Wüsten der Welt", "пустыни мира"),
        ("oceans and sea mysteries", "océanos y misterios del mar", "océans et mystères de la mer", "Ozeane und Meeresrätsel", "океаны и тайны моря"),
        ("climate and weather extremes", "clima y fenómenos meteorológicos extremos", "climat et phénomènes météo extrêmes", "Klima und Wetterextreme", "климат и экстремальная погода"),
    ],
    "business": [
        ("rise and fall of companies", "auge y caída de empresas", "essor et chute d'entreprises", "Aufstieg und Fall von Unternehmen", "взлёт и падение компаний"),
        ("abandoned factories history", "historia de fábricas abandonadas", "histoire des usines abandonnées", "Geschichte verlassener Fabriken", "история заброшенных заводов"),
        ("business case studies", "casos de estudio de negocios", "études de cas d'entreprises", "Business Fallstudien", "бизнес кейсы"),
        ("biggest corporate scandals", "los mayores escándalos corporativos", "les plus grands scandales d'entreprise", "größte Unternehmensskandale", "крупнейшие корпоративные скандалы"),
        ("how billionaires made their fortune", "cómo los multimillonarios hicieron su fortuna", "comment les milliardaires ont fait fortune", "wie Milliardäre ihr Vermögen machten", "как миллиардеры сделали состояния"),
        ("brand history and origin", "historia y origen de marcas", "histoire et origine des marques", "Markengeschichte und Ursprung", "история и происхождение брендов"),
        ("failed startups", "startups fracasadas", "start-ups qui ont échoué", "gescheiterte Startups", "провальные стартапы"),
        ("business model explained", "modelo de negocio explicado", "modèle économique expliqué", "Geschäftsmodell erklärt", "бизнес-модель объяснение"),
        ("monopolies and big companies", "monopolios y grandes empresas", "monopoles et grandes entreprises", "Monopole und Großkonzerne", "монополии и крупные компании"),
        ("retail store closures", "cierre de tiendas minoristas", "fermeture de magasins", "Schließung von Einzelhandelsgeschäften", "закрытие розничных магазинов"),
    ],
    "real_estate": [
        ("luxury mansions flooding or sinking", "mansiones de lujo inundadas o hundidas", "villas de luxe inondées ou qui s'enfoncent", "Luxusvillen überflutet oder versinkend", "роскошные особняки затопление или оседание"),
        ("cheap homes with land", "casas baratas con terreno", "maisons pas chères avec terrain", "günstige Häuser mit Grundstück", "дешёвые дома с землёй"),
        ("empty homes and ghost neighborhoods", "casas vacías y barrios fantasma", "maisons vides et quartiers fantômes", "leere Häuser und Geisterviertel", "пустые дома и районы-призраки"),
        ("housing market crash", "caída del mercado inmobiliario", "krach immobilier", "Immobiliencrash", "обвал рынка недвижимости"),
        ("most expensive houses in the world", "las casas más caras del mundo", "les maisons les plus chères du monde", "teuerste Häuser der Welt", "самые дорогие дома мира"),
        ("house flipping", "reformar y vender casas", "revente de maisons rénovées", "Häuser renovieren und verkaufen", "флиппинг домов"),
        ("tiny homes", "casas pequeñas", "micro-maisons", "Tiny Houses", "крошечные дома"),
        ("why houses are so expensive", "por qué las casas son tan caras", "pourquoi les maisons sont si chères", "warum Häuser so teuer sind", "почему дома так дорогие"),
        ("abandoned mansions", "mansiones abandonadas", "manoirs abandonnés", "verlassene Villen", "заброшенные особняки"),
        ("city housing crisis", "crisis de vivienda en las ciudades", "crise du logement dans les villes", "Wohnungskrise in Städten", "жилищный кризис в городах"),
    ],
    "crypto": [
        ("bitcoin explained", "bitcoin explicado", "le bitcoin expliqué", "Bitcoin erklärt", "биткоин объяснение"),
        ("crypto scams and collapses", "estafas y colapsos cripto", "arnaques et effondrements crypto", "Krypto Betrug und Zusammenbrüche", "крипто мошенничество и крахи"),
        ("currency collapse explained", "colapso de una moneda explicado", "effondrement d'une monnaie expliqué", "Währungskollaps erklärt", "крах валюты объяснение"),
        ("economic crisis explained", "crisis económica explicada", "crise économique expliquée", "Wirtschaftskrise erklärt", "экономический кризис объяснение"),
        ("great depression", "la gran depresión", "la grande dépression", "Weltwirtschaftskrise", "великая депрессия"),
        ("inflation explained", "inflación explicada", "l'inflation expliquée", "Inflation erklärt", "инфляция объяснение"),
        ("history of money", "historia del dinero", "histoire de la monnaie", "Geschichte des Geldes", "история денег"),
        ("ethereum and altcoins", "ethereum y altcoins", "ethereum et altcoins", "Ethereum und Altcoins", "эфириум и альткоины"),
        ("stock market crash history", "historia de los crashes bursátiles", "histoire des krachs boursiers", "Geschichte der Börsencrashs", "история биржевых крахов"),
        ("banks and financial system explained", "bancos y sistema financiero explicados", "banques et système financier expliqués", "Banken und Finanzsystem erklärt", "банки и финансовая система объяснение"),
    ],
    "celebrities": [
        ("hollywood actors facts", "datos de actores de hollywood", "faits sur les acteurs d'hollywood", "Fakten über Hollywood-Schauspieler", "факты об актёрах голливуда"),
        ("richest people in history", "las personas más ricas de la historia", "les personnes les plus riches de l'histoire", "reichste Menschen der Geschichte", "самые богатые люди в истории"),
        ("celebrity life stories", "historias de vida de famosos", "histoires de vie de célébrités", "Lebensgeschichten von Prominenten", "истории жизни знаменитостей"),
        ("fall of famous stars", "caída de famosos", "chute de stars célèbres", "Absturz berühmter Stars", "падение известных звёзд"),
        ("child stars what happened", "qué pasó con los niños estrella", "que sont devenues les enfants stars", "was aus Kinderstars wurde", "что стало с детьми-звёздами"),
        ("celebrity net worth", "fortuna de los famosos", "fortune des célébrités", "Vermögen von Prominenten", "состояние знаменитостей"),
        ("musicians biography", "biografía de músicos", "biographie de musiciens", "Musiker Biografie", "биография музыкантов"),
        ("celebrity scandals", "escándalos de famosos", "scandales de célébrités", "Promi-Skandale", "скандалы знаменитостей"),
        ("tragic deaths of famous people", "muertes trágicas de famosos", "morts tragiques de célébrités", "tragische Tode berühmter Menschen", "трагические смерти знаменитостей"),
        ("movie stars before they were famous", "estrellas de cine antes de la fama", "stars de cinéma avant la célébrité", "Filmstars vor dem Ruhm", "кинозвёзды до славы"),
    ],
    "luxury": [
        ("luxury brands history", "historia de marcas de lujo", "histoire des marques de luxe", "Geschichte von Luxusmarken", "история люксовых брендов"),
        ("billionaire lifestyle", "estilo de vida de multimillonarios", "mode de vie des milliardaires", "Lebensstil von Milliardären", "образ жизни миллиардеров"),
        ("most expensive things in the world", "las cosas más caras del mundo", "les choses les plus chères du monde", "teuerste Dinge der Welt", "самые дорогие вещи в мире"),
        ("luxury watches", "relojes de lujo", "montres de luxe", "Luxusuhren", "роскошные часы"),
        ("superyachts and private jets", "superyates y jets privados", "superyachts et jets privés", "Superyachten und Privatjets", "суперяхты и частные самолёты"),
        ("luxury hotels", "hoteles de lujo", "hôtels de luxe", "Luxushotels", "роскошные отели"),
        ("how luxury brands make money", "cómo ganan dinero las marcas de lujo", "comment les marques de luxe gagnent de l'argent", "wie Luxusmarken Geld verdienen", "как люксовые бренды зарабатывают деньги"),
        ("fashion house rise and fall", "auge y caída de casas de moda", "essor et chute de maisons de mode", "Aufstieg und Fall von Modehäusern", "взлёт и падение модных домов"),
        ("royal wealth and palaces", "riqueza real y palacios", "richesse royale et palais", "königlicher Reichtum und Paläste", "богатство королевских семей и дворцы"),
        ("luxury cars and supercars collectors", "coleccionistas de coches de lujo", "collectionneurs de voitures de luxe", "Sammler von Luxusautos", "коллекционеры роскошных автомобилей"),
    ],
    "psychology": [
        ("psychology explained signs", "psicología explicada señales", "psychologie expliquée signes", "Psychologie erklärt Anzeichen", "психология объяснение признаки"),
        ("human behavior facts", "datos sobre el comportamiento humano", "faits sur le comportement humain", "Fakten über menschliches Verhalten", "факты о поведении человека"),
        ("psychology of generations", "psicología de las generaciones", "psychologie des générations", "Psychologie der Generationen", "психология поколений"),
        ("habits of high iq people", "hábitos de personas con alto coeficiente intelectual", "habitudes des personnes à haut qi", "Gewohnheiten von Menschen mit hohem IQ", "привычки людей с высоким IQ"),
        ("emotional immaturity signs", "señales de inmadurez emocional", "signes d'immaturité émotionnelle", "Anzeichen emotionaler Unreife", "признаки эмоциональной незрелости"),
        ("psychology of introverts", "psicología de los introvertidos", "psychologie des introvertis", "Psychologie der Introvertierten", "психология интровертов"),
        ("cognitive biases", "sesgos cognitivos", "biais cognitifs", "kognitive Verzerrungen", "когнитивные искажения"),
        ("stoicism and mindset", "estoicismo y mentalidad", "stoïcisme et état d'esprit", "Stoizismus und Denkweise", "стоицизм и мышление"),
    ],
    "finance": [
        ("currency collapse", "colapso de una moneda", "effondrement d'une monnaie", "Währungskollaps", "крах валюты"),
        ("great depression explained", "la gran depresión explicada", "la grande dépression expliquée", "Weltwirtschaftskrise erklärt", "великая депрессия объяснение"),
        ("why countries go bankrupt", "por qué los países quiebran", "pourquoi les pays font faillite", "warum Länder bankrott gehen", "почему страны банкротятся"),
        ("how the economy works", "cómo funciona la economía", "comment fonctionne l'économie", "wie die Wirtschaft funktioniert", "как работает экономика"),
    ],
    "disasters": [
        ("plane crash investigation", "investigación de accidentes aéreos", "enquête sur un accident d'avion", "Flugzeugabsturz Untersuchung", "расследование авиакатастроф"),
        ("engineering failures", "fallos de ingeniería", "échecs d'ingénierie", "Ingenieurversagen", "инженерные ошибки"),
        ("dam failure disaster", "desastre por rotura de presa", "catastrophe de rupture de barrage", "Dammbruch Katastrophe", "катастрофа прорыва плотины"),
        ("building collapse", "colapso de edificios", "effondrement de bâtiments", "Gebäudeeinsturz", "обрушение зданий"),
        ("industrial disasters", "desastres industriales", "catastrophes industrielles", "Industriekatastrophen", "промышленные катастрофы"),
        ("nuclear accident", "accidente nuclear", "accident nucléaire", "Atomunfall", "ядерная авария"),
        ("train and rail disasters", "desastres ferroviarios", "catastrophes ferroviaires", "Zugunglücke", "железнодорожные катастрофы"),
        ("shipwreck disasters", "naufragios", "naufrages", "Schiffsunglücke", "кораблекрушения"),
        ("mine and oil rig disasters", "desastres mineros y de plataformas petroleras", "catastrophes minières et de plateformes pétrolières", "Bergwerks- und Bohrinselunglücke", "аварии на шахтах и нефтяных платформах"),
        ("chemical explosion", "explosión química", "explosion chimique", "Chemieexplosion", "химический взрыв"),
        ("tsunami disaster history", "historia de desastres por tsunami", "histoire des catastrophes de tsunami", "Tsunami Katastrophen Geschichte", "история катастроф цунами"),
        ("ignored warnings before disaster", "advertencias ignoradas antes del desastre", "avertissements ignorés avant la catastrophe", "ignorierte Warnungen vor der Katastrophe", "проигнорированные предупреждения перед катастрофой"),
        ("bridge collapse", "colapso de puentes", "effondrement de ponts", "Brückeneinsturz", "обрушение мостов"),
        ("space shuttle and rocket disasters", "desastres de transbordadores y cohetes", "catastrophes de navettes et de fusées", "Raumfähren- und Raketenunglücke", "катастрофы шаттлов и ракет"),
    ],
    "geopolitics": [
        ("geopolitics explained", "geopolítica explicada", "la géopolitique expliquée", "Geopolitik erklärt", "геополитика объяснение"),
        ("why countries are hard to defend", "por qué es difícil defender a algunos países", "pourquoi certains pays sont difficiles à défendre", "warum manche Länder schwer zu verteidigen sind", "почему некоторые страны трудно защищать"),
        ("world map country rankings", "ranking de países en el mapa", "classement des pays sur la carte", "Länderranking Weltkarte", "рейтинг стран на карте мира"),
        ("how countries became powerful", "cómo los países se hicieron poderosos", "comment les pays sont devenus puissants", "wie Länder mächtig wurden", "как страны стали могущественными"),
        ("us china rivalry", "rivalidad entre eeuu y china", "rivalité entre les usa et la chine", "Rivalität USA China", "соперничество США и Китая"),
        ("russia geography and history", "geografía e historia de rusia", "géographie et histoire de la russie", "Geografie und Geschichte Russlands", "география и история России"),
        ("middle east conflicts explained", "conflictos de oriente medio explicados", "conflits du moyen-orient expliqués", "Nahostkonflikte erklärt", "конфликты на ближнем востоке объяснение"),
        ("country economy collapse", "colapso de la economía de un país", "effondrement de l'économie d'un pays", "Wirtschaftskollaps eines Landes", "крах экономики страны"),
        ("neutral countries in wars", "países neutrales en las guerras", "pays neutres dans les guerres", "neutrale Länder in Kriegen", "нейтральные страны в войнах"),
        ("borders and territorial disputes", "fronteras y disputas territoriales", "frontières et litiges territoriaux", "Grenzen und Gebietsstreitigkeiten", "границы и территориальные споры"),
        ("empires that disappeared from the map", "imperios que desaparecieron del mapa", "empires disparus de la carte", "Reiche die von der Karte verschwanden", "империи исчезнувшие с карты"),
        ("future superpowers", "futuras superpotencias", "futures superpuissances", "zukünftige Supermächte", "будущие сверхдержавы"),
    ],
    "mythology": [
        ("greek mythology", "mitología griega", "mythologie grecque", "griechische Mythologie", "греческая мифология"),
        ("norse mythology", "mitología nórdica", "mythologie nordique", "nordische Mythologie", "скандинавская мифология"),
        ("egyptian mythology", "mitología egipcia", "mythologie égyptienne", "ägyptische Mythologie", "египетская мифология"),
        ("celtic mythology and folklore", "mitología y folclore celta", "mythologie et folklore celtes", "keltische Mythologie und Folklore", "кельтская мифология и фольклор"),
        ("japanese mythology", "mitología japonesa", "mythologie japonaise", "japanische Mythologie", "японская мифология"),
        ("slavic mythology", "mitología eslava", "mythologie slave", "slawische Mythologie", "славянская мифология"),
        ("mesopotamian and ancient gods", "mitología mesopotámica y dioses antiguos", "mythologie mésopotamienne et dieux anciens", "mesopotamische Mythologie und alte Götter", "месопотамская мифология и древние боги"),
        ("mythical creatures", "criaturas míticas", "créatures mythiques", "mythische Kreaturen", "мифические существа"),
        ("ancient religions explained", "religiones antiguas explicadas", "religions antiques expliquées", "antike Religionen erklärt", "древние религии объяснение"),
        ("folklore legends and urban legends", "leyendas y folclore", "légendes et folklore", "Legenden und Folklore", "легенды и фольклор"),
        ("demons and forgotten gods", "demonios y dioses olvidados", "démons et dieux oubliés", "Dämonen und vergessene Götter", "демоны и забытые боги"),
        ("mythology bedtime stories long", "mitología para dormir", "mythologie pour s'endormir", "Mythologie zum Einschlafen", "мифология для сна"),
    ],
}

NEW_MARKETS = list(NEW_MARKET_FORMULAS)
_LANG_INDEX = {"es": 1, "fr": 2, "de": 3, "ru": 4}

# Sujets supplémentaires en anglais, par marché
EXTRA_TOPICS = {}
# Sujets supplémentaires traduits, par marché puis par langue
EXTRA_TRANSLATED = {}


def register(markets: dict) -> None:
    """Ajoute les mots-clés au dictionnaire MARKETS (appelé à la fin de markets.py)."""
    for market, rows in KEYWORDS.items():
        if market in NEW_MARKETS:
            # Nouveaux marchés : les 4 premiers mots-clés sont les sujets de base
            markets[market] = {"topics": [r[0] for r in rows[:4]], "title_formulas": NEW_MARKET_FORMULAS[market]}
            TRANSLATED_TOPICS[market] = {
                lang: [r[i] for r in rows[:4]] for lang, i in _LANG_INDEX.items()
            }
            extra_rows = rows[4:]
        else:
            extra_rows = rows
        EXTRA_TOPICS[market] = [r[0] for r in extra_rows]
        EXTRA_TRANSLATED[market] = {
            lang: [r[i] for r in extra_rows] for lang, i in _LANG_INDEX.items()
        }