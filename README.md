# Modification des fichiers Excel par adresse — Projet SNA

Application Tkinter qui écrit une valeur d'**ID erreur** dans les fichiers
audit des communes, pour des lignes désignées par leur **adresse** plutôt que
par un identifiant déjà connu. L'utilisateur colle des paires
« adresse → nouvel ID erreur » ; le programme résout la commune de chaque
adresse et en déduit tout le reste.

Arborescence attendue des audits :

```
<racine>/Dep<XX>/<commune>/audit_*.xlsx
```

## Principe

L'utilisateur saisit, une ligne par entrée, une **adresse** associée à la
valeur qu'elle doit prendre dans la colonne « ID erreur » :

```
12 rue de la Paix, 75002 Paris    13001_1
75020_4   20 avenue Foch, Marseille
5 place Bellecour, Lyon ; 2A004_3
```

Le séparateur accepté entre les deux membres est une tabulation (pour un
copier/coller depuis deux colonnes Excel), un point-virgule (`;`) ou une
flèche (`->` ou `=>`). **Les deux colonnes peuvent être collées dans
n'importe quel ordre** (adresse puis ID erreur, ou l'inverse) : le membre qui
a la forme d'un ID erreur (`<insee>_<numéro>`, par exemple `13001_1`) est
reconnu automatiquement, quelle que soit sa position. Une éventuelle ligne
d'en-tête (« ID erreur » / « Adresse », copiée avec les données depuis Excel)
est ignorée silencieusement.

À partir de la saisie, le programme :

1. **extrait** les paires (adresse, valeur) valides — une ligne sans
   séparateur reconnu, ou dont l'un des deux membres est vide, est ignorée et
   signalée ;
2. **résout le code INSEE** de chaque adresse via l'[API Adresse](https://api-adresse.data.gouv.fr)
   (data.gouv.fr, gratuite, sans clé) — nécessite un accès Internet ; une
   adresse sans correspondance est signalée et écartée ;
3. **regroupe** les paires par commune → `{ "13001": [...], "75020": [...] }` ;
4. **déduit** le département de chaque code INSEE (`Dep13`, `Dep75`, `Dep2A`) et
   ouvre `<racine>/Dep<XX>/<insee>/audit_*.xlsx` — un seul fichier par
   commune, quel que soit le nombre d'adresses demandées pour elle ;
5. **modifie** uniquement les lignes dont la colonne **« Adresse »** porte
   l'une des adresses demandées pour cette commune, en y écrivant la valeur
   d'ID erreur qui lui est associée.

La comparaison des adresses est tolérante aux espaces (y compris multiples) et
à la casse : `12 Rue de la Paix` et `12   rue de la paix` sont considérées
identiques.

## Ce que l'utilisateur paramètre

| Élément | Où | Persistance |
|---|---|---|
| Dossier racine des audits | champ « Dossier racine » de la fenêtre principale | `config.json` (clé `root_path_be`) |
| Colonne comparée aux adresses saisies | panneau « ⚙️ Configuration » | `config.json` (clé `config_adresses.colonne_adresse`, « Adresse » par défaut) |
| Colonne où écrire l'ID erreur | panneau « ⚙️ Configuration » | `config.json` (clé `config_adresses.colonne_id`, « ID erreur » par défaut) |
| Ligne d'en-tête du classeur | panneau « ⚙️ Configuration » | `config.json` (clé `config_adresses.ligne_entete`) |
| Reprise de la mise en forme | panneau « ⚙️ Configuration » | `config.json` (clé `config_adresses.harmoniser_style`) |

Il n'y a pas de configuration métier livrée par défaut : au premier
lancement, seules des valeurs de repli structurelles (« Adresse », « ID
erreur ») sont proposées ; rien n'est écrit dans les fichiers tant que
l'utilisateur n'a pas saisi ses propres adresses.

## Une seule opération, volontairement

Contrairement à un constructeur de règles généraliste, ce programme ne fait
**qu'une seule chose** : pour chaque ligne dont la colonne « Adresse »
correspond à l'une des adresses saisies, écrire dans la colonne « ID erreur »
la valeur qui lui est associée dans la saisie. Il n'y a ni condition, ni choix
de colonne cible par ligne, ni valeur uniforme imposée à tout un lot : la
valeur vient de la saisie elle-même, adresse par adresse.

- **Valeur écrite** : une valeur ressemblant à un identifiant (« 13001_2 »)
  reste du texte — jamais convertie en nombre — sauf si elle est purement
  numérique (« 42 »), auquel cas elle est écrite comme un nombre.
