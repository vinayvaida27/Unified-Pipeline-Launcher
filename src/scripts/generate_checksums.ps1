param([Parameter(Mandatory=$true)][string]$Path)

$ErrorActionPreference = "Stop"
$Path = $Path.Trim().Trim([char]34)
$Root = (Resolve-Path -LiteralPath $Path -ErrorAction Stop).Path
$Out = Join-Path $Root "checksums.sha256"
Remove-Item -LiteralPath $Out -ErrorAction SilentlyContinue
Get-ChildItem -LiteralPath $Root -Recurse -File | Where-Object { $_.FullName -ne $Out } | ForEach-Object {
  $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
  $rel = [System.IO.Path]::GetRelativePath($Root, $_.FullName).Replace('\','/')
  "$hash $rel" | Add-Content -LiteralPath $Out -Encoding UTF8
}
Write-Host "Wrote $Out"
