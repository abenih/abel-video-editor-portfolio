# Pushes CODE ONLY to the VPS. Never db.sqlite3, never media/ - those live on the
# server and the owner edits them through the site. Overwriting them would destroy
# his work.
#
#   pwsh deploy/push.ps1            # upload + run the provisioner (asks for sudo)
#   pwsh deploy/push.ps1 -NoProvision   # upload only
[CmdletBinding()]
param(
    [string]$Server = 'abeni@153.75.245.152',
    [string]$AppDir = '/home/abeni/apps/kingo-portfolio',
    [switch]$NoProvision
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Push-Location $repo

try {
    $archive = Join-Path $env:TEMP 'kingo-portfolio-code.tar.gz'
    if (Test-Path $archive) { Remove-Item $archive -Force }

    # Deliberately excludes db.sqlite3 and media/.
    $payload = @('manage.py', 'requirements.txt', 'Procfile', 'sandbox', 'portfolio', 'idea', 'deploy')
    foreach ($item in $payload) {
        if (-not (Test-Path $item)) { throw "missing from repo: $item" }
    }

    tar --exclude=__pycache__ --exclude=*.pyc -czf $archive @payload
    if ($LASTEXITCODE -ne 0) { throw 'tar failed' }

    $names = tar -tzf $archive | ForEach-Object { ($_ -split '/')[0] } | Sort-Object -Unique
    if ($names -contains 'db.sqlite3' -or $names -contains 'media') {
        throw 'REFUSING TO PUSH: archive contains live data (db.sqlite3 or media/)'
    }

    $mb = [math]::Round((Get-Item $archive).Length / 1MB, 2)
    Write-Host "code archive: $mb MB -> $($names -join ', ')"

    scp -o BatchMode=yes $archive "${Server}:/tmp/kingo-code.tar.gz"
    if ($LASTEXITCODE -ne 0) { throw 'scp failed' }

    # Extract over the code only; db.sqlite3 and media/ on the server are untouched.
    ssh -o BatchMode=yes $Server "set -e; cd '$AppDir'; tar -xzf /tmp/kingo-code.tar.gz; rm -f /tmp/kingo-code.tar.gz; chmod +x deploy/*.sh; echo 'extracted'; ls db.sqlite3 >/dev/null && echo 'db.sqlite3 still present (untouched)'"
    if ($LASTEXITCODE -ne 0) { throw 'remote extract failed' }

    if ($NoProvision) {
        Write-Host 'uploaded; skipping provision (-NoProvision)'
        return
    }

    Write-Host ''
    Write-Host 'Running the provisioner - type your sudo password in this terminal when asked.'
    ssh -t $Server "cd '$AppDir' && sudo bash deploy/provision-vps.sh"
}
finally {
    Pop-Location
}