- **Une même adresse saisie plusieurs fois, avec des valeurs différentes**
  (cas de deux logements à la même adresse, chacun avec son propre ID erreur
  à corriger) : les lignes du classeur qui portent cette adresse reçoivent
  les valeurs saisies **dans l'ordre** — la 1re ligne rencontrée (de haut en
  bas dans le fichier) reçoit la 1re valeur saisie pour cette adresse, la 2e
  ligne la 2e valeur, etc. S'il y a plus de lignes que de valeurs saisies, la
  dernière valeur saisie est réutilisée pour les lignes excédentaires.
- **Une même adresse saisie une seule fois** : toutes les lignes du classeur
  qui la portent reçoivent cette unique valeur.
- **Mise en forme** : la case « Reprendre la mise en forme de la colonne »
  donne aux cellules écrites la **police, la taille, l'alignement et le
  format d'affichage** des valeurs déjà présentes dans la colonne « ID
  erreur ». Quand cette colonne est **entièrement vide**, c'est la **police
  dominante du classeur** qui prend le relais, relevée sur les données
  réelles du fichier. Le fond et les bordures de la cellule sont laissés
  intacts.

### Détection automatique des colonnes

À l'ouverture du panneau de configuration, le programme cherche le premier
`<racine>/Dep<XX>/<insee>/audit_*.xlsx` et en extrait les en-têtes ainsi que le
type de chaque colonne (numérique / texte / date), pour peupler les menus
déroulants « Adresse » et « ID erreur ». Le bouton « 📄 Colonnes depuis un
autre fichier… » permet de pointer un classeur différent.

### Résolution des codes INSEE

