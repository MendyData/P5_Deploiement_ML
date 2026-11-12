"""Génère les fichiers de référence du P4 utilisés par les tests de non-régression.

Le script s'exécute avec l'environnement du P4, seul à recharger de façon fiable
le modèle final (même version de scikit-learn que lors de sa sauvegarde) :

    uv run --no-sync --project <P4> python scripts/generer_reference_p4.py <P4>

Il lit le P4 sans le modifier et écrit dans le P5 : les références des tests dans
tests/fixtures/, le découpage à côté de l'artefact dans models/, et les données
complètes, non suivies par Git, dans data/interim/.
Il n'importe aucun module du paquet src : la référence reste ainsi indépendante
du code qu'elle sert à tester, ce qui explique les quelques noms de colonnes
repris ici.
"""

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline

journal = logging.getLogger(__name__)

RACINE_P5 = Path(__file__).resolve().parents[1]
DOSSIER_FIXTURES = RACINE_P5 / "tests" / "fixtures"
FICHIER_DECOUPAGE_P5 = RACINE_P5 / "models" / "identifiants_decoupage.json"
DOSSIER_INTERIM_P5 = RACINE_P5 / "data" / "interim"
FICHIER_CONSOLIDE_P5 = DOSSIER_INTERIM_P5 / "consolide.csv"
FICHIER_X_P5 = DOSSIER_INTERIM_P5 / "x_p4.csv"

# Emplacements relatifs à la racine du dépôt du P4.
CONSOLIDE_P4 = Path("data", "interim", "consolide.parquet")
X_P4 = Path("data", "processed", "X.parquet")
Y_P4 = Path("data", "processed", "y.parquet")
DECOUPAGE_P4 = Path("data", "processed", "split_indices.json")
MODELE_P4 = Path("models", "modele_final.joblib")
METADONNEES_P4 = Path("models", "metadonnees_modele.json")

# Vocabulaire du P4, repris tel quel, fautes de frappe comprises.
IDENTIFIANT = "id_employee"
CIBLE = "a_quitte_l_entreprise"
MODALITE_DEPART = "Oui"
COLONNE_Y = "depart"
JEU_TEST = "test"
SCORE_P4 = "score_p4"
FEATURES_METIER = ["satisfaction_minimale", "nouveau_responsable", "debut_de_carriere"]

# Valeurs de part et d'autre des seuils des features métier.
BORNES = {"annee_experience_totale": (2, 3), "annes_sous_responsable_actuel": (0, 1)}

# 17 chiffres significatifs : chaque score se relit à l'identique.
FORMAT_REEL = "%.17g"


@dataclass(frozen=True)
class DonneesP4:
    """Données et artefacts du P4 nécessaires à la référence.

    Attributes:
        consolide: Jeu consolidé, une ligne par collaborateur, dans l'ordre de X.
        x: Les 46 colonnes encodées du P4.
        y: Cible binaire du P4, 1 pour un départ.
        decoupage: Positions des lignes de chaque jeu, par nom de jeu.
        metadonnees: Métadonnées du modèle final du P4.
        modele: Modèle final du P4 (mise à l'échelle et régression logistique).
    """

    consolide: pd.DataFrame
    x: pd.DataFrame
    y: pd.Series
    decoupage: dict[str, list[int]]
    metadonnees: dict[str, object]
    modele: Pipeline


def lire_json(chemin: Path) -> dict:
    """Lit un fichier JSON encodé en UTF-8.

    Args:
        chemin: Fichier à lire.

    Returns:
        Le contenu du fichier.
    """
    return json.loads(chemin.read_text(encoding="utf-8"))


def charger_p4(racine_p4: Path) -> DonneesP4:
    """Charge les données, les métadonnées et le modèle final du P4.

    Args:
        racine_p4: Racine du dépôt du P4.

    Returns:
        Les données et le modèle du P4.
    """
    decoupage = lire_json(racine_p4 / DECOUPAGE_P4)
    return DonneesP4(
        consolide=pd.read_parquet(racine_p4 / CONSOLIDE_P4),
        x=pd.read_parquet(racine_p4 / X_P4),
        y=pd.read_parquet(racine_p4 / Y_P4)[COLONNE_Y],
        decoupage={nom.removeprefix("index_"): pos for nom, pos in decoupage.items()},
        metadonnees=lire_json(racine_p4 / METADONNEES_P4),
        modele=joblib.load(racine_p4 / MODELE_P4),
    )


