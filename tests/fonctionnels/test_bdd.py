"""Tests de l'initialisation de la base : tables, jeu de données, clients de l'API."""

import time

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import OperationalError

from src import config
from src.api.securite import creer_utilisateur, empreinte_cle
from src.bdd.initialisation import creer_base, inserer_dataset
from src.bdd.modeles import Base, Collaborateur, Utilisateur
from src.bdd.session import DELAI_CONNEXION, creer_moteur


def test_creer_base_cree_les_quatre_tables_et_peut_etre_relancee(
    parametres_bdd, session_bdd
):
    creer_base(parametres_bdd)

    tables = inspect(session_bdd.get_bind()).get_table_names()
    assert set(tables) == set(Base.metadata.tables)
    assert set(tables) == {"utilisateurs", "collaborateurs", "demandes", "reponses"}


def test_inserer_dataset_insere_toutes_les_lignes(session_bdd, reference_test_p4):
    total = inserer_dataset(session_bdd.get_bind(), reference_test_p4)

    assert total == len(reference_test_p4)
    premier = reference_test_p4.iloc[0]
    ligne = session_bdd.get(Collaborateur, int(premier[config.IDENTIFIANT]))
    assert ligne.poste == premier["poste"]
    assert ligne.age == premier["age"]
    assert ligne.a_quitte_l_entreprise == (
        premier[config.CIBLE] == config.MODALITE_DEPART
    )


def test_inserer_dataset_remplace_le_contenu_precedent(session_bdd, reference_test_p4):
    moteur = session_bdd.get_bind()
    inserer_dataset(moteur, reference_test_p4)

    total = inserer_dataset(moteur, reference_test_p4.head(10))

    assert total == 10


def test_creer_utilisateur_n_enregistre_que_l_empreinte_de_la_cle(session_bdd):
    cle = creer_utilisateur(session_bdd, "equipe-rh")

    utilisateur = session_bdd.scalars(select(Utilisateur)).one()
    assert utilisateur.nom == "equipe-rh"
    assert utilisateur.actif is True
    assert utilisateur.empreinte_cle == empreinte_cle(cle)
    assert utilisateur.empreinte_cle != cle


def test_base_injoignable_signalee_sans_attente(parametres_bdd):
    # Port 1 : aucune base n'y répond, comme une base arrêtée.
    moteur = creer_moteur(parametres_bdd.url_api.set(port=1))
    debut = time.monotonic()

    with pytest.raises(OperationalError), moteur.connect():
        pass

    assert time.monotonic() - debut < DELAI_CONNEXION + 5
    moteur.dispose()
