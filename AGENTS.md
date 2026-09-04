# Repository Rules

## Network Path Regression Requirement

The project source may be opened as either
`Z:\Vinay_Vaida\Unified-Pipeline-Launcher` or
`\\wcsmb\Mycology\Vinay_Vaida\Unified-Pipeline-Launcher` (`Z:\` maps to
`\\wcsmb\Mycology\`). The installed runtime remains local under
`%LOCALAPPDATA%\OrganizationName\UnifiedPipelineLauncher`.

For launcher, updater, runtime, PowerShell, Qt resource, or path changes, test
the mapped path, equivalent UNC path, and local installed runtime. Never let a
network source path become `sys.prefix` for the local runtime. Regressions must
cover missing `encodings`, quoted/illegal `Resolve-Path` input, and malformed
SVG warnings.
