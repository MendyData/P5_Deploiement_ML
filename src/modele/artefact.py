"""Contrat de l'artefact : métadonnées enregistrées avec le pipeline et empreinte."""

import hashlib
import json
import platform
from dataclasses import asdict, dataclass
from importlib import metadata
from pathlib import Path
from typing import Self

from src import config


def empreinte_sha256(chemin: Path) -> str:
    """Calcule l'empreinte SHA-256 d'un fichier.

    Args:
        chemin: Fichier à lire.

    Returns:
        L'empreinte, en hexadécimal.
    """
    with chemin.open("rb") as fichier:
        return hashlib.file_digest(fichier, "sha256").hexdigest()


def versions_environnement() -> dict[str, str]:
    """Relève les versions de Python et des bibliothèques dont dépend l'artefact.

    Returns:
        La version de Python, puis celle de chaque bibliothèque de la configuration.
    """
    versions = {nom: metadata.version(nom) for nom in config.BIBLIOTHEQUES_ARTEFACT}
    return {"python": platform.python_version(), **versions}


@dataclass(frozen=True)
class MetadonneesArtefact:
    """Description de l'artefact, enregistrée à côté de lui au format JSON.

    Attributes:
        version_modele: Version du projet qui a entraîné le pipeline.
        date_entrainement: Date et heure de l'entraînement, en UTC (ISO 8601).
        seuil_decision: Seuil exact du P4 : un score au moins égal donne une alerte.
        colonnes_entree: Les 26 variables attendues pour chaque collaborateur.
        features: Les 46 colonnes reçues par le modèle, dans son ordre.
        versions: Versions de Python et des bibliothèques à l'entraînement.
        sha256: Empreinte du fichier de l'artefact.
        metriques_test: Métriques recalculées sur les collaborateurs du test du P4.
    """

    version_modele: str
    date_entrainement: str
    seuil_decision: float
    colonnes_entree: list[str]
    features: list[str]
    versions: dict[str, str]
    sha256: str
    metriques_test: dict[str, float]

    @classmethod
    def lire(cls, chemin: Path) -> Self:
        """Lit des métadonnées écrites par ecrire.

        Args:
            chemin: Fichier JSON des métadonnées.

        Returns:
            Les métadonnées du fichier.
        """
        return cls(**json.loads(chemin.read_text(encoding="utf-8")))

    def ecrire(self, chemin: Path) -> None:
        """Écrit les métadonnées en JSON lisible.

        Args:
            chemin: Fichier de destination.
        """
        texte = json.dumps(asdict(self), ensure_ascii=False, indent=2)
        # Fins de ligne LF, celles que le dépôt enregistre (.gitattributes).
        chemin.write_text(texte + "\n", encoding="utf-8", newline="\n")
