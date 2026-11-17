"""Règle de décision au seuil, probabilité de départ et métriques de test."""

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    fbeta_score,
    precision_score,
    recall_score,
)

from src import config


def appliquer_seuil(scores: np.ndarray, seuil: float) -> np.ndarray:
    """Transforme des scores de départ en alertes.

    Un score au moins égal au seuil donne une alerte : la borne est incluse, comme
    au P4.

    Args:
        scores: Scores de départ, entre 0 et 1.
        seuil: Seuil de décision.

    Returns:
        Pour chaque score, 1 en cas d'alerte de départ, 0 sinon.
    """
    return (scores >= seuil).astype(int)


def probabilite_depart(scores: np.ndarray, taux_depart: float) -> np.ndarray:
    """Convertit des scores en probabilités de départ, corrigées du rééquilibrage.

    Avec class_weight="balanced", le modèle apprend comme si départs et maintiens
    étaient aussi fréquents : ses scores supposent un taux de départ de 50 %. La
    cote du score (score / (1 - score)) est donc multipliée par la cote du vrai
    taux de départ (taux / (1 - taux)), puis reconvertie en probabilité. L'ordre
    des scores, donc l'alerte, ne change pas.

    Args:
        scores: Scores de départ du modèle, entre 0 et 1.
        taux_depart: Part des départs dans les données d'entraînement.

    Returns:
        La probabilité de départ estimée de chaque collaborateur, entre 0 et 1.
    """
    departs = scores * taux_depart
    maintiens = (1 - scores) * (1 - taux_depart)
    # Forme sans division par (1 - score) : un score de 1 reste une probabilité de 1.
    return departs / (departs + maintiens)


def calculer_metriques(
    departs: pd.Series, scores: np.ndarray, seuil: float
) -> dict[str, float]:
    """Calcule les métriques de test du P4 au seuil de décision.

    Args:
        departs: Départs observés : 1 pour un départ, 0 sinon.
        scores: Scores de départ du modèle, entre 0 et 1.
        seuil: Seuil de décision.

    Returns:
        L'accuracy, la précision, le rappel et le F2 des alertes au seuil, puis
        l'AUC-PR des scores, sous les noms des métadonnées du P4.
    """
    alertes = appliquer_seuil(scores, seuil)
    return {
        "accuracy": accuracy_score(departs, alertes),
        "precision": precision_score(departs, alertes, zero_division=0),
        "rappel": recall_score(departs, alertes),
        "f2": fbeta_score(departs, alertes, beta=config.BETA_F2),
        # Précision moyenne, comme au P4 : elle résume la courbe précision-rappel
        # sans dépendre du seuil.
        "auc_pr": average_precision_score(departs, scores),
    }
