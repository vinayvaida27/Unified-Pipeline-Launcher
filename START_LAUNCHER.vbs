Option Explicit

Dim fso, shell, root, launcherBat, command, exitCode

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

' Resolve from this script's own location so mapped drives, UNC paths and paths
' containing spaces all use the same repository root.
root = fso.GetParentFolderName(WScript.ScriptFullName)
launcherBat = fso.BuildPath(root, "START_LAUNCHER.bat")

If Not fso.FileExists(launcherBat) Then
    MsgBox "START_LAUNCHER.bat was not found:" & vbCrLf & launcherBat, _
           vbCritical, "Unified Pipeline Launcher"
    WScript.Quit 1
End If

' START_LAUNCHER.bat is the single source of truth for normal startup.  Run it
' hidden so VBS and the .lnk shortcut behave exactly like the known-good batch
' launcher without duplicating Python/path logic here.
command = """" & launcherBat & """ --silent"

On Error Resume Next
exitCode = shell.Run(command, 0, True)
If Err.Number <> 0 Then
    MsgBox "The launcher bootstrap could not be started." & vbCrLf & vbCrLf & _
           "Run START_LAUNCHER_DEBUG.bat for details.", _
           vbCritical, "Unified Pipeline Launcher"
    WScript.Quit 1
End If
On Error GoTo 0

If exitCode <> 0 Then
    MsgBox "The launcher failed to start (exit code " & exitCode & ")." & vbCrLf & vbCrLf & _
           "Run START_LAUNCHER_DEBUG.bat for details.", _
           vbCritical, "Unified Pipeline Launcher"
    WScript.Quit exitCode
End If
