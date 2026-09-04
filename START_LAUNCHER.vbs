Option Explicit

Dim fso, shell, root, srcRoot, pythonw, config, command

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

' Always resolve from this script's own location, never from the current shell directory.
root = fso.GetParentFolderName(WScript.ScriptFullName)
srcRoot = fso.BuildPath(root, "src")
If Not fso.FolderExists(srcRoot) Then srcRoot = root

pythonw = fso.BuildPath(srcRoot, "runtime\pythonw.exe")
config = fso.BuildPath(srcRoot, "config\launcher_config.json")

If Not fso.FileExists(pythonw) Then
    MsgBox "Python runtime was not found:" & vbCrLf & pythonw & vbCrLf & vbCrLf & _
           "Run INSTALL.bat or src\scripts\deploy_network.ps1 first.", _
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

' --no-local-cache is intentional for the network-distributed launcher. The
' verified bundled runtime executes directly instead of copying the complete
' runtime and every app to LOCALAPPDATA before the window appears.
command = """" & pythonw & """ -I -m launcher --config """ & config & """ --no-local-cache"

shell.Run command, 0, False
