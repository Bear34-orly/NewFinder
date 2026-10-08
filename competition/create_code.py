"""
Crée un code d'accès personnel pour la page Concurrence.

Usage :
    python -m competition.create_code "Nom de la personne" 3
(3 = nombre d'analyses autorisées par 24 h ; 50 pour toi par exemple)
"""

import sys

from competition import store


def main():
    if len(sys.argv) < 2:
        raise SystemExit('Usage : python -m competition.create_code "Nom" [analyses_par_jour]')
    name = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    code = store.create_code(name, limit)
    print(f"\nCode d'accès pour {name} ({limit} analyses / 24 h) :\n\n    {code}\n")
    print("Donne-lui ce code : il le saisit une seule fois sur la page Concurrence.")


if __name__ == "__main__":
    main()
