"""Tests du prédicteur : vérifications avant tout chargement, puis prédictions."""

import dataclasses
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from src import config
from src.modele.artefact import MetadonneesArtefact
from src.modele.predicteur import ArtefactInvalide, PredicteurAttrition

# Exécuté dans un processus Python neuf : recharge l'artefact, puis écrit les scores
# des collaborateurs lus dans le CSV reçu. Détecte une classe définie hors de src/.
SCRIPT_RECHARGEMENT = """
import sys
import numpy as np
import pandas as pd
from src import config
from src.modele.predicteur import PredicteurAttrition
collaborateurs = pd.read_csv(sys.argv[1])
scores = PredicteurAttrition().predire(collaborateurs)[config.COL_SCORE]
np.save(sys.argv[2], scores.to_numpy())
"""


@pytest.fixture
def entrees(reference_test_p4):
    return reference_test_p4[config.COLONNES_ENTREE]


@pytest.fixture
def copie_artefact(tmp_path):
    # Copie de l'artefact et de ses métadonnées, modifiable sans toucher aux originaux.
    artefact = tmp_path / config.FICHIER_ARTEFACT.name
    metadonnees = tmp_path / config.FICHIER_METADONNEES.name
    shutil.copy(config.FICHIER_ARTEFACT, artefact)
    shutil.copy(config.FICHIER_METADONNEES, metadonnees)
    return artefact, metadonnees


@pytest.fixture
def chargement_interdit(monkeypatch):
    # Fait échouer le test si joblib charge un fichier : le refus doit venir avant.
    def charger(chemin):
        pytest.fail(f"{chemin.name} chargé alors qu'une vérification devait refuser.")

    monkeypatch.setattr("joblib.load", charger)


def test_rechargement_dans_un_processus_neuf_redonne_les_memes_scores(
    tmp_path, entrees, predicteur
):
    fichier_entrees = tmp_path / "entrees.csv"
    fichier_scores = tmp_path / "scores.npy"
    entrees.to_csv(fichier_entrees, index=False)
    subprocess.run(
        [sys.executable, "-c", SCRIPT_RECHARGEMENT, fichier_entrees, fichier_scores],
        check=True,
    )
    attendus = predicteur.predire(entrees)[config.COL_SCORE].to_numpy()
    np.testing.assert_array_equal(np.load(fichier_scores), attendus)


def test_empreinte_alteree_refusee_avant_tout_chargement(
    copie_artefact, chargement_interdit
):
    artefact, metadonnees = copie_artefact
    with artefact.open("ab") as fichier:
        fichier.write(b"\0")
    with pytest.raises(ArtefactInvalide, match="Empreinte"):
        PredicteurAttrition(artefact, metadonnees)


@pytest.mark.parametrize("bibliotheque", config.BIBLIOTHEQUES_ARTEFACT)
def test_version_differente_d_une_bibliotheque_refusee_avant_tout_chargement(
    copie_artefact, chargement_interdit, bibliotheque
):
    artefact, metadonnees = copie_artefact
    originales = MetadonneesArtefact.lire(metadonnees)
    versions = {**originales.versions, bibliotheque: "0.0.0"}
    dataclasses.replace(originales, versions=versions).ecrire(metadonnees)
    with pytest.raises(ArtefactInvalide, match=bibliotheque):
        PredicteurAttrition(artefact, metadonnees)


def test_autre_correctif_de_python_tolere(copie_artefact):
    artefact, metadonnees = copie_artefact
    originales = MetadonneesArtefact.lire(metadonnees)
    versions = {**originales.versions, "python": "3.11.0"}
    dataclasses.replace(originales, versions=versions).ecrire(metadonnees)
    predicteur_tolerant = PredicteurAttrition(artefact, metadonnees)
    assert predicteur_tolerant.metadonnees.versions["python"] == "3.11.0"


def test_predire_renvoie_le_score_et_l_alerte_par_identifiant(
    predicteur, reference_test_p4
):
    collaborateurs = reference_test_p4.set_index(config.IDENTIFIANT)
    sortie = predicteur.predire(collaborateurs[config.COLONNES_ENTREE])
    assert sortie.columns.tolist() == [config.COL_SCORE, config.COL_ALERTE]
    assert sortie.index.equals(collaborateurs.index)


def test_predire_redonne_les_scores_du_p4_a_1e_6_pres(
    predicteur, entrees, reference_test_p4
):
    scores = predicteur.predire(entrees)[config.COL_SCORE]
    np.testing.assert_allclose(scores, reference_test_p4["score_p4"], rtol=0, atol=1e-6)


def test_predire_redonne_les_alertes_du_p4(predicteur, entrees, reference_test_p4):
    alertes = predicteur.predire(entrees)[config.COL_ALERTE]
    attendues = (reference_test_p4["score_p4"] >= config.SEUIL_DECISION).astype(int)
    assert alertes.tolist() == attendues.tolist()


def test_un_collaborateur_seul_et_dans_un_lot_obtient_le_meme_score(
    predicteur, entrees
):
    seul = predicteur.predire(entrees.iloc[[0]])[config.COL_SCORE]
    dans_le_lot = predicteur.predire(entrees)[config.COL_SCORE].iloc[[0]]
    np.testing.assert_allclose(seul, dans_le_lot, rtol=0, atol=1e-12)


def test_deux_appels_successifs_donnent_le_meme_resultat(predicteur, entrees):
    pd.testing.assert_frame_equal(
        predicteur.predire(entrees), predicteur.predire(entrees)
    )
