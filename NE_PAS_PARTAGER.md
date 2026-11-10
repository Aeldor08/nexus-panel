# Fichiers à ne jamais partager

Ces fichiers et dossiers sont créés sur **ton** PC et contiennent tes secrets ou tes données.
`preparer_partage.bat` les laisse de côté automatiquement, et `.gitignore` les exclut de Git.

| Fichier / dossier | Ce qu'il contient |
|---|---|
| `config.json` | Jeton du bot Discord, ton ID Discord, l'ID du salon, l'empreinte du mot de passe du deck |
| `.env` | (si tu en crées un) les mêmes secrets |
| `deck.json` | Tes boutons du stream deck (chemins de tes applis, tes scripts) |
| `data\` | Agenda (et ses sauvegardes `data\backups\`), rappels envoyés (`data\rappels.json`), notes, to-do, horloges, noms des ventilateurs, appareils du réseau local et téléphones appairés (avec leurs jetons), sessions du deck, icônes extraites de tes applis, historique des tests de débit |
| `data\nexus.db` | Base locale : **journal** (humeurs, activités, textes), **statistiques personnelles** (temps par appli et par jeu, sessions), index des souvenirs |
| `data\souvenirs\` | Tes **photos** (et leurs miniatures) |
| `jeux.json` | Ta liste de jeux et d'applis suivis (seul `jeux.example.json` est partagé) |
| `logs\` | Journal des boutons du deck (heure, adresse IP de l'appareil) |
| `versions\` | Sauvegardes automatiques du code (peuvent contenir d'anciens fichiers) |
| `actions\` (sauf `exemple.bat`) | Tes scripts personnels pour le deck |
| `LibreHardwareMonitor\` | Logiciel tiers : chacun le télécharge lui-même (voir README) |
| `.venv\`, `__pycache__\` | Environnement Python propre à ton PC (recréé par `installer.bat`) |
| `partage\` | Les copies déjà préparées pour le partage |
| `maj\` | État des mises à jour (dernière vérification, archive téléchargée en cours d'installation) |
| `sauvegardes-maj\` | Copie complète (code, `data\`, `config.json`) faite avant chaque mise à jour |
| Jeton GitHub | Rangé dans le gestionnaire d'identifiants de Windows (ou, à défaut, dans `config.json`) : ne le colle jamais ailleurs |
| `*.lnk`, `*.log` | Raccourcis et journaux de ton PC |

**Si tu as partagé `config.json` par erreur :** régénère le jeton du bot sur
https://discord.com/developers/applications (Bot → Reset Token) puis relance `configurer.bat`.
