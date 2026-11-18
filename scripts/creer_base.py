"""Crée les tables de la base, leurs relations et le rôle de l'API.

Le script se connecte avec le rôle propriétaire, lu dans le fichier .env. Il peut
être relancé sans risque : les tables et les données existantes sont conservées.

    uv run python scripts/creer_base.py
"""

import logging

from src.bdd.initialisation import creer_base
from src.parametres import obtenir_parametres


def main() -> None:
    """Initialise la base de l'environnement courant."""
    parametres = obtenir_parametres()
    logging.basicConfig(level=parametres.log_level, format="%(message)s")
    creer_base(parametres)


if __name__ == "__main__":
    main()
