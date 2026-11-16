# P5 : déployer le modèle de départ des collaborateurs

[![CI](https://github.com/MendyData/P5_Deploiement_ML/actions/workflows/ci.yml/badge.svg)](https://github.com/MendyData/P5_Deploiement_ML/actions/workflows/ci.yml)
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
7. [Environnements](#environnements)
8. [Intégration et déploiement continus](#intégration-et-déploiement-continus)
9. [Déploiement local](#déploiement-local)
10. [Structure du projet](#structure-du-projet)
11. [Organisation du dépôt](#organisation-du-dépôt)
12. [Licence](#licence)

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
| Paramètres par environnement | En place |
| Tests (85 tests, couverture de 100 % sur `src`) | En place |
| Pipeline CI/CD (GitHub Actions) | En place |
| Image Docker et lancement avec Docker Compose | En place |
| API FastAPI | À venir |
| Base PostgreSQL | À venir |

## Technologies

| Outil | Version | Rôle |
| --- | --- | --- |
| Python | 3.11 | Langage, à la version d'entraînement du modèle |
| scikit-learn | 1.9.1 | Pipeline et régression logistique |
| pandas | 3.0.6 | Manipulation des données |
| numpy | 2.4.6 | Calcul numérique |
| joblib | 1.6.0 | Sauvegarde et chargement du modèle |
| pydantic-settings | 2.16 | Paramètres lus dans l'environnement et validés |
| uv | 0.12 ou plus | Environnement et dépendances |
| Pytest et pytest-cov | 9.2 et 7.1 | Tests et couverture |
| Ruff | 0.17 | Vérification et format du code |
| GitHub Actions | | Intégration et déploiement continus |
| Docker et Docker Compose | Docker Desktop | Image de l'application et lancement local |

Les versions exactes de toutes les dépendances, y compris indirectes, sont figées
dans `uv.lock`. Ce fichier et `pyproject.toml` remplacent un `requirements.txt`.

## Prérequis

- Git
- [uv](https://docs.astral.sh/uv/) : il installe lui-même Python 3.11 si besoin
- [Docker Desktop](https://docs.docker.com/desktop/), pour le déploiement local

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

## Environnements

La variable `APP_ENV` indique où l'application tourne. Elle est lue et validée au
démarrage par `src/parametres.py` : une valeur inconnue arrête le démarrage.

| Environnement | `APP_ENV` | Où | D'où viennent les réglages |
| --- | --- | --- | --- |
| Développement | `development` | Mon poste | Fichier `.env`, ignoré par Git |
| Test | `test` | CI et branche `staging` | Environnement GitHub `test` |
| Production | `production` | Version taguée `vX.Y.Z` | Environnement GitHub `production` |

Aucun réglage sensible n'est écrit dans le code ni dans les workflows : les
variables et les secrets de test et de production sont déclarés dans GitHub
(Settings, Environments).

## Intégration et déploiement continus

Deux workflows GitHub Actions, dans `.github/workflows/` :

| Workflow | Déclencheur | Ce qu'il fait |
| --- | --- | --- |
| `ci.yml` | Chaque push, sur toutes les branches | `uv sync --locked`, contrôles Ruff, tests avec couverture |
| `deploiement.yml` | Push sur `staging`, tag `vX.Y.Z` | Construction de l'image Docker, puis test de fumée |

- Je ne fusionne une branche dans `main` que si la CI est verte.
- Le test de fumée lance le conteneur : il doit charger le modèle et s'arrêter
  sans erreur.

## Déploiement local

```bash
docker compose up --build
```

- Docker construit l'image en suivant le `Dockerfile` : Python 3.11, dépendances
  figées de `uv.lock`, code, modèle, utilisateur sans droits d'administration.
- Le conteneur lit `APP_ENV` et `LOG_LEVEL` dans le fichier `.env`, vérifie puis
  charge le modèle, et affiche sa version et son seuil de décision.
- L'installation est entièrement automatisée : aucune commande à lancer dans le
  conteneur.

## Structure du projet

```text
P5_Deploiement_ML/
├── .github/workflows/     Workflows GitHub Actions : CI et déploiement
├── data/                  Données (non versionnées)
├── models/                Modèle sauvegardé, métadonnées et découpage des données
├── notebooks/             Explorations
├── scripts/               Entraînement, références du P4, vérification du modèle
├── src/
│   ├── config.py          Colonnes, modalités et chemins du projet
│   ├── parametres.py      Paramètres par environnement (APP_ENV, LOG_LEVEL)
│   └── modele/            Pipeline, features métier, entraînement, prédicteur
├── tests/
│   ├── fixtures/          Données de référence versionnées
│   ├── fonctionnels/      Non-régression et prédicteur
│   └── unitaires/         Configuration, paramètres, features, pipeline, entraînement
├── .dockerignore          Fichiers laissés hors de l'image
├── .env.example           Modèle des variables d'environnement
├── CHANGELOG.md           Journal des changements, version par version
├── Dockerfile             Recette de l'image de l'application
├── docker-compose.yml     Lancement local
├── pyproject.toml         Projet, dépendances et réglages des outils
└── uv.lock                Versions figées de toutes les dépendances
```

## Organisation du dépôt

- Branches permanentes : `main` (développement), `staging` (test) et `production`
  (versions livrées).
- Une branche `feature/<nom>` par fonctionnalité, fusionnée dans `main` avec un
  commit de fusion, une fois la CI verte.
- Messages de commit au format conventionnel, en français : `feat`, `fix`, `test`,
  `docs`, `refactor`, `ci`, `build`, `chore`.
- Une version par étape, taguée `vX.Y.Z` sur `production` et décrite dans
  `CHANGELOG.md`.

## Licence

Code publié sous licence MIT : voir le fichier [LICENCE](LICENCE). Les données RH
ne font pas partie du dépôt.
