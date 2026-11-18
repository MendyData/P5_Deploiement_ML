"""Schémas de sortie de l'API : prédiction, état du service et erreurs."""

from typing import Literal

from pydantic import BaseModel, Field


class Facteur(BaseModel):
    """Une variable du modèle et sa part dans le score du collaborateur."""

    variable: str = Field(description="Variable du modèle, après encodage.")
    contribution: float = Field(
        description="Part de la variable dans le score, en log-cote et non en "
        "pourcentage : positive, elle pousse vers le départ ; négative, vers le "
        "maintien."
    )
    impact_points: float = Field(
        description="La même part, en points de probabilité de départ : l'écart "
        "avec la probabilité qu'aurait le collaborateur si cette variable valait "
        "la moyenne. Les impacts de plusieurs variables ne s'additionnent pas."
    )
    effet: Literal["augmente le risque", "réduit le risque"]


class Prediction(BaseModel):
    """Réponse de POST /predict : score, alerte, probabilité et fiche RH."""

    score_risque: float = Field(
        ge=0,
        le=1,
        description="Score brut du modèle, de 0 à 1. Il classe les collaborateurs "
        "et déclenche l'alerte, mais ne se lit pas comme un pourcentage.",
    )
    alerte: bool = Field(description="Vrai quand le score atteint le seuil.")
    decision: Literal["Risque de départ", "Pas de risque détecté"] = Field(
        description="L'alerte, en clair pour les RH."
    )
    probabilite_depart: float = Field(
        ge=0,
        le=1,
        description="Probabilité estimée de départ : le score corrigé du "
        "rééquilibrage des classes de l'entraînement.",
    )
    probabilite_maintien: float = Field(
        ge=0, le=1, description="Probabilité estimée de maintien : 1 - départ."
    )
    lecture: str = Field(
        description="Les deux probabilités en pourcentages, pour les RH : "
        "maintien (classe 0) et départ (classe 1)."
    )
    seuil_decision: float = Field(
        description="Seuil du score à partir duquel l'alerte part."
    )
    seuil_probabilite: float = Field(
        description="Le même seuil, exprimé en probabilité de départ."
    )
    version_modele: str = Field(description="Version du modèle qui a calculé.")
    facteurs: list[Facteur] = Field(
        description="Fiche RH : les variables qui pèsent le plus dans ce score."
    )


class Sante(BaseModel):
    """Réponse de GET /health : le service, le modèle et la base répondent."""

    statut: Literal["ok"]
    environnement: str
    version_modele: str
    base_de_donnees: Literal["ok"]


class ErreurChamp(BaseModel):
    """Un champ refusé et la raison du refus, en français."""

    champ: str
    message: str


class ErreursValidation(BaseModel):
    """Réponse 422 : la liste des champs refusés."""

    detail: list[ErreurChamp]


class ErreurSimple(BaseModel):
    """Réponse 401 (clé refusée), 500 (erreur de la base) ou 503 (base injoignable)."""

    detail: str
