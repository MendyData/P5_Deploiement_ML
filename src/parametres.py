"""Paramètres de l'application, propres à chaque environnement d'exécution.

Les valeurs viennent des variables d'environnement, puis du fichier .env du poste
de développement. Aucune valeur sensible n'est écrite dans le code.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

from src import config


class Parametres(BaseSettings):
    """Paramètres lus au démarrage et validés par Pydantic.

    Une variable d'environnement l'emporte sur le fichier .env. Une valeur hors
    de la liste autorisée arrête le démarrage avec un message explicite.

    Attributes:
        app_env: Environnement d'exécution : development sur le poste, test dans
            la CI et sur la branche staging, production pour une version livrée.
        log_level: Niveau de détail des journaux.
        postgres_host: Machine qui héberge PostgreSQL.
        postgres_port: Port de PostgreSQL vu depuis le poste : 5433 pour la base
            Docker, 5432 dans les conteneurs et dans la CI, qui le fixent.
        postgres_db: Nom de la base.
        postgres_user: Rôle propriétaire : il crée les tables et insère le jeu
            de données.
        postgres_password: Mot de passe du rôle propriétaire.
        postgres_api_user: Rôle de l'API, aux droits limités.
        postgres_api_password: Mot de passe du rôle de l'API.
    """

    model_config = SettingsConfigDict(
        env_file=config.RACINE_PROJET / ".env",
        env_file_encoding="utf-8",
        # Le fichier .env peut contenir des variables lues ailleurs : elles sont
        # ignorées ici au lieu de provoquer une erreur.
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    # 127.0.0.1 plutôt que localhost : sous Windows, localhost essaie d'abord
    # l'adresse IPv6, sur laquelle Docker ne publie pas la base.
    postgres_host: str = "127.0.0.1"
    # 5433 : port publié par Docker Compose, le 5432 du poste étant pris par le
    # PostgreSQL installé sous Windows.
    postgres_port: int = 5433
    postgres_db: str = "p5"
    postgres_user: str = "proprietaire"
    postgres_password: str = ""
    postgres_api_user: str = "api"
    postgres_api_password: str = ""

    def _url(self, role: str, mot_de_passe: str) -> URL:
        """Construit l'adresse de la base pour un rôle donné."""
        return URL.create(
            "postgresql+psycopg",
            username=role,
            password=mot_de_passe,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )

    @property
    def url_proprietaire(self) -> URL:
        """Adresse de la base pour le rôle propriétaire (scripts d'initialisation)."""
        return self._url(self.postgres_user, self.postgres_password)

    @property
    def url_api(self) -> URL:
        """Adresse de la base pour le rôle de l'API, aux droits limités."""
        return self._url(self.postgres_api_user, self.postgres_api_password)


@lru_cache
def obtenir_parametres() -> Parametres:
    """Lit les paramètres une seule fois, puis renvoie toujours le même objet.

    Returns:
        Les paramètres de l'environnement courant.
    """
    return Parametres()
