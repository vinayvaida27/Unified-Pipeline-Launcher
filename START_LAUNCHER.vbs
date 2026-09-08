Option Explicit

Dim fso, shell, root, launcherBat, command, exitCode, commandProcessor

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

' Resolve from this script's own location so mapped drives, UNC paths and paths
' containing spaces all use the same repository root.
root = fso.GetParentFolderName(WScript.ScriptFullName)
launcherBat = fso.BuildPath(root, "START_LAUNCHER.bat")

If Not fso.FileExists(launcherBat) Then
    Fail "START_LAUNCHER.bat was not found:" & vbCrLf & launcherBat, 1
End If

' START_LAUNCHER.bat is the single source of truth for normal startup.  Run it
' hidden so VBS and the .lnk shortcut behave exactly like the known-good batch
' launcher without duplicating Python/path logic here.
commandProcessor = fso.BuildPath(shell.ExpandEnvironmentStrings("%SystemRoot%"), "System32\cmd.exe")
' Invoke cmd explicitly: direct .bat association handling can report success
' without running a batch file whose parent folder contains shell metacharacters.
command = """" & commandProcessor & """ /d /s /c """"" & launcherBat & """ --silent"""

On Error Resume Next
exitCode = shell.Run(command, 0, True)
If Err.Number <> 0 Then
    On Error GoTo 0
    Fail "The launcher bootstrap could not be started.", 1
End If
On Error GoTo 0

If exitCode <> 0 Then
    Fail "The launcher exited with code " & exitCode & ".", exitCode
End If

Sub Fail(message, code)
    message = message & vbCrLf & vbCrLf & "Run START_LAUNCHER_DEBUG.bat for details."
    If LCase(fso.GetFileName(WScript.FullName)) = "cscript.exe" Then
        WScript.Echo message
    Else
        MsgBox message, vbCritical, "Unified Pipeline Launcher"
    End If
    WScript.Quit code
End Sub
