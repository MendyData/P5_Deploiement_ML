"""Génère une clé d'API et son empreinte.

La clé est remise au client. Seule l'empreinte est conservée, dans la variable
API_KEY_HASH du fichier .env ou d'un environnement GitHub.

    uv run python scripts/generer_cle_api.py
"""

import logging
import secrets

from src.api.securite import empreinte_cle

journal = logging.getLogger(__name__)


def main() -> None:
    """Tire une clé au hasard, puis affiche la clé et son empreinte une seule fois."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cle = secrets.token_urlsafe(32)
    journal.info("Clé d'API, à transmettre au client : %s", cle)
    journal.info("Empreinte, à placer dans API_KEY_HASH : %s", empreinte_cle(cle))


if __name__ == "__main__":
    main()
