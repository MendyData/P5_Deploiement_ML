"""Explication d'un score : part de chaque variable dans le calcul du modèle."""

import numpy as np
import pandas as pd
from scipy.special import expit
from sklearn.pipeline import Pipeline

from src.modele.evaluation import probabilite_depart


def contributions(pipeline: Pipeline, collaborateurs: pd.DataFrame) -> pd.DataFrame:
    """Calcule la part de chaque variable dans le score de chaque collaborateur.

    La régression logistique additionne, pour chaque variable, son coefficient
    multiplié par sa valeur mise à l'échelle. Ces parts s'expriment en log-cote,
    le logarithme de score / (1 - score), et non en pourcentage. Une part positive
    pousse le score vers le départ, une part négative vers le maintien, par
    rapport à un collaborateur moyen. La somme des parts et de la constante du
    modèle, passée par la fonction logistique, redonne le score.

    Args:
        pipeline: Pipeline entraîné, terminé par la régression logistique.
        collaborateurs: Les 26 variables d'entrée, une ligne par collaborateur.

    Returns:
        Une ligne par collaborateur et une colonne par variable du modèle.
    """
    valeurs = pipeline[:-1].transform(collaborateurs)
    return valeurs * pipeline[-1].coef_[0]


def impacts_en_points(
    parts: pd.Series, constante: float, taux_depart: float
) -> pd.Series:
    """Traduit les parts d'un collaborateur en points de probabilité de départ.

    L'impact d'une variable est l'écart entre la probabilité de départ du
    collaborateur et celle qu'il aurait si cette variable valait la moyenne de
    l'entraînement (part nulle), toutes les autres restant inchangées. Les impacts
    ne s'additionnent pas : la fonction logistique n'est pas linéaire.

    Args:
        parts: Parts des variables pour un collaborateur, en log-cote.
        constante: Constante de la régression logistique.
        taux_depart: Part des départs dans les données d'entraînement.

    Returns:
        Pour chaque variable, son impact en points de pourcentage : positif, il
        augmente la probabilité de départ ; négatif, il la réduit.
    """
    log_cote = parts.sum() + constante
    probabilite = probabilite_depart(np.array([expit(log_cote)]), taux_depart)[0]
    sans_la_variable = probabilite_depart(
        expit(log_cote - parts.to_numpy()), taux_depart
    )
    return pd.Series(100 * (probabilite - sans_la_variable), index=parts.index)
