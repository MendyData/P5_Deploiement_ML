"""Lecture du jeu de référence : un collaborateur retrouvé par son identifiant."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from src import config
from src.bdd.modeles import Collaborateur


def lire_collaborateur(
    session: Session, identifiant: int
) -> dict[str, int | str] | None:
    """Lit les 26 informations d'un collaborateur de la table collaborateurs.

    Seules les entrées du modèle sont lues : ni l'identifiant ni le départ observé
    ne rejoignent le calcul, comme pour une demande envoyée en JSON.

    Args:
        session: Session de la requête en cours.
        identifiant: id_employee du collaborateur.

    Returns:
        Les 26 informations, ou None si l'identifiant est inconnu.
    """
    table = Collaborateur.__table__
    requete = select(*(table.c[nom] for nom in config.COLONNES_ENTREE)).where(
        table.c[config.IDENTIFIANT] == identifiant
    )
    ligne = session.execute(requete).mappings().one_or_none()
    return None if ligne is None else dict(ligne)
