"""Tests du transformateur des features métier."""

import pandas as pd
import pytest

from src import config
from src.modele.features_metier import FeaturesMetier


def test_fit_renvoie_le_transformateur(collaborateur):
    transformateur = FeaturesMetier()
    assert transformateur.fit(collaborateur) is transformateur


@pytest.mark.parametrize(("experience", "attendu"), [(2, 1), (3, 0)])
def test_debut_de_carriere_jusqu_a_deux_ans_inclus(collaborateur, experience, attendu):
    entree = collaborateur.assign(**{config.COL_EXPERIENCE_TOTALE: experience})
    sortie = FeaturesMetier().fit_transform(entree)
    assert sortie[config.COL_DEBUT_DE_CARRIERE].iloc[0] == attendu


@pytest.mark.parametrize(("anciennete", "attendu"), [(0, 1), (1, 0)])
def test_nouveau_responsable_seulement_a_zero_an(collaborateur, anciennete, attendu):
    entree = collaborateur.assign(**{config.COL_SOUS_RESPONSABLE_ACTUEL: anciennete})
    sortie = FeaturesMetier().fit_transform(entree)
    assert sortie[config.COL_NOUVEAU_RESPONSABLE].iloc[0] == attendu


@pytest.mark.parametrize("colonne_basse", config.COLONNES_SATISFACTION)
def test_satisfaction_minimale_prend_la_plus_basse_des_quatre(
    collaborateur, colonne_basse
):
    satisfactions = dict.fromkeys(config.COLONNES_SATISFACTION, 4) | {colonne_basse: 1}
    sortie = FeaturesMetier().fit_transform(collaborateur.assign(**satisfactions))
    assert sortie[config.COL_SATISFACTION_MINIMALE].iloc[0] == 1


def test_features_identiques_a_celles_du_p4_sur_les_cas_limites(cas_limites):
    entree = cas_limites.drop(columns=config.FEATURES_METIER)
    sortie = FeaturesMetier().fit_transform(entree)
    pd.testing.assert_frame_equal(
        sortie[config.FEATURES_METIER], cas_limites[config.FEATURES_METIER]
    )


def test_entree_non_modifiee(collaborateur):
    copie = collaborateur.copy()
    FeaturesMetier().fit_transform(collaborateur)
    pd.testing.assert_frame_equal(collaborateur, copie)


def test_fonctionne_sans_cible_ni_identifiant(collaborateur):
    sortie = FeaturesMetier().fit_transform(collaborateur)
    assert list(sortie.columns) == [*config.COLONNES_ENTREE, *config.FEATURES_METIER]


@pytest.mark.parametrize(
    "colonne",
    [
        *config.COLONNES_SATISFACTION,
        config.COL_EXPERIENCE_TOTALE,
        config.COL_SOUS_RESPONSABLE_ACTUEL,
    ],
)
def test_erreur_nommant_la_colonne_source_absente(collaborateur, colonne):
    with pytest.raises(ValueError, match=colonne):
        FeaturesMetier().fit_transform(collaborateur.drop(columns=colonne))
