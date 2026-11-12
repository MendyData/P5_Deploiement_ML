"""Entraîne le pipeline complet, puis écrit l'artefact et ses métadonnées.

Le jeu consolidé, non suivi par Git, est écrit dans data/interim/ par
scripts/generer_reference_p4.py ; le découpage du P4 est suivi dans models/.

    uv run python scripts/entrainer_pipeline.py
"""

import json
import logging

import pandas as pd

from src import config
from src.modele.entrainement import EntraineurPipeline


def main() -> None:
    """Entraîne le pipeline sur le découpage du P4, puis le sauvegarde."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    consolide = pd.read_csv(config.FICHIER_CONSOLIDE)
    decoupage = json.loads(config.FICHIER_DECOUPAGE.read_text(encoding="utf-8"))
    entraineur = EntraineurPipeline(consolide, decoupage)
    entraineur.sauvegarder(entraineur.entrainer())


if __name__ == "__main__":
    main()
