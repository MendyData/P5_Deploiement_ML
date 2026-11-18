"""Insère le jeu de données complet du projet 4 dans la table collaborateurs.

Le jeu consolidé n'est pas suivi par Git : il est écrit dans data/interim/ par
scripts/generer_reference_p4.py. Le script contrôle le nombre de lignes insérées
et s'arrête sur une erreur s'il diffère de celui du fichier.

    uv run python scripts/inserer_dataset.py
"""

import logging
import sys

import pandas as pd

from src import config
from src.bdd.initialisation import inserer_dataset
from src.bdd.session import creer_moteur
from src.parametres import obtenir_parametres

journal = logging.getLogger(__name__)


def main() -> None:
    """Lit le jeu consolidé, l'insère, puis contrôle le nombre de lignes."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    consolide = pd.read_csv(config.FICHIER_CONSOLIDE)
    moteur = creer_moteur(obtenir_parametres().url_proprietaire)
    total = inserer_dataset(moteur, consolide)
    journal.info("%d lignes dans la table, %d dans le fichier.", total, len(consolide))
    if total != len(consolide):
        sys.exit("Contrôle en échec : les deux nombres devraient être égaux.")


if __name__ == "__main__":
    main()
