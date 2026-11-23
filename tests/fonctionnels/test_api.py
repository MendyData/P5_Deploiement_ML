"""Tests de l'API : santé, prédiction tracée, authentification, données refusées.

Les deux portes de prédiction sont couvertes : les 26 informations en JSON, ou
l'identifiant d'un collaborateur déjà en base.
"""

import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import DataError, IntegrityError, OperationalError

from src import config
from src.api.application import app
from src.api.erreurs import traduire
from src.api.securite import creer_utilisateur
from src.bdd.initialisation import inserer_dataset
from src.bdd.modeles import Demande, Reponse, Utilisateur
from src.bdd.session import obtenir_session
from src.schemas.collaborateur import EXEMPLE
from src.services.prediction import NOMBRE_FACTEURS, lire_en_pourcentages


@pytest.fixture(scope="module")
def client(parametres_bdd):
    """Client de l'API : modèle chargé une fois pour ce fichier, base de test."""
    # Le bloc with déclenche le démarrage de l'application.
    with TestClient(app) as client_api:
        yield client_api


@pytest.fixture
def en_tete(session_bdd):
    """En-tête d'un client enregistré dans la base de test."""
    return {"X-API-Key": creer_utilisateur(session_bdd, "client-de-test")}


def compter(session, table):
    return session.scalar(select(func.count()).select_from(table))


def session_en_panne():
    raise OperationalError("SELECT 1", {}, Exception("base arrêtée"))


def test_health_repond_sans_cle(client):
    reponse = client.get("/health")

    assert reponse.status_code == 200
    assert reponse.json() == {
        "statut": "ok",
        "environnement": "test",
        "version_modele": "0.1.0",
        "base_de_donnees": "ok",
    }


def test_predict_renvoie_le_score_du_predicteur(client, en_tete, predicteur):
    attendu = predicteur.predire(pd.DataFrame([EXEMPLE])).iloc[0]

    reponse = client.post("/predict", json=EXEMPLE, headers=en_tete)

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["score_risque"] == pytest.approx(attendu[config.COL_SCORE])
    assert corps["alerte"] == bool(attendu[config.COL_ALERTE])
    assert corps["seuil_decision"] == predicteur.metadonnees.seuil_decision
    assert corps["version_modele"] == predicteur.metadonnees.version_modele


def test_predict_renvoie_la_probabilite_corrigee(client, en_tete, predicteur):
    attendu = predicteur.predire(pd.DataFrame([EXEMPLE])).iloc[0]

    corps = client.post("/predict", json=EXEMPLE, headers=en_tete).json()

    probabilite = attendu[config.COL_PROBABILITE]
    assert corps["probabilite_depart"] == pytest.approx(probabilite, abs=1e-4)
    assert corps["probabilite_depart"] + corps["probabilite_maintien"] == (
        pytest.approx(1)
    )
    assert corps["seuil_probabilite"] == pytest.approx(0.1215, abs=5e-4)


def test_predict_decision_suit_l_alerte(client, en_tete):
    corps = client.post("/predict", json=EXEMPLE, headers=en_tete).json()

    attendue = "Risque de départ" if corps["alerte"] else "Pas de risque détecté"
    assert corps["decision"] == attendue
    assert corps["alerte"] == (
        corps["probabilite_depart"] >= corps["seuil_probabilite"]
    )


def test_predict_renvoie_la_fiche_rh_triee_par_poids(client, en_tete):
    facteurs = client.post("/predict", json=EXEMPLE, headers=en_tete).json()["facteurs"]

    poids = [abs(facteur["contribution"]) for facteur in facteurs]
    assert len(facteurs) == NOMBRE_FACTEURS
    assert poids == sorted(poids, reverse=True)
    for facteur in facteurs:
        attendu = "augmente" if facteur["contribution"] > 0 else "réduit"
        assert facteur["effet"] == f"{attendu} le risque"
        assert (facteur["impact_points"] > 0) == (facteur["contribution"] > 0)


def test_predict_lit_les_probabilites_en_pourcentages(client, en_tete):
    corps = client.post("/predict", json=EXEMPLE, headers=en_tete).json()

    # L'exemple de Swagger : 3,68 % de probabilité de départ.
    assert corps["lecture"] == "Maintien (0) : 96,3 % ; départ (1) : 3,7 %"


@pytest.mark.parametrize(
    ("probabilite", "attendue"),
    [
        (0.0365, "Maintien (0) : 96,4 % ; départ (1) : 3,6 %"),
        (0.6, "Maintien (0) : 40,0 % ; départ (1) : 60,0 %"),
        (0.0, "Maintien (0) : 100,0 % ; départ (1) : 0,0 %"),
    ],
)
def test_lecture_en_pourcentages_qui_font_toujours_100(probabilite, attendue):
    assert lire_en_pourcentages(probabilite) == attendue


