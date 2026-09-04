Option Explicit

Dim fso, shell, root, srcRoot, launcherExe, sourcePythonw, pythonw, config, command
Dim cacheRoot, cachedRuntime, cachedPython, cachedPythonw, sourceMarker, cachedMarker

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

root = fso.GetParentFolderName(WScript.ScriptFullName)
launcherExe = fso.BuildPath(root, "launcher.exe")
srcRoot = fso.BuildPath(root, "src")
If Not fso.FolderExists(srcRoot) Then
    srcRoot = root
End If

sourcePythonw = fso.BuildPath(srcRoot, "runtime\pythonw.exe")
pythonw = sourcePythonw
config = fso.BuildPath(srcRoot, "config\launcher_config.json")

cacheRoot = LocalCacheDirectory(config)
If cacheRoot <> "" Then
    cachedRuntime = fso.BuildPath(cacheRoot, "runtime\current")
    cachedPython = fso.BuildPath(cachedRuntime, "python.exe")
    cachedPythonw = fso.BuildPath(cachedRuntime, "pythonw.exe")
    sourceMarker = fso.BuildPath(srcRoot, "runtime\.shared_runtime_ready.json")
    cachedMarker = fso.BuildPath(cacheRoot, "runtime\current\.shared_runtime_ready.json")
    If fso.FileExists(cachedPythonw) And fso.FileExists(cachedPython) And FilesMatch(sourceMarker, cachedMarker) Then
        If RuntimeIsSelfContained(cachedPython) Then
            pythonw = cachedPythonw
        End If
    End If
End If

shell.CurrentDirectory = srcRoot

If fso.FileExists(launcherExe) Then
    command = """" & launcherExe & """"
ElseIf fso.FileExists(pythonw) Then
    command = """" & pythonw & """ -m launcher --config """ & config & """"
Else
    MsgBox "Could not find launcher.exe or runtime\pythonw.exe in:" & vbCrLf & root, vbCritical, "Unified Pipeline Launcher"
    WScript.Quit 1
End If

shell.Run command, 1, False

Function LocalCacheDirectory(configPath)
    Dim handle, text, expression, matches, value
    LocalCacheDirectory = ""
    If Not fso.FileExists(configPath) Then Exit Function
    Set handle = fso.OpenTextFile(configPath, 1, False)
    text = handle.ReadAll
    handle.Close
    Set expression = New RegExp
    expression.Pattern = """local_cache_directory""\s*:\s*""([^""]+)"""
    expression.IgnoreCase = True
    Set matches = expression.Execute(text)
    If matches.Count = 0 Then Exit Function
    value = matches(0).SubMatches(0)
    value = Replace(value, "\\", "\")
    value = Replace(value, "/", "\")
    LocalCacheDirectory = shell.ExpandEnvironmentStrings(value)
End Function

Function RuntimeIsSelfContained(pythonPath)
    Dim probe, exitCode
    RuntimeIsSelfContained = False
    probe = """" & pythonPath & """ -I -c ""import encodings,os,sys;root=os.path.normcase(os.path.realpath(os.path.dirname(sys.executable)));paths=(sys.prefix,sys.base_prefix,encodings.__file__);raise SystemExit(0 if all(os.path.commonpath((root,os.path.normcase(os.path.realpath(path))))==root for path in paths) else 86)"""
    On Error Resume Next
    exitCode = shell.Run(probe, 0, True)
    If Err.Number = 0 Then RuntimeIsSelfContained = (exitCode = 0)
    Err.Clear
    On Error GoTo 0
End Function

Function FilesMatch(firstPath, secondPath)
    Dim firstFile, secondFile
    FilesMatch = False
    If Not fso.FileExists(firstPath) Or Not fso.FileExists(secondPath) Then Exit Function
    If fso.GetFile(firstPath).Size <> fso.GetFile(secondPath).Size Then Exit Function
    Set firstFile = fso.OpenTextFile(firstPath, 1, False)
    Set secondFile = fso.OpenTextFile(secondPath, 1, False)
    FilesMatch = (firstFile.ReadAll = secondFile.ReadAll)
    firstFile.Close
    secondFile.Close
End Function
