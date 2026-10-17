"""
Réglages du moteur de mots-clés (étape 4) et listes de mots à ignorer.

Tout se règle ici, rien d'autre à toucher dans le code.
"""

# ---------- Rythme d'apprentissage ----------

# Nombre maximum de NOUVEAUX mots-clés mis en test à chaque passe
# (une passe = un lancement de la découverte pour un marché et une langue).
NEW_TESTS_PER_PASS = 3

# Part maximale des recherches consacrée aux mots-clés en test
# (par rapport au total des recherches du marché). 0.15 = environ 15 %.
TEST_QUOTA_SHARE = 0.15

# Part minimale de recherches "de départ" (seeds) dans chaque passe.
# 0.5 = au moins la moitié : les mots-clés appris ne dépassent jamais le nombre de seeds.
MIN_SEED_SHARE = 0.5

# Nombre maximum de mots-clés "actifs" (qui ont fait leurs preuves) relancés à chaque passe.
MAX_ACTIVE_PER_MARKET = 8

# ---------- Choix des expressions ----------

PHRASE_SIZES = (2, 3)            # expressions de 2 et 3 mots
MIN_CHANNELS_PER_PHRASE = 3      # une expression doit venir d'au moins 3 chaînes différentes
MIN_CHANNELS_PER_MIX = 2         # mélange (mot-clé de départ + mot fréquent) : au moins 2 chaînes différentes,
                                 # quand les titres contiennent TOUS les mots du mot-clé de départ
MIX_ALLOW_PARTIAL_SEED = False   # True : on accepte aussi des titres qui contiennent AU MOINS UN mot du mot-clé
                                 # de départ, mais alors il faut MIN_CHANNELS_PER_PARTIAL_MIX chaînes
MIN_CHANNELS_PER_PARTIAL_MIX = 3
NEGATIVE_SHARE_MAX = 0.5         # exclue si au moins 50 % des chaînes qui l'utilisent ont été refusées
MIN_CORPUS_CHANNELS = 8          # en dessous de ce nombre de chaînes, pas encore de proposition
MIN_CORPUS_TITLES = 30           # idem pour le nombre de titres

# True : une expression doit contenir au moins UN mot du vocabulaire du marché
# (les mots de ses mots-clés de départ), pour rester dans le sujet du marché.
# False : toute expression fréquente est acceptée (plus de variété, mais plus de hors-sujet).
REQUIRE_MARKET_WORD = True

# ---------- Piste "radar" (mots-clés venus du radar) ----------

RADAR_TEST_SLOTS = 2             # places de test réservées aux mots-clés du radar, par marché et par passe
RADAR_PROMOTE_AFTER_RUNS = 3     # un mot-clé radar reste 3 passes en test ; après, s'il a ramené au moins
                                 # PROMOTE_MIN_VALIDATED nouvelle chaîne validée, il rejoint les actifs d'habitude

# ---------- Jugement ----------

PROMOTE_MIN_VALIDATED = 1        # mot-clé "actif" dès qu'il ramène au moins 1 nouvelle chaîne validée
RETIRE_AFTER_RUNS = 3            # retiré après 3 passes sans aucune nouvelle chaîne validée

# ---------- Mots ignorés ----------
# Mots vides : une expression ne commence ni ne finit jamais par l'un d'eux.
# Mots génériques (bruit de format YouTube) : idem.
# Les mots d'une seule lettre sont toujours ignorés.

