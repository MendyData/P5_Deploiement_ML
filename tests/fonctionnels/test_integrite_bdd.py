"""Tests d'intégrité de la base : types, présence, contraintes, cohérence et droits."""

import pytest
from sqlalchemy import delete, func, insert, inspect, select, text, update
from sqlalchemy.exc import DataError, IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from src.api.securite import creer_utilisateur
from src.bdd.modeles import Collaborateur, Demande, Reponse, Utilisateur
from src.bdd.session import creer_moteur
from src.schemas.collaborateur import EXEMPLE

REPONSE = {
    "score_risque": 0.25,
    "alerte": False,
    "probabilite_depart": 0.06,
    "seuil_decision": 0.418,
    "version_modele": "0.1.0",
    "facteurs": [],
}


@pytest.fixture
def utilisateur_id(session_bdd):
    """Identifiant d'un client enregistré dans la base de test."""
    creer_utilisateur(session_bdd, "client-de-test")
    return session_bdd.scalars(select(Utilisateur.id)).one()


@pytest.fixture
def demande(session_bdd, utilisateur_id):
    """Demande valide, enregistrée dans la base de test."""
    demande = Demande(**EXEMPLE, utilisateur_id=utilisateur_id)
    session_bdd.add(demande)
    session_bdd.commit()
    return demande


@pytest.fixture
def session_api(parametres_bdd, session_bdd):
    """Session ouverte avec le rôle de l'API, aux droits limités."""
    moteur = creer_moteur(parametres_bdd.url_api)
    with Session(moteur) as session:
        yield session
    moteur.dispose()


def compter(session, table):
    return session.scalar(select(func.count()).select_from(table))


# --- Typage et présence -----------------------------------------------------


@pytest.mark.parametrize(
    ("table", "colonne", "type_attendu"),
    [
        ("demandes", "age", "INTEGER"),
        ("demandes", "poste", "TEXT"),
        ("demandes", "recue_le", "TIMESTAMP"),
        ("reponses", "score_risque", "DOUBLE PRECISION"),
        ("reponses", "alerte", "BOOLEAN"),
        ("reponses", "probabilite_depart", "DOUBLE PRECISION"),
        ("reponses", "facteurs", "JSONB"),
        ("utilisateurs", "empreinte_cle", "VARCHAR(64)"),
        ("collaborateurs", "a_quitte_l_entreprise", "BOOLEAN"),
    ],
)
def test_colonne_creee_avec_le_type_attendu(session_bdd, table, colonne, type_attendu):
    colonnes = inspect(session_bdd.get_bind()).get_columns(table)
    types = {description["name"]: str(description["type"]) for description in colonnes}

    assert types[colonne] == type_attendu


def test_aucune_colonne_n_accepte_une_valeur_absente(session_bdd):
    inspecteur = inspect(session_bdd.get_bind())

    facultatives = [
        f"{table}.{colonne['name']}"
        for table in inspecteur.get_table_names()
        for colonne in inspecteur.get_columns(table)
        if colonne["nullable"]
    ]

    assert facultatives == []


def test_valeur_du_mauvais_type_refusee(session_bdd, utilisateur_id):
    ligne = {**EXEMPLE, "age": "trente", "utilisateur_id": utilisateur_id}

    with pytest.raises(DataError):
        session_bdd.execute(insert(Demande), ligne)


# --- Contraintes et clés ----------------------------------------------------


@pytest.mark.parametrize(
    "modification",
    [
        {"poste": None},
        {"age": None},
        {"poste": "Astronaute"},
        {"genre": "X"},
        {"utilisateur_id": 999999},
    ],
    ids=[
        "poste absent",
        "age absent",
        "poste inconnu",
        "genre inconnu",
        "client inconnu",
    ],
)
def test_demande_invalide_refusee_par_la_base(
    session_bdd, utilisateur_id, modification
):
    ligne = {**EXEMPLE, "utilisateur_id": utilisateur_id, **modification}

    with pytest.raises(IntegrityError):
        session_bdd.execute(insert(Demande), ligne)


@pytest.mark.parametrize(
    "modification",
    [
        {"annees_dans_le_poste_actuel": 6, "annees_dans_l_entreprise": 5},
        {"annees_depuis_la_derniere_promotion": 6, "annees_dans_l_entreprise": 5},
        {"annes_sous_responsable_actuel": 6, "annees_dans_l_entreprise": 5},
        {"annees_dans_l_entreprise": 11, "annee_experience_totale": 10},
        {"revenu_mensuel": 0},
        {"age": 20, "annee_experience_totale": 5},
    ],
    ids=[
        "poste plus long que l'ancienneté",
        "promotion plus ancienne que l'arrivée",
        "responsable plus ancien que l'arrivée",
        "ancienneté plus longue que l'expérience",
        "revenu nul",
        "entrée dans la vie active à 15 ans",
    ],
)
def test_demande_incoherente_refusee_par_la_base(
    session_bdd, utilisateur_id, modification
):
    ligne = {**EXEMPLE, "utilisateur_id": utilisateur_id, **modification}

    with pytest.raises(IntegrityError, match="check constraint"):
        session_bdd.execute(insert(Demande), ligne)


