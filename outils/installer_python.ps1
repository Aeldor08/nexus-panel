# Installe (ou refait) le Python prive de NEXUS dans runtime\ : NEXUS ne depend plus du Python installe sur Windows
# (une desinstallation ou un passage a une autre version de Python ne le casse plus).
# Lance par installer.bat et lancer.bat. Usage :
#   powershell -NoProfile -ExecutionPolicy Bypass -File outils\installer_python.ps1 [-SiBesoin] [-Paquet chemin.nupkg]
#   -SiBesoin : ne fait rien si runtime\ est deja a la bonne version (outils\python-prive.json)
#   -Paquet   : utilise ce paquet deja telecharge au lieu de le telecharger (tests, installation hors ligne) ;
#               meme chose avec la variable d'environnement NEXUS_PAQUET_PYTHON (l'empreinte est toujours verifiee)
# Etapes : telechargement (nuget.org, paquet officiel de la Python Software Foundation) -> verification SHA256 ->
# extraction dans runtime.neuf\ -> dependances (requirements.txt) -> test -> runtime.neuf\ remplace runtime\.
# L'ancien runtime\ n'est remplace qu'une fois le nouveau pret et teste. Code de sortie 0 = pret.
param([switch]$SiBesoin, [string]$Paquet = "")

$ErrorActionPreference = "Stop"
# Python prive = rien d'exterieur : ni les paquets installes « pour l'utilisateur », ni un PYTHONPATH de Windows
$env:PYTHONNOUSERSITE = "1"; $env:PYTHONPATH = $null; $env:PYTHONHOME = $null
if (-not $Paquet -and $env:NEXUS_PAQUET_PYTHON) { $Paquet = $env:NEXUS_PAQUET_PYTHON }   # hors ligne, tests
$Dossier = Split-Path -Parent $PSScriptRoot
$Pins = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot "python-prive.json") | ConvertFrom-Json
$Version = $Pins.version
$Runtime = Join-Path $Dossier "runtime"
$Neuf = Join-Path $Dossier "runtime.neuf"
$Tmp = Join-Path $Dossier "runtime.tmp"
$Marque = Join-Path $Runtime "VERSION-PYTHON"

if ($SiBesoin -and (Test-Path -LiteralPath (Join-Path $Runtime "python.exe")) -and (Test-Path -LiteralPath $Marque)) {
    if ((Get-Content -LiteralPath $Marque -TotalCount 1).Trim() -eq $Version) { exit 0 }
}

function Retirer([string]$Chemin) {
    # un dossier encore utilise (NEXUS ouvert) ne peut pas etre retire : on reessaie quelques secondes
    for ($i = 0; $i -lt 10; $i++) {
        if (-not (Test-Path -LiteralPath $Chemin)) { return }
        try { Remove-Item -LiteralPath $Chemin -Recurse -Force -ErrorAction Stop; return } catch { Start-Sleep -Milliseconds 700 }
    }
    throw "impossible de remplacer $Chemin : NEXUS est-il encore ouvert ? (icone pres de l'horloge > Quitter NEXUS)"
}

function Nettoyer { foreach ($d in @($Neuf, $Tmp)) { try { Retirer $d } catch { } } }

try {
    Write-Host ""
    Write-Host "Installation du Python prive de NEXUS ($Version) dans runtime\ ..."
    Nettoyer
    New-Item -ItemType Directory -Force -Path $Tmp | Out-Null
    $Zip = Join-Path $Tmp "python.zip"
    if ($Paquet) {
        Copy-Item -LiteralPath $Paquet -Destination $Zip
    } else {
        Write-Host "  Telechargement de Python $Version ($($Pins.taille_mo) Mo, nuget.org, une seule fois)..."
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $ProgressPreference = "SilentlyContinue"
        Invoke-WebRequest -UseBasicParsing -Uri $Pins.url -OutFile $Zip
    }
    $Empreinte = (Get-FileHash -Algorithm SHA256 -LiteralPath $Zip).Hash
    if ($Empreinte -ne $Pins.sha256.ToUpper()) {
        throw "empreinte SHA256 inattendue ($Empreinte) : fichier abime ou modifie, installation annulee"
    }
    Write-Host "  [OK] Paquet verifie (SHA256)"

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($Zip, (Join-Path $Tmp "x"))
    Move-Item -LiteralPath (Join-Path $Tmp "x\tools") -Destination $Neuf
    $Py = Join-Path $Neuf "python.exe"

    Write-Host "  Installation des dependances (1 a 3 minutes la premiere fois)..."
    $ErrorActionPreference = "Continue"          # pip ecrit ses avertissements sur stderr : ce n'est pas une erreur
    & $Py -m pip install --disable-pip-version-check --no-warn-script-location -q -r (Join-Path $Dossier "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "l'installation des dependances a echoue (connexion Internet ?)" }
    & $Py -c "import fastapi, uvicorn, psutil, PIL, pystray, keyring, pycaw, qrcode, discord; print('  [OK] Python prive teste')"
    if ($LASTEXITCODE -ne 0) { throw "le test du Python prive a echoue" }
    $ErrorActionPreference = "Stop"

    Copy-Item -LiteralPath (Join-Path $Dossier "requirements.txt") -Destination (Join-Path $Neuf "requirements.installe")
    Set-Content -LiteralPath (Join-Path $Neuf "VERSION-PYTHON") -Value $Version -Encoding ASCII
    Retirer $Runtime
    Move-Item -LiteralPath $Neuf -Destination $Runtime
    Retirer $Tmp
    Write-Host "[OK] Python prive de NEXUS pret : runtime\ (Python $Version)"
    exit 0
} catch {
    Write-Host "[ERREUR] Python prive de NEXUS : $($_.Exception.Message)"
    Nettoyer
    exit 1
}