Chaque adresse saisie est envoyée à l'API Adresse officielle
(`https://api-adresse.data.gouv.fr/search/`), qui retourne le code INSEE
(`citycode`) de la commune la plus probable. Les adresses sont résolues en
parallèle (jusqu'à 8 requêtes simultanées). Une adresse sans correspondance —
ou si le service est injoignable — est signalée dans le journal et écartée du
traitement ; les autres adresses continuent d'être traitées normalement.

### Mode simulation

La case « Simulation (aucune écriture) » compte les modifications qui *seraient*
faites sans rien écrire sur le disque. À utiliser systématiquement avant un
premier lot.

### Contrôle de la saisie

Sous la zone de saisie, un compteur affiche en direct ce que le programme a
compris dans le texte : `12 adresse(s) reconnue(s)`, et signale les lignes
incomplètes (adresse ou ID erreur manquant). Les communes ne sont connues
qu'après résolution des codes INSEE — un appel réseau — qui n'a lieu qu'au
lancement du traitement.

### Journal en temps réel

Le journal s'alimente **pendant** le traitement, étape par étape :

```
🚀 5 adresse(s)
📂 Racine : D:\audit_SNA
🌐 Résolution des codes INSEE via l'API Adresse (data.gouv.fr)…
⚠️ 1 adresse(s) sans commune identifiée : 12 rue Introuvable, Nulle Part
🔎 Filtre : colonne « Adresse » → écriture dans « ID erreur »  ·  mise en forme reprise de la colonne
────────────────────────────────────────────────────────────
   · 13001 — recherche du fichier audit…
   · 13001 — audit_13001.xlsx (12,4 Mo)
   · 13001 — analyse du fichier…
   · 13001 — 3 ligne(s) à modifier — chargement du classeur…
   · 13001 — application des modifications…
   · 13001 — enregistrement de 3 modification(s)…
✅ 13001 — 3 modification(s) sur 3 ligne(s) · 3/3 adresses trouvées · 4,1 s
   · 75020 — recherche du fichier audit…
   · 75020 — analyse du fichier…
   · 75020 — aucune ligne concernée sur 8 200 lue(s) — non ouvert en écriture
⚠️ 75020 — 0 modification(s) sur 0 ligne(s) · 0/1 adresses trouvées · 0,2 s
   ↳ introuvables : 8 avenue Foch
```

Chaque commune indique le nombre de lignes touchées, sa durée, et **les
adresses demandées qui n'existent pas dans le fichier** — une saisie erronée
ne passe donc pas pour un traitement réussi. Les messages transitent par une
file vidée périodiquement : un fichier volumineux, qui produit un point
d'avancement toutes les 20 000 lignes, ne sature pas l'interface.

## Performances

Le coût réel d'un traitement, c'est l'ouverture des classeurs. Trois
décisions en découlent :

1. **Le repérage des lignes ne passe plus par openpyxl.** Le XML de la
   feuille est balayé en flux (`services/lecture_rapide.py`) sur la seule
   colonne « Adresse ». Structure inattendue → repli automatique sur
   openpyxl, avec un test d'équivalence croisée entre les deux chemins.
2. **Un fichier sans adresse correspondante n'est jamais chargé.** Le
   repérage suffit à le savoir.
3. **Les colonnes sont résolues avant tout chargement.** Une colonne mal
   orthographiée est signalée en quelques centièmes de seconde, plutôt
   qu'après plusieurs secondes d'attente.

## Structure

```
edit_by_address/
├── main.py                     # Point d'entrée (lance l'interface)
├── config.json.example         # Modèle de configuration
├── sna/
│   ├── chemins.py              # Emplacement de config.json (dev / packagé)
│   ├── config.py               # Chargement et sauvegarde (racine + colonnes)
│   ├── models/
│   │   ├── base.py             #   Statut, ResultatCommune
│   │   └── config_adresses.py  #   ConfigAdresses
│   ├── services/               # Logique métier (aucune dépendance à l'interface)
│   │   ├── adresses.py         #   saisie → paires (adresse, ID erreur), regroupement
│   │   ├── geocodage.py        #   adresse → code INSEE (API Adresse, data.gouv.fr)
│   │   ├── fichiers.py         #   recherche des audits et du fichier exemple
│   │   ├── lecture_rapide.py   #   balayage XML d'une colonne, sans openpyxl
│   │   ├── colonnes_excel.py   #   détection des colonnes et de leur type
│   │   ├── valeurs.py          #   typage, dates, reprise de mise en forme
│   │   ├── excel.py            #   application de la modification sur un classeur
│   │   └── traitement.py       #   orchestration d'un lot de communes
│   └── ui/
│       ├── theme.py            #   couleurs et polices centralisées
│       ├── panneau_config.py   #   panneau de configuration des colonnes
│       └── application.py      #   fenêtre principale
└── tests/                      # tests (pytest)
```

L'architecture sépare **modèles**, **services** et **interface** : la couche
métier ne dépend pas de Tkinter, elle est testable sans environnement
graphique. Seule `services/geocodage.py` fait un appel réseau ; le reste (y
compris `services/traitement.py`) reste testable hors ligne, la résolution des
codes INSEE ayant déjà eu lieu quand il est appelé.

## Installation et lancement

```bash
uv sync          # ou : pip install openpyxl pytest
python main.py
```

Au premier lancement, indiquez le dossier racine puis cliquez sur
« Enregistrer » : il est mémorisé pour les fois suivantes. Ouvrez
« ⚙️ Configuration » pour confirmer (ou changer) le nom des colonnes « Adresse »
et « ID erreur » — vos réglages sont conservés d'un lancement à l'autre.

## Tests

```bash
python -m pytest
```

`tests/test_equivalence.py` tient deux garde-fous, tous deux par comparaison
**cellule par cellule** sur une matrice de cas (valeur déjà en place, cellule
vide, valeur numérique, adresse dupliquée dans le fichier, adresse absente,
colonne Adresse partiellement vide…) :

- le moteur optimisé contre une **implémentation de référence** naïve de la
  règle métier ;
- le repérage par lecture directe du XML contre le repli openpyxl.

`tests/test_lecture_rapide.py` construit ses archives xlsx **à la main**
plutôt que par openpyxl : la façon dont les accents sont écrits (UTF-8 brut ou
références `&#244;` / `&#xF4;`) varie selon la version d'openpyxl et la
présence de lxml. Les trois formes sont vérifiées explicitement, faute de quoi
le test constaterait le comportement de la machine plutôt que celui du
programme.

`tests/test_geocodage.py` simule les réponses de l'API Adresse (aucun appel
réseau réel dans les tests).

## Points d'attention

- **openpyxl réécrit intégralement le classeur** à la sauvegarde : graphiques,
  images et mises en forme conditionnelles avancées peuvent ne pas être
  conservés. Le fichier n'est réécrit **que si une cellule a réellement changé**,
  et jamais en mode simulation. Testez toujours sur une copie.
- Une colonne « Adresse » ou « ID erreur » absente d'un fichier **échoue
  proprement pour cette commune** (statut ❌ dans le journal) plutôt que d'être
  ignorée en silence.
- `float("13001_2")` vaut `130012.0` en Python : les soulignés sont admis dans
  les littéraux numériques. Une valeur d'ID erreur imposée ressemblant à un
  nombre souligné serait donc devenue un nombre. La conversion refuse
  désormais les soulignés, ainsi que `nan` et `inf`.
- Consulter une cellule avec `feuille.cell(...)` la **crée**, ainsi que sa
  ligne : inspecter la mise en forme ajoutait des `<row/>` vides au classeur
  enregistré. La lecture passe donc par les cellules réellement présentes.
- Si plusieurs lignes d'un fichier portent la même adresse, toutes sont
  modifiées.
- La résolution des codes INSEE nécessite un accès Internet vers
  `api-adresse.data.gouv.fr`. Une adresse sans correspondance, ou une panne du
  service, ne bloque pas les autres adresses de la saisie.
