# P5 : déployer le modèle de départ des collaborateurs

![Python 3.11](https://img.shields.io/badge/python-3.11-blue)
![Licence MIT](https://img.shields.io/badge/licence-MIT-green)

Preuve de concept pour l'entreprise Futurisys : le modèle de prédiction des départs
construit au projet 4 devient un service, avec une API, une base de données, des tests
et un déploiement automatisés.

## Sommaire

1. [À propos du projet](#à-propos-du-projet)
2. [Avancement](#avancement)
3. [Technologies](#technologies)
4. [Prérequis](#prérequis)
5. [Installation](#installation)
6. [Tests et qualité du code](#tests-et-qualité-du-code)
7. [Structure du projet](#structure-du-projet)
8. [Organisation du dépôt](#organisation-du-dépôt)
9. [Licence](#licence)

## À propos du projet

Le modèle estime, pour un collaborateur, un score de risque de départ entre 0 et 1,
puis déclenche une alerte quand ce score atteint le seuil de décision (0,418).
Il a été conçu au projet 4 à partir de trois extraits RH (1 470 collaborateurs).

Dans ce dépôt, je le mets en production :

- un pipeline scikit-learn unique, des 26 informations brutes d'un collaborateur
  jusqu'au score ;
- une API FastAPI qui valide les données reçues et renvoie le score et l'alerte ;
- une base PostgreSQL qui conserve chaque demande et chaque réponse ;
- des tests automatisés et un pipeline CI/CD avec GitHub Actions ;
- un déploiement local avec Docker Compose.

## Avancement

| Brique | État |
| --- | --- |
| Pipeline d'inférence et prédicteur | En place |
| Tests du modèle (76 tests, couverture de 100 % sur `src`) | En place |
| Pipeline CI/CD (GitHub Actions) | À venir |
| API FastAPI | À venir |
| Base PostgreSQL | À venir |
| Déploiement Docker Compose | À venir |

## Technologies

| Outil | Version | Rôle |
| --- | --- | --- |
| Python | 3.11 | Langage, à la version d'entraînement du modèle |
| scikit-learn | 1.9.1 | Pipeline et régression logistique |
| pandas | 3.0.6 | Manipulation des données |
| numpy | 2.4.6 | Calcul numérique |
| joblib | 1.6.0 | Sauvegarde et chargement du modèle |
| uv | 0.12 ou plus | Environnement et dépendances |
| Pytest et pytest-cov | 9.2 et 7.1 | Tests et couverture |
| Ruff | 0.17 | Vérification et format du code |

Les versions exactes de toutes les dépendances, y compris indirectes, sont figées
dans `uv.lock`. Ce fichier et `pyproject.toml` remplacent un `requirements.txt`.

## Prérequis

- Git
- [uv](https://docs.astral.sh/uv/) : il installe lui-même Python 3.11 si besoin

## Installation

```bash
git clone https://github.com/MendyData/P5_Deploiement_ML.git
cd P5_Deploiement_ML
uv sync --locked
cp .env.example .env
```

- `uv sync --locked` crée l'environnement `.venv` et installe exactement les versions
  de `uv.lock`. La commande échoue si le verrou n'est plus à jour.
- `.env` contient les réglages de mon poste. Il est ignoré par Git : aucun secret
  n'est versionné. `.env.example` liste les variables attendues.

## Tests et qualité du code

```bash
uv run pytest -m "not lent" --cov=src
uv run ruff check .
uv run ruff format --check .
```

- Les tests rapides ne dépendent que de fichiers versionnés : ils passent sur un
  clone neuf.
- Les tests marqués `lent` réentraînent le modèle ou lisent les données RH complètes.
  Ces données ne sont pas dans le dépôt : sans elles, ces tests sont ignorés.
- Les tests de non-régression vérifient que le pipeline redonne les scores du
  projet 4 sur les 294 collaborateurs du jeu de test.

## Structure du projet

```text
P5_Deploiement_ML/
├── data/                  Données (non versionnées)
├── models/                Modèle sauvegardé, métadonnées et découpage des données
├── notebooks/             Explorations
├── scripts/               Entraînement du pipeline et génération des références
├── src/
│   ├── config.py          Colonnes, modalités et chemins du projet
│   └── modele/            Pipeline, features métier, entraînement, prédicteur
├── tests/
│   ├── fixtures/          Données de référence versionnées
│   ├── fonctionnels/      Non-régression et prédicteur
│   └── unitaires/         Configuration, features, pipeline, entraînement
├── .env.example           Modèle des variables d'environnement
├── CHANGELOG.md           Journal des changements, version par version
├── pyproject.toml         Projet, dépendances et réglages des outils
└── uv.lock                Versions figées de toutes les dépendances
```

## Organisation du dépôt

- Branches permanentes : `main` (développement), `staging` (test) et `production`
  (versions livrées).
- Une branche `feature/<nom>` par fonctionnalité, fusionnée dans `main` avec un
  commit de fusion.
- Messages de commit au format conventionnel, en français : `feat`, `fix`, `test`,
  `docs`, `refactor`, `ci`, `build`, `chore`.
- Une version par étape, taguée `vX.Y.Z` sur `production` et décrite dans
  `CHANGELOG.md`.

## Licence

Code publié sous licence MIT : voir le fichier [LICENCE](LICENCE). Les données RH
ne font pas partie du dépôt.
