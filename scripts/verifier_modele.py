"""Vérifie que le modèle se charge dans l'environnement courant.

Ce script sert de test de fumée : lancé dans le conteneur, il confirme que
l'image contient l'artefact, ses métadonnées et les mêmes versions de
bibliothèques qu'à l'entraînement. Dans le cas contraire, il s'arrête sur une
erreur et le conteneur renvoie un code différent de zéro.

    uv run python scripts/verifier_modele.py
"""

import logging

from src.modele.predicteur import PredicteurAttrition
from src.parametres import obtenir_parametres

journal = logging.getLogger(__name__)


def main() -> None:
    """Lit les paramètres, charge le prédicteur, puis journalise ce qui est prêt."""
    parametres = obtenir_parametres()
    logging.basicConfig(level=parametres.log_level, format="%(message)s")
    journal.info("Environnement : %s.", parametres.app_env)
    predicteur = PredicteurAttrition()
    journal.info(
        "Modèle %s prêt, seuil de décision : %s.",
        predicteur.metadonnees.version_modele,
        predicteur.metadonnees.seuil_decision,
    )


if __name__ == "__main__":
    main()
