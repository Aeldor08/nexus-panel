# Signature Authenticode de NEXUS.exe et de l'installeur.
#
# Prérequis : certificat de signature de code (OV/EV) dans le magasin Windows,
# ou fichier .pfx. signtool.exe vient du Windows SDK.
#
# Exemples :
#   powershell -ExecutionPolicy Bypass -File outils\sign_native.ps1 `
#       -Path dist\NEXUS\NEXUS.exe,dist\NEXUS-1.4.1-Setup.exe `
#       -Thumbprint 0123456789ABCDEF...
#
#   powershell -ExecutionPolicy Bypass -File outils\sign_native.ps1 `
#       -Path dist\NEXUS-1.4.1-Setup.exe -Pfx C:\certs\nexus.pfx -PfxPassword "..."

param(
    [Parameter(Mandatory = $true)]
    [string[]]$Path,

    [string]$Thumbprint = "",
    [string]$Pfx = "",
    [string]$PfxPassword = "",
    [string]$TimestampUrl = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"

function Find-SignTool {
    $cmd = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $roots = @(
        (Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"),
        (Join-Path $env:ProgramFiles "Windows Kits\10\bin")
    )
    foreach ($root in $roots) {
        if (Test-Path $root) {
            $hit = Get-ChildItem $root -Recurse -Filter signtool.exe |
                Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' } |
                Sort-Object FullName -Descending |
                Select-Object -First 1
            if ($hit) { return $hit.FullName }
        }
    }
    return $null
}

$signtool = Find-SignTool
if (-not $signtool) {
    throw "signtool.exe introuvable. Installe le Windows SDK (ou signe depuis Visual Studio)."
}

if (-not $Thumbprint -and -not $Pfx) {
    throw "Indique -Thumbprint (certificat du magasin Windows) ou -Pfx/-PfxPassword."
}

$targets = @()
foreach ($item in $Path) {
    foreach ($one in ($item -split ",")) {
        $trimmed = $one.Trim()
        if (-not $trimmed) { continue }
        $full = [System.IO.Path]::GetFullPath($trimmed)
        if (-not (Test-Path $full)) { throw "Fichier introuvable : $full" }
        $targets += $full
    }
}
if (-not $targets) { throw "Aucun fichier à signer." }

foreach ($target in $targets) {
    $signArgs = @("sign", "/fd", "SHA256", "/tr", $TimestampUrl, "/td", "SHA256")
    if ($Thumbprint) {
        $signArgs += @("/sha1", $Thumbprint)
    } else {
        $signArgs += @("/f", $Pfx)
        if ($PfxPassword) { $signArgs += @("/p", $PfxPassword) }
    }
    $signArgs += $target
    Write-Host "Signature : $target"
    & $signtool @signArgs
    if ($LASTEXITCODE -ne 0) { throw "signtool a échoué pour $target (code $LASTEXITCODE)" }
    & $signtool verify /pa /v $target
    if ($LASTEXITCODE -ne 0) { throw "signature invalide pour $target" }
}

Write-Host "Signature terminée : $($targets.Count) fichier(s)."
