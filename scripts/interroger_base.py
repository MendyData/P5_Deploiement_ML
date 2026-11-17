"""Interroge la base : volumes, dernières prédictions et taux d'alerte.

Le script se connecte avec le rôle de l'API, qui a le droit de lire les tables.

    uv run python scripts/interroger_base.py
"""

import logging

from sqlalchemy import text

from src.bdd.session import creer_moteur
from src.parametres import obtenir_parametres

journal = logging.getLogger(__name__)

VOLUMES = """
    SELECT
        (SELECT count(*) FROM collaborateurs) AS collaborateurs,
        (SELECT count(*) FROM utilisateurs) AS utilisateurs,
        (SELECT count(*) FROM demandes) AS demandes,
        (SELECT count(*) FROM reponses) AS reponses
"""

DERNIERES_PREDICTIONS = """
    SELECT d.id, d.recue_le, u.nom, d.poste, r.probabilite_depart, r.alerte
    FROM demandes AS d
    JOIN utilisateurs AS u ON u.id = d.utilisateur_id
    LEFT JOIN reponses AS r ON r.demande_id = d.id
    ORDER BY d.recue_le DESC
    LIMIT 5
"""

TAUX_ALERTE = """
    SELECT version_modele, count(*) AS predictions,
           round(avg(alerte::int)::numeric, 3) AS taux_alerte,
           round(avg(probabilite_depart)::numeric, 3) AS probabilite_moyenne
    FROM reponses
    GROUP BY version_modele
"""


def main() -> None:
    """Exécute chaque requête et affiche ses lignes."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    moteur = creer_moteur(obtenir_parametres().url_api)
    requetes = {
        "Volumes": VOLUMES,
        "Cinq dernières demandes": DERNIERES_PREDICTIONS,
        "Taux d'alerte par version du modèle": TAUX_ALERTE,
    }
    with moteur.connect() as connexion:
        for titre, requete in requetes.items():
            journal.info("--- %s", titre)
            for ligne in connexion.execute(text(requete)).mappings():
                journal.info("%s", dict(ligne))


if __name__ == "__main__":
    main()
