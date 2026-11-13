"""Tests de l'entraîneur, sur un découpage réduit des collaborateurs du test du P4."""

import pytest

from src import config
from src.modele.artefact import MetadonneesArtefact, empreinte_sha256
from src.modele.entrainement import EntraineurPipeline


@pytest.fixture
def entraineur(reference_test_p4):
    # Découpage fictif des 294 collaborateurs : seuls comptent l'ordre et la
    # séparation des jeux, pas leurs tailles.
    identifiants = reference_test_p4[config.IDENTIFIANT].tolist()
    entrainement, validation = config.JEUX_ENTRAINEMENT
    decoupage = {
        entrainement: identifiants[:150],
        validation: identifiants[150:200],
        config.JEU_TEST: identifiants[200:],
    }
    return EntraineurPipeline(reference_test_p4, decoupage)


def test_jeux_reunis_dans_l_ordre_du_decoupage(entraineur, reference_test_p4):
    entrees, _ = entraineur.jeu(config.JEUX_ENTRAINEMENT)
    attendus = reference_test_p4[config.IDENTIFIANT].tolist()[:200]
    assert entrees.index.tolist() == attendus


def test_entrainement_sans_les_collaborateurs_du_test(entraineur):
    pipeline = entraineur.entrainer()
    assert pipeline["echelle"].n_samples_seen_ == 200


def test_metadonnees_portent_l_empreinte_de_l_artefact_ecrit(
    entraineur, tmp_path, monkeypatch
):
    artefact = tmp_path / "pipeline.joblib"
    metadonnees = tmp_path / "pipeline.json"
    monkeypatch.setattr(config, "FICHIER_ARTEFACT", artefact)
    monkeypatch.setattr(config, "FICHIER_METADONNEES", metadonnees)
    entraineur.sauvegarder(entraineur.entrainer())
    assert MetadonneesArtefact.lire(metadonnees).sha256 == empreinte_sha256(artefact)
