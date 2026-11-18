"""Initialisation de la base : tables, rôle de l'API, droits et jeu de données."""

import logging

import pandas as pd
from psycopg import sql
from sqlalchemy import Connection, Engine, delete, func, insert, select, text
from sqlalchemy.orm import Session

from src import config
from src.bdd.modeles import Base, Collaborateur
from src.bdd.session import creer_moteur
from src.parametres import Parametres

journal = logging.getLogger(__name__)

# Droits du rôle de l'API : il lit, il ajoute des traces, mais il ne peut ni
# modifier ni supprimer une ligne.
DROITS_API: dict[str, str] = {
    "utilisateurs": "SELECT",
    "collaborateurs": "SELECT",
    "demandes": "SELECT, INSERT",
    "reponses": "SELECT, INSERT",
}


def _executer(connexion: Connection, modele: str, **parties: sql.Composable) -> None:
    """Exécute un ordre SQL dont les noms et les valeurs sont échappés par psycopg."""
    requete = sql.SQL(modele).format(**parties)
    connexion.exec_driver_sql(requete.as_string(connexion.connection.dbapi_connection))


def _creer_role_api(connexion: Connection, parametres: Parametres) -> None:
    """Crée le rôle de l'API, ou met à jour son mot de passe, puis fixe ses droits."""
    nom = parametres.postgres_api_user
    role = sql.Identifier(nom)
    mot_de_passe = sql.Literal(parametres.postgres_api_password)
    existe = connexion.scalar(
        text("SELECT 1 FROM pg_roles WHERE rolname = :nom"), {"nom": nom}
    )
    action = "ALTER" if existe else "CREATE"
    _executer(
        connexion,
        action + " ROLE {role} LOGIN PASSWORD {mot_de_passe}",
        role=role,
        mot_de_passe=mot_de_passe,
    )
    _executer(
        connexion,
        "GRANT CONNECT ON DATABASE {base} TO {role}",
        base=sql.Identifier(parametres.postgres_db),
        role=role,
    )
    _executer(connexion, "GRANT USAGE ON SCHEMA public TO {role}", role=role)
    # Les identifiants des demandes et des réponses sont tirés de séquences.
    _executer(
        connexion, "GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {role}", role=role
    )
    for table, droits in DROITS_API.items():
        _executer(
            connexion,
            "GRANT {droits} ON {table} TO {role}",
            droits=sql.SQL(droits),
            table=sql.Identifier(table),
            role=role,
        )


def creer_base(parametres: Parametres) -> None:
    """Crée les tables, leurs relations et le rôle de l'API.

    La fonction peut être relancée sans risque : une table qui existe est
    conservée avec ses données, et le rôle garde ses droits.

    Args:
        parametres: Paramètres de l'environnement, dont les deux rôles de la base.
    """
    moteur = creer_moteur(parametres.url_proprietaire)
    with moteur.begin() as connexion:
        Base.metadata.create_all(connexion)
        _creer_role_api(connexion, parametres)
    moteur.dispose()
    journal.info(
        "Base %s prête : %d tables, rôle %s.",
        parametres.postgres_db,
        len(Base.metadata.tables),
        parametres.postgres_api_user,
    )


def inserer_dataset(moteur: Engine, consolide: pd.DataFrame) -> int:
    """Remplace le contenu de la table collaborateurs par le jeu consolidé.

    Le vidage et l'insertion forment une seule transaction : en cas d'erreur, la
    table retrouve son contenu précédent.

    Args:
        moteur: Moteur connecté avec le rôle propriétaire.
        consolide: Jeu consolidé du projet 4, une ligne par collaborateur.

    Returns:
        Le nombre de lignes de la table après l'insertion.
    """
    colonnes = [config.IDENTIFIANT, *config.COLONNES_ENTREE]
    departs = consolide[config.CIBLE] == config.MODALITE_DEPART
    lignes = consolide[colonnes].assign(**{config.CIBLE: departs})
    with Session(moteur) as session, session.begin():
        session.execute(delete(Collaborateur))
        session.execute(insert(Collaborateur), lignes.to_dict(orient="records"))
        return session.scalar(select(func.count()).select_from(Collaborateur))
