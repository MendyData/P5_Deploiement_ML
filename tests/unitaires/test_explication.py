"""Tests de l'explication : parts des variables en log-cote et en points."""

import numpy as np
import pytest

from src import config
from src.modele.evaluation import probabilite_depart
from src.modele.explication import contributions, impacts_en_points


@pytest.fixture
def parts(predicteur, collaborateur):
    return contributions(predicteur.pipeline, collaborateur).iloc[0]


@pytest.fixture
def impacts(predicteur, parts):
    return impacts_en_points(
        parts,
        predicteur.pipeline[-1].intercept_[0],
        predicteur.metadonnees.taux_depart_entrainement,
    )


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

    # La somme est en log-cote : la fonction logistique la reconvertit en score.
    recalcules = 1 / (1 + np.exp(-(parts.sum(axis=1) + constante)))

    np.testing.assert_allclose(recalcules, scores)


def test_un_impact_par_variable_du_signe_de_sa_part(parts, impacts):
    assert impacts.index.equals(parts.index)
    non_nulles = parts != 0
    assert (np.sign(impacts[non_nulles]) == np.sign(parts[non_nulles])).all()


def test_impact_egal_a_l_ecart_avec_la_variable_a_la_moyenne(
    predicteur, collaborateur, impacts
):
    # Recalcul par le modèle lui-même : une valeur mise à l'échelle de 0 est la
    # moyenne de l'entraînement.
    valeurs = predicteur.pipeline[:-1].transform(collaborateur)
    taux = predicteur.metadonnees.taux_depart_entrainement
    probabilite = predicteur.predire(collaborateur)[config.COL_PROBABILITE].iloc[0]
    for variable in valeurs.columns:
        a_la_moyenne = valeurs.assign(**{variable: 0.0})
        score = predicteur.pipeline[-1].predict_proba(a_la_moyenne)[:, 1]
        sans = probabilite_depart(score, taux)[0]
        assert impacts[variable] == pytest.approx(100 * (probabilite - sans))


def test_part_nulle_sans_impact(predicteur, parts):
    nulle = parts.copy()
    nulle.iloc[0] = 0.0

    impacts = impacts_en_points(
        nulle,
        predicteur.pipeline[-1].intercept_[0],
        predicteur.metadonnees.taux_depart_entrainement,
    )

    assert impacts.iloc[0] == 0
