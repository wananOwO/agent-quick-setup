param(
  [string[]]$Agent,
  [switch]$Yes,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Refresh-ProcessPath {
  $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
  $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
  $currentPath = [Environment]::GetEnvironmentVariable("Path", "Process")
  $env:Path = @($machinePath, $userPath, $currentPath) -join ";"
}

function Find-WorkingPython {
  if ($env:AGENT_SETUP_PYTHON) {
    $candidateNames = @($env:AGENT_SETUP_PYTHON)
  } else {
    $candidateNames = @("py", "python", "python3")
    $userPythonPattern = Join-Path $env:LOCALAPPDATA "Programs\Python\Python*\python.exe"
    $candidateNames += @(Get-ChildItem -Path $userPythonPattern -File -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | ForEach-Object FullName)
    if ($env:ProgramFiles) {
      $systemPythonPattern = Join-Path $env:ProgramFiles "Python*\python.exe"
      $candidateNames += @(Get-ChildItem -Path $systemPythonPattern -File -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | ForEach-Object FullName)
    }
  }

  foreach ($candidateName in $candidateNames) {
    $candidate = Get-Command $candidateName -ErrorAction SilentlyContinue
    if (-not $candidate) { continue }

    $versionOutput = (& $candidate.Source --version 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { continue }
    if ($versionOutput -notmatch '^Python\s+(\d+)\.(\d+)') { continue }

    $major = [int]$Matches[1]
    $minor = [int]$Matches[2]
    if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 9)) {
      return $candidate
    }
  }

  return $null
}

Refresh-ProcessPath
$python = Find-WorkingPython
if (-not $python) {
  if ($env:AGENT_SETUP_NO_BOOTSTRAP -eq "1") {
    throw "No working Python 3.9+ interpreter was found. Install Python from https://www.python.org/downloads/ and retry."
  }

  $winget = Get-Command winget -ErrorAction SilentlyContinue
  if (-not $winget) {
    throw "No working Python 3.9+ interpreter or winget was found. Install Python from https://www.python.org/downloads/ and retry."
  }

  Write-Host "Python 3.9+ is required and was not found."
  Write-Host "The following command will be used:"
  Write-Host "  winget install --id Python.Python.3.12 --exact --source winget"
  if ($env:AGENT_SETUP_ASSUME_YES -eq "1") {
    $answer = "y"
  } else {
    $answer = Read-Host "Install Python 3.12 now? [Y/n]"
  }
  if ($answer -and $answer -notmatch '(?i)^y(?:es)?$') {
    throw "Python installation was cancelled."
  }

  & $winget.Source install --id Python.Python.3.12 --exact --source winget --accept-package-agreements --accept-source-agreements
  if ($LASTEXITCODE -ne 0) {
    throw "winget could not install Python (exit code $LASTEXITCODE)."
  }

  Refresh-ProcessPath
  $python = Find-WorkingPython
  if (-not $python) {
    throw "Python was installed, but this terminal cannot find it yet. Open a new terminal and run the command again."
  }
}

$argsList = @("-m", "agent_setup")
if ($Agent) { $argsList += $Agent }
if ($Yes) { $argsList += "--yes" }
if ($DryRun) { $argsList += "--dry-run" }

Push-Location $PSScriptRoot
try {
  & $python.Source @argsList
  if ($LASTEXITCODE -ne 0) {
    throw "Agent Quick Setup exited with code $LASTEXITCODE."
  }
} finally {
  Pop-Location
}
