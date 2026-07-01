param(
    [string]$ApiKey,
    [string]$BaseUrl = "https://api.deepseek.com",
    [string]$Model = "deepseek-v4-flash",
    [switch]$NoLocalFile,
    [switch]$Persist,
    [switch]$StartStreamlit
)

$ErrorActionPreference = "Stop"

function ConvertFrom-SecureStringToPlainText {
    param([securestring]$SecureValue)

    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try {
        [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

function Mask-Secret {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return "<empty>"
    }
    if ($Value.Length -le 8) {
        return "********"
    }
    return "$($Value.Substring(0, 4))****$($Value.Substring($Value.Length - 4))"
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $secureKey = Read-Host "Enter DEEPSEEK_API_KEY" -AsSecureString
    $ApiKey = ConvertFrom-SecureStringToPlainText $secureKey
}

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    throw "DEEPSEEK_API_KEY is empty. Configuration was not changed."
}

$env:DEEPSEEK_API_KEY = $ApiKey
$env:DEEPSEEK_BASE_URL = $BaseUrl
$env:DEEPSEEK_MODEL = $Model

if (-not $NoLocalFile) {
    $envPath = Join-Path $repoRoot ".env"
    $envLines = @(
        "DEEPSEEK_API_KEY=$ApiKey",
        "DEEPSEEK_BASE_URL=$BaseUrl",
        "DEEPSEEK_MODEL=$Model"
    )
    Set-Content -LiteralPath $envPath -Value $envLines -Encoding UTF8
}

if ($Persist) {
    [Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY", $ApiKey, "User")
    [Environment]::SetEnvironmentVariable("DEEPSEEK_BASE_URL", $BaseUrl, "User")
    [Environment]::SetEnvironmentVariable("DEEPSEEK_MODEL", $Model, "User")
}

Write-Host ""
Write-Host "DeepSeek configuration is ready for this PowerShell process."
Write-Host "DEEPSEEK_API_KEY=$(Mask-Secret $ApiKey)"
Write-Host "DEEPSEEK_BASE_URL=$BaseUrl"
Write-Host "DEEPSEEK_MODEL=$Model"

if (-not $NoLocalFile) {
    Write-Host ""
    Write-Host "Configuration was saved to .env in this project."
    Write-Host ".env is ignored by .gitignore and will be loaded automatically by the backend."
}

if ($Persist) {
    Write-Host ""
    Write-Host "Configuration was also saved to the current Windows user environment."
    Write-Host "New terminals and newly started apps will read it automatically."
}

if ($StartStreamlit) {
    Write-Host ""
    Write-Host "Starting Streamlit..."
    python -m streamlit run frontend/app.py
}
else {
    Write-Host ""
    Write-Host "To start the app now, run:"
    Write-Host "python -m streamlit run frontend/app.py"
    Write-Host ""
    Write-Host "Or run this script with -StartStreamlit to configure and launch in one step."
}
