"""Tests de l'explication : les parts des variables redonnent le score du modèle."""

import numpy as np

from src import config
from src.modele.explication import contributions


def test_une_part_par_variable_du_modele(predicteur, reference_test_p4):
    parts = contributions(predicteur.pipeline, reference_test_p4)

    assert list(parts.columns) == predicteur.metadonnees.features
    assert len(parts) == len(reference_test_p4)


def test_somme_des_parts_et_de_la_constante_redonne_le_score(
    predicteur, reference_test_p4
):
    parts = contributions(predicteur.pipeline, reference_test_p4)
    constante = predicteur.pipeline[-1].intercept_[0]
    scores = predicteur.predire(reference_test_p4)[config.COL_SCORE]

    # La fonction logistique convertit la somme en probabilité.
    recalcules = 1 / (1 + np.exp(-(parts.sum(axis=1) + constante)))

    np.testing.assert_allclose(recalcules, scores)
