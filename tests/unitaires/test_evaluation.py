"""Tests de la conversion des scores en probabilités de départ."""

import numpy as np
import pytest

from src import config
from src.modele.evaluation import probabilite_depart

TAUX = 0.16156462585034015


def test_score_de_0_5_donne_le_taux_de_depart():
    # Un score de 0,5 est neutre pour le modèle rééquilibré : il ne reste que le
    # taux de départ réel.
    assert probabilite_depart(np.array([0.5]), TAUX)[0] == pytest.approx(TAUX)


def test_bornes_conservees():
    np.testing.assert_array_equal(
        probabilite_depart(np.array([0.0, 1.0]), TAUX), [0, 1]
    )


def test_ordre_des_scores_conserve():
    scores = np.linspace(0.01, 0.99, 99)
    assert np.all(np.diff(probabilite_depart(scores, TAUX)) > 0)


def test_probabilite_toujours_inferieure_au_score_quand_les_departs_sont_rares():
    scores = np.linspace(0.01, 0.99, 99)
    assert np.all(probabilite_depart(scores, TAUX) < scores)


def test_seuil_de_decision_vaut_environ_12_pour_cent():
    seuil = probabilite_depart(np.array([config.SEUIL_DECISION]), TAUX)[0]
    assert seuil == pytest.approx(0.1215, abs=5e-4)


def test_taux_de_50_pour_cent_laisse_le_score_inchange():
    scores = np.array([0.1, 0.418, 0.9])
    np.testing.assert_allclose(probabilite_depart(scores, 0.5), scores)
