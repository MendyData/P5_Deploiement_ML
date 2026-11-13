"""Entraînement du pipeline complet sur le découpage du P4 et sauvegarde."""

import logging
from datetime import UTC, datetime
from importlib import metadata

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline

from src import config
from src.modele.artefact import (
    MetadonneesArtefact,
    empreinte_sha256,
    versions_environnement,
)
from src.modele.evaluation import calculer_metriques
from src.modele.pipeline import ConstructeurPipeline

journal = logging.getLogger(__name__)


class EntraineurPipeline:
    """Entraîne le pipeline complet comme le modèle final du P4, puis le sauvegarde.

    L'ajustement porte sur les collaborateurs d'entraînement puis de validation du
    découpage du P4, dans cet ordre ; ceux du test ne servent qu'aux métriques
    enregistrées avec l'artefact.

    Attributes:
        consolide: Jeu consolidé, indexé par identifiant de collaborateur.
        decoupage: Identifiants des collaborateurs de chaque jeu du découpage.
    """

    def __init__(
        self, consolide: pd.DataFrame, decoupage: dict[str, list[int]]
    ) -> None:
        """Prépare l'entraînement à partir des données du P4.

        Args:
            consolide: Jeu consolidé, une ligne par collaborateur, identifiant et
                cible compris.
            decoupage: Identifiants des collaborateurs, par nom de jeu.
        """
        self.consolide: pd.DataFrame = consolide.set_index(config.IDENTIFIANT)
        self.decoupage: dict[str, list[int]] = decoupage

    def jeu(self, noms: list[str]) -> tuple[pd.DataFrame, pd.Series]:
        """Réunit les collaborateurs des jeux nommés, dans l'ordre du découpage.

        Args:
            noms: Jeux du découpage, dans l'ordre voulu.

        Returns:
            Les 26 variables d'entrée et les départs : 1 pour un départ, 0 sinon.
        """
        identifiants = [ident for nom in noms for ident in self.decoupage[nom]]
        collaborateurs = self.consolide.loc[identifiants]
        departs = (collaborateurs[config.CIBLE] == config.MODALITE_DEPART).astype(int)
        return collaborateurs[config.COLONNES_ENTREE], departs

    def entrainer(self) -> Pipeline:
        """Ajuste le pipeline complet sur l'entraînement et la validation.

        Returns:
            Le pipeline ajusté.
        """
        entrees, departs = self.jeu(config.JEUX_ENTRAINEMENT)
        pipeline = ConstructeurPipeline().construire().fit(entrees, departs)
        journal.info("Pipeline ajusté sur %d collaborateurs.", len(entrees))
        return pipeline

    def evaluer(self, pipeline: Pipeline) -> dict[str, float]:
        """Recalcule les métriques du P4 sur les collaborateurs du test.

        Args:
            pipeline: Pipeline ajusté.

        Returns:
            Les métriques de test, au seuil de décision du P4.
        """
        entrees, departs = self.jeu([config.JEU_TEST])
        scores = pipeline.predict_proba(entrees)[:, 1]
        metriques = calculer_metriques(departs, scores, config.SEUIL_DECISION)
        journal.info("Métriques de test : %s", metriques)
        return metriques

    def sauvegarder(self, pipeline: Pipeline) -> None:
        """Écrit l'artefact, puis ses métadonnées, aux emplacements de la configuration.

        Les métadonnées portent l'empreinte de l'artefact écrit et les métriques
        recalculées sur le test.

        Args:
            pipeline: Pipeline ajusté.
        """
        joblib.dump(pipeline, config.FICHIER_ARTEFACT)
        metadonnees = MetadonneesArtefact(
            version_modele=metadata.version(config.NOM_PROJET),
            date_entrainement=datetime.now(UTC).isoformat(timespec="seconds"),
            seuil_decision=config.SEUIL_DECISION,
            colonnes_entree=config.COLONNES_ENTREE,
            features=pipeline["modele"].feature_names_in_.tolist(),
            versions=versions_environnement(),
            sha256=empreinte_sha256(config.FICHIER_ARTEFACT),
            metriques_test=self.evaluer(pipeline),
        )
        metadonnees.ecrire(config.FICHIER_METADONNEES)
        journal.info(
            "Artefact écrit dans %s, empreinte %s.",
            config.FICHIER_ARTEFACT,
            metadonnees.sha256,
        )
