Option Explicit

Dim fso, shell, root, launcherExe, pythonw, config, command

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

root = fso.GetParentFolderName(WScript.ScriptFullName)
launcherExe = fso.BuildPath(root, "launcher.exe")
pythonw = fso.BuildPath(root, "runtime\pythonw.exe")
config = fso.BuildPath(root, "config\launcher_config.json")

shell.CurrentDirectory = root

If fso.FileExists(launcherExe) Then
    command = """" & launcherExe & """"
ElseIf fso.FileExists(pythonw) Then
    command = """" & pythonw & """ -m launcher --config """ & config & """"
Else
    MsgBox "Could not find launcher.exe or runtime\pythonw.exe in:" & vbCrLf & root, vbCritical, "Unified Streamlit Launcher"
    WScript.Quit 1
End If

shell.Run command, 0, False
