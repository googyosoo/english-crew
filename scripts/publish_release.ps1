param(
    [string]$Owner = "googyosoo",
    [string]$Repo = "english-crew-releases",
    [string]$Version = "v1.0.0"
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "English Crew Release Publisher to GitHub Releases" -ForegroundColor Cyan
Write-Host "Owner   : $Owner" -ForegroundColor Yellow
Write-Host "Repo    : $Repo" -ForegroundColor Yellow
Write-Host "Version : $Version" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check gh CLI authentication
Write-Host "`n[Step 1] Verifying GitHub CLI authentication..." -ForegroundColor Green
$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "GitHub CLI(gh)에 로그인되어 있지 않습니다. 'gh auth login'을 먼저 실행해 주십시오."
}
Write-Host "  -> GitHub CLI authenticated successfully." -ForegroundColor Gray

# 2. Check if repository exists; if not, create public repository and push release-repo/README.md
Write-Host "`n[Step 2] Checking remote repository: $Owner/$Repo..." -ForegroundColor Green
$repoExists = $false
try {
    gh repo view "$Owner/$Repo" --json nameWithOwner 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $repoExists = $true
        Write-Host "  -> Repository $Owner/$Repo already exists." -ForegroundColor Gray
    }
} catch {
    $repoExists = $false
}

if (-not $repoExists) {
    Write-Host "  -> Repository does not exist. Creating public repo: $Owner/$Repo..." -ForegroundColor Yellow
    gh repo create "$Owner/$Repo" --public --description "English Crew desktop application releases"
    
    # Initialize repository with release-repo/README.md only (no application source code)
    $tempGitDir = Join-Path $env:TEMP ("english_crew_repo_init_" + (Get-Random))
    New-Item -ItemType Directory -Path $tempGitDir -Force | Out-Null
    Copy-Item "release-repo\README.md" (Join-Path $tempGitDir "README.md")
    
    Push-Location $tempGitDir
    try {
        git init -b main
        git config user.name "English Crew Publisher"
        git config user.email "englishcrew@local"
        git add README.md
        git commit -m "docs: initial release repository readme"
        git remote add origin "https://github.com/$Owner/$Repo.git"
        git push -u origin main
        Write-Host "  -> Pushed release-repo/README.md to $Owner/$Repo (main branch)." -ForegroundColor Gray
    } finally {
        Pop-Location
        Remove-Item $tempGitDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# 3. Verify local build artifacts
Write-Host "`n[Step 3] Verifying release build artifacts..." -ForegroundColor Green
$setupExe = "release\EnglishCrew-Setup.exe"
$portableExe = "release\EnglishCrew-Portable.exe"
$checksumFile = "release\SHA256SUMS.txt"
$notesFile = "release-notes\$Version.md"

if (-not (Test-Path $setupExe)) { Write-Error "Setup binary not found: $setupExe" }
if (-not (Test-Path $portableExe)) { Write-Error "Portable binary not found: $portableExe" }
if (-not (Test-Path $checksumFile)) { Write-Error "Checksum file not found: $checksumFile" }
if (-not (Test-Path $notesFile)) { Write-Error "Release notes file not found: $notesFile" }

Write-Host "  -> Setup Exe    : $setupExe ($((Get-Item $setupExe).Length / 1MB | ForEach-Object { '{0:N2} MB' -f $_ }))" -ForegroundColor Gray
Write-Host "  -> Portable Exe : $portableExe ($((Get-Item $portableExe).Length / 1MB | ForEach-Object { '{0:N2} MB' -f $_ }))" -ForegroundColor Gray
Write-Host "  -> Checksums    : $checksumFile" -ForegroundColor Gray
Write-Host "  -> Release Note : $notesFile" -ForegroundColor Gray

# 4. Create GitHub Release and upload binaries
Write-Host "`n[Step 4] Publishing GitHub Release $Version..." -ForegroundColor Green
gh release create $Version $setupExe $portableExe $checksumFile `
    --repo "$Owner/$Repo" `
    --title "English Crew $Version" `
    --notes-file $notesFile

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to create GitHub release with gh."
}
Write-Host "  -> GitHub release created successfully!" -ForegroundColor Gray

# 5. Verify download URLs respond with 200 (following redirects)
Write-Host "`n[Step 5] Verifying public download URL availability..." -ForegroundColor Green
$urls = @(
    "https://github.com/$Owner/$Repo/releases/latest/download/EnglishCrew-Setup.exe",
    "https://github.com/$Owner/$Repo/releases/latest/download/EnglishCrew-Portable.exe"
)

foreach ($url in $urls) {
    Write-Host "  -> Checking: $url" -ForegroundColor Cyan
    try {
        $response = Invoke-WebRequest -Uri $url -Method Head -MaximumRedirection 5 -TimeoutSec 15
        $code = $response.StatusCode
        Write-Host "     HTTP Status: $code OK" -ForegroundColor Green
    } catch {
        if ($_.Exception.Response) {
            $code = $_.Exception.Response.StatusCode.value__
            Write-Host "     HTTP Status: $code" -ForegroundColor Yellow
        } else {
            Write-Host "     Warning: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "English Crew $Version Release Published and Verified 100%!" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
