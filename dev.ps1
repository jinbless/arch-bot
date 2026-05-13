# Windows PowerShell wrapper. Delegates to WSL bash + the Makefile so the
# existing Linux .venv / node_modules and the bash recipes are reused unchanged.
#
# Usage:
#   .\dev.ps1                # help
#   .\dev.ps1 up
#   .\dev.ps1 down
#   .\dev.ps1 check
#   .\dev.ps1 status
#   .\dev.ps1 logs
#   .\dev.ps1 pg-up | pg-down | pg-status

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Command = "help",

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

# `wsl --cd <Windows path>` automatically translates to /mnt/<drive>/...
$extra = if ($Rest) { ($Rest -join ' ') } else { '' }
$bashCmd = "make dev-$Command $extra"

Write-Host "[dev.ps1] root=$root"
Write-Host "[dev.ps1] -> wsl --cd `"$root`" bash -c `"$bashCmd`""

& wsl.exe --cd "$root" bash -lc $bashCmd
exit $LASTEXITCODE
