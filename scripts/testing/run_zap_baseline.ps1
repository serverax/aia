param(
    [Parameter(Mandatory = $true)]
    [string]$TargetUrl,

    [string]$ReportPath = "chatgpt/sprint-8/zap-baseline-report.html",
    [string]$Image = "zaproxy/zap-stable:latest",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$reportDir = Split-Path -Parent $ReportPath
if ($reportDir) {
    New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
}

if ($DryRun) {
    Write-Output "DRY RUN: ZAP baseline"
    Write-Output "TargetUrl: $TargetUrl"
    Write-Output "ReportPath: $ReportPath"
    Write-Output "Image: $Image"
    Write-Output "RESULT: DRY RUN COMPLETE"
    exit 0
}

docker run --rm `
    -v "$((Resolve-Path $reportDir).Path):/zap/wrk/:rw" `
    $Image zap-baseline.py `
    -t $TargetUrl `
    -r (Split-Path -Leaf $ReportPath) `
    -I
