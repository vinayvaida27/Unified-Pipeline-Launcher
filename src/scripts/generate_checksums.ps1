param([Parameter(Mandatory=$true)][string]$Path)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path $Path
$Out = Join-Path $Root "checksums.sha256"
Remove-Item $Out -ErrorAction SilentlyContinue
Get-ChildItem -Path $Root -Recurse -File | Where-Object { $_.FullName -ne $Out } | ForEach-Object {
  $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
  $rel = [System.IO.Path]::GetRelativePath($Root, $_.FullName).Replace('\','/')
  "$hash $rel" | Add-Content -Encoding UTF8 $Out
}
Write-Host "Wrote $Out"
