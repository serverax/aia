param(
    [string]$Namespace = "synthetic-enterprise",
    [string]$Service = "compliance-service",
    [int]$LocalPort = 18080,
    [string]$WslKubeconfig = "~/.kube/aia-config.yaml"
)

$ErrorActionPreference = "Stop"

function Invoke-Kubectl {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    $command = "export KUBECONFIG=$WslKubeconfig; kubectl $($Arguments -join ' ')"
    wsl bash -lc $command
    if ($LASTEXITCODE -ne 0) {
        throw "kubectl failed: $($Arguments -join ' ')"
    }
}

Invoke-Kubectl -n $Namespace rollout status deployment/$Service --timeout=180s
Invoke-Kubectl -n $Namespace get pods -l app=$Service

$job = Start-Job -ScriptBlock {
    param($Namespace, $Service, $LocalPort, $WslKubeconfig)
    wsl bash -lc "export KUBECONFIG=$WslKubeconfig; kubectl -n $Namespace port-forward service/$Service ${LocalPort}:8000"
} -ArgumentList $Namespace, $Service, $LocalPort, $WslKubeconfig

try {
    Start-Sleep -Seconds 3
    Invoke-RestMethod -Uri "http://127.0.0.1:$LocalPort/health" -Method Get
    Invoke-RestMethod -Uri "http://127.0.0.1:$LocalPort/ready" -Method Get
    Invoke-RestMethod -Uri "http://127.0.0.1:$LocalPort/compliance/evaluate" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"agent_id":"domain_analyst_v1_20250520","project_id":"cluster-smoke","capability":"draft"}'
}
finally {
    Stop-Job $job -ErrorAction SilentlyContinue
    Remove-Job $job -ErrorAction SilentlyContinue
}
