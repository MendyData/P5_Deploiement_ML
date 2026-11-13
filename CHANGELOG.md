# Journal des changements

Je consigne ici les évolutions notables du projet, version par version. Le format
suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et la numérotation
[SemVer](https://semver.org/lang/fr/) : un tag par étape de la trame, jusqu'à la
version 1.0.0 de la clôture.

## [Non publié]

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
