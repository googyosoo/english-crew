param(
    [string]$Owner = "googyosoo"
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Preparing Firebase Hosting HTML with GitHub Owner: $Owner" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$htmlPath = "hosting\index.html"
if (-not (Test-Path $htmlPath)) {
    Write-Error "Target HTML file not found: $htmlPath"
}

$content = Get-Content $htmlPath -Raw -Encoding utf8

# Replace placeholder with specified Owner
$newContent = [System.Text.RegularExpressions.Regex]::Replace(
    $content,
    "https://github\.com/[^/]+/english-crew-releases",
    "https://github.com/$Owner/english-crew-releases"
)

# Also replace __OWNER__ placeholder directly
$newContent = $newContent.Replace("__OWNER__", $Owner)

Set-Content -Path $htmlPath -Value $newContent -Encoding utf8

Write-Host "PASS: Successfully updated hosting/index.html with Owner '$Owner'!" -ForegroundColor Green

# Output matching download lines for verification
$lines = $newContent -split "`n" | Where-Object { $_ -match "https://github\.com/$Owner/english-crew-releases" }
foreach ($line in $lines) {
    Write-Host "  -> $($line.Trim())" -ForegroundColor Gray
}
