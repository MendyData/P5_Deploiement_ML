"""Schéma d'entrée de l'API : les 26 informations d'un collaborateur.

Les noms des champs et les modalités autorisées viennent de la configuration du
pipeline, fautes de frappe du jeu d'origine comprises : rien n'est recopié.
"""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src import config

# Types réutilisés par plusieurs champs.
Annees = Annotated[int, Field(ge=0, le=50)]
Satisfaction = Annotated[int, Field(ge=1, le=4, description="De 1 (faible) à 4.")]
Note = Annotated[int, Field(ge=1, le=4, description="De 1 à 4.")]
Compte = Annotated[int, Field(ge=0)]

# Modalités autorisées, lues dans la configuration du pipeline.
Genre = Literal[tuple(config.CATEGORIES_ORDINALES["genre"])]
HeuresSupplementaires = Literal[
    tuple(config.CATEGORIES_ORDINALES["heure_supplementaires"])
]
FrequenceDeplacement = Literal[
    tuple(config.CATEGORIES_ORDINALES["frequence_deplacement"])
]
Departement = Literal[tuple(config.CATEGORIES_NOMINALES["departement"])]
Poste = Literal[tuple(config.CATEGORIES_NOMINALES["poste"])]
StatutMarital = Literal[tuple(config.CATEGORIES_NOMINALES["statut_marital"])]
DomaineEtude = Literal[tuple(config.CATEGORIES_NOMINALES["domaine_etude"])]

# Exemple affiché dans Swagger et repris par les tests.
EXEMPLE: dict[str, int | str] = {
    "age": 31,
    "genre": "M",
    "revenu_mensuel": 11557,
    "statut_marital": "Divorcé(e)",
    "departement": "Commercial",
    "poste": "Senior Manager",
    "nombre_experiences_precedentes": 9,
    "annee_experience_totale": 10,
    "annees_dans_l_entreprise": 5,
    "annees_dans_le_poste_actuel": 4,
    "annees_depuis_la_derniere_promotion": 0,
    "annes_sous_responsable_actuel": 1,
    "satisfaction_employee_environnement": 3,
    "satisfaction_employee_nature_travail": 4,
    "satisfaction_employee_equipe": 3,
    "satisfaction_employee_equilibre_pro_perso": 2,
    "note_evaluation_precedente": 2,
    "note_evaluation_actuelle": 4,
    "heure_supplementaires": "Non",
    "augementation_salaire_precedente": 21,
    "nombre_participation_pee": 1,
    "nb_formations_suivies": 3,
    "distance_domicile_travail": 7,
    "niveau_education": 3,
    "domaine_etude": "Infra & Cloud",
    "frequence_deplacement": "Occasionnel",
}


class Collaborateur(BaseModel):
    """Les 26 informations d'un collaborateur, validées avant toute prédiction.

    Un champ manquant, inconnu, hors bornes ou d'une modalité non prévue est
    refusé : le modèle ne reçoit que des données qu'il sait traiter.
    """

    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": EXEMPLE})

    age: int = Field(ge=18, le=70, description="Âge, en années.")
    genre: Genre
    revenu_mensuel: int = Field(gt=0, description="Revenu mensuel brut.")
    statut_marital: StatutMarital
    departement: Departement
    poste: Poste
    nombre_experiences_precedentes: Compte
    annee_experience_totale: Annees
    annees_dans_l_entreprise: Annees
    annees_dans_le_poste_actuel: Annees
    annees_depuis_la_derniere_promotion: Annees
    annes_sous_responsable_actuel: Annees
    satisfaction_employee_environnement: Satisfaction
    satisfaction_employee_nature_travail: Satisfaction
    satisfaction_employee_equipe: Satisfaction
    satisfaction_employee_equilibre_pro_perso: Satisfaction
    note_evaluation_precedente: Note
    note_evaluation_actuelle: Note
    heure_supplementaires: HeuresSupplementaires
    augementation_salaire_precedente: int = Field(
        ge=0, le=100, description="Dernière augmentation, en pourcentage."
    )
    nombre_participation_pee: Compte
    nb_formations_suivies: Compte
    distance_domicile_travail: int = Field(ge=0, description="En kilomètres.")
    niveau_education: int = Field(ge=1, le=5, description="De 1 à 5.")
    domaine_etude: DomaineEtude
    frequence_deplacement: FrequenceDeplacement

    @model_validator(mode="after")
    def verifier_la_coherence_des_durees(self) -> Self:
        """Refuse des durées incompatibles entre elles ou avec l'âge.

        Returns:
            Le collaborateur, inchangé, quand ses durées sont cohérentes.

        Raises:
            ValueError: Si, par exemple, l'ancienneté dans le poste dépasse
                l'ancienneté dans l'entreprise, ou si l'expérience totale
                suppose une entrée dans la vie active avant 16 ans.
        """
        for courte, longue in config.COHERENCES_DUREES:
            if getattr(self, courte) > getattr(self, longue):
                message = f"{courte} ne peut pas dépasser {longue}."
                raise ValueError(message)
        if self.age - self.annee_experience_totale < config.AGE_MINIMUM_VIE_ACTIVE:
            message = (
                "annee_experience_totale suppose une entrée dans la vie active "
                f"avant {config.AGE_MINIMUM_VIE_ACTIVE} ans."
            )
            raise ValueError(message)
        return self
