param(
    [string]$Root = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)),
    [string]$ConfigPath = ""
)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path -LiteralPath $Root).Path
$SourceRoot = Join-Path $Root "src"
$Pythonw = Join-Path $SourceRoot "runtime\pythonw.exe"
$Output = Join-Path $Root "Unified-Pipeline-Launcher.exe"
$Staged = "$Output.staging"
if (-not (Test-Path -LiteralPath $Pythonw)) { throw "Missing bundled runtime: $Pythonw" }
if ([string]::IsNullOrWhiteSpace($ConfigPath)) { $ConfigPath = Join-Path $SourceRoot "config\launcher_config.json" }
$ConfigPath = (Resolve-Path -LiteralPath $ConfigPath).Path
if (-not $ConfigPath.StartsWith($Root + "\", [StringComparison]::OrdinalIgnoreCase)) { throw "ConfigPath must be inside the repository root: $ConfigPath" }
$RelativeConfig = $ConfigPath.Substring($Root.Length).TrimStart("\").Replace('"', '""')
$source = @'
using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;
internal static class LauncherEntry {
    [STAThread]
    private static void Main() {
        string root = AppDomain.CurrentDomain.BaseDirectory;
        string source = Path.Combine(root, "src");
        string pythonw = Path.Combine(source, "runtime", "pythonw.exe");
        string config = Path.Combine(root, @"__CONFIG_RELATIVE__");
        try {
            if (!File.Exists(pythonw)) throw new FileNotFoundException("Bundled pythonw.exe is missing", pythonw);
            if (!File.Exists(config)) throw new FileNotFoundException("Launcher configuration is missing", config);
            var psi = new ProcessStartInfo { FileName = pythonw, Arguments = "-m launcher --config \"" + config + "\"", WorkingDirectory = source, UseShellExecute = false, CreateNoWindow = true };
            psi.EnvironmentVariables["PYTHONPATH"] = "";
            psi.EnvironmentVariables["PYTHONHOME"] = "";
            Process.Start(psi);
        } catch (Exception ex) { MessageBox.Show(ex.ToString(), "Unified Pipeline Launcher - Startup Error", MessageBoxButtons.OK, MessageBoxIcon.Error); }
    }
}
'@.Replace('__CONFIG_RELATIVE__', $RelativeConfig)
Remove-Item -LiteralPath $Staged -Force -ErrorAction SilentlyContinue
Add-Type -TypeDefinition $source -OutputAssembly $Staged -OutputType WindowsApplication -ReferencedAssemblies @("System.dll", "System.Windows.Forms.dll")
if (-not (Test-Path -LiteralPath $Staged)) { throw "EXE compilation did not produce $Staged" }
Move-Item -LiteralPath $Staged -Destination $Output -Force
Write-Host "Created: $Output" -ForegroundColor Green
Write-Host "Runtime: $Pythonw"
Write-Host "Config : $ConfigPath"
