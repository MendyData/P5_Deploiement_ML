"""Paramètres de l'application, propres à chaque environnement d'exécution.

Les valeurs viennent des variables d'environnement, puis du fichier .env du poste
de développement. Aucune valeur sensible n'est écrite dans le code.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from src import config


class Parametres(BaseSettings):
    """Paramètres lus au démarrage et validés par Pydantic.

    Une variable d'environnement l'emporte sur le fichier .env. Une valeur hors
    de la liste autorisée arrête le démarrage avec un message explicite.

    Attributes:
        app_env: Environnement d'exécution : development sur le poste, test dans
            la CI et sur la branche staging, production pour une version livrée.
        log_level: Niveau de détail des journaux.
        api_key_hash: Empreinte SHA-256 de la clé d'API attendue. Vide, elle
            fait refuser toutes les requêtes authentifiées.
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
    api_key_hash: str = ""


@lru_cache
def obtenir_parametres() -> Parametres:
    """Lit les paramètres une seule fois, puis renvoie toujours le même objet.

    Returns:
        Les paramètres de l'environnement courant.
    """
    return Parametres()