@pytest.mark.parametrize("table", ["collaborateurs", "demandes"])
def test_regles_de_coherence_dans_les_deux_tables(session_bdd, table):
    contraintes = inspect(session_bdd.get_bind()).get_check_constraints(table)
    noms = {contrainte["name"] for contrainte in contraintes}

    assert {
        "annees_dans_le_poste_actuel_coherente",
        "annees_depuis_la_derniere_promotion_coherente",
        "annes_sous_responsable_actuel_coherente",
        "annees_dans_l_entreprise_coherente",
        "revenu_mensuel_positif",
        "age_entree_vie_active",
    } <= noms


@pytest.mark.parametrize("valeur", [-0.1, 1.5])
@pytest.mark.parametrize("colonne", ["score_risque", "probabilite_depart"])
def test_score_ou_probabilite_hors_de_zero_a_un_refuse(
    session_bdd, demande, colonne, valeur
):
    ligne = {**REPONSE, "demande_id": demande.id, colonne: valeur}

    with pytest.raises(IntegrityError):
        session_bdd.execute(insert(Reponse), ligne)


def test_reponse_sans_demande_refusee(session_bdd):
    with pytest.raises(IntegrityError):
        session_bdd.execute(insert(Reponse), {**REPONSE, "demande_id": 999999})


def test_seconde_reponse_a_la_meme_demande_refusee(session_bdd, demande):
    session_bdd.execute(insert(Reponse), {**REPONSE, "demande_id": demande.id})

    with pytest.raises(IntegrityError):
        session_bdd.execute(insert(Reponse), {**REPONSE, "demande_id": demande.id})


def test_deux_clients_du_meme_nom_refuses(session_bdd, utilisateur_id):
    with pytest.raises(IntegrityError):
        creer_utilisateur(session_bdd, "client-de-test")


# --- Insertion et suppression -----------------------------------------------


def test_demande_et_reponse_inserees_puis_relues(session_bdd, demande):
    session_bdd.add(Reponse(**REPONSE, demande_id=demande.id))
    session_bdd.commit()

    relue = session_bdd.scalars(select(Demande)).one()
    reponse = session_bdd.scalars(select(Reponse)).one()
    assert {champ: getattr(relue, champ) for champ in EXEMPLE} == EXEMPLE
    assert relue.recue_le.tzinfo is not None
    assert reponse.demande_id == relue.id
    assert reponse.facteurs == []


def test_demande_qui_a_une_reponse_ne_peut_pas_etre_supprimee(session_bdd, demande):
    session_bdd.add(Reponse(**REPONSE, demande_id=demande.id))
    session_bdd.commit()

    with pytest.raises(IntegrityError):
        session_bdd.execute(delete(Demande))


def test_proprietaire_supprime_la_reponse_puis_la_demande(session_bdd, demande):
    session_bdd.add(Reponse(**REPONSE, demande_id=demande.id))
    session_bdd.commit()

    session_bdd.execute(delete(Reponse))
    session_bdd.execute(delete(Demande))
    session_bdd.commit()

    assert compter(session_bdd, Reponse) == 0
    assert compter(session_bdd, Demande) == 0


# --- Droits du rôle de l'API ------------------------------------------------


def test_role_api_lit_les_quatre_tables(session_api):
    for table in (Collaborateur, Utilisateur, Demande, Reponse):
        assert compter(session_api, table) == 0


def test_role_api_ajoute_une_demande_et_sa_reponse(session_api, utilisateur_id):
    demande = Demande(**EXEMPLE, utilisateur_id=utilisateur_id)
    session_api.add(demande)
    session_api.commit()
    session_api.add(Reponse(**REPONSE, demande_id=demande.id))
    session_api.commit()

    assert compter(session_api, Demande) == 1
    assert compter(session_api, Reponse) == 1


@pytest.mark.parametrize(
    "ordre",
    [
        delete(Demande),
        delete(Reponse),
        delete(Collaborateur),
        update(Demande).values(age=99),
        update(Reponse).values(score_risque=0),
        update(Utilisateur).values(actif=False),
        insert(Utilisateur).values(nom="intrus", empreinte_cle="0" * 64),
        text("TRUNCATE demandes CASCADE"),
        text("DROP TABLE reponses"),
    ],
    ids=[
        "supprimer des demandes",
        "supprimer des réponses",
        "supprimer le jeu de données",
        "modifier une demande",
        "modifier une réponse",
        "désactiver un client",
        "créer un client",
        "vider une table",
        "supprimer une table",
    ],
)
def test_role_api_ne_peut_ni_modifier_ni_supprimer(session_api, ordre):
    with pytest.raises(ProgrammingError, match=r"permission denied|must be owner"):
        session_api.execute(ordre)