STOPWORDS = {
    "en": set("""
        a an the and or but nor of in on at to for from by with without about as is are was were be been being am
        it its it's this that these those they them their theirs you your yours we our ours us i my me mine he she
        his her him hers who whom whose what when where why how which not no yes do does did doing done don't doesn't
        didn't can could can't couldn't will would won't wouldn't should shouldn't may might must just very more most
        less than then so if into onto over under out up down off after before again all any some such only own same
        too also there here have has had having get gets got getting isn't aren't wasn't weren't hasn't haven't
        i'm i've i'll you're you've you'll we're we've they're that's what's here's let's vs versus via per each
        every both either neither other another
    """.split()),
    "es": set("""
        el la los las un una unos unas y o pero ni de del al en con sin sobre por para como es son era eran ser fue
        fueron ha han he has hay lo le les se su sus mi mis tu tus nuestro nuestra que qué quien quién cual cuál
        cuando cuándo donde dónde cómo no sí si más menos muy ya también solo sólo todo todos toda todas esto esta
        este estos estas eso esa ese esos esas aquí allí entre hasta desde tras ante bajo contra durante según tan
        tanto cada otro otra otros otras mismo misma vs
    """.split()),
    "fr": set("""
        le la les un une des du de au aux et ou mais ni en dans sur sous avec sans pour par comme est sont était
        étaient être été a ont avait avoir ce cet cette ces se sa son ses mon ma mes ton ta tes notre nos votre vos
        leur leurs qui que quoi dont où quand comment pourquoi quel quelle quels quelles ne pas plus moins très déjà
        aussi seulement tout tous toute toutes il elle ils elles on nous vous je tu me te lui eux ça cela ceci si
        entre jusqu vers chez après avant depuis pendant contre selon même autre autres chaque vs qu
    """.split()),
    "de": set("""
        der die das den dem des ein eine einen einem einer eines und oder aber nicht kein keine von vom zu zum zur
        im in an auf aus bei mit nach über unter für gegen ohne um durch ist sind war waren sein gewesen hat haben
        hatte wird werden wurde wurden es sie er wir ihr ihm ihn sich mein dein unser euer wer was wie wo wann warum
        welche welcher welches nur auch noch schon sehr mehr weniger als wenn dass da dort hier alle alles jede jeder
        jedes andere anderen so ja nein vs
    """.split()),
    "ru": set("""
        и в во не что он на я с со как а то все она так его но да ты к у же вы за бы по только ее мне было вот от
        меня еще нет о из ему теперь когда даже ну вдруг ли если уже или ни быть был него до вас нибудь опять уж вам
        ведь там потом себя ничего ей может они тут где есть надо ней для мы тебя их чем была сам чтоб без будто
        чего раз тоже себе под будет тогда кто этот того потому этого какой совсем ним здесь этом один почти мой
        тем чтобы нее сейчас были куда зачем всех никогда можно при наконец два об другой хоть после над больше тот
        через эти нас про них какая много разве три эту моя впрочем хорошо свою этой перед иногда лучше чуть том
        нельзя такой им более всегда конечно всю между это почему
    """.split()),
}

GENERIC_WORDS = {
    "en": set("""
        video videos full new top best official episode episodes part shorts short live channel watch subscribe hd
        4k way ways thing things people guy guys man men one ones never ever really actually everything something
        nothing anything know knew need needs make makes made making take takes took come comes came look looks
        looked going gone want wants many much even still every today now simply literally
        later year years old finally shocked everyone revealed solved
    """.split()),
    "es": set("""
        video vídeo vídeos videos completo nuevo nueva mejor mejores oficial capítulo episodio parte shorts canal
        ver suscríbete forma cosa cosas gente hombre hombres uno nunca siempre realmente algo nada saber necesitas
        hacer hace hizo hecho venir mira hoy ahora simplemente literalmente
        después año años finalmente revelado resuelto
    """.split()),
    "fr": set("""
        vidéo vidéos complet nouveau nouvelle meilleur meilleurs meilleure officiel épisode épisodes partie shorts
        chaîne regarder abonne façon chose choses gens homme hommes jamais toujours vraiment rien savoir besoin
        faire fait venir regarde aujourd hui maintenant simplement littéralement
        ans an enfin révélé résolu
    """.split()),
    "de": set("""
        video videos komplett neu neue beste besten offiziell folge folgen teil shorts kanal ansehen abonnieren weg
        dinge sache sachen leute mann männer nie immer wirklich etwas nichts wissen brauchen machen macht heute jetzt
        einfach buchstäblich später jahre jahr endlich enthüllt gelöst
    """.split()),
    "ru": set("""
        видео полное новое новый лучший лучшие официальный серия эпизод часть shorts канал смотреть подписывайся
        способ вещь вещи люди человек мужчина никогда всегда действительно что-то знать нужно делать сегодня сейчас
        просто буквально спустя лет год наконец раскрыто решено
    """.split()),
}
