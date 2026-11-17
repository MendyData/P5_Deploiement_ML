"""Tests du schéma d'entrée : références acceptées, données invalides refusées."""

import pytest
from pydantic import ValidationError

from src import config
from src.schemas.collaborateur import EXEMPLE, Collaborateur


def test_champs_du_schema_identiques_aux_colonnes_du_pipeline():
    assert set(Collaborateur.model_fields) == set(config.COLONNES_ENTREE)


def test_exemple_de_swagger_valide():
    assert Collaborateur(**EXEMPLE).model_dump() == EXEMPLE


@pytest.mark.parametrize("jeu", ["reference_test_p4", "cas_limites"])
def test_collaborateurs_de_reference_tous_acceptes(jeu, request):
    collaborateurs = request.getfixturevalue(jeu)[config.COLONNES_ENTREE]

    for ligne in collaborateurs.to_dict(orient="records"):
        Collaborateur(**ligne)


@pytest.mark.parametrize(
    ("champ", "valeur"),
    [
        ("age", 17),
        ("age", "trente"),
        ("revenu_mensuel", 0),
        ("satisfaction_employee_equipe", 5),
        ("niveau_education", 6),
        ("genre", "X"),
        ("poste", "Astronaute"),
        ("frequence_deplacement", "Souvent"),
    ],
)
def test_valeur_hors_domaine_refusee(champ, valeur):
    with pytest.raises(ValidationError) as erreur:
        Collaborateur(**{**EXEMPLE, champ: valeur})

    assert erreur.value.errors()[0]["loc"] == (champ,)


def test_champ_manquant_refuse():
    incomplet = {cle: valeur for cle, valeur in EXEMPLE.items() if cle != "age"}

    with pytest.raises(ValidationError, match="age"):
        Collaborateur(**incomplet)


def test_champ_inconnu_refuse():
    with pytest.raises(ValidationError, match="salaire"):
        Collaborateur(**EXEMPLE, salaire=3000)


@pytest.mark.parametrize(
    ("courte", "longue"),
    [
        ("annees_dans_le_poste_actuel", "annees_dans_l_entreprise"),
        ("annees_depuis_la_derniere_promotion", "annees_dans_l_entreprise"),
        ("annes_sous_responsable_actuel", "annees_dans_l_entreprise"),
    ],
)
def test_duree_superieure_a_celle_qui_la_contient_refusee(courte, longue):
    incoherent = {**EXEMPLE, courte: EXEMPLE[longue] + 1}

    with pytest.raises(ValidationError, match="ne peut pas dépasser"):
        Collaborateur(**incoherent)
