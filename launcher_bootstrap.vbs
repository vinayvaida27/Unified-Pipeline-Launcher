Option Explicit

Const ForAppending = 8

Dim fso, shell, network, processEnvironment
Dim bootstrapPath, launcherRoot, launcherRootUnc, sourceRoot, configPath, cacheRoot, logPath
Dim sourcePython, sourcePythonw, cachedRuntime, cachedPython, cachedPythonw
Dim sourceMarker, cachedMarker, selectedPython, selectedPythonw, mode, exitCode
Dim inheritedPythonHome, inheritedPythonPath

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
Set network = CreateObject("WScript.Network")
Set processEnvironment = shell.Environment("PROCESS")

bootstrapPath = WScript.ScriptFullName
launcherRoot = NormalizePath(fso.GetParentFolderName(bootstrapPath))
launcherRootUnc = EquivalentUncPath(launcherRoot)
sourceRoot = fso.BuildPath(launcherRoot, "src")
If Not fso.FolderExists(sourceRoot) Then sourceRoot = launcherRoot
configPath = fso.BuildPath(sourceRoot, "config\launcher_config.json")
cacheRoot = LocalCacheDirectory(configPath)
If cacheRoot = "" Then cacheRoot = fso.BuildPath(shell.ExpandEnvironmentStrings("%TEMP%"), "UnifiedPipelineLauncher")
logPath = InitializeLog(cacheRoot)

inheritedPythonHome = processEnvironment("PYTHONHOME")
inheritedPythonPath = processEnvironment("PYTHONPATH")
SanitizePythonEnvironment
processEnvironment("LAUNCHER_ROOT") = launcherRoot
processEnvironment("LAUNCHER_ROOT_UNC") = launcherRootUnc

sourcePython = fso.BuildPath(sourceRoot, "runtime\python.exe")
sourcePythonw = fso.BuildPath(sourceRoot, "runtime\pythonw.exe")
cachedRuntime = fso.BuildPath(cacheRoot, "runtime\current")
cachedPython = fso.BuildPath(cachedRuntime, "python.exe")
cachedPythonw = fso.BuildPath(cachedRuntime, "pythonw.exe")
sourceMarker = fso.BuildPath(sourceRoot, "runtime\.shared_runtime_ready.json")
cachedMarker = fso.BuildPath(cachedRuntime, ".shared_runtime_ready.json")

mode = "launch"
If WScript.Arguments.Count > 0 Then mode = LCase(Replace(Replace(WScript.Arguments(0), "/", ""), "-", ""))

LogMessage "mode=" & mode & "; root=" & launcherRoot & "; canonical=" & launcherRootUnc & "; cwd=" & shell.CurrentDirectory

Select Case mode
    Case "diagnose"
        WScript.Echo DiagnosticReport()
        WScript.Quit 0
    Case "install"
        exitCode = RunPowerShell(fso.BuildPath(sourceRoot, "scripts\deploy_network.ps1"))
        LogMessage "install exit_code=" & exitCode
        WScript.Quit exitCode
    Case "update"
        exitCode = RunPowerShell(fso.BuildPath(sourceRoot, "scripts\update_all_environments.ps1"))
        LogMessage "update exit_code=" & exitCode
        WScript.Quit exitCode
    Case "repair"
        exitCode = RunPowerShell(fso.BuildPath(sourceRoot, "scripts\deploy_network.ps1"))
        LogMessage "repair exit_code=" & exitCode
        WScript.Quit exitCode
    Case "debug", "launch"
        LaunchApplication mode = "debug"
    Case Else
        Fail "Unknown bootstrap option: " & WScript.Arguments(0)
End Select

Sub LaunchApplication(debugMode)
    Dim launcherExe, command, waitForExit, windowStyle

    selectedPython = ""
    selectedPythonw = ""
    If fso.FileExists(cachedPython) And fso.FileExists(cachedPythonw) And FilesMatch(sourceMarker, cachedMarker) Then
        If RuntimeIsSelfContained(cachedPython) Then
            selectedPython = cachedPython
            selectedPythonw = cachedPythonw
            LogMessage "runtime=local_cache; validation=passed"
        Else
            processEnvironment("UPL_REPAIR_RUNTIME_CACHE") = "1"
            LogMessage "runtime=local_cache; validation=failed; repair=scheduled"
        End If
    End If

    If selectedPython = "" Then
        If Not RuntimeIsSelfContained(sourcePython) Then
            Fail "Python runtime validation failed." & vbCrLf & vbCrLf & DiagnosticReport()
        End If
        selectedPython = sourcePython
        selectedPythonw = sourcePythonw
        LogMessage "runtime=source; validation=passed"
    End If

    launcherExe = fso.BuildPath(launcherRoot, "launcher.exe")
    shell.CurrentDirectory = sourceRoot
    waitForExit = debugMode
    windowStyle = 1
    If fso.FileExists(launcherExe) Then
        command = QuoteArgument(launcherExe)
    ElseIf debugMode Then
        command = QuoteArgument(selectedPython) & " -m launcher --config " & QuoteArgument(configPath)
    Else
        command = QuoteArgument(selectedPythonw) & " -m launcher --config " & QuoteArgument(configPath)
    End If

    LogMessage "launch command=" & command
    exitCode = shell.Run(command, windowStyle, waitForExit)
    LogMessage "launch exit_code=" & exitCode
    If debugMode Then WScript.Quit exitCode
