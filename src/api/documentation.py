"""Textes et exemples de la documentation interactive : Swagger (/docs) et ReDoc.

Les 26 champs de POST /predict viennent des trois extraits RH du projet 4, une
fois joints pour un même collaborateur. Cette page explique ce passage, pour
qu'une demande puisse être écrite à la main à partir des fichiers d'origine.
La répartition des champs par extrait est contrôlée par les tests : elle couvre
exactement les entrées du modèle déclarées dans la configuration.
"""

from dataclasses import dataclass

from src.schemas.collaborateur import EXEMPLE


@dataclass(frozen=True)
class ExtraitRH:
    """Un extrait RH d'origine et sa place dans une demande.

    Attributes:
        fichier: Nom du fichier CSV fourni.
        cle: Colonne qui identifie le collaborateur, avec un exemple de valeur.
        champs: Colonnes reprises telles quelles dans la demande.
        a_retirer: Colonnes à ne pas envoyer : clé, cible ou variables écartées.
    """

    fichier: str
    cle: str
    champs: tuple[str, ...]
    a_retirer: tuple[str, ...]


EXTRAITS_RH: tuple[ExtraitRH, ...] = (
    ExtraitRH(
        fichier="extrait_sirh.csv",
        cle="id_employee (1)",
        champs=(
            "age",
            "genre",
            "revenu_mensuel",
            "statut_marital",
            "departement",
            "poste",
            "nombre_experiences_precedentes",
            "annee_experience_totale",
            "annees_dans_l_entreprise",
            "annees_dans_le_poste_actuel",
        ),
        a_retirer=("id_employee", "nombre_heures_travailless"),
    ),
    ExtraitRH(
        fichier="extrait_eval.csv",
        cle="eval_number (E_1)",
        champs=(
            "satisfaction_employee_environnement",
            "satisfaction_employee_nature_travail",
            "satisfaction_employee_equipe",
            "satisfaction_employee_equilibre_pro_perso",
            "note_evaluation_precedente",
            "note_evaluation_actuelle",
            "heure_supplementaires",
            "augementation_salaire_precedente",
        ),
        a_retirer=("eval_number", "niveau_hierarchique_poste"),
    ),
    ExtraitRH(
        fichier="extrait_sondage.csv",
        cle="code_sondage (000001)",
        champs=(
            "nombre_participation_pee",
            "nb_formations_suivies",
            "distance_domicile_travail",
            "niveau_education",
            "domaine_etude",
            "frequence_deplacement",
            "annees_depuis_la_derniere_promotion",
            "annes_sous_responsable_actuel",
        ),
        a_retirer=(
            "code_sondage",
            "a_quitte_l_entreprise",
            "nombre_employee_sous_responsabilite",
            "ayant_enfants",
        ),
    ),
)


def _code(noms: tuple[str, ...]) -> str:
    """Met chaque nom de colonne en forme de code, séparé par des virgules."""
    return ", ".join(f"`{nom}`" for nom in noms)


def _tableau_extraits() -> str:
    """Construit le tableau Markdown de correspondance entre extraits et champs."""
    lignes = [
        "| Extrait | Clé du collaborateur | Champs à reprendre | À ne pas envoyer |",
        "| --- | --- | --- | --- |",
    ]
    lignes += [
        f"| `{extrait.fichier}` | {extrait.cle} | {_code(extrait.champs)} "
        f"| {_code(extrait.a_retirer)} |"
        for extrait in EXTRAITS_RH
    ]
    return "\n".join(lignes)


DESCRIPTION_PREDICT: str = f"""
Renvoie le score, l'alerte, la probabilité de départ et leurs explications.

### Construire une demande à partir des extraits RH d'origine

Un collaborateur occupe une ligne dans chacun des trois extraits. Les trois clés
désignent la même personne : `id_employee` 1, `eval_number` E_1 et
`code_sondage` 000001 correspondent au collaborateur 1.

{_tableau_extraits()}

| Règle | Détail |
| --- | --- |
| Conversion | `augementation_salaire_precedente` est écrite `"11 %"` dans \
`extrait_eval.csv` : envoyer le nombre seul, `11` |
| Variables calculées | `satisfaction_minimale`, `nouveau_responsable` et \
`debut_de_carriere` sont calculées par le modèle : ne pas les envoyer |
| Champ en trop | Une colonne absente de la liste des 26 champs est refusée (422) |
| Noms des champs | Ceux des extraits, fautes de frappe comprises \
(`annes_sous_responsable_actuel`) |

Les exemples « Collaborateur 1 » et « Collaborateur 2 » ci-dessous sont les deux
premières lignes des extraits, ainsi assemblées.
"""

# Exemples proposés dans la liste déroulante de Swagger et affichés par ReDoc.
EXEMPLES_PREDICT: dict[str, dict[str, object]] = {
    "reference": {
        "summary": "Exemple de référence",
        "value": EXEMPLE,
    },
    "collaborateur_1": {
        "summary": "Collaborateur 1 des extraits RH (départ observé)",
        "description": "Ligne 1 de chacun des trois extraits, assemblée.",
        "value": {
            "age": 41,
            "genre": "F",
            "revenu_mensuel": 5993,
            "statut_marital": "Célibataire",
            "departement": "Commercial",
            "poste": "Cadre Commercial",
            "nombre_experiences_precedentes": 8,
            "annee_experience_totale": 8,
            "annees_dans_l_entreprise": 6,
            "annees_dans_le_poste_actuel": 4,
            "annees_depuis_la_derniere_promotion": 0,
            "annes_sous_responsable_actuel": 5,
            "satisfaction_employee_environnement": 2,
            "satisfaction_employee_nature_travail": 4,
            "satisfaction_employee_equipe": 1,
            "satisfaction_employee_equilibre_pro_perso": 1,
            "note_evaluation_precedente": 3,
            "note_evaluation_actuelle": 3,
            "heure_supplementaires": "Oui",
            "augementation_salaire_precedente": 11,
            "nombre_participation_pee": 0,
            "nb_formations_suivies": 0,
            "distance_domicile_travail": 1,
            "niveau_education": 2,
            "domaine_etude": "Infra & Cloud",
            "frequence_deplacement": "Occasionnel",
        },
    },
    "collaborateur_2": {
        "summary": "Collaborateur 2 des extraits RH (resté)",
        "description": "Ligne 2 de chacun des trois extraits, assemblée.",
        "value": {
            "age": 49,
            "genre": "M",
            "revenu_mensuel": 5130,
            "statut_marital": "Marié(e)",
            "departement": "Consulting",
            "poste": "Assistant de Direction",
            "nombre_experiences_precedentes": 1,
            "annee_experience_totale": 10,
            "annees_dans_l_entreprise": 10,
            "annees_dans_le_poste_actuel": 7,
            "annees_depuis_la_derniere_promotion": 1,
            "annes_sous_responsable_actuel": 7,
            "satisfaction_employee_environnement": 3,
            "satisfaction_employee_nature_travail": 2,
            "satisfaction_employee_equipe": 4,
            "satisfaction_employee_equilibre_pro_perso": 3,
            "note_evaluation_precedente": 2,
            "note_evaluation_actuelle": 4,
            "heure_supplementaires": "Non",
            "augementation_salaire_precedente": 23,
            "nombre_participation_pee": 1,
            "nb_formations_suivies": 3,
            "distance_domicile_travail": 8,
            "niveau_education": 1,
            "domaine_etude": "Infra & Cloud",
            "frequence_deplacement": "Frequent",
        },
    },
}
