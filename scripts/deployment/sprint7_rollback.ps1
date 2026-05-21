[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$Namespace = "synthetic-enterprise",
    [string]$ManifestPath = "infrastructure/compliance/",
    [int]$TimeoutSeconds = 60
)

$ErrorActionPreference = "Stop"

Write-Output "Sprint 7 rollback starting"
Write-Output "Namespace: $Namespace"
Write-Output "Manifest path: $ManifestPath"

if ($WhatIfPreference) {
    Write-Output "WHATIF: no cluster calls will be made."
    Write-Output "Would inspect:"
    Write-Output "- deployment,service,networkpolicy labeled app=compliance-service"
    Write-Output "- service/compliance-service"
    Write-Output "- networkpolicy/compliance-service-ingress"
    Write-Output "Would delete:"
    Write-Output "- kubectl delete -f $ManifestPath --ignore-not-found"
    Write-Output "Would verify removal within $TimeoutSeconds seconds."
    Write-Output "RESULT: WHATIF COMPLETE"
    exit 0
}

Write-Output "Current compliance resources before rollback:"
kubectl -n $Namespace get deployment,service,networkpolicy -l app=compliance-service --ignore-not-found
kubectl -n $Namespace get service compliance-service --ignore-not-found
kubectl -n $Namespace get networkpolicy compliance-service-ingress --ignore-not-found

Write-Output "Deleting Sprint 7 compliance manifests"
if ($PSCmdlet.ShouldProcess($ManifestPath, "kubectl delete Sprint 7 compliance manifests")) {
    kubectl delete -f $ManifestPath --ignore-not-found
}
else {
    Write-Output "RESULT: WHATIF COMPLETE"
    exit 0
}

Write-Output "Verifying rollback state"
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    $deployment = kubectl -n $Namespace get deployment compliance-service --ignore-not-found
    $service = kubectl -n $Namespace get service compliance-service --ignore-not-found
    $policy = kubectl -n $Namespace get networkpolicy compliance-service-ingress --ignore-not-found

    if ([string]::IsNullOrWhiteSpace($deployment) -and
        [string]::IsNullOrWhiteSpace($service) -and
        [string]::IsNullOrWhiteSpace($policy)) {
        Write-Output "RESULT: ROLLBACK COMPLETE"
        exit 0
    }

    Start-Sleep -Seconds 3
} while ((Get-Date) -lt $deadline)

Write-Output "RESULT: ROLLBACK INCOMPLETE"
Write-Output "Remaining resources:"
kubectl -n $Namespace get deployment compliance-service --ignore-not-found
kubectl -n $Namespace get service compliance-service --ignore-not-found
kubectl -n $Namespace get networkpolicy compliance-service-ingress --ignore-not-found
exit 1
