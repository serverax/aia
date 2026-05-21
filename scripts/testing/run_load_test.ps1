param(
    [Parameter(Mandatory = $true)]
    [string]$HostUrl,

    [int]$Users = 1000,
    [int]$SpawnRate = 50,
    [string]$RunTime = "30m",
    [string]$ReportPath = "chatgpt/sprint-8/load-test-report.html",
    [switch]$Docker,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$reportDir = Split-Path -Parent $ReportPath
if ($reportDir) {
    New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
}

if ($DryRun) {
    Write-Output "DRY RUN: Load test"
    Write-Output "HostUrl: $HostUrl"
    Write-Output "Users: $Users"
    Write-Output "SpawnRate: $SpawnRate"
    Write-Output "RunTime: $RunTime"
    Write-Output "ReportPath: $ReportPath"
    Write-Output "Docker: $Docker"
    Write-Output "Locustfile: scripts/testing/load_locustfile.py"
    Write-Output "RESULT: DRY RUN COMPLETE"
    exit 0
}

if ($Docker) {
    docker run --rm `
        --add-host=host.docker.internal:host-gateway `
        -v "$((Resolve-Path scripts/testing).Path):/mnt/locust:ro" `
        -v "$((Resolve-Path $reportDir).Path):/mnt/reports:rw" `
        locustio/locust:2.32.4 `
        -f /mnt/locust/load_locustfile.py `
        --host $HostUrl `
        --users $Users `
        --spawn-rate $SpawnRate `
        --run-time $RunTime `
        --headless `
        --html "/mnt/reports/$(Split-Path -Leaf $ReportPath)"
}
else {
    locust `
        -f scripts/testing/load_locustfile.py `
        --host $HostUrl `
        --users $Users `
        --spawn-rate $SpawnRate `
        --run-time $RunTime `
        --headless `
        --html $ReportPath
}
