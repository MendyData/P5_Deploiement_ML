# Requêtes SQL courantes

Ce document rassemble les requêtes qui servent le plus souvent à interroger la
base `p5` : le jeu de données du projet 4 d'un côté, la trace des appels à l'API
de l'autre. Les noms de tables et de colonnes sont ceux de `src/bdd/modeles.py`,
fautes de frappe du jeu d'origine comprises (`annes_sous_responsable_actuel`,
`augementation_salaire_precedente`).

`scripts/interroger_base.py` exécute déjà trois de ces requêtes. Celles-ci se
tapent à la main, pour explorer ou pour une démonstration.

## Sommaire

1. [Se connecter à la base](#se-connecter-à-la-base)
2. [Commandes utiles de psql](#commandes-utiles-de-psql)
3. [Jeu de données du projet 4](#jeu-de-données-du-projet-4)
4. [Traces des appels à l'API](#traces-des-appels-à-lapi)
5. [Lire un score ou une probabilité](#lire-un-score-ou-une-probabilité)

## Se connecter à la base

La base tourne dans le conteneur `db` de Docker Compose. Docker la publie sur le
port **5433** de mon poste, et non sur 5432 : ce port est déjà occupé par le
PostgreSQL installé sous Windows. Le conteneur, lui, écoute toujours sur 5432,
et l'API le joint à cette adresse à l'intérieur du réseau Compose.

| Serveur | Adresse depuis mon poste | Contient la base `p5` |
| --- | --- | --- |
| PostgreSQL de Docker (projet P5) | `127.0.0.1:5433` | Oui |
| PostgreSQL installé sous Windows | `127.0.0.1:5432` | Non |

Toutes les commandes se tapent dans le terminal Git Bash de VS Code, depuis la
racine du projet.

### 1. Démarrer la base

```bash
docker compose up -d db
docker compose ps
```

La colonne `PORTS` doit afficher `127.0.0.1:5433->5432/tcp`. Si elle affiche
encore 5432, le conteneur date d'avant le changement de port : `docker compose up
-d db` le recrée de lui-même dès que sa configuration change. Les données sont
conservées, car elles vivent dans le volume `donnees_postgres`, pas dans le
conteneur.

### 2. Vérifier que psql est accessible depuis Git Bash

```bash
psql --version
```

Si la commande est introuvable, le dossier `bin` de PostgreSQL n'est pas dans le
`PATH` de Git Bash. Je repère la version installée, puis je l'ajoute une fois
pour toutes à `~/.bashrc` :

```bash
ls "/c/Program Files/PostgreSQL/"
echo 'export PATH="/c/Program Files/PostgreSQL/16/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Je remplace `16` par le numéro affiché par `ls`. La version du client n'a pas
besoin d'être exactement celle du serveur, du moment qu'elle n'est pas plus
ancienne.

### 3. Se connecter

```bash
winpty psql -h 127.0.0.1 -p 5433 -U api -d p5
```

| Option | Valeur | Raison |
| --- | --- | --- |
| `-h 127.0.0.1` | Adresse du poste | Pas `localhost`, qui essaie d'abord l'IPv6, où Docker ne publie pas la base |
| `-p 5433` | Port publié par Docker | Sans lui, `psql` vise 5432, donc le serveur Windows |
| `-U api` | Rôle de l'API | Lecture seule sur l'historique : une fausse manipulation ne peut rien effacer |
| `-d p5` | Base du projet | |

`winpty` sert d'intermédiaire entre Git Bash et un programme Windows interactif.
Sans lui, `psql` peut rester bloqué sans afficher la demande de mot de passe.

Le mot de passe demandé est la valeur de `POSTGRES_API_PASSWORD` dans `.env`.
L'invite `p5=>` confirme la connexion ; `\conninfo` rappelle le serveur, le port
et le rôle utilisés.

Le rôle `proprietaire` (`POSTGRES_PASSWORD`) reste réservé aux scripts de
création, d'insertion et de purge. Je ne l'utilise à la main que pour une
opération d'administration précise.

### 4. Ne plus retaper le mot de passe

Deux méthodes, à choisir selon l'usage.

**Pour la session du terminal en cours.** Je lis le mot de passe dans `.env` au
lieu de l'écrire : il n'apparaît ni à l'écran ni dans l'historique de Git Bash.

```bash
export PGHOST=127.0.0.1 PGPORT=5433 PGUSER=api PGDATABASE=p5
export PGPASSWORD="$(grep '^POSTGRES_API_PASSWORD=' .env | cut -d= -f2 | tr -d '\r')"
winpty psql
```

`psql` lit ces variables d'environnement : la commande se réduit à `psql`. Elles
disparaissent à la fermeture du terminal.

**De façon permanente.** Sous Windows, `psql` lit le fichier
`%APPDATA%\postgresql\pgpass.conf`, une ligne par connexion, au format
`adresse:port:base:rôle:mot_de_passe`.

```bash
mkdir -p "$APPDATA/postgresql"
echo "127.0.0.1:5433:p5:api:$(grep '^POSTGRES_API_PASSWORD=' .env | cut -d= -f2 | tr -d '\r')" >> "$APPDATA/postgresql/pgpass.conf"
```

Ce fichier est hors du dépôt, dans mon profil Windows : il n'est jamais versionné.
Si je change le mot de passe dans `.env`, je mets aussi cette ligne à jour.

### 5. Lancer une requête sans ouvrir de session

```bash
psql -h 127.0.0.1 -p 5433 -U api -d p5 -c "SELECT count(*) FROM collaborateurs;"
```

`-c` exécute une seule requête puis rend la main : pratique pour un contrôle
rapide ou dans un script. `winpty` n'est pas nécessaire ici, puisque rien n'est
saisi au clavier, à condition que le mot de passe vienne de `PGPASSWORD` ou de
`pgpass.conf`.

### 6. Exporter un résultat en CSV

```sql
\copy (SELECT d.id AS demande, d.recue_le, d.poste, r.probabilite_depart, r.alerte FROM demandes AS d JOIN reponses AS r ON r.demande_id = d.id ORDER BY d.id) TO 'docs/exemples/entrees_en_base.csv' WITH CSV HEADER
```

`\copy` est exécuté par `psql`, côté poste : le fichier est écrit dans le dossier
d'où `psql` a été lancé, et le rôle `api` suffit, puisqu'il ne faut qu'un droit de
lecture. La commande tient sur une seule ligne, sans point-virgule final.

### 7. Avec une interface graphique

**pgAdmin**, installé avec PostgreSQL. Clic droit sur Servers, Register, Server :

| Onglet | Champ | Valeur |
| --- | --- | --- |
| General | Name | `P5 Docker` |
| Connection | Host name/address | `127.0.0.1` |
| Connection | Port | `5433` |
| Connection | Maintenance database | `p5` |
| Connection | Username | `api` |
| Connection | Password | `POSTGRES_API_PASSWORD` du fichier `.env` |

Le nom `P5 Docker` distingue ce serveur de celui de Windows, que pgAdmin affiche
déjà. Les requêtes se tapent dans Tools, Query Tool.

**Dans VS Code**, l'extension PostgreSQL de Microsoft se règle avec les mêmes
valeurs : adresse, port 5433, base `p5`, rôle `api`. Je coche l'option qui demande
le mot de passe à chaque connexion plutôt que de l'enregistrer.

### En cas d'erreur

| Message | Cause probable | Solution |
| --- | --- | --- |
| `connection refused` | Le conteneur est arrêté, ou le port est faux | `docker compose ps`, puis vérifier `-p 5433` |
| `database "p5" does not exist` | `psql` a joint le serveur Windows sur 5432 | Ajouter `-p 5433` |
| `password authentication failed for user "api"` | Mot de passe différent de `.env`, ou rôle pas encore créé | Relire `.env` ; lancer `uv run python scripts/creer_base.py` |
| `permission denied for table ...` | Le rôle `api` tente de modifier ou de supprimer | Comportement voulu : il n'a que la lecture et l'ajout |
| `psql` reste muet, sans invite | Programme Windows lancé sans `winpty` dans Git Bash | Préfixer par `winpty` |

## Commandes utiles de psql

Ces commandes commencent par une barre oblique inversée et ne se terminent pas par
un point-virgule. Une requête SQL, elle, se termine toujours par `;` : sans lui,
`psql` attend la suite et l'invite passe de `p5=>` à `p5->`.

| Commande | Effet |
| --- | --- |
| `\conninfo` | Rappelle le serveur, le port, la base et le rôle de la connexion |
| `\l` | Liste les bases du serveur |
| `\dt` | Liste les tables |
| `\d collaborateurs` | Décrit une table : colonnes, types, contraintes, index |
| `\du` | Liste les rôles et leurs attributs |
| `\dp` | Affiche les droits de chaque rôle sur chaque table |
| `\x auto` | Affiche les lignes larges en colonne, une valeur par ligne |
| `\timing on` | Affiche la durée de chaque requête |
| `\i chemin/fichier.sql` | Exécute un fichier de requêtes |
| `\q` | Quitte `psql` |

`\dp` est utile en démonstration : il montre que le rôle `api` n'a que `r`
(lecture) et `a` (ajout) sur `demandes` et `reponses`.

## Jeu de données du projet 4

La table `collaborateurs` contient les 1 470 collaborateurs du projet 4 et leur
départ observé (`a_quitte_l_entreprise`, booléen). Ces requêtes décrivent la
population sur laquelle le modèle a appris : ce sont les chiffres de référence
auxquels comparer les prédictions.

### Effectif total

```sql
-- Nombre de collaborateurs dans le jeu de référence.
SELECT count(*) AS effectif
FROM collaborateurs;
```

Résultat attendu : 1 470. Un autre nombre signale une insertion incomplète ou en
double ; `scripts/inserer_dataset.py` contrôle déjà ce point.

### Taux de départ

```sql
-- Nombre de départs et leur part dans l'effectif, en pourcentage.
-- Un booléen converti en entier vaut 1 (vrai) ou 0 (faux) : sa moyenne est
-- donc directement la proportion de vrais.
SELECT
    count(*) AS effectif,
    count(*) FILTER (WHERE a_quitte_l_entreprise) AS departs,
    round(100.0 * avg(a_quitte_l_entreprise::int), 1) AS taux_depart_pct
FROM collaborateurs;
```

Résultat attendu : 237 départs, soit 16,1 %. C'est le déséquilibre de classes qui
a conduit au modèle pondéré (`class_weight="balanced"`), puis à la correction de
la probabilité renvoyée par l'API.

### Départs par département

```sql
-- Taux de départ de chaque département, du plus exposé au moins exposé.
SELECT
    departement,
    count(*) AS effectif,
    count(*) FILTER (WHERE a_quitte_l_entreprise) AS departs,
    round(100.0 * avg(a_quitte_l_entreprise::int), 1) AS taux_depart_pct
FROM collaborateurs
GROUP BY departement
ORDER BY taux_depart_pct DESC;
```

Lecture : un taux nettement au-dessus de 16,1 % désigne un département où cibler
les actions de rétention. Je regarde toujours l'effectif à côté du taux : un taux
élevé sur 20 personnes est bien moins solide que sur 900.

### Départs par poste

```sql
-- Taux de départ par poste. HAVING écarte les postes trop rares pour qu'un
-- taux soit interprétable.
SELECT
    poste,
    count(*) AS effectif,
    count(*) FILTER (WHERE a_quitte_l_entreprise) AS departs,
    round(100.0 * avg(a_quitte_l_entreprise::int), 1) AS taux_depart_pct
FROM collaborateurs
GROUP BY poste
HAVING count(*) >= 30
ORDER BY taux_depart_pct DESC;
```

Le seuil de 30 collaborateurs est une convention courante pour qu'une proportion
reste stable ; je l'abaisse à 1 pour voir tous les postes.

### Départs selon les heures supplémentaires

```sql
-- Le premier facteur de départ identifié au projet 4.
SELECT
    heure_supplementaires,
    count(*) AS effectif,
    round(100.0 * avg(a_quitte_l_entreprise::int), 1) AS taux_depart_pct
FROM collaborateurs
GROUP BY heure_supplementaires
ORDER BY heure_supplementaires;
```

Lecture : l'écart entre « Oui » et « Non » mesure le poids de la charge de travail
dans les départs. C'est un levier directement actionnable par les RH.

### Profil moyen des partants et des restants

```sql
-- Moyennes comparées : âge, revenu, ancienneté et expérience.
SELECT
    CASE WHEN a_quitte_l_entreprise THEN 'Départ' ELSE 'Reste' END AS groupe,
    count(*) AS effectif,
    round(avg(age), 1) AS age_moyen,
    round(avg(revenu_mensuel)) AS revenu_mensuel_moyen,
    round(avg(annees_dans_l_entreprise), 1) AS anciennete_moyenne,
    round(avg(annee_experience_totale), 1) AS experience_moyenne,
    round(avg(annees_depuis_la_derniere_promotion), 1) AS annees_depuis_promotion
FROM collaborateurs
GROUP BY groupe
ORDER BY groupe;
```

Lecture : au projet 4, les partants sont en moyenne plus jeunes, moins payés et
moins anciens. Une moyenne résume mal une distribution très étalée comme le
revenu : la requête suivante le complète par la médiane.

### Revenu médian selon le départ

```sql
-- La médiane résiste aux quelques très hauts salaires qui tirent la moyenne.
SELECT
    CASE WHEN a_quitte_l_entreprise THEN 'Départ' ELSE 'Reste' END AS groupe,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY revenu_mensuel) AS revenu_median
FROM collaborateurs
GROUP BY groupe
ORDER BY groupe;
```

### Départs selon la satisfaction minimale

```sql
-- Reconstitue la feature métier satisfaction_minimale du projet 4 : la plus
-- basse des quatre notes de satisfaction, le point de rupture du collaborateur.
SELECT
    least(
        satisfaction_employee_environnement,
        satisfaction_employee_nature_travail,
        satisfaction_employee_equipe,
        satisfaction_employee_equilibre_pro_perso
    ) AS satisfaction_minimale,
    count(*) AS effectif,
    round(100.0 * avg(a_quitte_l_entreprise::int), 1) AS taux_depart_pct
FROM collaborateurs
GROUP BY satisfaction_minimale
ORDER BY satisfaction_minimale;
```

Lecture : le taux de départ décroît quand la satisfaction minimale monte. Il
suffit d'une seule dimension au plus bas pour exposer un collaborateur, ce que la
moyenne des quatre notes masquerait.

## Traces des appels à l'API

Chaque appel accepté par `POST /predict` laisse une ligne dans `demandes` (les
26 informations reçues), puis une ligne dans `reponses` (la prédiction), reliée
par `reponses.demande_id`. `utilisateurs` dit quel client a appelé.

### Volume de chaque table

```sql
-- Vue d'ensemble : une ligne, quatre compteurs.
SELECT
    (SELECT count(*) FROM collaborateurs) AS collaborateurs,
    (SELECT count(*) FROM utilisateurs) AS utilisateurs,
    (SELECT count(*) FROM demandes) AS demandes,
    (SELECT count(*) FROM reponses) AS reponses;
```

Lecture : `demandes` et `reponses` doivent avoir le même nombre de lignes. Un
écart signale des demandes restées sans réponse (voir plus bas).

### Nombre de prédictions par client

```sql
-- Qui utilise l'API, et combien.
SELECT
    u.nom AS client,
    u.actif,
    count(d.id) AS demandes,
    min(d.recue_le) AS premiere_demande,
    max(d.recue_le) AS derniere_demande
FROM utilisateurs AS u
LEFT JOIN demandes AS d ON d.utilisateur_id = u.id
GROUP BY u.id, u.nom, u.actif
ORDER BY demandes DESC;
```

Le `LEFT JOIN` garde les clients qui n'ont encore rien envoyé : ils apparaissent
avec 0 demande au lieu de disparaître du résultat.

### Probabilité moyenne, score moyen et taux d'alerte

```sql
-- Indicateurs de synthèse des prédictions, par version du modèle.
SELECT
    version_modele,
    count(*) AS predictions,
    round(avg(probabilite_depart)::numeric * 100, 1) AS probabilite_moyenne_pct,
    round(avg(score_risque)::numeric, 3) AS score_moyen,
    count(*) FILTER (WHERE alerte) AS alertes,
    round(100.0 * avg(alerte::int), 1) AS taux_alerte_pct
FROM reponses
GROUP BY version_modele
ORDER BY version_modele;
```

`avg` d'une colonne `float` renvoie un `double precision`, que `round(x, n)`
n'accepte pas : la conversion `::numeric` est donc nécessaire.

Lecture : la probabilité moyenne se compare au taux de départ réel (16,1 %). Le
taux d'alerte est plus haut, et c'est voulu : le seuil a été fixé pour détecter
au moins 80 % des départs, au prix de fausses alertes. Grouper par version du
modèle permet de voir l'effet d'une mise à jour.

### Répartition des prédictions par niveau de probabilité

```sql
-- Nombre de prédictions par tranche de probabilité de départ.
SELECT
    CASE
        WHEN probabilite_depart < 0.10 THEN '1. moins de 10 %'
        WHEN probabilite_depart < 0.25 THEN '2. de 10 à 25 %'
        WHEN probabilite_depart < 0.50 THEN '3. de 25 à 50 %'
        ELSE '4. 50 % et plus'
    END AS tranche,
    count(*) AS predictions,
    round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS part_pct
FROM reponses
GROUP BY tranche
ORDER BY tranche;
```

`sum(count(*)) OVER ()` calcule le total de toutes les tranches sans seconde
requête : chaque tranche est rapportée à ce total. Le numéro en tête de libellé
garde les tranches dans l'ordre croissant au tri.

### Répartition entre alertes et absences d'alerte

```sql
SELECT
    CASE WHEN alerte THEN 'Risque de départ' ELSE 'Pas de risque détecté' END AS decision,
    count(*) AS predictions,
    round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS part_pct
FROM reponses
GROUP BY decision
ORDER BY decision;
```

Le libellé est celui que renvoie l'API. Il est recalculé ici à partir de
`alerte`, car la base ne stocke pas ce qui se déduit d'une autre colonne.

### Dernières demandes avec leur réponse

```sql
-- Les dix derniers appels : qui, quand, pour quel profil, avec quel résultat.
SELECT
    d.id AS demande,
    d.recue_le,
    u.nom AS client,
    d.poste,
    d.departement,
    round(r.probabilite_depart::numeric * 100, 1) AS probabilite_pct,
    r.alerte
FROM demandes AS d
JOIN utilisateurs AS u ON u.id = d.utilisateur_id
LEFT JOIN reponses AS r ON r.demande_id = d.id
ORDER BY d.recue_le DESC
LIMIT 10;
```

Le `LEFT JOIN` sur `reponses` garde les demandes sans réponse : leurs colonnes de
prédiction sont vides, ce qui les rend visibles au lieu de les cacher.

### Demandes sans réponse

```sql
-- Demandes enregistrées pour lesquelles aucune prédiction n'a été servie.
SELECT d.id AS demande, d.recue_le, u.nom AS client
FROM demandes AS d
JOIN utilisateurs AS u ON u.id = d.utilisateur_id
WHERE NOT EXISTS (
    SELECT 1 FROM reponses AS r WHERE r.demande_id = d.id
)
ORDER BY d.recue_le DESC;
```

Lecture : la demande est enregistrée avant le calcul. Une ligne ici signifie donc
que le calcul ou l'enregistrement de la réponse a échoué après coup. En
fonctionnement normal, cette requête ne renvoie rien ; toute ligne est un incident
à rapprocher des journaux de l'API à la même heure.

### Activité par jour

```sql
-- Nombre de demandes et d'alertes par jour.
SELECT
    date_trunc('day', d.recue_le)::date AS jour,
    count(*) AS demandes,
    count(*) FILTER (WHERE r.alerte) AS alertes
FROM demandes AS d
LEFT JOIN reponses AS r ON r.demande_id = d.id
GROUP BY jour
ORDER BY jour DESC;
```

`date_trunc('week', ...)` ou `date_trunc('month', ...)` donnent la même vue par
semaine ou par mois.

### Facteurs les plus souvent cités dans les fiches RH

```sql
-- facteurs est une liste JSON : jsonb_array_elements la déplie en une ligne
-- par facteur, et ->> en extrait un champ sous forme de texte.
SELECT
    facteur ->> 'variable' AS variable,
    count(*) AS citations,
    count(*) FILTER (WHERE facteur ->> 'effet' = 'augmente le risque') AS augmente_le_risque
FROM reponses,
     jsonb_array_elements(facteurs) AS facteur
GROUP BY variable
ORDER BY citations DESC
LIMIT 10;
```

Lecture : les variables qui reviennent le plus souvent parmi les cinq facteurs
principaux de chaque fiche. Elles orientent les sujets à préparer pour les
entretiens de rétention.

### Probabilité moyenne par département

```sql
-- Où se concentre le risque prédit parmi les collaborateurs soumis à l'API.
SELECT
    d.departement,
    count(*) AS predictions,
    round(avg(r.probabilite_depart)::numeric * 100, 1) AS probabilite_moyenne_pct,
    round(100.0 * avg(r.alerte::int), 1) AS taux_alerte_pct
FROM demandes AS d
JOIN reponses AS r ON r.demande_id = d.id
GROUP BY d.departement
ORDER BY probabilite_moyenne_pct DESC;
```

### Comparaison des demandes reçues avec le jeu d'entraînement

```sql
-- Les profils envoyés à l'API ressemblent-ils encore à ceux du projet 4 ?
SELECT
    'collaborateurs (projet 4)' AS source,
    count(*) AS effectif,
    round(avg(age), 1) AS age_moyen,
    round(avg(revenu_mensuel)) AS revenu_mensuel_moyen,
    round(100.0 * avg((heure_supplementaires = 'Oui')::int), 1) AS heures_sup_pct
FROM collaborateurs
UNION ALL
SELECT
    'demandes (API)',
    count(*),
    round(avg(age), 1),
    round(avg(revenu_mensuel)),
    round(100.0 * avg((heure_supplementaires = 'Oui')::int), 1)
FROM demandes;
```

Lecture : un écart marqué entre les deux lignes est un signe de dérive des
données. Le modèle a appris sur une population ; s'il reçoit durablement une autre
population, ses prédictions perdent leur fiabilité. C'est l'un des déclencheurs du
protocole de mise à jour décrit dans `docs/modele.md`.

## Lire un score ou une probabilité

`reponses` contient deux mesures du risque, qui ne se lisent pas de la même façon.

| Colonne | Ce qu'elle mesure | Comment la lire |
| --- | --- | --- |
| `score_risque` | Score brut du modèle, entre 0 et 1 | Il classe les collaborateurs et déclenche l'alerte au seuil de 0,418. Il ne se lit pas comme un pourcentage : le modèle pondéré gonfle ses scores. |
| `probabilite_depart` | Score corrigé du rééquilibrage des classes | C'est le chiffre à communiquer aux RH, comparable au taux de départ réel de 16,1 %. |

Pour un « score moyen » présenté à un public métier, j'utilise donc
`avg(probabilite_depart)`. `avg(score_risque)` reste utile pour suivre le modèle
dans le temps, d'une version à l'autre.
