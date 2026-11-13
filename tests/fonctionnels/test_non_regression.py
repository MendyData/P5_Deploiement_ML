"""Tests de non-régression : le pipeline redonne les résultats du modèle du P4."""

import json

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import confusion_matrix

from src import config
from src.modele.entrainement import EntraineurPipeline
from src.modele.evaluation import appliquer_seuil, calculer_metriques

# X complet du P4, écrit à côté du jeu consolidé par scripts/generer_reference_p4.py.
FICHIER_X_P4 = config.FICHIER_CONSOLIDE.with_name("x_p4.csv")

# Matrice de confusion du P4 sur ses 294 collaborateurs de test, au seuil :
# [[sans départ ni alerte, fausses alertes], [départs manqués, départs détectés]].
MATRICE_DE_CONFUSION_P4 = [[184, 63], [11, 36]]


# Le prédicteur a vérifié l'empreinte et les versions de l'artefact avant de le charger.
@pytest.fixture(scope="module")
def pipeline_sauvegarde(predicteur):
    return predicteur.pipeline


# Les données complètes ne sont pas suivies par Git : sans elles, les tests lents
# qui en dépendent sont ignorés.
@pytest.fixture(scope="module")
def consolide_complet():
    if not config.FICHIER_CONSOLIDE.exists():
        pytest.skip("Jeu consolidé absent : lancer scripts/generer_reference_p4.py.")
    return pd.read_csv(config.FICHIER_CONSOLIDE)


@pytest.fixture(scope="module")
def x_p4_complet():
    if not FICHIER_X_P4.exists():
        pytest.skip("X du P4 absent : lancer scripts/generer_reference_p4.py.")
    return pd.read_csv(FICHIER_X_P4, index_col=config.IDENTIFIANT)


@pytest.fixture(scope="module")
def pipeline_reentraine(consolide_complet):
    decoupage = json.loads(config.FICHIER_DECOUPAGE.read_text(encoding="utf-8"))
    return EntraineurPipeline(consolide_complet, decoupage).entrainer()


# Chaque vérification porte sur le pipeline sauvegardé, puis, sous le marqueur lent,
# sur un pipeline réentraîné à partir des données complètes.
@pytest.fixture(
    scope="module",
    params=[
        pytest.param("pipeline_sauvegarde", id="sauvegarde"),
        pytest.param("pipeline_reentraine", id="reentraine", marks=pytest.mark.lent),
    ],
)
def pipeline(request):
    return request.getfixturevalue(request.param)


@pytest.fixture(scope="module")
def scores(pipeline, reference_test_p4):
    return pipeline.predict_proba(reference_test_p4[config.COLONNES_ENTREE])[:, 1]


@pytest.fixture(scope="module")
def metriques(scores, departs_test_p4, metadonnees_artefact):
    return calculer_metriques(
        departs_test_p4, scores, metadonnees_artefact.seuil_decision
    )


def test_scores_identiques_a_ceux_du_p4_a_1e_6_pres(scores, reference_test_p4):
    np.testing.assert_allclose(scores, reference_test_p4["score_p4"], rtol=0, atol=1e-6)


def test_matrice_de_confusion_identique_a_celle_du_p4(
    scores, departs_test_p4, metadonnees_artefact
):
    alertes = appliquer_seuil(scores, metadonnees_artefact.seuil_decision)
    matrice = confusion_matrix(departs_test_p4, alertes).tolist()
    assert matrice == MATRICE_DE_CONFUSION_P4


@pytest.mark.parametrize("nom", ["accuracy", "precision", "rappel", "f2", "auc_pr"])
def test_metrique_identique_a_celle_du_p4_a_trois_decimales(
    metriques, metadonnees_p4, nom
):
    assert round(metriques[nom], 3) == metadonnees_p4["metriques_test"][nom]


def test_score_egal_au_seuil_donne_une_alerte(metadonnees_artefact):
    seuil = metadonnees_artefact.seuil_decision
    juste_en_dessous = np.nextafter(seuil, 0)
    alertes = appliquer_seuil(np.array([juste_en_dessous, seuil]), seuil)
    assert alertes.tolist() == [0, 1]


def test_metadonnees_reprennent_le_seuil_exact_du_p4(
    metadonnees_artefact, metadonnees_p4
):
    assert metadonnees_artefact.seuil_decision == metadonnees_p4["seuil_decision"]


def test_metadonnees_listent_les_features_recues_par_le_modele(
    metadonnees_artefact, pipeline_sauvegarde
):
    noms = pipeline_sauvegarde["modele"].feature_names_in_.tolist()
    assert metadonnees_artefact.features == noms


@pytest.mark.lent
def test_pretraitement_des_1470_collaborateurs_identique_au_x_du_p4(
    pipeline_sauvegarde, consolide_complet, x_p4_complet
):
    sortie = pipeline_sauvegarde["pretraitement"].transform(consolide_complet)
    sortie = sortie.set_axis(consolide_complet[config.IDENTIFIANT])
    pd.testing.assert_frame_equal(
        sortie[x_p4_complet.columns], x_p4_complet, check_exact=True
    )
