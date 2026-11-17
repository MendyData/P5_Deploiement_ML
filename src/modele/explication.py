"""Explication d'un score : part de chaque variable dans le calcul du modèle."""

import pandas as pd
from sklearn.pipeline import Pipeline


def contributions(pipeline: Pipeline, collaborateurs: pd.DataFrame) -> pd.DataFrame:
    """Calcule la part de chaque variable dans le score de chaque collaborateur.

    La régression logistique additionne, pour chaque variable, son coefficient
    multiplié par sa valeur mise à l'échelle. Une part positive pousse le score
    vers le départ, une part négative vers le maintien, par rapport à un
    collaborateur moyen. La somme des parts et de la constante du modèle redonne
    le score, avant sa conversion en probabilité.

    Args:
        pipeline: Pipeline entraîné, terminé par la régression logistique.
        collaborateurs: Les 26 variables d'entrée, une ligne par collaborateur.

    Returns:
        Une ligne par collaborateur et une colonne par variable du modèle.
    """
    valeurs = pipeline[:-1].transform(collaborateurs)
    return valeurs * pipeline[-1].coef_[0]
