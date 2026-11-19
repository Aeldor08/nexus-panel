# NEXUS pour Android

Petite appli (≈ 50 Ko) qui affiche le NEXUS du PC **en plein écran, sans navigateur**, sur le Wi-Fi de la maison.
C'est une télécommande : les mesures viennent du PC, qui doit être allumé avec NEXUS ouvert et l'accès téléphone
activé (📱 Téléphone sur le PC).

## Installer sur le téléphone

1. Copie `NEXUS-Android-x.y.z.apk` sur le téléphone (câble USB, Google Drive, envoi à soi-même…).
2. Ouvre-le depuis l'appli **Fichiers**. Android demande d'autoriser l'installation depuis cette source : accepte
   (Paramètres → Applications → accès spécial → Installer des applis inconnues).
3. Sur le PC : 📱 Téléphone → **Afficher le QR code** (le code à 6 chiffres est à côté, valable 2 minutes).
4. Ouvre **NEXUS** sur le téléphone et remplis l'écran d'appairage :
   1. le **nom du téléphone** (il s'affichera sur le PC, dans la liste des appareils) ;
   2. l'**adresse du PC**, affichée dans 📱 Téléphone (ex. `http://192.168.x.x:8765`) ;
   3. le **code à 6 chiffres**. Ne scanne pas le QR code : il ouvrirait le navigateur et utiliserait le code.
5. **Appairer** : NEXUS s'ouvre. L'appairage est gardé ; s'il est révoqué sur le PC, l'écran d'appairage revient.

Play Protect peut avertir « appli inconnue » : c'est normal pour une appli qui ne vient pas du Play Store.

## Ce que fait (et ne fait pas) l'appli

- Une seule permission : Internet. Pas de publicité, pas de statistiques, rien envoyé ailleurs que le PC.
- N'accepte que les adresses du réseau local (192.168.x.x, 10.x.x.x, 172.16 à 31.x.x, *.local / *.lan / *.home).
- PC éteint ou autre réseau : écran « NEXUS injoignable » avec **Réessayer** et **Changer d'adresse**.
- Les liens vers d'autres sites (GitHub…) s'ouvrent dans le navigateur du téléphone.
- Souvenirs : le bouton d'ajout de photo ouvre la galerie du téléphone.

## Construire l'APK (PC Windows)

Prérequis : JDK 17 (`winget install Microsoft.OpenJDK.17`) et le SDK Android en ligne de commande
(plateforme 35, build-tools 35) ; `local.properties` doit contenir `sdk.dir=…` (chemin du SDK).

```bat
cd android
set JAVA_HOME=%LOCALAPPDATA%\Programs\Microsoft\jdk-17.0.10.7-hotspot
gradlew.bat assembleRelease
```

L'APK est dans `app\build\outputs\apk\release\app-release.apk`. La version suit le fichier `VERSION` de NEXUS.

L'APK est signé avec la clé de débogage du SDK (`%USERPROFILE%\.android\debug.keystore`, créée automatiquement) :
pour installer une nouvelle version par-dessus l'ancienne, construis-la sur le **même PC** (sinon Android refuse,
il faut désinstaller l'appli d'abord).
