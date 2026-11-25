"""Démarrage de l'API : sans base joignable, il échoue avec un message explicite."""

import pytest
from fastapi.testclient import TestClient

from src.api.application import app
from src.bdd.attente import BaseInjoignable
from src.parametres import obtenir_parametres


@pytest.fixture
def base_arretee(monkeypatch):
    """Paramètres d'une base injoignable, relus par l'application au démarrage."""
    # Port 1 : aucune base n'y répond, comme une base arrêtée. Deux essais sans
    # pause parcourent toute la boucle sans ralentir les tests.
    monkeypatch.setenv("POSTGRES_PORT", "1")
    monkeypatch.setenv("POSTGRES_TENTATIVES", "2")
    monkeypatch.setenv("POSTGRES_PAUSE", "0")
    obtenir_parametres.cache_clear()
    yield
    # Les tests suivants relisent les paramètres d'origine.
    obtenir_parametres.cache_clear()


@pytest.mark.usefixtures("base_arretee")
def test_api_ne_demarre_pas_sans_base():
    # Le bloc with déclenche le démarrage : l'erreur de l'attente en sort.
    with pytest.raises(BaseInjoignable, match="après 2 essais"), TestClient(app):
        pass
