param([string]$AppFolder = "apps\01_hello_pipeline")

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$PublicRoot = Split-Path -Parent $Root
$Python = Join-Path $PublicRoot ".venv\Scripts\python.exe"
if (!(Test-Path $Python)) { $Python = Join-Path $Root ".venv\Scripts\python.exe" }
if (!(Test-Path $Python)) { throw "Run src/scripts/setup_dev.ps1 first." }

$AppPath = Join-Path $Root $AppFolder
$PortListener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse("127.0.0.1"), 0)
$PortListener.Start()
$Port = $PortListener.LocalEndpoint.Port
$PortListener.Stop()
$Log = Join-Path $Root "logs\manual_verify_dummy_app.log"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Log) | Out-Null

$Args = @(
  "-m", "streamlit", "run", (Join-Path $AppPath "app.py"),
  "--server.address", "127.0.0.1",
  "--server.port", "$Port",
  "--server.headless", "true",
  "--browser.gatherUsageStats", "false",
  "--server.fileWatcherType", "none"
)

$Process = Start-Process -FilePath $Python -ArgumentList $Args -WorkingDirectory $AppPath -RedirectStandardOutput $Log -RedirectStandardError $Log -WindowStyle Hidden -PassThru
try {
  $Deadline = (Get-Date).AddSeconds(60)
  do {
    if ($Process.HasExited) { throw "Streamlit exited early. See $Log" }
    try {
      $Response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Port/_stcore/health" -TimeoutSec 2
      if ($Response.StatusCode -ge 200 -and $Response.StatusCode -lt 500) {
        Write-Host "Dummy app is healthy at http://127.0.0.1:$Port"
        exit 0
      }
    } catch {
      Start-Sleep -Milliseconds 500
    }
  } while ((Get-Date) -lt $Deadline)
  throw "Timed out waiting for Streamlit health. See $Log"
} finally {
  if (!$Process.HasExited) {
    Stop-Process -Id $Process.Id -Force
  }
}
