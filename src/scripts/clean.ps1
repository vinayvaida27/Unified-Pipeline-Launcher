param()

$Root = Split-Path -Parent $PSScriptRoot
Remove-Item -Recurse -Force (Join-Path $Root "build\release") -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $Root "build\Unified-Streamlit-Launcher") -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $Root "build\pyinstaller") -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $Root ".pytest_cache") -ErrorAction SilentlyContinue
Get-ChildItem -Path $Root -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
