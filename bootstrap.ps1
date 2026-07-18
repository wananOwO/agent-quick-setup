$ErrorActionPreference = "Stop"

$repository = if ($env:AGENT_SETUP_REPOSITORY) { $env:AGENT_SETUP_REPOSITORY } else { "wananOwO/agent-quick-setup" }
$branch = if ($env:AGENT_SETUP_BRANCH) { $env:AGENT_SETUP_BRANCH } else { "main" }
$archiveUrl = if ($env:AGENT_SETUP_ARCHIVE_URL) {
    $env:AGENT_SETUP_ARCHIVE_URL
} else {
    "https://github.com/$repository/archive/refs/heads/$branch.zip"
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("agent-quick-setup-" + [guid]::NewGuid().ToString("N"))
$archivePath = Join-Path $tempRoot "source.zip"

try {
    New-Item -ItemType Directory -Path $tempRoot | Out-Null
    Write-Host "Downloading Agent Quick Setup from $repository..."
    Invoke-WebRequest -UseBasicParsing -Uri $archiveUrl -OutFile $archivePath
    Expand-Archive -LiteralPath $archivePath -DestinationPath $tempRoot -Force

    $projectFile = Get-ChildItem -Path $tempRoot -Filter "pyproject.toml" -File -Recurse | Select-Object -First 1
    if (-not $projectFile) {
        throw "Downloaded archive does not contain pyproject.toml."
    }
    $projectRoot = $projectFile.Directory.FullName

    if ($env:AGENT_SETUP_DOWNLOAD_ONLY -eq "1") {
        Write-Host "Download and extraction verified: $projectRoot"
    } else {
        & (Join-Path $projectRoot "install.cmd")
        if ($LASTEXITCODE -ne 0) {
            throw "Agent Quick Setup exited with code $LASTEXITCODE."
        }
    }
} finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