def verifier_alignement(donnees: DonneesP4) -> None:
    """Vérifie que X, y et le jeu consolidé décrivent les mêmes lignes.

    Les positions du découpage ne se traduisent en identifiants que si ces trois
    tables partagent le même ordre de collaborateurs.

    Args:
        donnees: Données du P4.

    Raises:
        ValueError: Si une colonne numérique commune ou la cible diffère.
    """
    numeriques = donnees.consolide.select_dtypes("number")
    communes = numeriques.columns.intersection(donnees.x.columns)
    if not numeriques[communes].equals(donnees.x[communes]):
        message = "X et le jeu consolidé du P4 ne sont pas alignés ligne à ligne."
        raise ValueError(message)
    departs = (donnees.consolide[CIBLE] == MODALITE_DEPART).astype(donnees.y.dtype)
    if not departs.equals(donnees.y):
        message = "y et la cible du jeu consolidé du P4 ne concordent pas."
        raise ValueError(message)


def identifiants_par_jeu(donnees: DonneesP4) -> dict[str, list[int]]:
    """Traduit les positions du découpage du P4 en identifiants de collaborateurs.

    Args:
        donnees: Données du P4, alignées ligne à ligne.

    Returns:
        Les identifiants de chaque jeu : entraînement, validation et test.
    """
    identifiants = donnees.consolide[IDENTIFIANT]
    return {
        jeu: identifiants.iloc[positions].tolist()
        for jeu, positions in donnees.decoupage.items()
    }


def reference_test(donnees: DonneesP4) -> pd.DataFrame:
    """Rassemble les collaborateurs du test et le score du modèle final du P4.

    Args:
        donnees: Données du P4.

    Returns:
        Les valeurs brutes du jeu consolidé, cible comprise, et le score du P4.
    """
    positions = donnees.decoupage[JEU_TEST]
    scores = donnees.modele.predict_proba(donnees.x.iloc[positions])[:, 1]
    return donnees.consolide.iloc[positions].assign(**{SCORE_P4: scores})


def x_par_identifiant(donnees: DonneesP4) -> pd.DataFrame:
    """Indexe les 46 colonnes encodées du P4 par identifiant de collaborateur.

    Args:
        donnees: Données du P4, alignées ligne à ligne.

    Returns:
        Le X complet du P4, indexé par identifiant.
    """
    identifiants = pd.Index(donnees.consolide[IDENTIFIANT], name=IDENTIFIANT)
    return donnees.x.set_axis(identifiants)


def conditions_a_couvrir(
    reference: pd.DataFrame, consolide: pd.DataFrame
) -> dict[str, pd.Series]:
    """Décrit les situations que les cas limites doivent couvrir.

    Chaque borne des features métier et chaque modalité de chaque variable
    qualitative du jeu consolidé doivent apparaître au moins une fois.

    Args:
        reference: Collaborateurs du test, valeurs brutes.
        consolide: Jeu consolidé complet, source des modalités.

    Returns:
        Un masque sur les collaborateurs du test par situation, indexé par sa
        description.
    """
    conditions = {
        f"{colonne} = {valeur}": reference[colonne] == valeur
        for colonne, valeurs in BORNES.items()
        for valeur in valeurs
    }
    qualitatives = consolide.drop(columns=CIBLE).select_dtypes(exclude="number")
    conditions.update(
        {
            f"{colonne} = {modalite}": reference[colonne] == modalite
            for colonne in qualitatives
            for modalite in sorted(qualitatives[colonne].unique())
        }
    )
    return conditions