End Sub

Function DiagnosticReport()
    Dim pythonPath, runtimeRoot, validation, version, configStatus, pythonHomeStatus, pythonPathStatus

    pythonPath = sourcePython
    If fso.FileExists(cachedPython) And FilesMatch(sourceMarker, cachedMarker) Then pythonPath = cachedPython
    runtimeRoot = fso.GetParentFolderName(pythonPath)
    If RuntimeIsSelfContained(pythonPath) Then
        validation = "passed"
        version = PythonVersion(pythonPath)
    Else
        validation = "failed"
        version = "unavailable"
    End If
    If fso.FileExists(configPath) Then configStatus = "found" Else configStatus = "missing"
    If inheritedPythonHome = "" Then pythonHomeStatus = "not set" Else pythonHomeStatus = "cleared for launcher process"
    If inheritedPythonPath = "" Then pythonPathStatus = "not set" Else pythonPathStatus = "cleared for launcher process"

    DiagnosticReport = _
        "Launcher root: " & launcherRoot & vbCrLf & _
        "Mapped/local path: " & launcherRoot & vbCrLf & _
        "UNC/canonical path: " & launcherRootUnc & vbCrLf & _
        "Current working directory: " & shell.CurrentDirectory & vbCrLf & _
        "Source directory: " & sourceRoot & vbCrLf & _
        "Configuration: " & configStatus & " (" & configPath & ")" & vbCrLf & _
        "Python executable: " & pythonPath & vbCrLf & _
        "Python runtime root: " & runtimeRoot & vbCrLf & _
        "Detected Python version: " & version & vbCrLf & _
        "PYTHONHOME: " & pythonHomeStatus & vbCrLf & _
        "PYTHONPATH: " & pythonPathStatus & vbCrLf & _
        "Runtime validation: " & validation & vbCrLf & _
        "pyvenv.cfg: " & FileStatus(fso.BuildPath(runtimeRoot, "pyvenv.cfg")) & vbCrLf & _
        "python311._pth: " & FileStatus(fso.BuildPath(runtimeRoot, "python311._pth")) & vbCrLf & _
        "python312._pth: " & FileStatus(fso.BuildPath(runtimeRoot, "python312._pth")) & vbCrLf & _
        "Diagnostic log: " & logPath
    LogMessage Replace(DiagnosticReport, vbCrLf, "; ")
End Function

Function RuntimeIsSelfContained(pythonPath)
    Dim runtimeRoot, encodingsPath, probe, result

    RuntimeIsSelfContained = False
    If Not fso.FileExists(pythonPath) Then Exit Function
    runtimeRoot = fso.GetParentFolderName(pythonPath)
    encodingsPath = fso.BuildPath(runtimeRoot, "Lib\encodings\__init__.py")
    If Not fso.FileExists(encodingsPath) Then Exit Function
    probe = QuoteArgument(pythonPath) & " -I -c ""import encodings,os,sys;root=os.path.normcase(os.path.realpath(os.path.dirname(sys.executable)));paths=(sys.prefix,sys.exec_prefix,sys.base_prefix,encodings.__file__);raise SystemExit(0 if all(os.path.commonpath((root,os.path.normcase(os.path.realpath(path))))==root for path in paths) else 86)"""
    On Error Resume Next
    result = shell.Run(probe, 0, True)
    If Err.Number = 0 Then RuntimeIsSelfContained = (result = 0)
    Err.Clear
    On Error GoTo 0
End Function

Function PythonVersion(pythonPath)
    Dim process, output

    PythonVersion = "unavailable"
    On Error Resume Next
    Set process = shell.Exec(QuoteArgument(pythonPath) & " -I -c ""import platform;print(platform.python_version())""")
    output = Trim(process.StdOut.ReadAll)
    If Err.Number = 0 And output <> "" Then PythonVersion = output
    Err.Clear
    On Error GoTo 0
End Function

Function RunPowerShell(scriptPath)
    Dim powershell, command

    If Not fso.FileExists(scriptPath) Then Fail "Required support script was not found: " & scriptPath
    powershell = fso.BuildPath(shell.ExpandEnvironmentStrings("%SystemRoot%"), "System32\WindowsPowerShell\v1.0\powershell.exe")
    command = QuoteArgument(powershell) & " -NoProfile -ExecutionPolicy Bypass -File " & QuoteArgument(scriptPath) & " -ReleaseDir " & QuoteArgument(launcherRoot)
    LogMessage "powershell command=" & command
    RunPowerShell = shell.Run(command, 1, True)
