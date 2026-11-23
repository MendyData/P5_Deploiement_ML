"""Tests de la documentation interactive : correspondance avec les extraits RH."""

from collections import Counter

import pytest

from src import config
from src.api.documentation import DESCRIPTION_PREDICT, EXEMPLES_PREDICT, EXTRAITS_RH
from src.schemas.collaborateur import Collaborateur


def test_les_extraits_couvrent_exactement_les_entrees_du_modele():
    champs = Counter(champ for extrait in EXTRAITS_RH for champ in extrait.champs)
    assert set(champs) == set(config.COLONNES_ENTREE)
    assert max(champs.values()) == 1


def test_aucune_colonne_a_retirer_n_est_une_entree_du_modele():
    a_retirer = {nom for extrait in EXTRAITS_RH for nom in extrait.a_retirer}
    assert a_retirer.isdisjoint(config.COLONNES_ENTREE)


@pytest.mark.parametrize("nom", list(EXEMPLES_PREDICT))
def test_chaque_exemple_de_la_documentation_est_accepte(nom):
    Collaborateur.model_validate(EXEMPLES_PREDICT[nom]["value"])


def test_la_description_cite_chaque_extrait():
    for extrait in EXTRAITS_RH:
        assert extrait.fichier in DESCRIPTION_PREDICT