def selectionner_cas_limites(
    reference: pd.DataFrame, conditions: dict[str, pd.Series]
) -> pd.DataFrame:
    """Retient peu de collaborateurs, couvrant toutes les situations demandées.

    Un collaborateur n'est ajouté que si aucun collaborateur déjà retenu ne
    couvre la situation examinée.

    Args:
        reference: Collaborateurs du test.
        conditions: Masques des situations à couvrir.

    Returns:
        Les collaborateurs retenus.

    Raises:
        ValueError: Si aucun collaborateur du test ne couvre une situation.
    """
    retenus = pd.Series(False, index=reference.index)
    for description, masque in conditions.items():
        if not masque.any():
            message = f"Aucun collaborateur du test ne couvre « {description} »."
            raise ValueError(message)
        if not (masque & retenus).any():
            retenus[masque.idxmax()] = True
    return reference[retenus]


def cas_limites(donnees: DonneesP4, reference: pd.DataFrame) -> pd.DataFrame:
    """Construit les cas limites des features métier et leurs valeurs attendues.

    Args:
        donnees: Données du P4 ; les valeurs attendues viennent de X.
        reference: Collaborateurs du test, valeurs brutes et score.

    Returns:
        Les valeurs brutes des collaborateurs retenus et les trois features
        métier calculées par le P4.
    """
    conditions = conditions_a_couvrir(reference, donnees.consolide)
    retenus = selectionner_cas_limites(reference, conditions)
    attendus = donnees.x.loc[retenus.index, FEATURES_METIER]
    return retenus.drop(columns=[CIBLE, SCORE_P4]).join(attendus)


def ecrire_csv(table: pd.DataFrame, chemin: Path, *, avec_index: bool = False) -> None:
    """Écrit une table en CSV UTF-8, avec des fins de ligne LF.

    Args:
        table: Table à écrire.
        chemin: Fichier de destination.
        avec_index: Écrit aussi l'index de la table.
    """
    table.to_csv(
        chemin, index=avec_index, float_format=FORMAT_REEL, lineterminator="\n"
    )


def ecrire_json(contenu: object, chemin: Path) -> None:
    """Écrit un objet en JSON indenté UTF-8, avec des fins de ligne LF.

    Args:
        contenu: Objet sérialisable en JSON.
        chemin: Fichier de destination.
    """
    texte = json.dumps(contenu, ensure_ascii=False, indent=2)
    chemin.write_text(texte + "\n", encoding="utf-8", newline="\n")


def ecrire_reference(donnees: DonneesP4) -> pd.DataFrame:
    """Écrit les références des tests, le découpage et les données complètes du P4.

    Args:
        donnees: Données du P4, alignées ligne à ligne.

    Returns:
        Les collaborateurs du test et leur score.
    """
    DOSSIER_FIXTURES.mkdir(parents=True, exist_ok=True)
    DOSSIER_INTERIM_P5.mkdir(parents=True, exist_ok=True)
    reference = reference_test(donnees)
    x = x_par_identifiant(donnees)
    ecrire_json(identifiants_par_jeu(donnees), FICHIER_DECOUPAGE_P5)
    ecrire_json(donnees.metadonnees, DOSSIER_FIXTURES / "metadonnees_p4.json")
    ecrire_csv(reference, DOSSIER_FIXTURES / "reference_test_p4.csv")
    ecrire_csv(
        x.iloc[donnees.decoupage[JEU_TEST]],
        DOSSIER_FIXTURES / "reference_x_test_p4.csv",
        avec_index=True,
    )
    ecrire_csv(cas_limites(donnees, reference), DOSSIER_FIXTURES / "cas_limites.csv")
    ecrire_csv(donnees.consolide, FICHIER_CONSOLIDE_P5)
    ecrire_csv(x, FICHIER_X_P5, avec_index=True)
    return reference


def main() -> None:
    """Lit le chemin du P4 et produit les fichiers de référence."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parseur = argparse.ArgumentParser(description="Génère la référence du P4.")
    parseur.add_argument("racine_p4", type=Path, help="Racine du dépôt du P4.")
    donnees = charger_p4(parseur.parse_args().racine_p4)
    verifier_alignement(donnees)
    reference = ecrire_reference(donnees)
    departs = int((reference[CIBLE] == MODALITE_DEPART).sum())
    journal.info(
        "Référence écrite dans %s : %d collaborateurs du test, dont %d départs.",
        DOSSIER_FIXTURES,
        len(reference),
        departs,
    )


if __name__ == "__main__":
    main()
