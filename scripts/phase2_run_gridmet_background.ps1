param(
    [string]$Python = "C:\anaconda3\python.exe"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$LogDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Log = Join-Path $LogDir "gridmet_download_$Stamp.log"
$Err = Join-Path $LogDir "gridmet_download_$Stamp.err.log"

Start-Process -FilePath $Python `
    -ArgumentList @("scripts\phase2_download_gridmet.py") `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $Log `
    -RedirectStandardError $Err `
    -WindowStyle Hidden

Write-Host "Started gridMET download in background."
Write-Host "stdout: $Log"
Write-Host "stderr: $Err"
