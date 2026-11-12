"""Transformateur des trois features métier du P4."""

from typing import Self

import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

from src import config

# Colonnes lues dans la configuration, jamais déduites des colonnes reçues : une
# colonne absente lève une erreur au lieu de fausser le calcul.
COLONNES_SOURCES: list[str] = [
    *config.COLONNES_SATISFACTION,
    config.COL_SOUS_RESPONSABLE_ACTUEL,
    config.COL_EXPERIENCE_TOTALE,
]


# Le mixin précède BaseEstimator : c'est l'ordre dans lequel scikit-learn
# reconnaît un transformateur.
class FeaturesMetier(TransformerMixin, BaseEstimator):
    """Ajoute les trois features métier du P4 à une copie des données reçues.

    - satisfaction_minimale : la plus basse des quatre satisfactions ;
    - nouveau_responsable : 1 si l'ancienneté sous le responsable actuel est de
      0 an, 0 sinon ;
    - debut_de_carriere : 1 si l'expérience totale ne dépasse pas le seuil de la
      configuration, 0 sinon.

    Chaque ligne se calcule seule : fit n'apprend rien. Les autres colonnes, cible
    ou identifiant compris, sont transmises telles quelles sans être exigées. La
    sortie est déjà un DataFrame dont les colonnes suivent celles reçues : la classe
    ne définit pas get_feature_names_out, pour que set_output ne les renomme jamais
    d'après les colonnes vues pendant fit.
    """

    def fit(self, X: pd.DataFrame, y: pd.Series | None = None) -> Self:
        """Renvoie le transformateur tel quel : il n'y a rien à apprendre.

        Args:
            X: Collaborateurs, un par ligne.
            y: Ignoré, accepté pour la compatibilité avec Pipeline.

        Returns:
            Le transformateur lui-même.
        """
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Calcule les features métier sans modifier les données reçues.

        Args:
            X: Collaborateurs, un par ligne, avec au moins les colonnes sources.

        Returns:
            Une copie de X complétée par les trois features métier.

        Raises:
            ValueError: Si une colonne source est absente ; le message la nomme.
        """
        absentes = [colonne for colonne in COLONNES_SOURCES if colonne not in X.columns]
        if absentes:
            message = (
                f"Colonnes absentes pour les features métier : {', '.join(absentes)}."
            )
            raise ValueError(message)
        sortie = X.copy()
        # Une satisfaction manquante rend le minimum inconnu, au lieu de le calculer
        # sur les trois autres.
        sortie[config.COL_SATISFACTION_MINIMALE] = X[config.COLONNES_SATISFACTION].min(
            axis=1, skipna=False
        )
        sortie[config.COL_NOUVEAU_RESPONSABLE] = (
            X[config.COL_SOUS_RESPONSABLE_ACTUEL] == 0
        ).astype(int)
        sortie[config.COL_DEBUT_DE_CARRIERE] = (
            X[config.COL_EXPERIENCE_TOTALE] <= config.SEUIL_DEBUT_DE_CARRIERE
        ).astype(int)
        return sortie
