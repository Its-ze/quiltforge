param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$Version = '1.0.0'

if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Run: py -3.11 -m venv .venv"
}

Push-Location $ProjectRoot
try {
    $env:PYTHONPATH = 'src'
    & $Python -m pytest -q
    & $Python scripts\build-assets.py

    & $Python -m PyInstaller `
        --noconfirm `
        --clean `
        --windowed `
        --name QuiltForge `
        --icon "$ProjectRoot\src\quiltforge\resources\quiltforge.ico" `
        --version-file "$ProjectRoot\scripts\version-info.txt" `
        --paths "$ProjectRoot\src" `
        --add-data "$ProjectRoot\src\quiltforge\resources;quiltforge\resources" `
        --distpath "$ProjectRoot\dist" `
        --workpath "$ProjectRoot\build\pyinstaller" `
        --specpath "$ProjectRoot\build" `
        "$ProjectRoot\launcher.py"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

    Copy-Item LICENSE.txt dist\QuiltForge\LICENSE.txt -Force
    $Portable = "dist\QuiltForge-Portable-$Version.zip"
    if (Test-Path $Portable) { Remove-Item -LiteralPath $Portable -Force }
    Compress-Archive -Path dist\QuiltForge\* -DestinationPath $Portable -CompressionLevel Optimal

    if (-not $SkipInstaller) {
        $Candidates = @(
            "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
            "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
            "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
        )
        $Iscc = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
        if (-not $Iscc) { throw 'Inno Setup 6 was not found. Install it or run with -SkipInstaller.' }
        & $Iscc installer\QuiltForge.iss
    }

    Get-FileHash dist\QuiltForge-Portable-$Version.zip -Algorithm SHA256
    if (Test-Path "dist\QuiltForge-Setup-$Version.exe") {
        Get-FileHash "dist\QuiltForge-Setup-$Version.exe" -Algorithm SHA256
    }
}
finally {
    Pop-Location
}
