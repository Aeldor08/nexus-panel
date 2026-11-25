# Composants tiers

NEXUS est distribué sous licence MIT (voir `LICENSE`). Il s'appuie sur les composants suivants, qui gardent
chacun leur propre licence.

## Polices embarquées (dans les profils visuels)

| Police | Où | Licence | Fichier de licence |
|---|---|---|---|
| Uncial Antiqua | `profils/des-du-destin/assets/` | SIL Open Font License 1.1 | `profils/des-du-destin/OFL-UncialAntiqua.txt` |
| Inter | `profils/des-du-destin/assets/`, `profils/pluie-d-etoiles/assets/`, `profils/averse-de-neons/assets/` | SIL Open Font License 1.1 | `OFL-Inter.txt` dans chacun de ces profils |
| Cinzel | `profils/pluie-d-etoiles/assets/` | SIL Open Font License 1.1 | `profils/pluie-d-etoiles/OFL-Cinzel.txt` |

Les polices sont livrées telles quelles (sous-ensembles WOFF2), sans changement de nom.
Les illustrations, sprites et SVG des profils sont des créations originales pour NEXUS.

## Bibliothèques Python (installées par `installer.bat` depuis PyPI, non incluses dans le dépôt)

| Paquet | Usage | Licence |
|---|---|---|
| FastAPI | serveur web local | MIT |
| Uvicorn | serveur ASGI | BSD-3-Clause |
| psutil | processeur, mémoire, disques, réseau, processus | BSD-3-Clause |
| nvidia-ml-py | carte graphique NVIDIA | BSD-3-Clause |
| winrt-runtime et winrt-Windows.* (PyWinRT) | lecture en cours (Windows Media) | MIT |
| pycaw | volume par application | MIT |
| qrcode | QR code d'appairage du téléphone | BSD |
| discord.py | bot Discord facultatif | MIT |
| Pillow | miniatures des souvenirs, icônes | MIT-CMU (HPND) |
| keyring | rangement du jeton GitHub dans le gestionnaire d'identifiants de Windows | MIT |
| pywebview | fenêtre native WebView2 (lanceur `nexus_launcher.py`) | BSD-3-Clause |
| pystray | icône dans la zone de notification | LGPL-3.0 (bibliothèque installée par pip, non modifiée) |
| winotify | notifications Windows natives | MIT |
| PyInstaller | fabrication de l'exécutable (outil de build, Phase 2) | GPL-2.0 avec exception bootloader |

Outils de développement seulement (`requirements-dev.txt`, non nécessaires pour utiliser NEXUS) : ruff (MIT), httpx / httpx2 (BSD-3-Clause), gitleaks (MIT).

`pystray` est utilisé comme bibliothèque non modifiée (LGPL-3.0) : sa licence et le moyen d'en obtenir
le code source seront joints à l'installeur. `PyInstaller` n'est utilisé que pour fabriquer l'exécutable.

## Logiciel téléchargé séparément

| Logiciel | Usage | Licence |
|---|---|---|
| LibreHardwareMonitor | températures et ventilateurs (facultatif) | MPL-2.0 |
| Python 3.12 (paquet `python` de la Python Software Foundation sur nuget.org) | Python privé de NEXUS (`runtime\`), téléchargé par `installer.bat` avec vérification SHA256 | PSF License 2.0 |

LibreHardwareMonitor n'est **pas** inclus dans le dépôt ni dans l'archive source : pour la version source, chacun
le télécharge depuis son site officiel (voir README). L'installeur Windows (option cochée) et le ZIP portable
livrent **LibreHardwareMonitor 0.9.6 sans modification** (archive officielle, empreinte SHA256 vérifiée au build),
avec le texte de sa licence (`LibreHardwareMonitor\LICENCE-LibreHardwareMonitor.txt`). Code source :
<https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/tree/v0.9.6> (Mozilla Public License 2.0).

## Exécutable Windows (installeur et portable)

`NEXUS.exe` est fabriqué avec PyInstaller (GPL-2.0 avec exception pour le chargeur : les programmes produits peuvent
avoir leur propre licence) et embarque l'interpréteur Python (PSF License 2.0) et les bibliothèques ci-dessus.
L'installeur est fabriqué avec Inno Setup (licence Inno Setup, usage libre).
