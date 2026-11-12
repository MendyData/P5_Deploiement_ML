"""Fixtures partagées : fichiers de référence produits à partir du P4.

Chaque fixture est lue une fois par session et partagée entre les tests : aucun
test ne doit la modifier.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from src import config
from src.modele.artefact import MetadonneesArtefact
from src.modele.predicteur import PredicteurAttrition

DOSSIER_FIXTURES = Path(__file__).parent / "fixtures"


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
