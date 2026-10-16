"""
Rapport et commandes du moteur de mots-clés.

Usage :
    python -m discovery.keywords_report                              (rapport de tous les marchés)
    python -m discovery.keywords_report report --market history      (un marché)
    python -m discovery.keywords_report report --market history --lang fr
    python -m discovery.keywords_report suggest --market history --lang en
        (montre les expressions que le moteur proposerait, sans rien enregistrer ni consommer de quota)
    python -m discovery.keywords_report ban "famous people" --market history --lang en
        (interdit une expression : elle ne sera plus jamais proposée ni testée)
    python -m discovery.keywords_report unban "famous people" --market history --lang en
"""

import argparse

from config.queries import LANGUAGES, build_queries
from discovery.database import (
    ban_keyword, list_keywords, load_keyword_corpus, unban_keyword,
)
from discovery.keyword_engine import (
    market_vocabulary, normalize_phrase, phrase_words, pick_non_overlapping, propose_candidates, slot_budget,
)

STATUS_LABEL = {"active": "ACTIF", "test": "EN TEST", "retired": "RETIRÉ", "banned": "BANNI"}
STATUS_ORDER = ["active", "test", "retired", "banned"]


def _print_report(market: str | None, language: str | None):
    rows = list_keywords(market, language)
    if not rows:
        print("Aucun mot-clé appris pour l'instant.")
        print("Le moteur en propose dès qu'il y a assez de titres en base, à la prochaine découverte.")
        return

    groups = {}
    for r in rows:
        groups.setdefault((r["market"], r["language"]), []).append(r)

    totals = {s: 0 for s in STATUS_ORDER}
    for (mk, lg), items in sorted(groups.items()):
        print(f"\n=== {mk} [{lg}] ===")
        items.sort(key=lambda r: (STATUS_ORDER.index(r["status"]) if r["status"] in STATUS_ORDER else 9,
                                  -(r["validated_found"] or 0)))
        for r in items:
            totals[r["status"]] = totals.get(r["status"], 0) + 1
            label = STATUS_LABEL.get(r["status"], r["status"])
            if r["status"] == "banned":
                print(f"  [{label:<8}] {r['query']}")
            else:
                print(f"  [{label:<8}] {r['query']:<40} passes={r['times_run']}  "
                      f"chaînes trouvées={r['channels_found']}  nouvelles validées={r['validated_found']}")

    print("\nTotal : " + ", ".join(f"{STATUS_LABEL[s].lower()} {totals.get(s, 0)}" for s in STATUS_ORDER))


def _print_suggestions(market: str, language: str):
    seeds = build_queries(market, language)
    rows = list_keywords(market, language)
    positives, negatives = load_keyword_corpus(market, language)
    known = [phrase_words(s, language) for s in seeds] + [phrase_words(r["query"], language) for r in rows]
    banned = [phrase_words(r["query"], language) for r in rows if r["status"] == "banned"]
    vocab = market_vocabulary(market, language, seeds)
    result = propose_candidates(positives, negatives, language, known, banned, vocab)
    info = result["info"]
    budget = slot_budget(len(seeds))

    print(f"Marché {market} [{language}] : {len(seeds)} seeds, "
          f"{budget['test_slots']} place(s) de test et {budget['active_slots']} place(s) d'actif par passe.")
    print(f"Corpus : {info['titles']} titres, {info['channels']} chaînes.")
    if not info["enough_data"]:
        print("Pas encore assez de titres pour proposer des expressions "
              "(il faut plus de chaînes enregistrées pour ce marché et cette langue).")
        return
    print(f"Écartées : {info['too_few_channels']} (moins de 3 chaînes), {info['excluded_refused']} (viennent de chaînes refusées), "
          f"{info['excluded_known']} (déjà couvertes par un mot-clé), {info['excluded_banned']} (bannies), "
          f"{info['excluded_off_market']} (hors du sujet du marché).")
    if not result["candidates"]:
        print("Aucune expression candidate pour l'instant.")
        return
    print("\nMeilleures candidates (sans doublons entre elles) :")
    for c in pick_non_overlapping(result["candidates"], 15, known, language):
        print(f"  {c['phrase']:<40} {c['channels']} chaînes  ex : {c['example'][:70]}")


def main():
    parser = argparse.ArgumentParser(description="Rapport et commandes du moteur de mots-clés")
    parser.add_argument("command", nargs="?", default="report",
                        choices=["report", "suggest", "ban", "unban"], help="commande (défaut : report)")
    parser.add_argument("phrase", nargs="?", help="expression à bannir / débannir")
    parser.add_argument("--market", default=None)
    parser.add_argument("--lang", default=None, choices=LANGUAGES)
    args = parser.parse_args()

    if args.command == "report":
        _print_report(args.market, args.lang)
        return

    if not args.market or not args.lang:
        raise SystemExit("Précise le marché et la langue : --market history --lang en")

    if args.command == "suggest":
        _print_suggestions(args.market, args.lang)
        return

    if not args.phrase:
        raise SystemExit('Précise l\'expression entre guillemets, par exemple : ban "famous people" --market history --lang en')
    phrase = normalize_phrase(args.phrase, args.lang)
    if not phrase:
        raise SystemExit("Expression vide.")

    if args.command == "ban":
        seeds = {normalize_phrase(s, args.lang) for s in build_queries(args.market, args.lang)}
        if phrase in seeds:
            raise SystemExit(f"'{phrase}' est un mot-clé de départ (seed) : il se retire dans les fichiers de config, pas ici.")
        ban_keyword(args.market, args.lang, phrase)
        print(f"Banni : '{phrase}' ({args.market} [{args.lang}]). Il ne sera plus proposé ni testé.")
    else:
        if unban_keyword(args.market, args.lang, phrase):
            print(f"Interdiction levée : '{phrase}'. Il pourra être reproposé.")
        else:
            print(f"'{phrase}' n'était pas banni pour {args.market} [{args.lang}].")


if __name__ == "__main__":
    main()