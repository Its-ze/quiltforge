param(
    [string]$Owner = 'Its-ze',
    [string]$Repo = 'quiltforge',
    [string]$Version = '1.0.0'
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
    $path = [Environment]::GetEnvironmentVariable('GITHUB_TOKEN_FILE')
    if ([string]::IsNullOrWhiteSpace($path)) { $path = $TokenFile }
    $secure = Import-Clixml -LiteralPath $path
    if ($secure -isnot [securestring]) { throw 'Stored GitHub token is not a secure string.' }
    return ConvertFrom-SecureToken $secure
}

function Upload-ReleaseAsset([hashtable]$Headers, [string]$UploadUrl, [string]$Path, [string]$ContentType) {
    $name = [IO.Path]::GetFileName($Path)
    $uri = ($UploadUrl -replace '\{\?name,label\}', '') + "?name=$([uri]::EscapeDataString($name))"
    Invoke-RestMethod -Headers $Headers -Uri $uri -Method Post -InFile $Path -ContentType $ContentType | Out-Null
}

$installer = Join-Path $Root "dist\QuiltForge-Setup-$Version.exe"
$portable = Join-Path $Root "dist\QuiltForge-Portable-$Version.zip"
foreach ($path in @($installer, $portable)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Release artifact missing: $path" }
}
$checksums = Join-Path $Root 'dist\checksums.txt'
@(
    "$(Get-FileHash -LiteralPath $installer -Algorithm SHA256 | Select-Object -ExpandProperty Hash)  $([IO.Path]::GetFileName($installer))",
    "$(Get-FileHash -LiteralPath $portable -Algorithm SHA256 | Select-Object -ExpandProperty Hash)  $([IO.Path]::GetFileName($portable))"
) | Set-Content -LiteralPath $checksums -Encoding ASCII

$token = Get-GitHubToken
$headers = @{
    Authorization = "Bearer $token"
    Accept = 'application/vnd.github+json'
    'X-GitHub-Api-Version' = '2022-11-28'
}
$tag = "v$Version"
$releaseBody = @{
    tag_name = $tag
    target_commitish = 'main'
    name = "QuiltForge $tag"
    body = @"
Initial Windows release of QuiltForge Barn Quilt Studio.

- Turn photographs into Blocks, Triangles, or Diamonds
- Adjust the grid, paint palette, and board measurements
- Autosave and reopen local projects
- Export numbered PNG, SVG, and printable PDF paint guides
- Includes a complete Windows installer and portable build

QuiltForge processes images locally and does not require an account or internet connection.
"@
    draft = $false
    prerelease = $false
} | ConvertTo-Json
try {
    $release = Invoke-RestMethod -Headers $headers -Uri "https://api.github.com/repos/$Owner/$Repo/releases" -Method Post -Body $releaseBody -ContentType 'application/json'
} catch {
    if ($_.Exception.Response.StatusCode.value__ -ne 422) { throw }
    $release = Invoke-RestMethod -Headers $headers -Uri "https://api.github.com/repos/$Owner/$Repo/releases/tags/$tag"
}

$assetPaths = @($installer, $portable, $checksums)
$assetNames = $assetPaths | ForEach-Object { [IO.Path]::GetFileName($_) }
foreach ($asset in @($release.assets)) {
    if ($assetNames -contains $asset.name) {
        Invoke-RestMethod -Headers $headers -Uri "https://api.github.com/repos/$Owner/$Repo/releases/assets/$($asset.id)" -Method Delete | Out-Null
    }
}
Upload-ReleaseAsset $headers $release.upload_url $installer 'application/vnd.microsoft.portable-executable'
Upload-ReleaseAsset $headers $release.upload_url $portable 'application/zip'
Upload-ReleaseAsset $headers $release.upload_url $checksums 'text/plain'
Write-Host "Release: $($release.html_url)"

