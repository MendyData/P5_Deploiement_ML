"""Tests du schéma d'entrée : références acceptées, données invalides refusées."""

import pandas as pd
import pytest
from pydantic import ValidationError

from src import config
from src.schemas.collaborateur import EXEMPLE, Collaborateur


def test_champs_du_schema_identiques_aux_colonnes_du_pipeline():
    assert set(Collaborateur.model_fields) == set(config.COLONNES_ENTREE)


def test_chaque_nombre_a_une_borne_haute():
    proprietes = Collaborateur.model_json_schema()["properties"]

    sans_borne = [
        nom
        for nom, propriete in proprietes.items()
        if propriete.get("type") == "integer" and "maximum" not in propriete
    ]

    assert sans_borne == []


@pytest.mark.lent
def test_les_1470_collaborateurs_du_projet_4_respectent_les_bornes():
    if not config.FICHIER_CONSOLIDE.exists():
        pytest.skip("Jeu consolidé absent : lancer scripts/generer_reference_p4.py.")
    consolide = pd.read_csv(config.FICHIER_CONSOLIDE)

    for ligne in consolide[config.COLONNES_ENTREE].to_dict(orient="records"):
        Collaborateur(**ligne)


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
        ("age", None),
        ("age", "trente"),
        ("revenu_mensuel", 0),
        ("revenu_mensuel", 50_001),
        ("revenu_mensuel", 3_000_000_000),
        ("nombre_experiences_precedentes", 21),
        ("nombre_participation_pee", 11),
        ("nb_formations_suivies", 21),
        ("distance_domicile_travail", 201),
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


@pytest.mark.parametrize(("courte", "longue"), config.COHERENCES_DUREES)
def test_duree_superieure_a_celle_qui_la_contient_refusee(courte, longue):
    incoherent = {**EXEMPLE, courte: EXEMPLE[longue] + 1}

    with pytest.raises(ValidationError, match="ne peut pas dépasser"):
        Collaborateur(**incoherent)


def test_entree_dans_la_vie_active_avant_16_ans_refusee():
    # 20 ans et 5 ans d'expérience : une entrée dans la vie active à 15 ans.
    incoherent = {**EXEMPLE, "age": 20, "annee_experience_totale": 5}

    with pytest.raises(ValidationError, match="avant 16 ans"):
        Collaborateur(**incoherent)


def test_entree_dans_la_vie_active_a_16_ans_acceptee():
    limite = {**EXEMPLE, "age": 26, "annee_experience_totale": 10}

    assert Collaborateur(**limite).age == 26
