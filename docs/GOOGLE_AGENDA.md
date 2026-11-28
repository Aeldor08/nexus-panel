# Relier l'Agenda de NEXUS à Google Agenda

NEXUS affiche les évènements de ton Google Agenda dans son onglet **Agenda**, et peut en **créer, modifier et
supprimer** : les changements arrivent dans Google Agenda (et donc sur ton téléphone). Ce que tu changes dans
Google Agenda apparaît dans NEXUS au plus tard 10 minutes après (ou tout de suite avec **⟳ Relire**).

Google demande que chaque programme qui touche à un agenda ait son propre « identifiant client ». NEXUS n'a pas
de serveur à lui : tu crées donc **ton** identifiant, dans **ton** compte Google, une seule fois (10 minutes
environ, gratuit, aucune carte bancaire).

## 1. Créer un projet Google Cloud

1. Va sur <https://console.cloud.google.com/> et connecte-toi avec le compte Google de ton agenda.
2. En haut à gauche, clique sur le sélecteur de projet → **Nouveau projet**.
3. **Nom du projet** : `NEXUS` → **Créer**. Vérifie ensuite que ce projet est bien sélectionné en haut.

## 2. Activer l'API Google Calendar

1. Menu ☰ → **API et services** → **Bibliothèque**.
2. Cherche **Google Calendar API**, ouvre-la, clique sur **Activer**.

## 3. Écran de consentement (ce que Google te montrera à la connexion)

1. Menu ☰ → **API et services** → **Écran de consentement OAuth** (selon l'interface : **Google Auth Platform**)
   → **Commencer**.
2. **Nom de l'application** : `Tableau de bord PC` (ou un autre nom à toi) ; **Adresse e-mail d'assistance** : la
   tienne → **Suivant**.
   > **Pas « NEXUS »** : Google refuse les noms qui reprennent une de ses marques (Nexus était une gamme de
   > téléphones Google ; de même Google, Gmail, Android, Chrome, YouTube, Pixel…). L'erreur est « le nom de
   > l'application ne respecte pas les exigences de Google ». Ce nom n'apparaît que sur la page de connexion de
   > Google : il ne change rien pour NEXUS.
3. **Audience** : **Externe** → **Suivant**. **Coordonnées** : ton adresse → **Suivant** → accepte → **Créer**.
4. **Audience** → **Utilisateurs test** → **Ajouter des utilisateurs** → ton adresse Gmail → **Enregistrer**.

> **À savoir :** tant que l'application est « en test », Google oublie l'autorisation au bout de **7 jours** :
> NEXUS affiche alors « reconnecte-toi » et il faut recliquer sur **Se connecter à Google**. Pour l'éviter :
> **Audience** → **Publier l'application** → **Confirmer**. Pas besoin de validation par Google pour ton seul
> compte ; à la connexion, Google affichera juste « Google n'a pas validé cette application » : clique sur
> **Paramètres avancés** → **Accéder à Tableau de bord PC** (le nom choisi plus haut). C'est normal, c'est ton
> propre projet.

## 4. Créer l'identifiant client

1. Menu ☰ → **API et services** → **Identifiants** (ou **Google Auth Platform** → **Clients**).
2. **Créer des identifiants** → **ID client OAuth** (ou **Créer un client**).
3. **Type d'application** : **Application de bureau** ; **Nom** : `NEXUS` → **Créer**.
4. Google affiche l'**ID client** (il se termine par `.apps.googleusercontent.com`) et le **Code secret du
   client** (il commence par `GOCSPX-`). Garde cette fenêtre ouverte (ou **Télécharger le JSON**).

## 5. Le donner à NEXUS et se connecter

Sur le PC (pas depuis le téléphone) : **⚙ Réglages** → **Google Agenda** :

1. colle l'**Identifiant client** et le **Code secret du client** → **Enregistrer** ;
2. **🔗 Se connecter à Google** : une page de Google s'ouvre dans ton navigateur. Choisis ton compte, accepte
   l'accès à ton agenda (voir l'avertissement ci-dessus) ;
