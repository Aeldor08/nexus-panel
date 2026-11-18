param(
    [Parameter(Mandatory = $true)]
    [string]$Job
)

# Helper de mise à jour native de NEXUS.
# Lancé par maj_natif.py avec un fichier de travail JSON. Il attend la fin de
# NEXUS, lance l'installeur Inno en silence, relance l'application et vérifie
# qu'elle écrit bien maj/demarrage_ok.json. En cas d'échec, il remet la
# sauvegarde de l'installation précédente et relance l'ancienne version.
#
# Aucun chemin n'est interprété par un shell : tout vient du JSON, et les
# appels à Start-Process / Copy-Item utilisent des chemins littéraux.

$ErrorActionPreference = "Stop"
$j = Get-Content -LiteralPath $Job -Raw -Encoding UTF8 | ConvertFrom-Json

function Write-Log([string]$Message) {
    try {
        $ligne = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
        Add-Content -LiteralPath $j.log -Value $ligne -Encoding UTF8
    } catch {
        # Le journal ne doit jamais empêcher la mise à jour.
    }
}

function Write-JsonFile([string]$Chemin, $Donnees) {
    $json = $Donnees | ConvertTo-Json -Depth 8
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Chemin, $json, $utf8)
}

function Write-Result([bool]$Ok, [string]$Type, [string]$Message) {
    $donnees = [ordered]@{
        ok         = $Ok
        type       = $Type
        de         = [string]$j.from_version
        vers       = [string]$j.expected_version
        date       = [double]([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())
        message    = $Message
        journalise = $false
    }
    Write-JsonFile -Chemin $j.result -Donnees $donnees
    Write-Log ("Résultat : " + $Message)
}

function Stop-Nexus {
    # Laisse à NEXUS le temps de s'arrêter proprement, puis force si besoin.
    $limite = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $limite) {
        $restants = @(Get-Process -Name "NEXUS" -ErrorAction SilentlyContinue)
        if ($restants.Count -eq 0) {
            Start-Sleep -Milliseconds 800      # laisse WebView2 et les DLL se libérer
            return
        }
        foreach ($p in $restants) {
            try { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } catch { }
        }
        Start-Sleep -Milliseconds 500
    }
}

function Wait-Parent {
    try {
        $parent = Get-Process -Id ([int]$j.parent_pid) -ErrorAction SilentlyContinue
        if ($parent) { $null = $parent.WaitForExit(30000) }
    } catch {
        # Déjà arrêté : continue.
    }
}

function Test-Marker {
    if (-not (Test-Path -LiteralPath $j.marker)) { return $false }
    try {
        $m = Get-Content -LiteralPath $j.marker -Raw -Encoding UTF8 | ConvertFrom-Json
        return ([string]$m.version -eq [string]$j.expected_version) -and
               ([double]$m.date -ge [double]$j.started)
    } catch {
        return $false
    }
}

function Wait-Marker([int]$Timeout) {
    $limite = (Get-Date).AddSeconds($Timeout)
    while ((Get-Date) -lt $limite) {
        Start-Sleep -Seconds 2
        if (Test-Marker) { return $true }
    }
    return $false
}

function Start-App {
    if (-not (Test-Path -LiteralPath $j.app_exe)) {
        throw "exécutable introuvable : $($j.app_exe)"
    }
    $arguments = @()
    if ($j.restart_args) { $arguments = @($j.restart_args) }
    if ($arguments.Count -gt 0) {
        Start-Process -FilePath $j.app_exe -WorkingDirectory $j.app_dir -ArgumentList $arguments | Out-Null
    } else {
        Start-Process -FilePath $j.app_exe -WorkingDirectory $j.app_dir | Out-Null
    }
    Write-Log "NEXUS relancé : $($j.app_exe)"
}

function Restore-App {
    if (-not (Test-Path -LiteralPath $j.backup_dir)) {
        throw "sauvegarde introuvable : $($j.backup_dir)"
    }
    Stop-Nexus
    Get-ChildItem -LiteralPath $j.app_dir -Force -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction Stop
    }
    Get-ChildItem -LiteralPath $j.backup_dir -Force -ErrorAction Stop | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $j.app_dir -Recurse -Force -ErrorAction Stop
    }
    Write-Log "Ancienne installation restaurée depuis $($j.backup_dir)"
}

function Clear-Travail {
    Remove-Item -LiteralPath $j.marker -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $Job -Force -ErrorAction SilentlyContinue
}

function Install-NouvelleVersion {
    $ligne = '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /DIR="' +
             [string]$j.app_dir + '" /LOG="' + [string]$j.installer_log + '"'
    Write-Log "Installeur : $($j.installer)"
    $p = Start-Process -FilePath $j.installer -ArgumentList $ligne -Wait -PassThru
    Write-Log "Installeur terminé, code $($p.ExitCode)"
    if ($p.ExitCode -notin @(0, 3010)) {
        throw "l'installeur a échoué (code $($p.ExitCode))"
    }
    if (-not (Test-Path -LiteralPath $j.app_exe)) {
        throw "l'installeur n'a pas remis NEXUS.exe en place"
    }
}

try {
    Write-Log "Début de la mise à jour ($($j.action), $($j.from_version) -> $($j.expected_version))"
    Wait-Parent
    Stop-Nexus

    if ($j.action -eq "restore") {
        Restore-App
        Start-App
        if (Wait-Marker ([int]$j.timeout)) {
            Write-Result $true "retour" ("Retour à la version " + $j.expected_version + " effectué (tes données sont conservées).")
            Clear-Travail
            exit 0
        }
        throw "la version restaurée n'a pas confirmé son démarrage"
    }

    Install-NouvelleVersion
    Start-App
    if (Wait-Marker ([int]$j.timeout)) {
        $note = ""
        if ($j.signature_note) { $note = " " + ([string]$j.signature_note).TrimEnd(".") + "." }
        Write-Result $true "installation" ("Mise à jour vers la version " + $j.expected_version + " réussie." + $note)
        Clear-Travail
        try {
            Remove-Item -LiteralPath (Split-Path -Path $j.installer -Parent) -Recurse -Force -ErrorAction SilentlyContinue
        } catch { }
        exit 0
    }

    throw "la nouvelle version n'a pas confirmé son démarrage"
} catch {
    $erreur = $_.Exception.Message
    Write-Log "ERREUR : $erreur"
    try {
        if ($j.action -eq "install") {
            Stop-Nexus
            Restore-App
            Start-App
            $message = "La mise à jour vers la version $($j.expected_version) a échoué : $erreur. " +
                       "La version $($j.from_version) a été restaurée automatiquement."
            Write-Result $false "rollback" $message
        } else {
            $message = "Le retour à la version $($j.expected_version) a échoué ($erreur)."
            Write-Result $false "retour" $message
        }
    } catch {
        $seconde = $_.Exception.Message
        Write-Log "ERREUR pendant la restauration : $seconde"
        Write-Result $false "rollback" ("Mise à jour impossible ($erreur) et restauration impossible ($seconde). " +
                                      "Réinstalle NEXUS avec l'installeur de la version voulue.")
    }
    Clear-Travail
    exit 1
}
