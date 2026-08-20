param(
    [string]$Owner = 'Its-ze',
    [string]$Repo = 'quiltforge',
    [string]$Description = 'Offline Windows studio that turns photos into paintable barn quilt patterns.'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$TokenFile = 'F:\Dropbox\Dev Ops\ITSZ Studio\.secrets\github-token.clixml'

function ConvertFrom-SecureToken([securestring]$SecureToken) {
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureToken)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

function Get-GitHubToken {
    $envToken = [Environment]::GetEnvironmentVariable('GITHUB_TOKEN')
    if (-not [string]::IsNullOrWhiteSpace($envToken)) { return $envToken }
    $path = [Environment]::GetEnvironmentVariable('GITHUB_TOKEN_FILE')
    if ([string]::IsNullOrWhiteSpace($path)) { $path = $TokenFile }
    $secure = Import-Clixml -LiteralPath $path
    if ($secure -isnot [securestring]) { throw 'Stored GitHub token is not a secure string.' }
    return ConvertFrom-SecureToken $secure
}

function Invoke-ProjectGit([string[]]$Arguments) {
    & git -C $Root @Arguments
    if ($LASTEXITCODE -ne 0) { throw "git $($Arguments -join ' ') failed with exit code $LASTEXITCODE" }
}

function Push-WithToken([string]$Token) {
    $askPassCmd = Join-Path ([IO.Path]::GetTempPath()) "quiltforge-askpass-$PID.cmd"
    $askPassPs1 = Join-Path ([IO.Path]::GetTempPath()) "quiltforge-askpass-$PID.ps1"
@'
param([string]$Prompt)
if ($Prompt -match 'Username') { [Console]::Out.WriteLine('x-access-token') }
else { [Console]::Out.WriteLine($env:QUILTFORGE_GITHUB_TOKEN) }
'@ | Set-Content -LiteralPath $askPassPs1 -Encoding UTF8
@"
@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$askPassPs1" "%~1"
"@ | Set-Content -LiteralPath $askPassCmd -Encoding ASCII
    $oldAsk = $env:GIT_ASKPASS
    $oldPrompt = $env:GIT_TERMINAL_PROMPT
    $oldToken = $env:QUILTFORGE_GITHUB_TOKEN
    try {
        $env:GIT_ASKPASS = $askPassCmd
        $env:GIT_TERMINAL_PROMPT = '0'
        $env:QUILTFORGE_GITHUB_TOKEN = $Token
        Invoke-ProjectGit @('push', '-u', 'origin', 'main')
    } finally {
        $env:GIT_ASKPASS = $oldAsk
        $env:GIT_TERMINAL_PROMPT = $oldPrompt
        $env:QUILTFORGE_GITHUB_TOKEN = $oldToken
        Remove-Item -LiteralPath $askPassCmd, $askPassPs1 -Force -ErrorAction SilentlyContinue
    }
}

& (Join-Path $PSScriptRoot 'build-pages.ps1')
$env:PYTHONPATH = 'src'
& (Join-Path $Root '.venv\Scripts\python.exe') -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed; publication stopped.' }

$token = Get-GitHubToken
$headers = @{
    Authorization = "Bearer $token"
    Accept = 'application/vnd.github+json'
    'X-GitHub-Api-Version' = '2022-11-28'
}
$me = Invoke-RestMethod -Headers $headers -Uri 'https://api.github.com/user'
if ($me.login -ne $Owner) { throw "Token belongs to $($me.login), not $Owner." }

$repoBody = @{
    name = $Repo
    description = $Description
    private = $false
    has_issues = $true
    has_projects = $false
    has_wiki = $false
    auto_init = $false
} | ConvertTo-Json
try {
    $remoteRepo = Invoke-RestMethod -Headers $headers -Uri 'https://api.github.com/user/repos' -Method Post -Body $repoBody -ContentType 'application/json'
} catch {
    if ($_.Exception.Response.StatusCode.value__ -ne 422) { throw }
    $remoteRepo = Invoke-RestMethod -Headers $headers -Uri "https://api.github.com/repos/$Owner/$Repo"
}

if (-not (Test-Path -LiteralPath (Join-Path $Root '.git'))) { Invoke-ProjectGit @('init', '-b', 'main') }
else { Invoke-ProjectGit @('branch', '-M', 'main') }
if ([string]::IsNullOrWhiteSpace((& git -C $Root config user.name))) { Invoke-ProjectGit @('config', 'user.name', $me.login) }
if ([string]::IsNullOrWhiteSpace((& git -C $Root config user.email))) { Invoke-ProjectGit @('config', 'user.email', "$($me.id)+$($me.login)@users.noreply.github.com") }

$publishPaths = @(
    '.github', '.gitignore', 'LICENSE.txt', 'README.md', 'docs', 'installer', 'launcher.py',
    'pyproject.toml', 'requirements-build.txt', 'scripts', 'site', 'src', 'tests'
)
Invoke-ProjectGit (@('add', '--') + $publishPaths)
& git -C $Root diff --cached --quiet
if ($LASTEXITCODE -eq 0) { Write-Host 'No source changes to commit.' }
elseif ($LASTEXITCODE -eq 1) { Invoke-ProjectGit @('commit', '-m', 'Launch QuiltForge Barn Quilt Studio') }
else { throw "git diff --cached --quiet failed with exit code $LASTEXITCODE" }

if ((& git -C $Root remote) -contains 'origin') { Invoke-ProjectGit @('remote', 'set-url', 'origin', $remoteRepo.clone_url) }
else { Invoke-ProjectGit @('remote', 'add', 'origin', $remoteRepo.clone_url) }
Push-WithToken $token

$pagesBody = @{ build_type = 'workflow' } | ConvertTo-Json
try {
    Invoke-RestMethod -Headers $headers -Uri "https://api.github.com/repos/$Owner/$Repo/pages" -Method Post -Body $pagesBody -ContentType 'application/json' | Out-Null
} catch {
    if ($_.Exception.Response.StatusCode.value__ -notin 409, 422) { throw }
}

Write-Host "Repository: $($remoteRepo.html_url)"
Write-Host "Pages: https://$($Owner.ToLower()).github.io/$Repo/"