3. la page affiche « NEXUS est relié à Google Agenda ✔ » : ferme-la. Les évènements apparaissent dans l'Agenda.

Ensuite, dans **⚙ Réglages → Google Agenda** :
- **Agenda relié** : ton agenda principal, ou un autre agenda où tu peux écrire ;
- **Nouveaux évènements** : où le formulaire les crée par défaut (Google Agenda ou NEXUS seulement). Le
  formulaire de l'Agenda propose aussi le choix pour chaque évènement ;
- **Relire Google Agenda toutes les** 5 à 60 minutes ;
- **Rappels de NEXUS aussi pour les évènements Google** : bannière, son et Discord, avec les rappels de
  l'évènement Google (ou ceux par défaut de ton agenda Google) ;
- **Se déconnecter** : NEXUS oublie l'accès (et le retire chez Google) et sa copie des évènements. Tes
  évènements restent dans Google Agenda.

## Ce que fait NEXUS (et ne fait pas)

- Les évènements Google restent **dans Google Agenda**. NEXUS en garde une copie (`data\agenda_google.json`)
  pour les afficher hors connexion et envoyer les rappels. Les évènements NEXUS restent dans NEXUS.
- Une modification depuis NEXUS n'envoie **que ce que tu as changé** : invités, lieu, visioconférence, couleur…
  ne sont jamais effacés.
- Répétitions : « tous les jours / semaines / mois / ans » se modifient comme dans NEXUS (**cet évènement
  seulement**, **et les suivants**, **toute la série**). Une répétition plus riche réglée dans Google Agenda
  (« toutes les 2 semaines », « lundi et jeudi »…) s'affiche **Répétition personnalisée** : tu peux changer le
  reste, la règle est gardée telle quelle.
- **Lecture seule** (pas de ✎ ni ✕, mention « lecture seule ») : invitations dont tu n'es pas l'organisateur,
  anniversaires de tes contacts, agenda partagé où tu ne peux pas écrire. Le lien **↗** ouvre l'évènement dans
  Google Agenda.

## Sécurité

- Le **code secret du client** et l'**accès donné par Google** (jeton de rafraîchissement) sont rangés dans le
  **gestionnaire d'identifiants de Windows** (comme le jeton GitHub des mises à jour) ; seulement si celui-ci
  est indisponible, dans `config.json` (exclu de Git). Ils ne sont jamais affichés, ni envoyés au téléphone, ni
  écrits dans les journaux, et ne partent que vers Google.
- La connexion utilise OAuth « application de bureau » avec PKCE : Google renvoie ton navigateur vers un petit
  serveur temporaire de NEXUS sur `127.0.0.1` (port au hasard, 5 minutes, une seule réponse vérifiée).
- NEXUS demande l'accès aux évènements de tes agendas et à la liste de tes agendas (pour choisir lequel
  relier) — rien d'autre (ni Gmail, ni Drive, ni contacts).
- Pour tout retirer : **Se déconnecter** dans NEXUS, ou <https://myaccount.google.com/permissions> → NEXUS →
  **Supprimer l'accès**.

## En cas de problème

| Message | Que faire |
|---|---|
| « L'API Google Calendar n'est pas activée… » | Étape 2, dans le bon projet (sélecteur en haut de la console) |
| « Google ne reconnaît pas l'identifiant client… » | Recopie l'ID et le code secret (étape 4) : **Changer d'identifiant client** |
| « Google a retiré l'accès de NEXUS… reconnecte-toi » | Application en test (7 jours) ou accès retiré : **Se connecter à Google** (et étape 3 pour publier) |
| `Error 403: access_denied` sur la page de Google | Ajoute ton adresse dans **Utilisateurs test** (étape 3.4), ou publie l'application |
| « Délai dépassé (5 minutes) » | Relance **Se connecter à Google** et termine la connexion dans les 5 minutes |
| « Cet agenda Google est en lecture seule » | Choisis un autre **Agenda relié** |
