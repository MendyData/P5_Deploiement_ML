"""Application FastAPI : modèle et base préparés au démarrage, routes de l'API."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib import metadata
from typing import Annotated

from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.middleware.base import RequestResponseEndpoint

from src import config
from src.api.erreurs import refuser_donnees_invalides
from src.api.securite import utilisateur_courant
from src.bdd.modeles import Utilisateur
from src.bdd.session import creer_moteur, obtenir_session
from src.modele.predicteur import PredicteurAttrition
from src.parametres import Parametres, obtenir_parametres
from src.schemas.collaborateur import Collaborateur
from src.schemas.prediction import (
    ErreurSimple,
    ErreursValidation,
    Prediction,
    Sante,
)
from src.services.prediction import ServicePrediction

journal = logging.getLogger(__name__)


@asynccontextmanager
async def cycle_de_vie(application: FastAPI) -> AsyncIterator[None]:
    """Charge le modèle et prépare l'accès à la base, une seule fois.

    Si l'artefact est invalide, l'erreur arrête le démarrage : l'API ne répond
    jamais avec un modèle non vérifié.

    Args:
        application: Application qui garde le service et le moteur de la base.

    Yields:
        Rien : la main est rendue à l'application le temps de son exécution.
    """
    parametres = obtenir_parametres()
    logging.basicConfig(
        level=parametres.log_level,
        format="%(asctime)s %(levelname)s %(name)s : %(message)s",
    )
    application.state.service = ServicePrediction(PredicteurAttrition())
    # L'API se connecte avec son propre rôle, aux droits limités.
    application.state.moteur = creer_moteur(parametres.url_api)
    yield
    application.state.moteur.dispose()


app = FastAPI(
    title="API de prédiction des départs",
    description=(
        "Estime le risque de départ d'un collaborateur à partir de 26 "
        "informations RH. La route /predict demande une clé d'API, à saisir "
        "avec le bouton Authorize. Chaque demande et chaque réponse sont "
        "enregistrées."
    ),
    version=metadata.version(config.NOM_PROJET),
    # Description technique de l'API, lue par la page Swagger : elle est servie
    # sous /schema.json, nom choisi pour le projet, au lieu de /openapi.json.
    openapi_url="/schema.json",
    # Auteure et licence, affichées sous le titre de la page Swagger.
    contact={
        "name": "Angèle GOMIS",
        "url": "https://github.com/MendyData/P5_Deploiement_ML",
    },
    license_info={"name": "MIT", "identifier": "MIT"},
    lifespan=cycle_de_vie,
)
app.add_exception_handler(RequestValidationError, refuser_donnees_invalides)

# Type de contenu des réponses JSON, encodage compris.
JSON_UTF8: str = "application/json; charset=utf-8"


@app.middleware("http")
async def preciser_l_encodage(
    requete: Request, suite: RequestResponseEndpoint
) -> Response:
    """Déclare l'encodage UTF-8 de chaque réponse JSON, erreurs comprises.

    Sans cette précision, Windows PowerShell 5.1 lit la réponse dans un ancien
    encodage et affiche « dÃ©part » au lieu de « départ ».

    Args:
        requete: Requête reçue, transmise telle quelle.
        suite: Traitement de la requête par l'application.

    Returns:
        La réponse de l'application, avec l'encodage déclaré si elle est en JSON.
    """
    reponse = await suite(requete)
    if reponse.headers.get("content-type") == "application/json":
        reponse.headers["content-type"] = JSON_UTF8
    return reponse


# Les deux gestionnaires visent des erreurs de la base : pour chaque erreur, FastAPI
# retient le plus précis, donc OperationalError avant SQLAlchemyError.
@app.exception_handler(OperationalError)
def signaler_base_indisponible(
    requete: Request, erreur: OperationalError
) -> JSONResponse:
    """Répond 503 quand la base est injoignable : arrêtée, coupée ou trop lente.

    Args:
        requete: Requête reçue, non utilisée.
        erreur: Erreur de connexion, écrite dans les journaux.

    Returns:
        La réponse 503 : sans trace possible, aucune prédiction n'est servie.
    """
    journal.error("Base de données indisponible : %s", erreur)
    detail = "Base de données indisponible : aucune prédiction n'est servie."
    return JSONResponse(status_code=503, content={"detail": detail})


@app.exception_handler(SQLAlchemyError)
def signaler_erreur_de_la_base(
    requete: Request, erreur: SQLAlchemyError
) -> JSONResponse:
    """Répond 500 quand la base répond mais refuse l'ordre reçu.

    Le schéma d'entrée applique déjà les règles de la base : un refus révèle un
    écart entre les deux, donc une erreur du serveur, et non une donnée invalide
    du client.

    Args:
        requete: Requête reçue, non utilisée.
        erreur: Erreur remontée par la base, écrite dans les journaux.

    Returns:
        La réponse 500 : sans trace possible, aucune prédiction n'est servie.
    """
    journal.error("Ordre refusé par la base de données : %s", erreur)
    detail = "Erreur de la base de données : aucune prédiction n'est servie."
    return JSONResponse(status_code=500, content={"detail": detail})


def obtenir_service(requete: Request) -> ServicePrediction:
    """Renvoie le service de prédiction créé au démarrage.

    Args:
        requete: Requête en cours, qui donne accès à l'application.

    Returns:
        Le service, avec son modèle déjà chargé.
    """
    return requete.app.state.service


@app.get(
    "/health",
    tags=["Supervision"],
    summary="Vérifier que l'API, le modèle et la base répondent",
    responses={
        500: {"model": ErreurSimple, "description": "Erreur de la base"},
        503: {"model": ErreurSimple, "description": "Base indisponible"},
    },
)
def sante(
    service: Annotated[ServicePrediction, Depends(obtenir_service)],
    parametres: Annotated[Parametres, Depends(obtenir_parametres)],
    session: Annotated[Session, Depends(obtenir_session)],
) -> Sante:
    """Indique l'environnement, la version du modèle et l'état de la base."""
    session.execute(text("SELECT 1"))
    return Sante(
        statut="ok",
        environnement=parametres.app_env,
        version_modele=service.version_modele,
        base_de_donnees="ok",
    )


@app.post(
    "/predict",
    tags=["Prédiction"],
    summary="Estimer le risque de départ d'un collaborateur",
    responses={
        401: {"model": ErreurSimple, "description": "Clé d'API refusée"},
        422: {"model": ErreursValidation, "description": "Données refusées"},
        500: {"model": ErreurSimple, "description": "Erreur de la base"},
        503: {"model": ErreurSimple, "description": "Base indisponible"},
    },
)
def predire(
    collaborateur: Collaborateur,
    utilisateur: Annotated[Utilisateur, Depends(utilisateur_courant)],
    service: Annotated[ServicePrediction, Depends(obtenir_service)],
    session: Annotated[Session, Depends(obtenir_session)],
) -> Prediction:
    """Renvoie le score, l'alerte, la probabilité de départ et leurs explications."""
    return service.predire(collaborateur, utilisateur.id, session)
