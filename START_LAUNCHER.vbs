Option Explicit

Dim fso, shell, root, srcRoot, launcherExe, pythonw, config, command

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

root = fso.GetParentFolderName(WScript.ScriptFullName)
launcherExe = fso.BuildPath(root, "launcher.exe")
srcRoot = fso.BuildPath(root, "src")
If Not fso.FolderExists(srcRoot) Then
    srcRoot = root
End If

pythonw = fso.BuildPath(srcRoot, "runtime\pythonw.exe")
config = fso.BuildPath(srcRoot, "config\launcher_config.json")

shell.CurrentDirectory = srcRoot

If fso.FileExists(launcherExe) Then
    command = """" & launcherExe & """"
ElseIf fso.FileExists(pythonw) Then
    command = """" & pythonw & """ -m launcher --config """ & config & """"
Else
    MsgBox "Could not find launcher.exe or runtime\pythonw.exe in:" & vbCrLf & root, vbCritical, "Unified Streamlit Launcher"
    WScript.Quit 1
End If

shell.Run command, 0, False
