"""Authentification par clé d'API : seule l'empreinte de la clé est conservée."""

import hashlib
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from src.parametres import Parametres, obtenir_parametres

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


def verifier_cle(
    cle: Annotated[str | None, Security(EN_TETE_CLE)],
    parametres: Annotated[Parametres, Depends(obtenir_parametres)],
) -> None:
    """Refuse la requête si la clé d'API est absente ou invalide.

    Sans empreinte configurée, toutes les requêtes sont refusées.

    Args:
        cle: Valeur de l'en-tête X-API-Key, ou None s'il est absent.
        parametres: Paramètres de l'environnement, dont l'empreinte attendue.

    Raises:
        HTTPException: Réponse 401 quand la clé est absente ou invalide.
    """
    attendue = parametres.api_key_hash.encode("utf-8")
    recue = empreinte_cle(cle or "").encode("utf-8")
    # compare_digest prend le même temps que les empreintes soient proches ou non.
    if not cle or not attendue or not secrets.compare_digest(recue, attendue):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé d'API absente ou invalide.",
        )
