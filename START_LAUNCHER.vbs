Option Explicit

Dim fso, shell, root, srcRoot, python, pythonw, config, command, probe, launcherProbe, exitCode

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

' Always resolve from this script's own location, never from the current shell directory.
root = fso.GetParentFolderName(WScript.ScriptFullName)
srcRoot = fso.BuildPath(root, "src")
If Not fso.FolderExists(srcRoot) Then srcRoot = root

python = fso.BuildPath(srcRoot, "runtime\python.exe")
pythonw = fso.BuildPath(srcRoot, "runtime\pythonw.exe")
config = fso.BuildPath(srcRoot, "config\launcher_config.json")

If Not fso.FileExists(python) Or Not fso.FileExists(pythonw) Then
    MsgBox "Python runtime was not found or is incomplete:" & vbCrLf & fso.BuildPath(srcRoot, "runtime") & vbCrLf & vbCrLf & _
           "Run src\scripts\deploy_network.ps1 first.", _
           vbCritical, "Unified Pipeline Launcher"
    WScript.Quit 1
End If

If Not fso.FileExists(config) Then
    MsgBox "Launcher configuration was not found:" & vbCrLf & config, _
           vbCritical, "Unified Pipeline Launcher"
    WScript.Quit 1
End If

' Prevent inherited Python/Conda configuration from changing the bundled runtime.
On Error Resume Next
shell.Environment("PROCESS").Remove "PYTHONHOME"
shell.Environment("PROCESS").Remove "PYTHONPATH"
shell.Environment("PROCESS").Remove "PYTHONSTARTUP"
shell.Environment("PROCESS").Remove "PYTHONUSERBASE"
shell.Environment("PROCESS")("PYTHONNOUSERSITE") = "1"
On Error GoTo 0

shell.CurrentDirectory = srcRoot

' Validate the runtime itself in isolated mode.
probe = """" & python & """ -I -c ""import encodings; from PySide6.QtWidgets import QApplication; import streamlit"""
On Error Resume Next
exitCode = shell.Run(probe, 0, True)
If Err.Number <> 0 Then
    MsgBox "The bundled Python runtime could not be started." & vbCrLf & vbCrLf & _
           "Run START_LAUNCHER_DEBUG.bat for details.", vbCritical, "Unified Pipeline Launcher"
    WScript.Quit 1
End If
On Error GoTo 0
If exitCode <> 0 Then
    MsgBox "The bundled Python runtime failed validation (exit code " & exitCode & ")." & vbCrLf & vbCrLf & _
           "Run START_LAUNCHER_DEBUG.bat for details.", vbCritical, "Unified Pipeline Launcher"
    WScript.Quit exitCode
End If

' The launcher package lives beside the runtime under src\.  Do not use -I for
' module startup because isolated mode intentionally removes the working/source
' directory from sys.path. Environment contamination is already scrubbed above.
launcherProbe = """" & python & """ -c ""import launcher"""
exitCode = shell.Run(launcherProbe, 0, True)
If exitCode <> 0 Then
    MsgBox "The launcher source package could not be imported." & vbCrLf & vbCrLf & _
           "Run START_LAUNCHER_DEBUG.bat for details.", vbCritical, "Unified Pipeline Launcher"
    WScript.Quit exitCode
End If

command = """" & pythonw & """ -m launcher --config """ & config & """ --no-local-cache"
shell.Run command, 0, False
