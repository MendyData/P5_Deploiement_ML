# Documentation du modèle

Le modèle estime le risque de départ d'un collaborateur. Il a été conçu au projet 4
et il est déployé ici sans changement de comportement : le pipeline du dépôt
redonne exactement les scores du projet 4.

## Fiche d'identité

| Élément | Valeur |
| --- | --- |
| Tâche | Classification binaire : départ ou maintien |
| Algorithme | Régression logistique, précédée d'une mise à l'échelle (`StandardScaler`) |
| Hyperparamètres | `C=1.0`, `class_weight="balanced"`, `max_iter=2000`, `random_state=42` |
| Version | `0.1.0`, entraînée le 10/11/2026 |
| Fichiers | `models/pipeline_attrition.joblib` et ses métadonnées `models/pipeline_attrition.json` |
| Environnement | Python 3.11, scikit-learn 1.9.1, pandas 3.0.6, numpy 2.4.6 |
| Sortie | Score de risque entre 0 et 1 ; alerte quand le score atteint 0,418 ; probabilité de départ corrigée du rééquilibrage |

## Données

- Trois extraits RH (SIRH, évaluations, sondage) réunis en un jeu de 1 470
  collaborateurs. Taux de départ observé : 16,1 %.
- Découpage du projet 4 : 882 collaborateurs pour l'entraînement, 294 pour la
  validation, 294 pour le test. Le modèle final est ajusté sur l'entraînement et la
  validation (1 176 collaborateurs) ; le test ne sert qu'aux métriques.
- Les données ne sont pas dans le dépôt. Les identifiants du découpage le sont
  (`models/identifiants_decoupage.json`), pour réentraîner à l'identique.

## Variables

Le modèle reçoit 26 informations par collaborateur et calcule sur 46 colonnes.

| Étape du pipeline | Ce qu'elle fait |
| --- | --- |
| Features métier | Ajoute `satisfaction_minimale` (la plus basse des quatre satisfactions), `nouveau_responsable` (aucune année sous le responsable actuel) et `debut_de_carriere` (deux ans d'expérience au plus) |
| Encodage ordinal | `genre`, `heure_supplementaires`, `frequence_deplacement` deviennent des entiers |
| Encodage en colonnes | `departement`, `poste`, `statut_marital`, `domaine_etude` deviennent une colonne par modalité (21 colonnes) |
| Mise à l'échelle | Chaque colonne est centrée et réduite |
| Régression logistique | Calcule le score |

- Les noms de colonnes et les modalités sont ceux du jeu d'origine, fautes de
  frappe comprises. Ils sont définis une seule fois, dans `src/config.py`.
- `niveau_hierarchique_poste` a été écartée au projet 4 : elle est corrélée à 0,95
  avec `revenu_mensuel`.
- Une modalité inconnue est refusée, par l'API puis par le pipeline.

## Seuil de décision

Le seuil vaut 0,418. C'est le plus haut seuil qui atteint un rappel de 0,80 en
validation croisée : pour le commanditaire, un départ manqué coûte plus cher
qu'une fausse alerte. Le F2, qui compte le rappel deux fois plus que la précision,
suit la même logique.

## Score et probabilité de départ

Le modèle a été entraîné avec `class_weight="balanced"` : il donne autant de poids
aux 190 départs qu'aux 986 maintiens, comme si les deux étaient aussi fréquents.
C'est ce qui lui fait repérer les départs, mais ses scores surestiment le risque :
sur le test, le score moyen vaut 0,33 alors que 16 % des collaborateurs partent.

L'API convertit donc chaque score `s` en probabilité de départ `p`, en remettant
le vrai taux de départ de l'entraînement `π = 0,1616` (rangé dans les métadonnées) :

```text
p = s × π / (s × π + (1 − s) × (1 − π))
```

| Mesure sur les 294 collaborateurs du test | Score brut | Probabilité corrigée |
| --- | --- | --- |
| Moyenne (départs observés : 0,16) | 0,331 | 0,139 |
| Score de Brier (plus bas, plus juste) | 0,146 | 0,103 |
| Seuil de décision | 0,418 | 0,122 |

La correction ne change pas l'ordre des collaborateurs : l'alerte, le rappel, la
précision et l'AUC-PR restent ceux du projet 4. Un réentraînement sans
rééquilibrage donne la même justesse (Brier 0,103) mais un rappel plus bas, à
nombre d'alertes égal : 0,72 contre 0,77. Les tests vérifient que la probabilité
moyenne reste proche du taux observé et que l'ordre est conservé.

## Performances

Mesurées sur les 294 collaborateurs du test, jamais vus à l'entraînement.

| Métrique | Valeur | Lecture |
| --- | --- | --- |
| Rappel | 0,766 | Sur 47 départs réels, 36 sont signalés et 11 sont manqués |
| Précision | 0,364 | Sur 99 alertes, 36 correspondent à un départ et 63 sont de fausses alertes |
| F2 | 0,627 | Synthèse qui privilégie le rappel |
| AUC-PR | 0,531 | Qualité du classement, tous seuils confondus (un tirage au hasard donnerait 0,16) |
| Exactitude | 0,748 | Part des collaborateurs bien classés |

Les tests de non-régression (`tests/fonctionnels/test_non_regression.py`) vérifient
à chaque exécution que le pipeline redonne les scores et les métriques du projet 4.

## Explication d'un score

L'API renvoie, avec chaque score, les cinq variables qui pèsent le plus. La
contribution d'une variable est son coefficient multiplié par sa valeur mise à
l'échelle : positive, elle pousse vers le départ ; négative, vers le maintien.
Elle s'exprime en log-cote, le logarithme de score / (1 − score), et non en
pourcentage. La somme des contributions et de la constante du modèle, passée par
la fonction logistique, redonne le score (`src/modele/explication.py`).

Pour les RH, chaque contribution est aussi traduite en points de probabilité de
départ (`impact_points`) : l'écart entre la probabilité du collaborateur et celle
qu'il aurait si cette variable valait la moyenne de l'entraînement. Ces impacts
ne s'additionnent pas, car la fonction logistique n'est pas linéaire. La réponse
donne enfin les deux probabilités en pourcentages (`lecture`) : maintien
(classe 0) et départ (classe 1).

## Limites et points de vigilance

- Le modèle aide à préparer un échange RH. Il ne décide pas : près de deux alertes
  sur trois sont de fausses alertes, par choix.
- `genre`, `statut_marital` et `age` sont des variables sensibles. Leur poids dans
  un score est visible dans la fiche RH.
- Le jeu d'entraînement est petit (1 176 collaborateurs) et vient d'une seule
  entreprise : le modèle ne se transpose pas tel quel ailleurs.
- Chaque nombre reçu par l'API a une borne haute, un peu au-dessus du maximum du
  jeu d'entraînement (par exemple un âge jusqu'à 70 ans pour 60 observés, 20
  formations pour 6) : au-delà, la demande est refusée. Près de ces bornes, loin
  des valeurs connues, le score est moins fiable.

