"""Tests de l'API : santé, prédiction, authentification et données refusées."""

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src import config
from src.api.application import app
from src.api.erreurs import traduire
from src.api.securite import empreinte_cle
from src.parametres import Parametres, obtenir_parametres
from src.schemas.collaborateur import EXEMPLE
from src.services.prediction import NOMBRE_FACTEURS

CLE = "cle-de-test"
EN_TETE = {"X-API-Key": CLE}


def parametres_de_test(empreinte: str) -> Parametres:
    return Parametres(_env_file=None, app_env="test", api_key_hash=empreinte)


@pytest.fixture(scope="module")
def client():
    """Client de l'API, modèle chargé une fois pour ce fichier, clé d'API connue."""
    app.dependency_overrides[obtenir_parametres] = lambda: parametres_de_test(
        empreinte_cle(CLE)
    )
    # Le bloc with déclenche le démarrage de l'application : le modèle est chargé.
    with TestClient(app) as client_api:
        yield client_api
    app.dependency_overrides.clear()


def test_health_repond_sans_cle(client):
    reponse = client.get("/health")

    assert reponse.status_code == 200
    assert reponse.json() == {
        "statut": "ok",
        "environnement": "test",
        "version_modele": "0.1.0",
    }


def test_predict_renvoie_le_score_du_predicteur(client, predicteur):
    attendu = predicteur.predire(pd.DataFrame([EXEMPLE])).iloc[0]

    reponse = client.post("/predict", json=EXEMPLE, headers=EN_TETE)

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["score_risque"] == pytest.approx(attendu[config.COL_SCORE])
    assert corps["alerte"] == bool(attendu[config.COL_ALERTE])
    assert corps["seuil_decision"] == predicteur.metadonnees.seuil_decision
    assert corps["version_modele"] == predicteur.metadonnees.version_modele


def test_predict_renvoie_la_probabilite_corrigee(client, predicteur):
    attendu = predicteur.predire(pd.DataFrame([EXEMPLE])).iloc[0]

    corps = client.post("/predict", json=EXEMPLE, headers=EN_TETE).json()

    probabilite = attendu[config.COL_PROBABILITE]
    assert corps["probabilite_depart"] == pytest.approx(probabilite, abs=1e-4)
    assert corps["probabilite_depart"] + corps["probabilite_maintien"] == (
        pytest.approx(1)
    )
    assert corps["seuil_probabilite"] == pytest.approx(0.1215, abs=5e-4)


def test_predict_decision_suit_l_alerte(client):
    corps = client.post("/predict", json=EXEMPLE, headers=EN_TETE).json()

    attendue = "Risque de départ" if corps["alerte"] else "Pas de risque détecté"
    assert corps["decision"] == attendue
    assert corps["alerte"] == (
        corps["probabilite_depart"] >= corps["seuil_probabilite"]
    )


def test_predict_renvoie_la_fiche_rh_triee_par_poids(client):
    facteurs = client.post("/predict", json=EXEMPLE, headers=EN_TETE).json()["facteurs"]

    poids = [abs(facteur["contribution"]) for facteur in facteurs]
    assert len(facteurs) == NOMBRE_FACTEURS
    assert poids == sorted(poids, reverse=True)
    for facteur in facteurs:
        attendu = "augmente" if facteur["contribution"] > 0 else "réduit"
        assert facteur["effet"] == f"{attendu} le risque"


@pytest.mark.parametrize("en_tete", [{}, {"X-API-Key": "mauvaise-cle"}])
def test_predict_sans_cle_valide_refuse(client, en_tete):
    reponse = client.post("/predict", json=EXEMPLE, headers=en_tete)

    assert reponse.status_code == 401
    assert reponse.json() == {"detail": "Clé d'API absente ou invalide."}


def test_predict_refuse_tout_sans_empreinte_configuree(client, monkeypatch):
    # monkeypatch remet la clé des tests en place à la fin de ce test.
    monkeypatch.setitem(
        app.dependency_overrides, obtenir_parametres, lambda: parametres_de_test("")
    )

    reponse = client.post("/predict", json=EXEMPLE, headers=EN_TETE)

    assert reponse.status_code == 401


@pytest.mark.parametrize(
    ("modification", "champ", "message"),
    [
        ({"age": 17}, "age", "La valeur doit être supérieure ou égale à 18."),
        ({"age": 71}, "age", "La valeur doit être inférieure ou égale à 70."),
        ({"age": "trente"}, "age", "Un nombre entier est attendu."),
        (
            {"revenu_mensuel": 0},
            "revenu_mensuel",
            "La valeur doit être supérieure à 0.",
        ),
        (
            {"genre": "X"},
            "genre",
            "Valeur non autorisée. Valeurs possibles : 'F' ou 'M'.",
        ),
        ({"salaire": 3000}, "salaire", "Champ inconnu."),
        (
            {"annees_dans_le_poste_actuel": 6},
            "",
            "ne peut pas dépasser annees_dans_l_entreprise.",
        ),
    ],
)
def test_predict_donnee_invalide_refusee_en_francais(
    client, modification, champ, message
):
    reponse = client.post("/predict", json={**EXEMPLE, **modification}, headers=EN_TETE)

    assert reponse.status_code == 422
    detail = reponse.json()["detail"][0]
    assert detail["message"].endswith(message)
    assert detail["champ"] == (champ or "corps de la requête")


def test_predict_champ_manquant_refuse(client):
    incomplet = {cle: valeur for cle, valeur in EXEMPLE.items() if cle != "poste"}

    reponse = client.post("/predict", json=incomplet, headers=EN_TETE)

    assert reponse.status_code == 422
    assert reponse.json() == {
        "detail": [{"champ": "poste", "message": "Champ obligatoire."}]
    }


def test_swagger_documente_les_deux_routes(client):
    schema = client.get("/openapi.json").json()

    assert client.get("/docs").status_code == 200
    assert set(schema["paths"]) == {"/health", "/predict"}
    assert set(schema["paths"]["/predict"]["post"]["responses"]) == {
        "200",
        "401",
        "422",
    }


def test_erreur_de_type_non_prevu_garde_son_message_d_origine():
    erreur = {"type": "inconnu", "loc": ("body",), "msg": "Message d'origine"}

    assert traduire(erreur) == {
        "champ": "corps de la requête",
        "message": "Message d'origine",
    }