def test_predict_enregistre_la_demande_puis_la_reponse_reliee(
    client, en_tete, session_bdd
):
    corps = client.post("/predict", json=EXEMPLE, headers=en_tete).json()

    demande = session_bdd.scalars(select(Demande)).one()
    reponse = session_bdd.scalars(select(Reponse)).one()
    utilisateur = session_bdd.get(Utilisateur, demande.utilisateur_id)
    assert utilisateur.nom == "client-de-test"
    assert {champ: getattr(demande, champ) for champ in EXEMPLE} == EXEMPLE
    assert reponse.demande_id == demande.id
    assert reponse.score_risque == pytest.approx(corps["score_risque"])
    assert reponse.probabilite_depart == pytest.approx(corps["probabilite_depart"])
    assert reponse.facteurs == corps["facteurs"]


@pytest.mark.parametrize("en_tete_recu", [{}, {"X-API-Key": "mauvaise-cle"}])
def test_predict_sans_cle_valide_refuse_sans_trace(client, session_bdd, en_tete_recu):
    reponse = client.post("/predict", json=EXEMPLE, headers=en_tete_recu)

    assert reponse.status_code == 401
    assert reponse.json() == {"detail": "Clé d'API absente ou invalide."}
    assert compter(session_bdd, Demande) == 0


def test_predict_client_desactive_refuse(client, en_tete, session_bdd):
    session_bdd.scalars(select(Utilisateur)).one().actif = False
    session_bdd.commit()

    assert client.post("/predict", json=EXEMPLE, headers=en_tete).status_code == 401


@pytest.mark.parametrize(
    ("modification", "champ", "message"),
    [
        ({"age": 17}, "age", "La valeur doit être supérieure ou égale à 18."),
        ({"age": 71}, "age", "La valeur doit être inférieure ou égale à 70."),
        ({"age": "trente"}, "age", "Un nombre entier est attendu."),
        ({"revenu_mensuel": 0}, "revenu_mensuel", "doit être supérieure à 0."),
        (
            {"revenu_mensuel": 3_000_000_000},
            "revenu_mensuel",
            "doit être inférieure ou égale à 50000.",
        ),
        ({"genre": "X"}, "genre", "Valeurs possibles : 'F' ou 'M'."),
        ({"salaire": 3000}, "salaire", "Champ inconnu."),
        (
            {"annees_dans_le_poste_actuel": 6},
            "",
            "ne peut pas dépasser annees_dans_l_entreprise.",
        ),
    ],
)
def test_predict_donnee_invalide_refusee_en_francais(
    client, en_tete, modification, champ, message
):
    reponse = client.post("/predict", json={**EXEMPLE, **modification}, headers=en_tete)

    assert reponse.status_code == 422
    detail = reponse.json()["detail"][0]
    assert detail["message"].endswith(message)
    assert detail["champ"] == (champ or "corps de la requête")


def test_predict_donnee_invalide_ne_laisse_aucune_trace(client, en_tete, session_bdd):
    client.post("/predict", json={**EXEMPLE, "age": 17}, headers=en_tete)

    assert compter(session_bdd, Demande) == 0


def test_predict_champ_manquant_refuse(client, en_tete):
    incomplet = {cle: valeur for cle, valeur in EXEMPLE.items() if cle != "poste"}

    reponse = client.post("/predict", json=incomplet, headers=en_tete)

    assert reponse.status_code == 422
    assert reponse.json() == {
        "detail": [{"champ": "poste", "message": "Champ obligatoire."}]
    }


@pytest.mark.parametrize(
    ("methode", "chemin"),
    [("GET", "/health"), ("POST", "/predict"), ("POST", "/predict/1")],
)
def test_base_indisponible_repond_503_sans_prediction(
    client, monkeypatch, methode, chemin
):
    # monkeypatch remet la vraie session en place à la fin de ce test.
    monkeypatch.setitem(app.dependency_overrides, obtenir_session, session_en_panne)

    reponse = client.request(methode, chemin, json=EXEMPLE, headers={"X-API-Key": "x"})

    assert reponse.status_code == 503
    assert reponse.json() == {
        "detail": "Base de données indisponible : aucune prédiction n'est servie."
    }


