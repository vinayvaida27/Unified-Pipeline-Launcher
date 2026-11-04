param(
    [string]$ToolsDirectory = ""
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")

$UvVersion = "0.11.14"
if ($ToolsDirectory -eq "") {
    $ToolsDirectory = Join-Path $env:LOCALAPPDATA "OrganizationName\UnifiedPipelineLauncher\tools"
} else {
    $ToolsDirectory = Normalize-LauncherPathInput $ToolsDirectory
}
$UvDirectory = Join-Path $ToolsDirectory "uv"
$Uv = Join-Path $UvDirectory "uv.exe"

if (Test-Path -LiteralPath $Uv) {
    $InstalledVersion = & $Uv --version 2>$null
    if ($LASTEXITCODE -eq 0 -and $InstalledVersion -like "uv $UvVersion *") {
        Write-Output $Uv
        exit 0
    }
}

$Architecture = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
switch ($Architecture) {
    "X64" {
        $ArchiveName = "uv-x86_64-pc-windows-msvc.zip"
        $ExpectedSha256 = "52ba5d19409aaa688a8a1a6ec8dfb6a4817230d20186e75f4006105c3e39a846"
    }
    "Arm64" {
        $ArchiveName = "uv-aarch64-pc-windows-msvc.zip"
        $ExpectedSha256 = "d66c76ba912ba66fed011e0189dfbc4527dd9e620a2b5d5d5ecd2ad8936601b8"
    }
    default { throw "uv $UvVersion is not configured for Windows architecture: $Architecture" }
}

$DownloadUrl = "https://github.com/astral-sh/uv/releases/download/$UvVersion/$ArchiveName"
$Work = Join-Path $env:TEMP "upl-uv-$UvVersion-$([guid]::NewGuid().ToString('N'))"
$Archive = "$Work.zip"
try {
    Write-Host "Downloading pinned uv $UvVersion..."
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $Archive -UseBasicParsing
    $ActualSha256 = (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($ActualSha256 -ne $ExpectedSha256) {
        throw "uv archive checksum mismatch. Expected $ExpectedSha256, received $ActualSha256."
    }
    Expand-Archive -LiteralPath $Archive -DestinationPath $Work -Force
    $DownloadedUv = Join-Path $Work "uv.exe"
    if (-not (Test-Path -LiteralPath $DownloadedUv)) { throw "Downloaded uv archive did not contain uv.exe." }
    New-Item -ItemType Directory -Path $UvDirectory -Force | Out-Null
    Copy-Item -LiteralPath $DownloadedUv -Destination $Uv -Force
} finally {
    Remove-Item -LiteralPath $Archive -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $Work -Recurse -Force -ErrorAction SilentlyContinue
}

$InstalledVersion = & $Uv --version
if ($LASTEXITCODE -ne 0 -or $InstalledVersion -notlike "uv $UvVersion *") {
    throw "Pinned uv validation failed at: $Uv"
}
Write-Output $Uv
