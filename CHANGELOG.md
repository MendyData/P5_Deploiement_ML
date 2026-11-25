# Journal des changements

Je consigne ici les évolutions notables du projet, version par version. Le format
suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et la numérotation
[SemVer](https://semver.org/lang/fr/) : un tag par étape de la trame, jusqu'à la
version 1.0.0 de la clôture.

## [Non publié]

## [1.3.0] - 2026-11-25

### Ajouté

- L'API attend la base au démarrage : jusqu'à 10 essais de connexion espacés de
  2 secondes, réglables par `POSTGRES_TENTATIVES` et `POSTGRES_PAUSE`. Si la base
  reste injoignable, elle s'arrête avec un message explicite. Une panne survenue
  après le démarrage donne toujours une réponse 503.
- Tests de l'attente (`tests/unitaires/test_attente.py`) et du démarrage sans base
  (`tests/fonctionnels/test_demarrage.py`).

## [1.2.0] - 2026-11-23

### Ajouté

- `POST /predict/{id_employee}` : prédiction pour un collaborateur déjà enregistré
  dans la table `collaborateurs`, désigné par son seul identifiant. Même schéma,
  même clé d'API et même trace que `POST /predict` ; 404 si l'identifiant est
  inconnu.
- Swagger et ReDoc expliquent comment construire une demande à partir des trois
  extraits RH d'origine, et proposent deux collaborateurs de ces extraits comme
  exemples.
- Requêtes SQL courantes (`docs/requetes_sql.md`) et diagramme de classes UML de
  la base (`docs/schema_bdd_uml.md`).

### Modifié

- La base Docker est publiée sur le port 5433 du poste : le 5432 est déjà pris par
  le PostgreSQL installé sous Windows. Les conteneurs et la CI restent sur 5432.
- README, guide d'utilisation, schéma de la base et rapport de couverture
  décrivent la nouvelle route.
- Capture de Swagger : version 1.2.0 et ses trois routes.

## [1.1.0] - 2026-11-18

### Ajouté

- Réponse de `POST /predict` : `lecture` donne les probabilités de maintien
  (classe 0) et de départ (classe 1) en pourcentages ; chaque facteur de la fiche
  RH gagne `impact_points`, son effet en points de probabilité de départ.
- Guide d'utilisation de l'API (`docs/guide_utilisateur.md`) : demande pas à pas
  dans Swagger, les 26 informations et leurs valeurs, lecture de la réponse,
  erreurs, appels en PowerShell, curl et Python.

### Corrigé

- Chaque nombre reçu par l'API a une borne haute, un peu au-dessus du maximum
  observé au projet 4 : un nombre démesuré est refusé (422) au lieu de produire un
  score extrapolé ou une réponse 503.
- La réponse 503 est réservée à une base injoignable ; un ordre refusé par la base
  répond 500.
- Les réponses JSON déclarent l'encodage UTF-8 : Windows PowerShell 5.1 affiche
  les accents correctement.
- Fiche RH : la contribution d'un facteur est décrite en log-cote, son unité.
- README : version de FastAPI.

### Modifié

- Le workflow de déploiement rejoue la CI avant de construire l'image : un commit
  dont les tests échouent n'est jamais déployé.
- L'action `setup-uv` est épinglée par l'empreinte de son commit, comme `checkout`.
- Captures de Swagger et de la réponse de l'API.

### Sécurité

- Les messages d'erreur de la base ne reprennent plus les valeurs envoyées : aucune
  information RH n'entre dans les journaux.

## [1.0.0] - 2026-11-18

Première version complète de la preuve de concept.

### Modifié

- Protocole de mise à jour du modèle : la validation commence par
  `scripts/verifier_modele.py`, qui confirme que le nouvel artefact se charge.

## [0.6.0] - 2026-11-18

### Ajouté

- Documentation du modèle (`docs/modele.md`) : données, variables, seuil,
  performances, limites, maintenance et protocole de mise à jour.
- README : architecture avec son diagramme, aperçu en captures, résumé du modèle,
  choix techniques et sommaire complet.
- Captures de Swagger et d'une réponse de l'API dans `docs/captures/`.

### Modifié

- README : la section Avancement laisse la place à l'architecture.

## [0.5.0] - 2026-11-18

### Ajouté

- Règle de cohérence issue de l'analyse du projet 4 : l'API refuse une entrée dans
  la vie active avant 16 ans (âge moins expérience totale).
- Contraintes `CHECK` de cohérence métier dans les tables `collaborateurs` et
  `demandes` : durées emboîtées, revenu positif, âge d'entrée dans la vie active.
- Tests d'intégrité de la base (`tests/fonctionnels/test_integrite_bdd.py`) : types
  des colonnes, valeurs absentes, contraintes `CHECK`, cohérence métier, clés
  étrangères, unicité, insertion, suppression et droits du rôle de l'API.
- Test du parcours complet (`tests/fonctionnels/test_parcours_complet.py`) : un
  client envoie les exemples fournis, ses traces sont relues, puis il est
  désactivé.
- Seuil de couverture à 80 % (`fail_under`) : en dessous, les tests échouent en
  local comme dans la CI.
- Rapport de couverture dans `docs/rapport_couverture.md`.
- README : organisation des tests et couverture, règles de cohérence.

### Modifié

- Les règles de cohérence des durées passent dans `src/config.py`, lues à la fois
  par le schéma de l'API et par la base ; le test couvre désormais les quatre
  paires de durées.

## [0.4.0] - 2026-11-18

### Ajouté

- Base PostgreSQL 16 dans Docker Compose : volume de données, contrôle de santé,
  port lié au poste seulement.
- Tables `collaborateurs`, `utilisateurs`, `demandes` et `reponses`
  (`src/bdd/modeles.py`) : clés, unicité, `NOT NULL`, `CHECK` sur les modalités et
  sur le score, index sur la date et le client ; schéma dans `docs/schema_bdd.md`.
- Scripts `creer_base.py` (tables, relations, rôle de l'API aux droits limités),
  `inserer_dataset.py` (jeu complet, contrôle du nombre de lignes),
  `creer_utilisateur.py` et `interroger_base.py` ; exemples d'entrées dans
  `docs/exemples/`.
- Traçabilité : chaque demande est enregistrée avant le calcul, chaque réponse
  est reliée à sa demande ; réponse 503 quand la base est indisponible.
- Clients de l'API enregistrés en base, avec l'empreinte de leur clé.
- Base PostgreSQL jetable dans la CI ; tests de l'initialisation et des traces sur
  une base de test recréée à chaque exécution.
- README : base de données, stockage et gestion des données, besoins analytiques.

### Modifié

- `GET /health` vérifie aussi la base.
- Documentation interactive : schéma servi sous `/schema.json`, en-tête avec
  l'autrice du projet et la licence MIT.
- Connexion à la base : hôte `127.0.0.1` par défaut et délai de connexion de
  5 secondes, pour que la réponse 503 arrive sans attente.
- Docker Compose lance la base, son initialisation, puis l'API ; le workflow de
  déploiement s'appuie sur Docker Compose.

### Supprimé

- Variable `API_KEY_HASH` et script `generer_cle_api.py`, remplacés par la table
  `utilisateurs` et `creer_utilisateur.py`.

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

## [0.2.0] - 2026-11-16

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

## [0.1.0] - 2026-11-13

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
