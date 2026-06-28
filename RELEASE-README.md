# Release Helper Notes

Use `release.ps1` when you, the app author, need to update the Windows app
version or one or more Papi Jo target library versions.

The script can:

- update `APP_VERSION` in `src/papijo_converter.py`
- update Papi Jo target major/minor versions in the converter rules
- run the test suite
- rebuild `dist\H5P-Convert-to-Papi-Jo.exe`
- create a release ZIP in `releases\`

## Basic Release

From PowerShell:

```powershell
Set-Location "C:\Users\josep\OneDrive\Documents\h5p-convert-to-papijo-for windows standalone"
.\release.ps1 -Version 0.1.2
```

## Update One Papi Jo Library Version

Example: update Dialog Cards Papi Jo to `1.18`.

```powershell
.\release.ps1 -Version 0.1.2 -LibraryVersion 'H5P.Dialogcards=1.18'
```

The left side uses the original H5P machine name. The right side is the Papi Jo
target major/minor version to write into converted `.h5p` packages.

## Update Several Papi Jo Library Versions

```powershell
.\release.ps1 -Version 0.1.2 `
  -LibraryVersion 'H5P.Dialogcards=1.18' `
  -LibraryVersion 'H5P.QuestionSet=1.22'
```

## Test Without Changing Files

Use `-WhatIf` to preview the operation without updating files, rebuilding, or
creating a ZIP.

```powershell
.\release.ps1 -Version 0.1.2 -LibraryVersion 'H5P.Dialogcards=1.18' -WhatIf
```

The message:

```text
What if: Performing the operation "release version 0.1.2" on target "..."
```

means the script would perform that release if `-WhatIf` were removed.

## Outputs

After a real run, the rebuilt executable is:

```text
dist\H5P-Convert-to-Papi-Jo.exe
```

The release ZIP is created in:

```text
releases\
```

Upload the rebuilt `.exe` or the release ZIP to the matching GitHub Release.
