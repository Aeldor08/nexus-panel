# Jeton GitHub pour les mises à jour (dépôt privé)

Le dépôt de NEXUS est **privé** : pour que le panel puisse voir les nouvelles versions, il lui faut un jeton
GitHub **en lecture seule, limité à ce seul dépôt**. Sans jeton, la vérification affiche « dépôt introuvable ».

## Créer le jeton (5 minutes)

1. Sur GitHub : photo de profil → **Settings** → **Developer settings** → **Personal access tokens** →
   **Fine-grained tokens** → **Generate new token**.
2. **Token name** : `NEXUS mises à jour (nom du PC)`.
3. **Expiration** : 1 an (GitHub te prévient avant l'expiration ; il suffira d'en créer un nouveau).
4. **Resource owner** : le propriétaire du dépôt (toi, ou la personne qui t'a invité·e).
5. **Repository access** : **Only select repositories** → choisis uniquement `nexus-panel`.
6. **Permissions** → **Repository permissions** → **Contents : Read-only**.
   (GitHub ajoute tout seul **Metadata : Read-only**.) **Ne coche rien d'autre.**
7. **Generate token**, puis copie le jeton (il commence par `github_pat_`). GitHub ne le montre qu'une fois.

> Si le dépôt appartient à quelqu'un d'autre, il faut d'abord avoir accepté son invitation de collaborateur.
> Pour un dépôt d'organisation, l'organisation peut devoir approuver le jeton.

## Le donner à NEXUS

**⚙ Réglages** → **Version et mises à jour** :

1. **Dépôt GitHub** : `propriétaire/nexus-panel` ;
2. **Jeton (dépôt privé)** : colle le jeton ;
3. **Enregistrer**. NEXUS vérifie aussitôt et affiche « Jeton enregistré et vérifié ✔ ».

## Où il est gardé, à qui il est envoyé

- Il est rangé dans le **gestionnaire d'identifiants de Windows** (entrée « NEXUS-panel-mises-a-jour »).
  Si ce n'est pas possible, il va dans `config.json`, section `mises_a_jour`, qui n'est **jamais** dans Git.
- Il n'est jamais réaffiché, ni écrit dans le code, les journaux ou les sauvegardes partagées.
- Pour des tests automatiques, la variable d'environnement `NEXUS_MAJ_JETON` peut fournir un jeton : il est alors lu en mémoire et jamais enregistré.
- Il n'est envoyé **qu'à `api.github.com`**. Les téléchargements redirigés vers les serveurs de fichiers de
  GitHub se font **sans** le jeton.
- Même avec ce jeton, rien ne s'installe sans ton clic **et** le mot de passe du panel.

## En cas de problème

| Message | Que faire |
|---|---|
| « Jeton refusé (invalide ou expiré) » | Crée un nouveau jeton et enregistre-le |
| « Dépôt ou release introuvable » | Vérifie le nom du dépôt, l'accès « Only select repositories » et l'invitation |
| « Limite de requêtes GitHub atteinte » | Attends l'heure indiquée ; avec un jeton, la limite est bien plus haute |
| « GitHub injoignable » | Pas d'internet ou GitHub en panne : NEXUS réessaiera plus tard |

Pour retirer le jeton : **Effacer le jeton** dans les réglages, puis supprime-le sur GitHub.
