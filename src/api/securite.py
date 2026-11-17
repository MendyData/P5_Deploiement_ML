"""Authentification par clé d'API : seule l'empreinte de la clé est conservée."""

import hashlib
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.bdd.modeles import Utilisateur
from src.bdd.session import obtenir_session

# Le client envoie sa clé dans cet en-tête ; Swagger propose le bouton Authorize.
EN_TETE_CLE = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="Clé d'API remise au client.",
)


def empreinte_cle(cle: str) -> str:
    """Calcule l'empreinte SHA-256 d'une clé d'API.

    La clé est longue et tirée au hasard : une empreinte SHA-256 suffit à la
    protéger, et la clé elle-même n'est jamais enregistrée.

    Args:
        cle: Clé d'API en clair.

    Returns:
        L'empreinte, en hexadécimal.
    """
    return hashlib.sha256(cle.encode("utf-8")).hexdigest()


def creer_utilisateur(session: Session, nom: str) -> str:
    """Enregistre un client de l'API et lui attribue une clé.

    Args:
        session: Session ouverte avec le rôle propriétaire.
        nom: Nom du client, unique dans la table.

    Returns:
        La clé, à transmettre au client : seule son empreinte est enregistrée,
        elle ne pourra donc plus être retrouvée.
    """
    cle = secrets.token_urlsafe(32)
    session.add(Utilisateur(nom=nom, empreinte_cle=empreinte_cle(cle)))
    session.commit()
    return cle


def utilisateur_courant(
    cle: Annotated[str | None, Security(EN_TETE_CLE)],
    session: Annotated[Session, Depends(obtenir_session)],
) -> Utilisateur:
    """Retrouve le client à partir de sa clé, ou refuse la requête.

    Args:
        cle: Valeur de l'en-tête X-API-Key, ou None s'il est absent.
        session: Session de la requête en cours.

    Returns:
        Le client actif dont l'empreinte de clé correspond.

    Raises:
        HTTPException: Réponse 401 quand la clé est absente, inconnue ou
            rattachée à un client désactivé.
    """
    recherche = select(Utilisateur).where(
        Utilisateur.empreinte_cle == empreinte_cle(cle or ""), Utilisateur.actif
    )
    utilisateur = session.scalar(recherche) if cle else None
    if utilisateur is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé d'API absente ou invalide.",
        )
    return utilisateur
