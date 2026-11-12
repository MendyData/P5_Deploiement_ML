"""Configuration du pipeline d'inférence : source unique des colonnes et des valeurs.

Les noms de colonnes et les modalités sont ceux du jeu consolidé du P4, fautes de
frappe comprises (annes, augementation), pour garder la traçabilité avec le modèle
d'origine. Le schéma de l'API réutilisera ces listes sans les recopier.
"""

from pathlib import Path

# Emplacements, relatifs à la racine du projet.
RACINE_PROJET: Path = Path(__file__).resolve().parents[1]
DOSSIER_MODELES: Path = RACINE_PROJET / "models"
FICHIER_CONSOLIDE: Path = RACINE_PROJET / "data" / "interim" / "consolide.csv"
FICHIER_ARTEFACT: Path = DOSSIER_MODELES / "pipeline_attrition.joblib"
FICHIER_METADONNEES: Path = DOSSIER_MODELES / "pipeline_attrition.json"
FICHIER_DECOUPAGE: Path = DOSSIER_MODELES / "identifiants_decoupage.json"

# Identifiant et cible du jeu consolidé : aucun des deux n'entre dans le modèle.
IDENTIFIANT: str = "id_employee"
CIBLE: str = "a_quitte_l_entreprise"
MODALITE_DEPART: str = "Oui"

# Colonnes d'entrée qui servent aussi au calcul des features métier.
COLONNES_SATISFACTION: list[str] = [
    "satisfaction_employee_environnement",
    "satisfaction_employee_nature_travail",
    "satisfaction_employee_equipe",
    "satisfaction_employee_equilibre_pro_perso",
]
COL_EXPERIENCE_TOTALE: str = "annee_experience_totale"
COL_SOUS_RESPONSABLE_ACTUEL: str = "annes_sous_responsable_actuel"

# Colonnes numériques transmises telles quelles au modèle.
COLONNES_NUMERIQUES: list[str] = [
    "age",
    "revenu_mensuel",
    "nombre_experiences_precedentes",
    COL_EXPERIENCE_TOTALE,
    "annees_dans_l_entreprise",
    "annees_dans_le_poste_actuel",
    "annees_depuis_la_derniere_promotion",
    COL_SOUS_RESPONSABLE_ACTUEL,
    *COLONNES_SATISFACTION,
    "note_evaluation_precedente",
    "note_evaluation_actuelle",
    "augementation_salaire_precedente",
    "nombre_participation_pee",
    "nb_formations_suivies",
    "distance_domicile_travail",
    "niveau_education",
]

# Correspondances du P4 : le rang d'une modalité dans sa liste donne son code
# (F vaut 0 et M vaut 1 ; Aucun vaut 0, Occasionnel 1 et Frequent 2).
CATEGORIES_ORDINALES: dict[str, list[str]] = {
    "genre": ["F", "M"],
    "heure_supplementaires": ["Non", "Oui"],
    "frequence_deplacement": ["Aucun", "Occasionnel", "Frequent"],
}

# Variables encodées en une colonne par modalité, dans l'ordre des colonnes du P4.
# Les modalités sont celles du jeu consolidé du P4, triées comme pd.get_dummies.
CATEGORIES_NOMINALES: dict[str, list[str]] = {
    "departement": ["Commercial", "Consulting", "Ressources Humaines"],
    "poste": [
        "Assistant de Direction",
        "Cadre Commercial",
        "Consultant",
        "Directeur Technique",
        "Manager",
        "Représentant Commercial",
        "Ressources Humaines",
        "Senior Manager",
        "Tech Lead",
    ],
    "statut_marital": ["Célibataire", "Divorcé(e)", "Marié(e)"],
    "domaine_etude": [
        "Autre",
        "Entrepreunariat",
        "Infra & Cloud",
        "Marketing",
        "Ressources Humaines",
        "Transformation Digitale",
    ],
}

# Les 26 variables attendues pour chaque collaborateur.
COLONNES_ENTREE: list[str] = [
    *COLONNES_NUMERIQUES,
    *CATEGORIES_ORDINALES,
    *CATEGORIES_NOMINALES,
]

# Features métier ajoutées par FeaturesMetier, comme au P4.
SEUIL_DEBUT_DE_CARRIERE: int = 2  # années d'expérience totale, borne incluse
COL_SATISFACTION_MINIMALE: str = "satisfaction_minimale"
COL_NOUVEAU_RESPONSABLE: str = "nouveau_responsable"
COL_DEBUT_DE_CARRIERE: str = "debut_de_carriere"
FEATURES_METIER: list[str] = [
    COL_SATISFACTION_MINIMALE,
    COL_NOUVEAU_RESPONSABLE,
    COL_DEBUT_DE_CARRIERE,
]

# Régression logistique pondérée du P4 ; les autres paramètres gardent leur valeur
# par défaut dans scikit-learn 1.9.1.
RANDOM_STATE: int = 42
HYPERPARAMETRES: dict[str, float | int | str] = {
    "C": 1.0,
    "class_weight": "balanced",
    "max_iter": 2000,
    "random_state": RANDOM_STATE,
}

# Seuil de décision du P4 : le plus haut qui atteint un rappel hors pli de 0,80,
# car un départ manqué coûte plus cher qu'une fausse alerte.
SEUIL_DECISION: float = 0.41811496025861317

# Le F2 du P4 compte le rappel deux fois plus que la précision, pour la même raison.
BETA_F2: int = 2

# Découpage du P4 : son modèle final a été ajusté sur l'entraînement puis la
# validation, dans cet ordre ; le test sert seulement aux métriques.
JEUX_ENTRAINEMENT: list[str] = ["entrainement", "validation"]
JEU_TEST: str = "test"

# Métadonnées de l'artefact : la version du projet installé devient celle du
# modèle, et les versions de ces bibliothèques sont relevées, car un pipeline
# sérialisé ne se recharge de façon sûre qu'avec les mêmes.
NOM_PROJET: str = "p5-deploiement-ml"
BIBLIOTHEQUES_ARTEFACT: list[str] = ["scikit-learn", "pandas", "numpy"]

# Colonnes de sortie du prédicteur, reprises dans la réponse de l'API.
COL_SCORE: str = "score_risque"
COL_ALERTE: str = "alerte"
