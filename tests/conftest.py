"""Fixtures partagées : fichiers de référence du P4 et base de données de test.

Chaque fixture de données est lue une fois par session et partagée entre les
tests : aucun test ne doit la modifier.
"""

import json
from collections.abc import Iterator
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src import config
from src.bdd.initialisation import creer_base
from src.bdd.modeles import Base
from src.bdd.session import creer_moteur
from src.modele.artefact import MetadonneesArtefact
from src.modele.predicteur import PredicteurAttrition
from src.parametres import Parametres, obtenir_parametres

DOSSIER_FIXTURES = Path(__file__).parent / "fixtures"

# Base recréée vide à chaque exécution : jamais la base de développement.
BASE_DE_TEST = "p5_test"


@pytest.fixture(scope="session")
def reference_test_p4() -> pd.DataFrame:
    """Collaborateurs du test du P4 : valeurs brutes, cible et score du P4."""
    return pd.read_csv(DOSSIER_FIXTURES / "reference_test_p4.csv")


@pytest.fixture(scope="session")
def departs_test_p4(reference_test_p4: pd.DataFrame) -> pd.Series:
    """Départs observés des collaborateurs du test du P4 : 1 pour un départ, 0 sinon."""
    return (reference_test_p4[config.CIBLE] == config.MODALITE_DEPART).astype(int)


@pytest.fixture(scope="session")
def cas_limites() -> pd.DataFrame:
    """Collaborateurs couvrant les bornes des features métier et chaque modalité."""
    return pd.read_csv(DOSSIER_FIXTURES / "cas_limites.csv")


@pytest.fixture(scope="session")
def reference_x_test_p4() -> pd.DataFrame:
    """Les 46 colonnes encodées du P4 des collaborateurs du test, par identifiant."""
    return pd.read_csv(
        DOSSIER_FIXTURES / "reference_x_test_p4.csv", index_col=config.IDENTIFIANT
    )


@pytest.fixture
def collaborateur(reference_test_p4: pd.DataFrame) -> pd.DataFrame:
    """Un collaborateur du test du P4, réduit aux 26 variables d'entrée."""
    return reference_test_p4.loc[[0], config.COLONNES_ENTREE]


@pytest.fixture(scope="session")
def metadonnees_p4() -> dict:
    """Métadonnées du modèle final du P4 : seuil, features et hyperparamètres."""
    chemin = DOSSIER_FIXTURES / "metadonnees_p4.json"
    return json.loads(chemin.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def predicteur() -> PredicteurAttrition:
    """Prédicteur chargé une fois par session à partir de l'artefact suivi par Git."""
    return PredicteurAttrition()


@pytest.fixture(scope="session")
def metadonnees_artefact(predicteur: PredicteurAttrition) -> MetadonneesArtefact:
    """Métadonnées de l'artefact suivi par Git, vérifiées par le prédicteur."""
    return predicteur.metadonnees


@pytest.fixture(scope="session")
def parametres_bdd() -> Iterator[Parametres]:
    """Paramètres d'une base de test, recréée vide à chaque exécution des tests.

    Le serveur PostgreSQL est celui de l'environnement ; la base de développement
    n'est jamais touchée.
    """
    with pytest.MonkeyPatch.context() as environnement:
        environnement.setenv("APP_ENV", "test")
        environnement.setenv("POSTGRES_DB", BASE_DE_TEST)
        obtenir_parametres.cache_clear()
        parametres = obtenir_parametres()
        # CREATE DATABASE refuse de s'exécuter dans une transaction : chaque
        # ordre est donc validé tout de suite (AUTOCOMMIT).
        serveur = create_engine(
            parametres.url_proprietaire.set(database="postgres"),
            isolation_level="AUTOCOMMIT",
        )
        with serveur.connect() as connexion:
            connexion.execute(
                text(f"DROP DATABASE IF EXISTS {BASE_DE_TEST} WITH (FORCE)")
            )
            connexion.execute(text(f"CREATE DATABASE {BASE_DE_TEST}"))
        serveur.dispose()
        creer_base(parametres)
        yield parametres
    obtenir_parametres.cache_clear()


@pytest.fixture
def session_bdd(parametres_bdd: Parametres) -> Iterator[Session]:
    """Session du rôle propriétaire ; les tables sont vidées après chaque test."""
    moteur = creer_moteur(parametres_bdd.url_proprietaire)
    with Session(moteur) as session:
        yield session
    with moteur.begin() as connexion:
        tables = ", ".join(Base.metadata.tables)
        connexion.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    moteur.dispose()
