"""Tests de la configuration : colonnes, catégories et valeurs reprises du P4."""

import pytest
from sklearn.linear_model import LogisticRegression

from src import config

CATEGORIES = {**config.CATEGORIES_ORDINALES, **config.CATEGORIES_NOMINALES}

# Colonnes du jeu de référence qui ne sont pas des entrées du modèle :
# niveau_hierarchique_poste a été écartée au P4 (corrélation de 0,95 avec
# revenu_mensuel), et score_p4 est le score calculé par le modèle du P4.
HORS_ENTREE = {
    config.IDENTIFIANT,
    config.CIBLE,
    "niveau_hierarchique_poste",
    "score_p4",
}


@pytest.mark.parametrize("colonne", CATEGORIES)
def test_categories_identiques_aux_modalites_du_p4(
    colonne, reference_test_p4, cas_limites
):
    modalites = set(reference_test_p4[colonne]) | set(cas_limites[colonne])
    assert sorted(CATEGORIES[colonne]) == sorted(modalites)


def test_colonnes_d_entree_identiques_aux_variables_du_p4(reference_test_p4):
    attendues = set(reference_test_p4.columns) - HORS_ENTREE
    assert sorted(config.COLONNES_ENTREE) == sorted(attendues)


def test_seuil_de_decision_identique_au_p4(metadonnees_p4):
    assert metadonnees_p4["seuil_decision"] == config.SEUIL_DECISION


def test_hyperparametres_identiques_au_p4(metadonnees_p4):
    modele = LogisticRegression(**config.HYPERPARAMETRES)
    assert modele.get_params() == metadonnees_p4["hyperparametres"]
