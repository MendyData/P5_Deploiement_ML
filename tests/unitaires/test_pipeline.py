"""Tests de l'assemblage du pipeline : sortie du prétraitement et erreurs."""

import numpy as np
import pandas as pd
import pytest

from src import config
from src.modele.pipeline import ConstructeurPipeline

# Une colonne de chaque rôle, pour les cas d'erreur.
NUMERIQUE = config.COLONNES_NUMERIQUES[0]
ORDINALE = next(iter(config.CATEGORIES_ORDINALES))
NOMINALE = next(iter(config.CATEGORIES_NOMINALES))


@pytest.fixture(scope="module")
def pretraitement_ajuste(reference_test_p4):
    return ConstructeurPipeline().pretraitement().fit(reference_test_p4)


@pytest.fixture(scope="module")
def pipeline_ajuste(reference_test_p4, departs_test_p4):
    return ConstructeurPipeline().construire().fit(reference_test_p4, departs_test_p4)


def test_un_collaborateur_donne_les_46_features_du_p4(
    pretraitement_ajuste, collaborateur, metadonnees_p4
):
    sortie = pretraitement_ajuste.transform(collaborateur)
    assert sorted(sortie.columns) == sorted(metadonnees_p4["features"])


def test_sortie_numerique_sans_valeur_manquante(pretraitement_ajuste, collaborateur):
    sortie = pretraitement_ajuste.transform(collaborateur)
    assert all(pd.api.types.is_numeric_dtype(type_) for type_ in sortie.dtypes)
    assert not sortie.isna().any().any()


def test_encodage_identique_au_x_du_p4(
    pretraitement_ajuste, reference_test_p4, reference_x_test_p4
):
    sortie = pretraitement_ajuste.transform(reference_test_p4).set_axis(
        reference_test_p4[config.IDENTIFIANT]
    )
    pd.testing.assert_frame_equal(
        sortie[reference_x_test_p4.columns], reference_x_test_p4, check_exact=True
    )


def test_collaborateur_seul_identique_a_sa_ligne_dans_le_lot(
    pretraitement_ajuste, reference_test_p4, collaborateur
):
    lot = pretraitement_ajuste.transform(reference_test_p4)
    seul = pretraitement_ajuste.transform(collaborateur)
    pd.testing.assert_frame_equal(seul, lot.loc[collaborateur.index])


def test_ordre_des_colonnes_recues_sans_effet(pretraitement_ajuste, reference_test_p4):
    inverse = reference_test_p4[reference_test_p4.columns[::-1]]
    pd.testing.assert_frame_equal(
        pretraitement_ajuste.transform(inverse),
        pretraitement_ajuste.transform(reference_test_p4),
    )


def test_colonne_en_trop_ignoree(pretraitement_ajuste, collaborateur):
    pd.testing.assert_frame_equal(
        pretraitement_ajuste.transform(collaborateur.assign(colonne_en_trop=1)),
        pretraitement_ajuste.transform(collaborateur),
    )


@pytest.mark.parametrize("colonne", [NUMERIQUE, ORDINALE, NOMINALE])
def test_colonne_absente_refusee(pretraitement_ajuste, collaborateur, colonne):
    with pytest.raises(ValueError, match=colonne):
        pretraitement_ajuste.transform(collaborateur.drop(columns=colonne))


@pytest.mark.parametrize("colonne", [ORDINALE, NOMINALE])
@pytest.mark.parametrize("valeur", ["Modalité inconnue", None])
def test_modalite_hors_categories_refusee(
    pretraitement_ajuste, collaborateur, colonne, valeur
):
    with pytest.raises(ValueError, match="unknown categories"):
        pretraitement_ajuste.transform(collaborateur.assign(**{colonne: valeur}))


def test_valeur_numerique_manquante_refusee(pipeline_ajuste, collaborateur):
    entree = collaborateur.assign(**{NUMERIQUE: np.nan})
    with pytest.raises(ValueError, match="NaN"):
        pipeline_ajuste.predict_proba(entree)


def test_pipeline_complet_donne_un_score_par_collaborateur(
    pipeline_ajuste, reference_test_p4
):
    scores = pipeline_ajuste.predict_proba(reference_test_p4)[:, 1]
    assert scores.shape == (len(reference_test_p4),)
    assert ((scores >= 0) & (scores <= 1)).all()


def test_le_modele_recoit_les_46_features_nommees(pipeline_ajuste, metadonnees_p4):
    noms = pipeline_ajuste["modele"].feature_names_in_
    assert sorted(noms) == sorted(metadonnees_p4["features"])