End Function

Sub SanitizePythonEnvironment()
    processEnvironment.Remove "PYTHONHOME"
    processEnvironment.Remove "PYTHONPATH"
    processEnvironment.Remove "PYTHONSTARTUP"
    processEnvironment.Remove "PYTHONUSERBASE"
    processEnvironment("PYTHONNOUSERSITE") = "1"
End Sub

Function NormalizePath(value)
    Dim clean

    clean = Trim(CStr(value))
    Do While Len(clean) > 0 And (Left(clean, 1) = """" Or Right(clean, 1) = """")
        If Left(clean, 1) = """" Then clean = Trim(Mid(clean, 2))
        If Len(clean) > 0 And Right(clean, 1) = """" Then clean = Trim(Left(clean, Len(clean) - 1))
    Loop
    If clean = "" Or InStr(clean, """") > 0 Then Err.Raise vbObjectError + 1000, "launcher_bootstrap", "Invalid launcher path"
    clean = Replace(clean, "/", "\")
    NormalizePath = fso.GetAbsolutePathName(clean)
End Function

Function EquivalentUncPath(path)
    Dim driveName, drives, index, remoteRoot, relativePath

    EquivalentUncPath = path
    If Left(path, 2) = "\\" Then Exit Function
    driveName = fso.GetDriveName(path)
    If driveName = "" Then Exit Function
    Set drives = network.EnumNetworkDrives
    For index = 0 To drives.Count - 1 Step 2
        If StrComp(drives.Item(index), driveName, vbTextCompare) = 0 Then
            remoteRoot = drives.Item(index + 1)
            relativePath = Mid(path, Len(driveName) + 1)
            EquivalentUncPath = remoteRoot & relativePath
            Exit Function
        End If
    Next
End Function

Function LocalCacheDirectory(path)
    Dim handle, text, expression, matches, value

    LocalCacheDirectory = ""
    If Not fso.FileExists(path) Then Exit Function
    Set handle = fso.OpenTextFile(path, 1, False)
    text = handle.ReadAll
    handle.Close
    Set expression = New RegExp
    expression.Pattern = """local_cache_directory""\s*:\s*""([^""]+)"""
    expression.IgnoreCase = True
    Set matches = expression.Execute(text)
    If matches.Count = 0 Then Exit Function
    value = Replace(matches(0).SubMatches(0), "\\", "\")
    value = Replace(value, "/", "\")
    On Error Resume Next
    LocalCacheDirectory = NormalizePath(shell.ExpandEnvironmentStrings(value))
    If Err.Number <> 0 Then LocalCacheDirectory = ""
    Err.Clear
    On Error GoTo 0
End Function

Function InitializeLog(root)
    Dim logsDirectory

    InitializeLog = ""
    On Error Resume Next
    logsDirectory = fso.BuildPath(root, "logs")
    EnsureFolder logsDirectory
    If Err.Number = 0 Then InitializeLog = fso.BuildPath(logsDirectory, "bootstrap.log")
    Err.Clear
    On Error GoTo 0
End Function

Sub EnsureFolder(path)
    Dim parent

    If fso.FolderExists(path) Then Exit Sub
    parent = fso.GetParentFolderName(path)
    If parent <> "" And Not fso.FolderExists(parent) Then EnsureFolder parent
    fso.CreateFolder path
End Sub

Sub LogMessage(message)
    Dim handle

    If logPath = "" Then Exit Sub
    On Error Resume Next
    Set handle = fso.OpenTextFile(logPath, ForAppending, True)
    handle.WriteLine IsoTimestamp() & " " & message
    handle.Close
    Err.Clear
    On Error GoTo 0
End Sub

Function IsoTimestamp()
    Dim nowValue

    nowValue = Now
    IsoTimestamp = Year(nowValue) & "-" & Right("0" & Month(nowValue), 2) & "-" & Right("0" & Day(nowValue), 2) & "T" & Right("0" & Hour(nowValue), 2) & ":" & Right("0" & Minute(nowValue), 2) & ":" & Right("0" & Second(nowValue), 2)
End Function

Function FileStatus(path)
    If fso.FileExists(path) Then FileStatus = "present" Else FileStatus = "absent"
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

Function QuoteArgument(value)
    QuoteArgument = Chr(34) & Replace(CStr(value), Chr(34), Chr(34) & Chr(34)) & Chr(34)
End Function

Sub Fail(message)
    LogMessage "error=" & Replace(message, vbCrLf, "; ")
    MsgBox message & vbCrLf & vbCrLf & "Diagnostic log: " & logPath, vbCritical, "Unified Pipeline Launcher"
    WScript.Quit 1
End Sub
