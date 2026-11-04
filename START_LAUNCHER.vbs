Option Explicit

Dim fso, shell, env, root, srcRoot, launcherBat, launcherExe, pythonw, python, config, command, comspec

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
Set env = shell.Environment("PROCESS")

env("QT_LOGGING_RULES") = "qt.svg.warning=false;qt.svg.debug=false"

root = fso.GetParentFolderName(WScript.ScriptFullName)
launcherExe = fso.BuildPath(root, "launcher.exe")
launcherBat = fso.BuildPath(root, "START_LAUNCHER.bat")
srcRoot = fso.BuildPath(root, "src")

If Not fso.FolderExists(srcRoot) Then
    srcRoot = root
End If

pythonw = fso.BuildPath(srcRoot, "runtime\pythonw.exe")
python = fso.BuildPath(srcRoot, "runtime\python.exe")
config = fso.BuildPath(srcRoot, "config\launcher_config.json")

If Not fso.FileExists(launcherExe) Then
    If Not fso.FileExists(config) Then
        MsgBox "Launcher config not found:" & vbCrLf & config & vbCrLf & vbCrLf & _
               "Expected folder layout:" & vbCrLf & _
               root & "\src\config\launcher_config.json", _
               vbCritical, "Unified Streamlit Launcher"
        WScript.Quit 1
    End If
End If

shell.CurrentDirectory = srcRoot

If fso.FileExists(launcherBat) Then
    comspec = shell.ExpandEnvironmentStrings("%ComSpec%")
    command = """" & comspec & """ /d /c call """ & launcherBat & """ --silent"
ElseIf fso.FileExists(launcherExe) Then
    command = """" & launcherExe & """"
ElseIf fso.FileExists(pythonw) Then
    command = """" & pythonw & """ -m launcher --config """ & config & """"
ElseIf fso.FileExists(python) Then
    command = """" & python & """ -m launcher --config """ & config & """"
Else
    MsgBox "Python runtime not found:" & vbCrLf & pythonw & vbCrLf & python & vbCrLf & vbCrLf & _
           "Run src\scripts\update_dependencies.ps1 or deploy_network.ps1 first.", _
           vbCritical, "Unified Streamlit Launcher"
    WScript.Quit 1
End If

shell.Run command, 0, False
