"""Parcours complet : un client envoie les exemples, puis ses traces sont relues."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src import config
from src.api.application import app
from src.api.securite import creer_utilisateur
from src.bdd.modeles import Demande, Reponse, Utilisateur

DOSSIER_EXEMPLES = config.RACINE_PROJET / "docs" / "exemples"


@pytest.fixture(scope="module")
def client(parametres_bdd):
    """Client de l'API : modèle chargé une fois pour ce fichier, base de test."""
    with TestClient(app) as client_api:
        yield client_api


def lire_exemple(nom):
    chemin = DOSSIER_EXEMPLES / f"collaborateur_{nom}.json"
    return json.loads(chemin.read_text(encoding="utf-8"))


def test_exemples_fournis_traces_avec_leur_alerte_puis_client_desactive(
    client, session_bdd
):
    en_tete = {"X-API-Key": creer_utilisateur(session_bdd, "equipe-rh")}

    # 1. Le client envoie les deux exemples de la documentation.
    sans_alerte = client.post(
        "/predict", json=lire_exemple("sans_alerte"), headers=en_tete
    )
    avec_alerte = client.post(
        "/predict", json=lire_exemple("avec_alerte"), headers=en_tete
    )
    assert sans_alerte.status_code == avec_alerte.status_code == 200
    assert sans_alerte.json()["alerte"] is False
    assert avec_alerte.json()["alerte"] is True

    # 2. Chaque demande a sa réponse, dans l'ordre, rattachée au client.
    lignes = session_bdd.execute(
        select(
            Utilisateur.nom,
            Reponse.alerte,
            Reponse.score_risque,
            Reponse.probabilite_depart,
        )
        .join(Demande, Demande.utilisateur_id == Utilisateur.id)
        .join(Reponse, Reponse.demande_id == Demande.id)
        .order_by(Demande.id)
    ).all()
    assert [(ligne.nom, ligne.alerte) for ligne in lignes] == [
        ("equipe-rh", False),
        ("equipe-rh", True),
    ]
    assert lignes[1].score_risque == pytest.approx(avec_alerte.json()["score_risque"])
    assert lignes[1].probabilite_depart == pytest.approx(
        avec_alerte.json()["probabilite_depart"]
    )

    # 3. Le client est désactivé : sa clé est refusée et rien n'est enregistré.
    session_bdd.scalars(select(Utilisateur)).one().actif = False
    session_bdd.commit()
    refus = client.post("/predict", json=lire_exemple("sans_alerte"), headers=en_tete)
    assert refus.status_code == 401
    assert len(session_bdd.scalars(select(Demande)).all()) == len(lignes)
