# Soomgo Agent - Windows PowerShell Installer
# Usage: powershell -c "irm https://raw.githubusercontent.com/jungeol66104/soomgo-agent/main/scripts/install.ps1 | iex"

$ErrorActionPreference = "Stop"

# Configuration
$GITHUB_REPO = "jungeol66104/soomgo-agent"
$VERSION = "0.1.0"
$PACKAGE_NAME = "soomgo_agent-$VERSION.tar.gz"
$DOWNLOAD_URL = "https://github.com/$GITHUB_REPO/releases/download/v$VERSION/$PACKAGE_NAME"
$DATA_URL = "https://github.com/$GITHUB_REPO/releases/download/v$VERSION/data.tar.gz"

# Banner
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "  Soomgo Agent Installer" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Detect OS
Write-Host "Detected: Windows" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check/Install uv
Write-Host "Checking for uv package manager..." -ForegroundColor Cyan

if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "✓ uv is already installed" -ForegroundColor Green
} else {
    Write-Host "Installing uv..." -ForegroundColor Yellow
    irm https://astral.sh/uv/install.ps1 | iex

    # Refresh PATH for current session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Host "✓ uv installed successfully" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to install uv" -ForegroundColor Red
        Write-Host "Please restart your terminal and try again" -ForegroundColor Yellow
        exit 1
    }
}

# Step 2: Download package
Write-Host ""
Write-Host "Downloading Soomgo Agent..." -ForegroundColor Cyan

$TEMP_DIR = New-TemporaryFile | %{ Remove-Item $_; New-Item -ItemType Directory -Path $_ }
$PACKAGE_PATH = Join-Path $TEMP_DIR $PACKAGE_NAME

try {
    Invoke-WebRequest -Uri $DOWNLOAD_URL -OutFile $PACKAGE_PATH
    Write-Host "✓ Package downloaded" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to download package" -ForegroundColor Red
    Write-Host "URL: $DOWNLOAD_URL" -ForegroundColor Yellow
    exit 1
}

# Step 3: Install package
Write-Host ""
Write-Host "Installing Soomgo Agent..." -ForegroundColor Cyan

try {
    uv tool install $PACKAGE_PATH --force
    Write-Host "✓ Soomgo Agent installed" -ForegroundColor Green
} catch {
    Write-Host "✗ Installation failed" -ForegroundColor Red
    exit 1
}

# Cleanup package temp
Remove-Item -Recurse -Force $TEMP_DIR

# Step 4: Download conversation data
Write-Host ""
Write-Host "Downloading conversation data (this may take a few minutes)..." -ForegroundColor Cyan

$DATA_TEMP_DIR = New-TemporaryFile | %{ Remove-Item $_; New-Item -ItemType Directory -Path $_ }
$DATA_PATH = Join-Path $DATA_TEMP_DIR "data.tar.gz"

try {
    Invoke-WebRequest -Uri $DATA_URL -OutFile $DATA_PATH
    Write-Host "✓ Data downloaded" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to download data" -ForegroundColor Red
    Write-Host "URL: $DATA_URL" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Installation failed. The app requires conversation data to function." -ForegroundColor Red
    exit 1
}

# Step 5: Extract data (requires tar, available in Windows 10+)
if (Test-Path $DATA_PATH) {
    Write-Host ""
    Write-Host "Extracting data..." -ForegroundColor Cyan

    $SOOMGO_DIR = Join-Path $env:USERPROFILE ".soomgo"
    New-Item -ItemType Directory -Force -Path $SOOMGO_DIR | Out-Null

    # Check if tar is available
    if (-not (Get-Command tar -ErrorAction SilentlyContinue)) {
        Write-Host "✗ tar command not found. Windows 10+ required." -ForegroundColor Red
        Write-Host "Please upgrade to Windows 10 or later, or extract manually" -ForegroundColor Yellow
        exit 1
    }

    # Extract with error checking
    $extractOutput = tar -xzf $DATA_PATH -C $SOOMGO_DIR 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Failed to extract data" -ForegroundColor Red
        Write-Host "Error: $extractOutput" -ForegroundColor Red
        exit 1
    }

    # Validate critical files exist
    $criticalFiles = @(
        "$SOOMGO_DIR\data\knowledge\structured\services.json",
        "$SOOMGO_DIR\data\knowledge\structured\policies.json",
        "$SOOMGO_DIR\data\chat_list_master.jsonl"
    )

    $missingFiles = @()
    foreach ($file in $criticalFiles) {
        if (-not (Test-Path $file)) {
            $missingFiles += $file
        }
    }

    if ($missingFiles.Count -gt 0) {
        Write-Host "✗ Data extraction incomplete. Missing files:" -ForegroundColor Red
        foreach ($file in $missingFiles) {
            Write-Host "  - $file" -ForegroundColor Red
        }
        Write-Host ""
        Write-Host "Installation failed. Please report this issue at:" -ForegroundColor Yellow
        Write-Host "https://github.com/$GITHUB_REPO/issues" -ForegroundColor Yellow
        exit 1
    }

    Write-Host "✓ Data extracted and validated successfully" -ForegroundColor Green

    # Cleanup data temp
    Remove-Item -Recurse -Force $DATA_TEMP_DIR
}

# Step 6: Verify installation
Write-Host ""
Write-Host "Verifying installation..." -ForegroundColor Cyan

# Refresh PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

if (Get-Command soomgo -ErrorAction SilentlyContinue) {
    Write-Host "✓ soomgo command is available" -ForegroundColor Green
    $VERSION_OUTPUT = soomgo --version 2>&1
    Write-Host "✓ Installed: $VERSION_OUTPUT" -ForegroundColor Green
} else {
    Write-Host "⚠ soomgo command not found in PATH" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please restart your terminal for the changes to take effect" -ForegroundColor Yellow
    Write-Host ""
}

# Success message
Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "Get started:" -ForegroundColor White
Write-Host "  soomgo" -ForegroundColor Cyan -NoNewline
Write-Host "  - Launch the app" -ForegroundColor White
Write-Host ""
Write-Host "Need help? Visit: https://github.com/$GITHUB_REPO" -ForegroundColor White
Write-Host ""
Write-Host "Note: If 'soomgo' command is not found, please restart your terminal" -ForegroundColor Yellow
Write-Host ""
