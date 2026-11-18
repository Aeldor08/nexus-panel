# Travailler depuis un fork GitHub

Ce guide explique comment récupérer NEXUS sur **ton** compte GitHub, faire
construire l'application Windows par GitHub Actions, et publier tes propres
versions sans toucher au dépôt de ton frère.

## 1. Qu'est-ce qu'un fork ?

Un **fork** est une copie complète d'un dépôt GitHub, placée sous ton compte.
Elle garde un lien avec le dépôt d'origine (appelé **upstream**) :

- tu peux modifier ton fork librement, créer des branches et des releases ;
- tu peux récupérer les changements de ton frère avec `git fetch upstream` ;
- tu peux proposer tes changements à ton frère avec une **Pull Request**.

Un fork d'un dépôt **public** est lui aussi public : GitHub ne permet pas de le
rendre privé. Si le dépôt de ton frère est privé, ton fork hérite de cette
visibilité et il faut un accès au dépôt d'origine.

## 2. Créer le fork

1. Ouvre la page du dépôt de ton frère sur GitHub.
2. Clique sur **Fork** (en haut à droite).
3. Choisis ton compte comme destination, puis **Create fork**.
4. Tu arrives sur `https://github.com/<ton-compte>/<nom-du-depot>`.

## 3. Récupérer le projet sur le PC

Dans un dossier vide (ou à la place de l'ancien dossier téléchargé) :

```bat
git clone https://github.com/<ton-compte>/<nom-du-depot>.git NEXUS
cd NEXUS
git remote add upstream https://github.com/<compte-de-ton-frere>/<nom-du-depot>.git
git remote -v
```

`origin` = ton fork ; `upstream` = le dépôt d'origine.

Si le dossier NEXUS actuel n'est pas encore un dépôt Git, tu peux l'initialiser
et le relier à ton fork **après** avoir créé le fork :

```bat
cd NEXUS
git init
git add .
git commit -m "NEXUS 1.6.0"
git branch -M main
git remote add origin https://github.com/<ton-compte>/<nom-du-depot>.git
git push -u origin main
```

Le `.gitignore` du projet exclut déjà `config.json`, `data/`, `logs/`, `dist/`
et les autres fichiers personnels. Vérifie quand même avec `git status` avant
le premier envoi.

## 4. Récupérer les mises à jour de ton frère

```bat
git fetch upstream
git switch main
git merge upstream/main
git push origin main
```

Si tu travailles sur une fonctionnalité, fais-le sur une branche :

```bat
git switch -c ma-fonctionnalite
:: ... modifications ...
git add .
git commit -m "Description courte"
git push -u origin ma-fonctionnalite
```

## 5. Faire construire l'application

Le workflow **Build Windows native** (`.github/workflows/build-native.yml`) se
déclenche :

- automatiquement quand tu pousses un tag `v1.5.0` (ou un autre numéro) ;
- manuellement depuis l'onglet **Actions** → **Build Windows native** →
  **Run workflow**.

Il lance les tests, construit `NEXUS.exe`, `NEXUS-1.6.0-Setup.exe` et
`NEXUS-Portable-1.6.0.zip`, puis dépose ces fichiers et leurs `.sha256` dans les
**artefacts** du workflow (onglet Actions → run → Artifacts). Rien n'est publié
dans les releases tant que tu ne le fais pas toi-même.

Pour signer :

1. Ajoute les secrets du dépôt (Settings → Secrets and variables → Actions) :
   - `WINDOWS_CERT_PFX_BASE64` : le `.pfx` encodé en base64 ;
   - `WINDOWS_CERT_PFX_PASSWORD` : son mot de passe.
2. Le workflow signe l'exe **avant** de fabriquer l'installeur, puis signe
   l'installeur. Sans ces secrets, le build reste non signé.

Encodage du `.pfx` sous PowerShell :

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\certs\nexus.pfx")) |
  Set-Clipboard
```

## 6. Publier une release sur ton fork

Quand tu es prêt (et seulement à ce moment-là) :

1. Vérifie que `VERSION` et `CHANGELOG.md` sont à jour.
2. Crée et pousse un tag : `git tag v1.5.0` puis `git push origin v1.5.0`.
3. Attends la fin du workflow, télécharge les artefacts.
4. Dans **Releases** → **Draft a new release**, choisis le tag, joins
   `NEXUS-1.5.0-Setup.exe`, son `.sha256`, éventuellement
   `NEXUS-Portable-1.5.0.zip` et `SHA256SUMS.txt`, puis publie.

L'updater de NEXUS cherche `NEXUS-x.y.z-Setup.exe` et son `.sha256` dans la
dernière release du dépôt configuré. Le nom du fichier doit donc rester
exactement au format produit par le build.

## 7. Fork ou collaborateur ?

- **Fork** : recommandé pour expérimenter et publier tes propres builds sans
  risque pour le dépôt de ton frère.
- **Collaborateur** : ton frère peut t'ajouter dans Settings → Collaborators.
  Tu peux alors pousser des branches directement sur son dépôt, mais tu
  partages les droits d'écriture.

Dans les deux cas, une **Pull Request** permet de proposer une modification
sans l'imposer.
