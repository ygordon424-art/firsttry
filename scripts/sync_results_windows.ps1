[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ })]
    [string]$Source,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9_-]+$')]
    [string]$CaseId,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9_.-]+$')]
    [string]$RunId,

    [ValidatePattern('^\d{4}-\d{2}-\d{2}$')]
    [string]$Date = (Get-Date -Format 'yyyy-MM-dd'),

    [string]$DestinationRoot = 'D:\SWJT\大三\论文\result'
)

$ErrorActionPreference = 'Stop'
$resolvedSource = (Resolve-Path -LiteralPath $Source).Path
$destination = Join-Path -Path $DestinationRoot -ChildPath $CaseId
$destination = Join-Path -Path $destination -ChildPath $Date
$destination = Join-Path -Path $destination -ChildPath $RunId

if ($PSCmdlet.ShouldProcess($destination, "Synchronize $resolvedSource")) {
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    $item = Get-Item -LiteralPath $resolvedSource
    if ($item.PSIsContainer) {
        Get-ChildItem -LiteralPath $resolvedSource -Force | Copy-Item -Destination $destination -Recurse -Force
    }
    else {
        Copy-Item -LiteralPath $resolvedSource -Destination $destination -Force
    }
    Write-Output "Results synchronized to: $destination"
}
