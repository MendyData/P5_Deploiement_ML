"""Tests des paramètres : valeurs par défaut, environnement, fichier .env, refus."""

import pytest
from pydantic import ValidationError

from src.parametres import Parametres, obtenir_parametres


@pytest.fixture(autouse=True)
def environnement_vide(monkeypatch):
    """Retire les variables du poste ou de la CI : chaque test part de zéro."""
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("POSTGRES_TENTATIVES", raising=False)
    monkeypatch.delenv("POSTGRES_PAUSE", raising=False)


@pytest.fixture
def fichier_env(tmp_path):
    """Fichier .env temporaire, avec une variable que les paramètres ignorent."""
    fichier = tmp_path / ".env"
    fichier.write_text(
        "APP_ENV=test\nLOG_LEVEL=DEBUG\nAUTRE_VARIABLE=valeur\n", encoding="utf-8"
    )
    return fichier


def test_valeurs_par_defaut_sans_variable_ni_fichier():
    parametres = Parametres(_env_file=None)

    assert parametres.app_env == "development"
    assert parametres.log_level == "INFO"
    assert parametres.postgres_tentatives == 10
    assert parametres.postgres_pause == 2.0


@pytest.mark.parametrize("environnement", ["development", "test", "production"])
def test_app_env_lu_dans_la_variable_d_environnement(monkeypatch, environnement):
    monkeypatch.setenv("APP_ENV", environnement)

    assert Parametres(_env_file=None).app_env == environnement


def test_valeurs_lues_dans_le_fichier_env(fichier_env):
    parametres = Parametres(_env_file=fichier_env)

    assert parametres.app_env == "test"
    assert parametres.log_level == "DEBUG"


def test_variable_d_environnement_prioritaire_sur_le_fichier_env(
    monkeypatch, fichier_env
):
    monkeypatch.setenv("APP_ENV", "production")

    assert Parametres(_env_file=fichier_env).app_env == "production"


@pytest.mark.parametrize(
    ("variable", "valeur"), [("APP_ENV", "prod"), ("LOG_LEVEL", "VERBEUX")]
)
def test_valeur_hors_liste_refusee(monkeypatch, variable, valeur):
    monkeypatch.setenv(variable, valeur)

    with pytest.raises(ValidationError):
        Parametres(_env_file=None)


@pytest.mark.parametrize(
    ("variable", "valeur"), [("POSTGRES_TENTATIVES", "0"), ("POSTGRES_PAUSE", "-1")]
)
def test_attente_de_la_base_hors_bornes_refusee(monkeypatch, variable, valeur):
    monkeypatch.setenv(variable, valeur)

    with pytest.raises(ValidationError):
        Parametres(_env_file=None)


def test_obtenir_parametres_renvoie_toujours_le_meme_objet():
    obtenir_parametres.cache_clear()

    assert obtenir_parametres() is obtenir_parametres()

    obtenir_parametres.cache_clear()
