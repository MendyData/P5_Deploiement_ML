"""Règle de décision au seuil et métriques de test, définies comme au P4."""

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
