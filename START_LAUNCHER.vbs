Option Explicit

Dim fso, shell, bootstrap, command, index

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
bootstrap = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "launcher_bootstrap.vbs")

If Not fso.FileExists(bootstrap) Then
    MsgBox "Launcher bootstrap was not found: " & bootstrap, vbCritical, "Unified Pipeline Launcher"
    WScript.Quit 1
End If

command = QuoteArgument(WScript.FullName) & " " & QuoteArgument(bootstrap)
For index = 0 To WScript.Arguments.Count - 1
    command = command & " " & QuoteArgument(WScript.Arguments(index))
Next
shell.Run command, 1, False

Function QuoteArgument(value)
    QuoteArgument = """" & Replace(CStr(value), """", """"") & """"
End Function
