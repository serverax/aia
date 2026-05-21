[CmdletBinding()]
param(
    [string]$Namespace = "synthetic-enterprise",
    [int]$TimeoutSeconds = 120,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$script:Blockers = New-Object System.Collections.Generic.List[string]
$script:Warnings = New-Object System.Collections.Generic.List[string]

function Add-Blocker {
    param([string]$Message)
    $script:Blockers.Add($Message)
    Write-Host "[blocked] $Message"
}

function Add-Warning {
    param([string]$Message)
    $script:Warnings.Add($Message)
    Write-Host "[warning] $Message"
}

function Test-Kubectl {
    try {
        kubectl version --client | Out-Null
        kubectl cluster-info | Out-Null
        Write-Host "[ok] kubectl can reach cluster"
    }
    catch {
        Add-Blocker "kubectl cannot reach the K3s cluster"
    }
}

function Test-Resource {
    param(
        [string]$Kind,
        [string]$Name,
        [bool]$Required = $true
    )

    try {
        kubectl -n $Namespace get $Kind $Name | Out-Null
        Write-Host "[ok] $Kind/$Name"
        return $true
    }
    catch {
        if ($Required) {
            Add-Blocker "$Kind/$Name is required but missing"
        }
        else {
            Add-Warning "$Kind/$Name is not present yet"
        }
        return $false
    }
}

function Test-DeploymentReady {
    param(
        [string]$Name,
        [bool]$Required = $true
    )

    if (-not (Test-Resource -Kind "deployment" -Name $Name -Required $Required)) {
        return
    }

    try {
        kubectl -n $Namespace rollout status "deployment/$Name" "--timeout=$($TimeoutSeconds)s" | Out-Null
        Write-Host "[ok] deployment/$Name rollout ready"
    }
    catch {
        if ($Required) {
            Add-Blocker "deployment/$Name did not become ready within $TimeoutSeconds seconds"
        }
        else {
            Add-Warning "deployment/$Name did not become ready within $TimeoutSeconds seconds"
        }
    }
}

function Test-ServiceEndpoints {
    param(
        [string]$Name,
        [bool]$Required = $true
    )

    if (-not (Test-Resource -Kind "service" -Name $Name -Required $Required)) {
        return
    }

    $endpoints = kubectl -n $Namespace get endpoints $Name -o jsonpath='{.subsets[*].addresses[*].ip}' 2>$null
    if ([string]::IsNullOrWhiteSpace($endpoints)) {
        if ($Required) {
            Add-Blocker "service/$Name has no ready endpoints"
        }
        else {
            Add-Warning "service/$Name has no ready endpoints"
        }
    }
    else {
        Write-Host "[ok] service/$Name has ready endpoints"
    }
}

Write-Output "Pre-Week-14 Sprint 7 prerequisite check"
Write-Output "Namespace: $Namespace"
Write-Output "Timeout: $TimeoutSeconds seconds"
Write-Output "Blockers stop Sprint 7 deployment. Warnings require review but do not stop deployment."

if ($DryRun) {
    Write-Output "DRY RUN: no cluster calls will be made."
    Write-Output "Would verify:"
    Write-Output "- kubectl client and cluster reachability"
    Write-Output "- namespace/$Namespace"
    Write-Output "- service/postgres endpoints"
    Write-Output "- service/redis endpoints"
    Write-Output "- deployment/echo-agent rollout"
    Write-Output "- deployment/orchestrator rollout"
    Write-Output "- deployment/analyst-agent rollout"
    Write-Output "- deployment/frontend rollout"
    Write-Output "- deployment/editor-agent rollout"
    Write-Output "- deployment/wasm-security rollout"
    Write-Output "- networkpolicy/compliance-service-ingress warning state"
    Write-Output "- deployment/compliance-service conflict warning state"
    Write-Output "RESULT: DRY RUN COMPLETE"
    exit 0
}

Test-Kubectl
try {
    kubectl get namespace $Namespace | Out-Null
    Write-Host "[ok] namespace/$Namespace"
}
catch {
    Add-Blocker "namespace/$Namespace is missing"
}

Test-ServiceEndpoints -Name "postgres"
Test-ServiceEndpoints -Name "redis"
Test-DeploymentReady -Name "echo-agent"

$requiredDeployments = @(
    "orchestrator",
    "analyst-agent",
    "frontend",
    "editor-agent",
    "wasm-security"
)

foreach ($deployment in $requiredDeployments) {
    Test-DeploymentReady -Name $deployment
}

Test-Resource -Kind "networkpolicy" -Name "compliance-service-ingress" -Required $false | Out-Null

if (Test-Resource -Kind "deployment" -Name "compliance-service" -Required $false) {
    Add-Warning "deployment/compliance-service already exists. Verify ownership before applying Sprint 7 manifests."
}

Write-Output ""
Write-Output "Summary:"
Write-Output "Warnings: $($script:Warnings.Count)"
Write-Output "Blockers: $($script:Blockers.Count)"

if ($script:Blockers.Count -gt 0) {
    Write-Output "RESULT: BLOCKED"
    foreach ($blocker in $script:Blockers) {
        Write-Output "- $blocker"
    }
    exit 1
}

Write-Output "RESULT: READY TO DEPLOY"
Write-Output "Next:"
Write-Output "kubectl apply -f infrastructure/compliance/"
Write-Output ".\scripts\testing\sprint7_cluster_smoke.ps1"
