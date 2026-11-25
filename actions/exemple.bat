@echo off
rem Script d'exemple du stream deck NEXUS : il note simplement l'heure dans exemple.log.
rem Mets tes propres scripts (.bat, .cmd, .ps1, .py) dans ce dossier : ils apparaitront dans le mode edition.
echo %date% %time% - script d'exemple lance depuis NEXUS>> "%~dp0exemple.log"