## Sécurité du chargement

Un fichier `joblib` peut exécuter du code à son chargement. Le prédicteur compare
donc l'empreinte SHA-256 du fichier et les versions des bibliothèques aux
métadonnées avant de le charger. Un écart arrête le démarrage de l'API.

## Maintenance

| Quoi | Quand | Comment |
| --- | --- | --- |
| Surveiller l'usage et les erreurs | Chaque semaine | `scripts/interroger_base.py` ; demandes sans réponse |
| Vérifier la probabilité annoncée | Chaque trimestre | Comparer la probabilité moyenne de départ aux départs réellement observés ; un écart durable signale que le taux de départ a changé |
| Surveiller le taux d'alerte | Chaque mois | Requête par semaine et par version du modèle (README, besoins analytiques) |
| Surveiller la dérive des données | Chaque trimestre | Comparer les demandes au jeu `collaborateurs` : moyennes et répartitions des modalités |
| Mesurer la performance réelle | Quand les départs sont connus | Rapprocher les alertes des départs observés : rappel et précision |
| Mettre à jour les dépendances | À chaque correctif de sécurité | `uv lock --upgrade-package`, puis la CI ; scikit-learn, pandas et numpy restent figés tant que le modèle n'est pas réentraîné |

## Protocole de mise à jour du modèle

1. **Déclencheur.** L'un de ces constats : taux d'alerte qui s'écarte durablement de
   celui du test, données reçues qui ne ressemblent plus au jeu d'entraînement,
   rappel réel sous 0,70, nouveau jeu de données RH, changement de version de
   scikit-learn.
2. **Réentraînement, hors de l'API.** Sur une branche `feature/modele-...`, avec les
   nouvelles données dans `data/` : `uv run python scripts/entrainer_pipeline.py`.
   Le script écrit l'artefact et ses métadonnées (version, date, seuil, taux de
   départ de l'entraînement, empreinte, versions des bibliothèques, métriques de
   test).
3. **Validation.** `uv run python scripts/verifier_modele.py` confirme que le
   nouvel artefact se charge : empreinte et versions des bibliothèques conformes
   aux métadonnées. Puis `uv run pytest`, tests lents compris. Les métriques du nouveau
   modèle sont comparées à celles de la version en service ; le seuil est
   recalculé pour le rappel visé. Les références des tests de non-régression sont
   mises à jour dans le même commit que l'artefact.
4. **Nouvelle version.** La version du projet change (`uv version`), le CHANGELOG
   décrit le modèle, la CI doit être verte.
5. **Bascule.** Promotion vers `staging` : l'image est construite et le test de
   fumée charge le nouveau modèle. Puis promotion vers `production` et tag. L'API
   charge le modèle au démarrage : le redémarrage du conteneur fait la bascule.
6. **Suivi et retour arrière.** Chaque réponse enregistre `version_modele` : les
   deux versions se comparent dans la base. En cas de problème, je redéploie le
   tag précédent.
