param(
  [string]$HostName = "192.168.1.65",
  [string]$UserName = "admin",
  [string]$RemoteDir = "~/Clock"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$remote = "${UserName}@${HostName}"
$excludeArgs = @(
  "--exclude=.git",
  "--exclude=__pycache__",
  "--exclude=.venv",
  "--exclude=venv",
  "--exclude=*.pyc",
  "--exclude=.DS_Store",
  "--exclude=Thumbs.db"
)

Push-Location $repoRoot
try {
  ssh $remote "mkdir -p $RemoteDir"
  tar -czf - @excludeArgs . | ssh $remote "tar -xzf - -C $RemoteDir"
}
finally {
  Pop-Location
}
