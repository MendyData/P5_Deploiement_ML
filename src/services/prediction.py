"""Service de prédiction : du collaborateur validé à la réponse tracée de l'API."""

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from src import config
from src.bdd.modeles import Demande, Reponse
from src.modele.evaluation import probabilite_depart
from src.modele.explication import contributions
from src.modele.predicteur import PredicteurAttrition
from src.schemas.collaborateur import Collaborateur
from src.schemas.prediction import Facteur, Prediction

# Nombre de variables présentées dans la fiche RH.
NOMBRE_FACTEURS: int = 5

# Champs de la réponse qui se déduisent des autres : ils ne sont pas stockés.
CHAMPS_DEDUITS: set[str] = {"decision", "probabilite_maintien", "seuil_probabilite"}


class ServicePrediction:
    """Calcule la réponse de l'API pour un collaborateur et en garde la trace.

    Les routes ne manipulent jamais le modèle : elles passent par ce service, qui
    garde le prédicteur chargé au démarrage.

    Attributes:
        version_modele: Version du modèle chargé, lue dans ses métadonnées.
        seuil_probabilite: Seuil de décision exprimé en probabilité de départ.
    """

    def __init__(self, predicteur: PredicteurAttrition) -> None:
        """Garde le prédicteur chargé une seule fois, au démarrage de l'API.

        Args:
            predicteur: Prédicteur déjà vérifié et chargé.
        """
        self._predicteur = predicteur
        metadonnees = predicteur.metadonnees
        self.version_modele: str = metadonnees.version_modele
        self.seuil_probabilite: float = float(
            probabilite_depart(
                np.array([metadonnees.seuil_decision]),
                metadonnees.taux_depart_entrainement,
            )[0]
        )

    def predire(
        self, collaborateur: Collaborateur, utilisateur_id: int, session: Session
    ) -> Prediction:
        """Enregistre la demande, calcule la prédiction, puis enregistre la réponse.

        La demande est enregistrée avant tout calcul : si la base ne répond pas,
        l'erreur remonte et aucune prédiction n'est servie.

        Args:
            collaborateur: Les 26 informations, déjà validées par le schéma.
            utilisateur_id: Identifiant du client qui fait la demande.
            session: Session de la requête en cours.

        Returns:
            La réponse complète de POST /predict.
        """
        demande = Demande(**collaborateur.model_dump(), utilisateur_id=utilisateur_id)
        session.add(demande)
        session.commit()
        prediction = self.calculer(collaborateur)
        reponse = prediction.model_dump(exclude=CHAMPS_DEDUITS)
        session.add(Reponse(demande_id=demande.id, **reponse))
        session.commit()
        return prediction

    def calculer(self, collaborateur: Collaborateur) -> Prediction:
        """Calcule score, alerte, probabilité et fiche RH, sans rien enregistrer.

        Args:
            collaborateur: Les 26 informations, déjà validées par le schéma.

        Returns:
            La prédiction du modèle pour ce collaborateur.
        """
        donnees = pd.DataFrame([collaborateur.model_dump()])[config.COLONNES_ENTREE]
        resultat = self._predicteur.predire(donnees).iloc[0]
        alerte = bool(resultat[config.COL_ALERTE])
        probabilite = round(float(resultat[config.COL_PROBABILITE]), 4)
        return Prediction(
            score_risque=float(resultat[config.COL_SCORE]),
            alerte=alerte,
            decision="Risque de départ" if alerte else "Pas de risque détecté",
            probabilite_depart=probabilite,
            probabilite_maintien=round(1 - probabilite, 4),
            seuil_decision=self._predicteur.metadonnees.seuil_decision,
            seuil_probabilite=round(self.seuil_probabilite, 4),
            version_modele=self.version_modele,
            facteurs=self._facteurs(donnees),
        )

    def _facteurs(self, donnees: pd.DataFrame) -> list[Facteur]:
        """Retient les variables qui pèsent le plus dans le score, dans l'ordre."""
        parts = contributions(self._predicteur.pipeline, donnees).iloc[0]
        ordre = parts.abs().sort_values(ascending=False).index[:NOMBRE_FACTEURS]
        return [
            Facteur(
                variable=variable,
                contribution=round(float(parts[variable]), 4),
                effet="augmente le risque"
                if parts[variable] > 0
                else "réduit le risque",
            )
            for variable in ordre
        ]
