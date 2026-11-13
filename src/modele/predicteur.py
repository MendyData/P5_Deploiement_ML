"""Chargement vérifié de l'artefact et prédiction du risque de départ."""

import logging
from pathlib import Path

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline

from src import config
from src.modele.artefact import (
    MetadonneesArtefact,
    empreinte_sha256,
    versions_environnement,
)
from src.modele.evaluation import appliquer_seuil

journal = logging.getLogger(__name__)


class ArtefactInvalide(Exception):
    """L'artefact diffère de ses métadonnées ou de l'environnement d'entraînement."""


class PredicteurAttrition:
    """Charge l'artefact une seule fois, après vérification, puis prédit le risque.

    joblib exécute du code en chargeant un fichier : l'empreinte et les versions
    sont donc comparées aux métadonnées avant tout chargement. Un prédicteur est
    prévu pour être créé une fois, au démarrage de l'API, puis réutilisé.

    Attributes:
        metadonnees: Métadonnées de l'artefact chargé, seuil de décision compris.
        pipeline: Pipeline entraîné, de l'entrée consolidée au score.
    """

    def __init__(
        self,
        chemin_artefact: Path = config.FICHIER_ARTEFACT,
        chemin_metadonnees: Path = config.FICHIER_METADONNEES,
    ) -> None:
        """Vérifie l'artefact, puis le charge.

        Args:
            chemin_artefact: Fichier joblib du pipeline entraîné.
            chemin_metadonnees: Fichier JSON écrit avec l'artefact.

        Raises:
            ArtefactInvalide: Si l'empreinte du fichier ou la version d'une
                bibliothèque diffère des métadonnées.
        """
        self.metadonnees: MetadonneesArtefact = MetadonneesArtefact.lire(
            chemin_metadonnees
        )
        self._verifier_empreinte(chemin_artefact)
        self._verifier_versions()
        self.pipeline: Pipeline = joblib.load(chemin_artefact)
        journal.info(
            "Artefact vérifié et chargé : modèle %s entraîné le %s.",
            self.metadonnees.version_modele,
            self.metadonnees.date_entrainement,
        )

    def _verifier_empreinte(self, chemin_artefact: Path) -> None:
        """Refuse un fichier dont l'empreinte diffère de celle des métadonnées."""
        if empreinte_sha256(chemin_artefact) != self.metadonnees.sha256:
            message = (
                f"Empreinte de {chemin_artefact.name} différente de celle des "
                "métadonnées : fichier modifié ou issu d'un autre entraînement."
            )
            raise ArtefactInvalide(message)

    def _verifier_versions(self) -> None:
        """Refuse un environnement dont une bibliothèque diffère de l'entraînement.

        La version de Python reste informative : un autre correctif de Python 3.11
        ne change pas le calcul du pipeline.
        """
        attendues = self.metadonnees.versions
        installees = versions_environnement()
        ecarts = [
            f"{nom} {attendues[nom]} attendue, {installees[nom]} installée"
            for nom in config.BIBLIOTHEQUES_ARTEFACT
            if installees[nom] != attendues[nom]
        ]
        if ecarts:
            message = f"Versions différentes de l'entraînement : {' ; '.join(ecarts)}."
            raise ArtefactInvalide(message)

    def predire(self, collaborateurs: pd.DataFrame) -> pd.DataFrame:
        """Calcule le score de risque et l'alerte de chaque collaborateur.

        Args:
            collaborateurs: Les 26 variables d'entrée, une ligne par collaborateur.

        Returns:
            Le score de risque, entre 0 et 1, et l'alerte : 1 si le score atteint
            le seuil des métadonnées, 0 sinon. L'index reçu est conservé.
        """
        scores = self.pipeline.predict_proba(collaborateurs)[:, 1]
        alertes = appliquer_seuil(scores, self.metadonnees.seuil_decision)
        return pd.DataFrame(
            {config.COL_SCORE: scores, config.COL_ALERTE: alertes},
            index=collaborateurs.index,
        )
