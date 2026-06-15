Option Explicit

Dim fso, shell, root, pythonw, command

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

root = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = fso.BuildPath(root, "runtime\pythonw.exe")

shell.CurrentDirectory = root
command = """" & pythonw & """ -m launcher"
shell.Run command, 0, False