@pytest.mark.parametrize("erreur", [DataError, IntegrityError])
@pytest.mark.parametrize(
    ("methode", "chemin"),
    [("GET", "/health"), ("POST", "/predict"), ("POST", "/predict/1")],
)
def test_ordre_refuse_par_la_base_repond_500_et_non_503(
    client, monkeypatch, erreur, methode, chemin
):
    # La base répond, mais refuse l'ordre : elle n'est pas indisponible.
    def session_qui_refuse():
        raise erreur("INSERT INTO demandes", {}, Exception("ordre refusé"))

    monkeypatch.setitem(app.dependency_overrides, obtenir_session, session_qui_refuse)

    reponse = client.request(methode, chemin, json=EXEMPLE, headers={"X-API-Key": "x"})

    assert reponse.status_code == 500
    assert reponse.json() == {
        "detail": "Erreur de la base de données : aucune prédiction n'est servie."
    }


@pytest.mark.parametrize(
    ("methode", "chemin"),
    [("GET", "/health"), ("POST", "/predict"), ("GET", "/schema.json")],
)
def test_reponses_json_declarent_l_encodage_utf8(client, methode, chemin):
    # Sans clé, /predict répond 401 : les erreurs sont concernées elles aussi.
    reponse = client.request(methode, chemin, json=EXEMPLE)

    assert reponse.headers["content-type"] == "application/json; charset=utf-8"


def test_swagger_documente_les_trois_routes(client):
    schema = client.get("/schema.json").json()

    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 404
    assert set(schema["paths"]) == {"/health", "/predict", "/predict/{id_employee}"}
    assert set(schema["paths"]["/predict"]["post"]["responses"]) == {
        "200",
        "401",
        "422",
        "500",
        "503",
    }
    assert set(schema["paths"]["/predict/{id_employee}"]["post"]["responses"]) == {
        "200",
        "401",
        "404",
        "422",
        "500",
        "503",
    }
    assert schema["info"]["contact"]["name"] == "Angèle GOMIS"
    assert schema["info"]["license"]["name"] == "MIT"


def test_erreur_de_type_non_prevu_garde_son_message_d_origine():
    erreur = {"type": "inconnu", "loc": ("body",), "msg": "Message d'origine"}

    assert traduire(erreur) == {
        "champ": "corps de la requête",
        "message": "Message d'origine",
    }


@pytest.fixture
def collaborateurs_en_base(session_bdd, reference_test_p4):
    """Collaborateurs du test du P4, insérés dans la table collaborateurs."""
    inserer_dataset(session_bdd.get_bind(), reference_test_p4)
    return reference_test_p4


def test_predict_par_identifiant_donne_la_meme_reponse_qu_en_json(
    client, en_tete, collaborateurs_en_base
):
    premier = collaborateurs_en_base.iloc[0]
    # to_json convertit les entiers numpy en nombres JSON ordinaires.
    valeurs = json.loads(premier[config.COLONNES_ENTREE].to_json())

    par_identifiant = client.post(
        f"/predict/{int(premier[config.IDENTIFIANT])}", headers=en_tete
    )
    en_json = client.post("/predict", json=valeurs, headers=en_tete)

    assert par_identifiant.status_code == 200
    assert par_identifiant.json() == en_json.json()


def test_predict_par_identifiant_trace_la_demande_puis_la_reponse(
    client, en_tete, session_bdd, collaborateurs_en_base
):
    premier = collaborateurs_en_base.iloc[0]

    client.post(f"/predict/{int(premier[config.IDENTIFIANT])}", headers=en_tete)

    demande = session_bdd.scalars(select(Demande)).one()
    assert demande.poste == premier["poste"]
    assert demande.age == premier["age"]
    assert session_bdd.scalars(select(Reponse)).one().demande_id == demande.id


def test_predict_par_identifiant_inconnu_repond_404_sans_trace(
    client, en_tete, session_bdd, collaborateurs_en_base
):
    reponse = client.post("/predict/999999", headers=en_tete)

    assert reponse.status_code == 404
    assert reponse.json() == {"detail": "Collaborateur 999999 inconnu."}
    assert compter(session_bdd, Demande) == 0


@pytest.mark.parametrize("en_tete_recu", [{}, {"X-API-Key": "mauvaise-cle"}])
def test_predict_par_identifiant_sans_cle_valide_refuse(
    client, session_bdd, collaborateurs_en_base, en_tete_recu
):
    reponse = client.post("/predict/1", headers=en_tete_recu)

    assert reponse.status_code == 401
    assert compter(session_bdd, Demande) == 0


def test_predict_par_identifiant_negatif_refuse(client, en_tete):
    assert client.post("/predict/0", headers=en_tete).status_code == 422
