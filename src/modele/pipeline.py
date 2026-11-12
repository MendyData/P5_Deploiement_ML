"""Assemblage du pipeline complet : features métier, encodage, échelle et modèle."""

from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from src import config
from src.modele.features_metier import FeaturesMetier


class ConstructeurPipeline:
    """Assemble, d'après la configuration, le pipeline qui reproduit le modèle du P4.

    Le pipeline enchaîne les features métier, l'encodage en 46 colonnes, la mise à
    l'échelle et la régression logistique. La sortie pandas est réglée sur
    l'encodage et la mise à l'échelle : les noms des 46 colonnes suivent ainsi
    jusqu'au modèle.
    """

    def pretraitement(self) -> Pipeline:
        """Construit la préparation des données : features métier, puis encodage.

        Une modalité inconnue lève une erreur au lieu d'être encodée en zéros, et
        les colonnes qui ne sont pas des entrées du modèle sont ignorées.

        Returns:
            Un pipeline non ajusté qui produit les 46 colonnes du P4, en entiers
            comme dans le X du P4.
        """
        encodage = ColumnTransformer(
            [
                (
                    "ordinales",
                    OrdinalEncoder(
                        categories=list(config.CATEGORIES_ORDINALES.values()),
                        handle_unknown="error",
                        dtype=int,
                    ),
                    list(config.CATEGORIES_ORDINALES),
                ),
                (
                    "nominales",
                    OneHotEncoder(
                        categories=list(config.CATEGORIES_NOMINALES.values()),
                        handle_unknown="error",
                        sparse_output=False,
                        dtype=int,
                    ),
                    list(config.CATEGORIES_NOMINALES),
                ),
                (
                    "numeriques",
                    "passthrough",
                    [*config.COLONNES_NUMERIQUES, *config.FEATURES_METIER],
                ),
            ],
            remainder="drop",
            verbose_feature_names_out=False,
        )
        return Pipeline(
            [
                ("features_metier", FeaturesMetier()),
                ("encodage", encodage.set_output(transform="pandas")),
            ]
        )

    def construire(self) -> Pipeline:
        """Construit le pipeline complet, prêt à être entraîné.

        Une valeur numérique manquante traverse la préparation, puis la régression
        logistique la refuse en levant une erreur.

        Returns:
            Un pipeline non ajusté : préparation, mise à l'échelle, puis modèle.
        """
        return Pipeline(
            [
                ("pretraitement", self.pretraitement()),
                ("echelle", StandardScaler().set_output(transform="pandas")),
                ("modele", LogisticRegression(**config.HYPERPARAMETRES)),
            ]
        )
