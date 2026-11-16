# Recette de l'image de mon application. Docker exécute ces instructions dans
# l'ordre et garde le résultat de chacune en cache tant que rien ne change avant elle.

# 1. Je pars d'une image officielle de Python 3.11, la version d'entraînement
#    du modèle. « slim » : un Linux allégé, sans outils superflus.
FROM python:3.11-slim

# 2. Je copie le programme uv depuis son image officielle : le même outil, à la
#    même version, que sur mon poste et dans la CI.
COPY --from=ghcr.io/astral-sh/uv:0.12.6 /uv /bin/uv

# 3. Réglages. uv : code compilé dès l'installation, Python de l'image utilisé,
#    aucun cache conservé (image plus légère). Python : journaux affichés tout
#    de suite, aucun fichier .pyc écrit au lancement.
ENV UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_CACHE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 4. Je travaille dans /app : les chemins qui suivent partent de ce dossier.
WORKDIR /app

# 5. J'installe d'abord les dépendances, à partir des deux fichiers qui les
#    décrivent. Tant qu'ils ne changent pas, Docker réutilise cette couche :
#    modifier mon code ne relance pas toute l'installation.
#    --locked : exactement les versions de uv.lock ; --no-dev : sans les outils
#    de test ; --no-install-project : mon propre code vient à l'instruction 6.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# 6. Je copie mon code, le modèle et le script de vérification, puis j'installe
#    mon paquet src. README.md est lu par l'installation (pyproject.toml).
COPY README.md ./
COPY src ./src
COPY models ./models
COPY scripts/verifier_modele.py ./scripts/
RUN uv sync --locked --no-dev

# 7. Je crée un utilisateur sans droits d'administration et je lui passe la
#    main : l'application ne tourne jamais en tant que root.
RUN useradd --system --no-create-home appli
USER appli

# 8. Je mets l'environnement virtuel en tête du PATH : « python » désigne celui
#    de /app/.venv, avec mes dépendances.
ENV PATH="/app/.venv/bin:$PATH"

# 9. Commande lancée au démarrage du conteneur : la vérification du modèle.
#    Le serveur de l'API la remplacera.
CMD ["python", "scripts/verifier_modele.py"]
