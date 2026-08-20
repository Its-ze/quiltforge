$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Source = Join-Path $Root 'site'
$Destination = Join-Path $Root 'docs'

if (-not (Test-Path -LiteralPath $Source)) {
    throw "Site source not found: $Source"
}
if (-not (Test-Path -LiteralPath $Destination)) {
    New-Item -ItemType Directory -Path $Destination | Out-Null
}
Get-ChildItem -LiteralPath $Destination -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Copy-Item -Path (Join-Path $Source '*') -Destination $Destination -Recurse -Force
Copy-Item -LiteralPath (Join-Path $Source '.nojekyll') -Destination (Join-Path $Destination '.nojekyll') -Force
Write-Host "Prepared GitHub Pages files in $Destination"

