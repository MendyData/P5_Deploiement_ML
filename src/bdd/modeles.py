"""Tables de la base : utilisateurs, jeu de données, demandes et réponses."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    func,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src import config


class Base(DeclarativeBase):
    """Classe de base : elle recense les tables à créer."""


def colonnes_collaborateur() -> list[Column]:
    """Construit les 26 colonnes d'un collaborateur d'après la configuration.

    Les colonnes numériques sont des entiers obligatoires. Les colonnes de
    catégories n'acceptent que les modalités connues du pipeline.

    Returns:
        De nouvelles colonnes à chaque appel : une colonne n'appartient qu'à
        une seule table.
    """
    numeriques = [
        Column(nom, Integer, nullable=False) for nom in config.COLONNES_NUMERIQUES
    ]
    categories = {**config.CATEGORIES_ORDINALES, **config.CATEGORIES_NOMINALES}
    textes = [
        Column(
            nom,
            Text,
            CheckConstraint(
                f"{nom} IN ({', '.join(repr(modalite) for modalite in modalites)})",
                name=f"{nom}_modalites",
            ),
            nullable=False,
        )
        for nom, modalites in categories.items()
    ]
    return [*numeriques, *textes]


class Utilisateur(Base):
    """Client autorisé à appeler l'API : seule l'empreinte de sa clé est stockée."""

    __tablename__ = "utilisateurs"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(Text, unique=True)
    empreinte_cle: Mapped[str] = mapped_column(String(64), unique=True)
    actif: Mapped[bool] = mapped_column(server_default=true())
    cree_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Collaborateur(Base):
    """Jeu de données du projet 4 : une ligne par collaborateur, avec son départ."""

    # Les 26 colonnes viennent de la configuration : la table est donc décrite
    # avec Table, qui accepte une liste de colonnes construite par le code.
    __table__ = Table(
        "collaborateurs",
        Base.metadata,
        Column(config.IDENTIFIANT, Integer, primary_key=True, autoincrement=False),
        *colonnes_collaborateur(),
        Column(config.CIBLE, Boolean, nullable=False),
    )


class Demande(Base):
    """Données reçues par POST /predict, enregistrées avant tout calcul."""

    __table__ = Table(
        "demandes",
        Base.metadata,
        Column("id", Integer, primary_key=True),
        # L'index sur la date sert aux recherches par période, les plus fréquentes.
        Column(
            "recue_le",
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            index=True,
        ),
        Column(
            "utilisateur_id", ForeignKey("utilisateurs.id"), nullable=False, index=True
        ),
        *colonnes_collaborateur(),
    )


class Reponse(Base):
    """Prédiction renvoyée par l'API, reliée à la demande qui l'a produite."""

    __tablename__ = "reponses"
    __table_args__ = (
        CheckConstraint("score_risque BETWEEN 0 AND 1", name="score_entre_0_et_1"),
        CheckConstraint(
            "probabilite_depart BETWEEN 0 AND 1", name="probabilite_entre_0_et_1"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # unique : une demande n'a qu'une seule réponse.
    demande_id: Mapped[int] = mapped_column(ForeignKey("demandes.id"), unique=True)
    score_risque: Mapped[float]
    alerte: Mapped[bool]
    # Le chiffre communiqué aux RH : le score corrigé du rééquilibrage.
    probabilite_depart: Mapped[float]
    seuil_decision: Mapped[float]
    version_modele: Mapped[str] = mapped_column(Text)
    facteurs: Mapped[list[dict]] = mapped_column(JSONB)
    calculee_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
