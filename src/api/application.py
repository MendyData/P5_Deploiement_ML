"""Application FastAPI : modèle chargé au démarrage, routes health et predict."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib import metadata
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError

from src import config
from src.api.erreurs import refuser_donnees_invalides
from src.api.securite import verifier_cle
from src.modele.predicteur import PredicteurAttrition
from src.parametres import Parametres, obtenir_parametres
from src.schemas.collaborateur import Collaborateur
from src.schemas.prediction import (
    ErreurAuthentification,
    ErreursValidation,
    Prediction,
    Sante,
)
from src.services.prediction import ServicePrediction


@asynccontextmanager
async def cycle_de_vie(application: FastAPI) -> AsyncIterator[None]:
    """Charge le modèle une seule fois, avant la première requête.

    Si l'artefact est invalide, l'erreur arrête le démarrage : l'API ne répond
    jamais avec un modèle non vérifié.

    Args:
        application: Application qui garde le service de prédiction.

    Yields:
        Rien : la main est rendue à l'application le temps de son exécution.
    """
    logging.basicConfig(
        level=obtenir_parametres().log_level,
        format="%(asctime)s %(levelname)s %(name)s : %(message)s",
    )
    application.state.service = ServicePrediction(PredicteurAttrition())
    yield


app = FastAPI(
    title="API de prédiction des départs",
    description=(
        "Estime le risque de départ d'un collaborateur à partir de 26 "
        "informations RH. La route /predict demande une clé d'API, à saisir "
        "avec le bouton Authorize."
    ),
    version=metadata.version(config.NOM_PROJET),
    lifespan=cycle_de_vie,
)
app.add_exception_handler(RequestValidationError, refuser_donnees_invalides)


def obtenir_service(requete: Request) -> ServicePrediction:
    """Renvoie le service de prédiction créé au démarrage.

    Args:
        requete: Requête en cours, qui donne accès à l'application.

    Returns:
        Le service, avec son modèle déjà chargé.
    """
    return requete.app.state.service


@app.get("/health", tags=["Supervision"], summary="Vérifier que l'API répond")
def sante(
    service: Annotated[ServicePrediction, Depends(obtenir_service)],
    parametres: Annotated[Parametres, Depends(obtenir_parametres)],
) -> Sante:
    """Indique que le service répond, dans quel environnement et avec quel modèle."""
    return Sante(
        statut="ok",
        environnement=parametres.app_env,
        version_modele=service.version_modele,
    )


@app.post(
    "/predict",
    tags=["Prédiction"],
    summary="Estimer le risque de départ d'un collaborateur",
    dependencies=[Depends(verifier_cle)],
    responses={
        401: {"model": ErreurAuthentification, "description": "Clé d'API refusée"},
        422: {"model": ErreursValidation, "description": "Données refusées"},
    },
)
def predire(
    collaborateur: Collaborateur,
    service: Annotated[ServicePrediction, Depends(obtenir_service)],
) -> Prediction:
    """Renvoie le score de risque, l'alerte et les variables qui l'expliquent."""
    return service.predire(collaborateur)
