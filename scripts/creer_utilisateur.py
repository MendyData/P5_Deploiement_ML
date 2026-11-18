"""Enregistre un client de l'API et affiche sa clé, une seule fois.

Seule l'empreinte de la clé est enregistrée dans la table utilisateurs : la clé
affichée doit être transmise au client tout de suite, elle ne peut pas être
retrouvée.

    uv run python scripts/creer_utilisateur.py equipe-rh
"""

import argparse
import logging
import sys

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.securite import creer_utilisateur
from src.bdd.session import creer_moteur
from src.parametres import obtenir_parametres

journal = logging.getLogger(__name__)


def main() -> None:
    """Crée le client dont le nom est passé en argument."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    analyseur = argparse.ArgumentParser(description="Crée un client de l'API.")
    analyseur.add_argument("nom", help="Nom du client, unique.")
    nom = analyseur.parse_args().nom
    moteur = creer_moteur(obtenir_parametres().url_proprietaire)
    try:
        with Session(moteur) as session:
            cle = creer_utilisateur(session, nom)
    except IntegrityError:
        sys.exit(f"Le client {nom} existe déjà : choisir un autre nom.")
    journal.info("Client %s créé. Clé d'API, à lui transmettre : %s", nom, cle)


if __name__ == "__main__":
    main()
