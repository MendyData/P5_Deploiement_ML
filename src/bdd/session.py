"""Connexion à la base : le moteur, créé au démarrage, et une session par requête."""

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.orm import Session

# Attente maximale, en secondes, pour ouvrir une connexion à la base.
DELAI_CONNEXION: int = 5


def creer_moteur(url: URL) -> Engine:
    """Crée le moteur qui ouvre les connexions à la base.

    Args:
        url: Adresse de la base, avec le rôle et son mot de passe.

    Returns:
        Le moteur. pool_pre_ping teste une connexion avant de la réutiliser : une
        connexion coupée est remplacée au lieu de faire échouer la requête.
        connect_timeout borne l'attente d'une base injoignable : sans lui,
        psycopg patiente jusqu'à 130 secondes avant que l'API ne réponde 503.
    """
    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": DELAI_CONNEXION},
    )


def obtenir_session(requete: Request) -> Iterator[Session]:
    """Ouvre une session pour la requête en cours, puis la ferme.

    Args:
        requete: Requête en cours, qui donne accès au moteur de l'application.

    Yields:
        La session, partagée par l'authentification et par la route.
    """
    with Session(requete.app.state.moteur) as session:
        yield session
