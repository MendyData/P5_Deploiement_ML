# Journal des changements

Je consigne ici les évolutions notables du projet, version par version. Le format
suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et la numérotation
[SemVer](https://semver.org/lang/fr/) : un tag par étape de la trame, jusqu'à la
version 1.0.0 de la clôture.

## [Non publié]

## [0.3.0] - 2026-11-17

### Ajouté

- API FastAPI (`src/api/`) : `GET /health` et `POST /predict`, modèle vérifié et
  chargé une seule fois au démarrage, documentation Swagger avec exemple.
- Schéma d'entrée des 26 informations d'un collaborateur (`src/schemas/`) :
  bornes, modalités lues dans la configuration, cohérence des durées ; erreurs
  422 renvoyées en français, champ par champ.
- Probabilité de départ corrigée du rééquilibrage des classes
  (`probabilite_depart` dans `src/modele/evaluation.py`) : le score est ramené au
  taux de départ de l'entraînement, rangé dans les métadonnées de l'artefact
  (`taux_depart_entrainement`). L'ordre des scores, donc l'alerte, ne change pas.
- Réponse enrichie : score, alerte, décision en clair, probabilités de départ et
  de maintien, seuils en score et en probabilité, version du modèle et fiche RH,
  les cinq variables qui pèsent le plus dans le score
  (`src/modele/explication.py`, `src/services/prediction.py`).
- Authentification par clé d'API dans l'en-tête `X-API-Key` : seule l'empreinte
  SHA-256 est conservée (`API_KEY_HASH`) ; script `scripts/generer_cle_api.py`.
- Tests de l'API, des schémas, de l'explication et de la probabilité corrigée.
- README : utilisation de l'API et authentification.

### Modifié

- Image Docker : le conteneur lance le serveur Uvicorn sur le port 8000.
- Workflow de déploiement : le test de fumée interroge `/health`.

## [0.2.0] - 2026-11-13

### Ajouté

- Paramètres par environnement (`src/parametres.py`) : `APP_ENV` (development,
  test, production) et `LOG_LEVEL`, lus dans l'environnement ou le fichier `.env`
  et validés par pydantic-settings.
- Intégration continue avec GitHub Actions (`.github/workflows/ci.yml`) : à chaque
  push, installation par `uv sync --locked`, contrôles Ruff et tests avec
  couverture.
- Image Docker (`Dockerfile`, `.dockerignore`) : Python 3.11 slim, dépendances
  figées installées par uv, utilisateur non root.
- Lancement local avec Docker Compose (`docker-compose.yml`).
- Script `scripts/verifier_modele.py` : test de fumée qui charge le modèle dans
  l'environnement courant.
- Workflow de déploiement (`.github/workflows/deploiement.yml`) : image construite
  et test de fumée à chaque push sur `staging` (environnement de test) et à chaque
  tag (environnement de production).
- README : environnements, CI/CD, déploiement local et badge de la CI.

## [0.1.0] - 2026-11-12

### Ajouté

- Pipeline d'inférence scikit-learn complet, des 26 variables d'un collaborateur
  du jeu consolidé jusqu'au score de départ : features métier, encodage en
  46 colonnes, mise à l'échelle et régression logistique, réentraîné à
  l'identique sur le découpage du P4.
- Artefact `models/pipeline_attrition.joblib` et ses métadonnées
  `models/pipeline_attrition.json` : version, date d'entraînement, seuil de
  décision, colonnes d'entrée, features, versions des bibliothèques, empreinte
  SHA-256 et métriques de test ; découpage du P4 conservé par identifiants.
- Prédicteur `PredicteurAttrition` : empreinte et versions vérifiées avant tout
  chargement de l'artefact, score de risque et alerte pour chaque collaborateur.
- Scripts de référence du P4 (`scripts/generer_reference_p4.py`) et
  d'entraînement (`scripts/entrainer_pipeline.py`).
- Tests unitaires et fonctionnels, dont la non-régression face au P4 et un
  marqueur `lent` pour les tests qui demandent les données complètes ;
  couverture mesurée sur `src`.
- Outils de qualité : Ruff avec des règles étendues, Pytest et pytest-cov.
- Structure du projet reprise du modèle NewProject_Template, Python 3.11
  épinglé, fins de ligne LF et environnement géré par uv.
- Fichier `.env.example` : modèle des variables d'environnement, sans valeur
  secrète ; le fichier `.env` reste ignoré par Git.
- Licence MIT.
- README : présentation, technologies, installation, tests et structure du projet.
