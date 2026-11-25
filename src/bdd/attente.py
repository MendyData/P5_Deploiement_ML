"""Attente de la base au démarrage de l'API : des essais espacés, en nombre borné.

Au démarrage, la base peut ne pas répondre encore : conteneur Docker en cours de
lancement, rôle de l'API pas encore créé par l'initialisation. Plutôt que de
démarrer une API qui répondrait 503, ou de boucler sans fin, l'API retente la
connexion quelques fois, puis s'arrête avec un message explicite.
"""

import logging
import time
from dataclasses import dataclass

from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError

journal = logging.getLogger(__name__)


class BaseInjoignable(RuntimeError):
    """La base n'a accepté aucune connexion dans le nombre d'essais autorisé."""


@dataclass(frozen=True)
class AttenteBase:
    """Attend que la base accepte une connexion, avant la première requête.

    Seule OperationalError est rattrapée : elle signale une base arrêtée, en
    cours de démarrage, ou un rôle pas encore créé, des situations qui se
    règlent d'elles-mêmes. Toute autre erreur, comme un pilote absent ou une
    adresse mal formée, remonte dès le premier essai : la retenter ne
    changerait rien.

    Attributes:
        moteur: Moteur de l'API, celui qui servira ensuite les requêtes.
        tentatives: Nombre maximal d'essais, au moins un.
        pause: Pause, en secondes, entre deux essais.
    """

    moteur: Engine
    tentatives: int
    pause: float

    @property
    def adresse(self) -> str:
        """Adresse de la base, mot de passe masqué : elle peut entrer au journal."""
        return self.moteur.url.render_as_string(hide_password=True)

    def attendre(self) -> None:
        """Retente la connexion jusqu'à ce que la base réponde.

        Raises:
            BaseInjoignable: Si aucun essai n'a abouti.
        """
        for essai in range(1, self.tentatives + 1):
            if self._essayer(essai):
                return
            # Aucune pause après le dernier essai : l'échec est déjà connu.
            if essai < self.tentatives:
                time.sleep(self.pause)
        raise BaseInjoignable(
            f"Base {self.adresse} injoignable après {self.tentatives} essais : "
            "l'API ne démarre pas."
        )

    def _essayer(self, essai: int) -> bool:
        """Ouvre une connexion et exécute SELECT 1, comme la route /health.

        Args:
            essai: Numéro de l'essai, à partir de 1, repris dans le journal.

        Returns:
            True si la base a répondu, False si elle reste injoignable.
        """
        try:
            with self.moteur.connect() as connexion:
                connexion.execute(text("SELECT 1"))
        except OperationalError as erreur:
            # erreur.orig : le message de psycopg seul, sans la requête ni le
            # lien de documentation que SQLAlchemy ajoute autour.
            journal.warning(
                "Base injoignable, essai %d sur %d : %s",
                essai,
                self.tentatives,
                erreur.orig,
            )
            return False
        journal.info(
            "Base %s joignable, essai %d sur %d.", self.adresse, essai, self.tentatives
        )
        return True
