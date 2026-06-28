# Author release helper.
# See RELEASE-README.md for full usage notes.
#
# Common examples:
#   .\release.ps1 -Version 0.1.2
#   .\release.ps1 -Version 0.1.2 -LibraryVersion 'H5P.Dialogcards=1.18'
#   .\release.ps1 -Version 0.1.2 -LibraryVersion 'H5P.Dialogcards=1.18' -WhatIf
#
# -LibraryVersion uses the original H5P machine name on the left and the
# Papi Jo target major/minor version on the right.

[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string] $Version,

    # Repeat this option for every Papi Jo target dependency version to update.
    # Format: H5P.MachineName=papijo-major.papijo-minor
    [string[]] $LibraryVersion = @(),

    [switch] $SkipBuild,

    [string] $OutputDirectory = (Join-Path $PSScriptRoot 'releases')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$converterFile = Join-Path $PSScriptRoot 'src\papijo_converter.py'
$executable = Join-Path $PSScriptRoot 'dist\H5P-Convert-to-Papi-Jo.exe'
$releaseName = "H5P-Convert-to-Papi-Jo-$Version"

if (-not (Test-Path -LiteralPath $converterFile -PathType Leaf)) {
    throw "Converter file not found: $converterFile"
}

function Set-AppVersion {
    param(
        [string] $Content,
        [string] $NewVersion
    )

    $pattern = '(?m)^APP_VERSION = "[^"]+"$'
    $matches = [regex]::Matches($Content, $pattern)
    if (1 -ne $matches.Count) {
        throw "Could not find exactly one APP_VERSION constant in $converterFile."
    }

    return [regex]::Replace($Content, $pattern, "APP_VERSION = `"$NewVersion`"", 1)
}

function Set-LibraryField {
    param(
        [string] $Content,
        [string] $MachineName,
        [string] $Field,
        [string] $NewValue
    )

    $machine = [regex]::Escape($MachineName)
    $fieldName = [regex]::Escape($Field)
    $pattern = "(?s)(`"$machine`"\s*:\s*LibraryRule\(\s*.*?$fieldName\s*=\s*)\d+"
    $matches = [regex]::Matches($Content, $pattern)
    if (1 -ne $matches.Count) {
        throw "Could not find exactly one '$Field' field for $MachineName in $converterFile."
    }

    return [regex]::Replace(
        $Content,
        $pattern,
        {
            param($match)
            return $match.Groups[1].Value + $NewValue
        },
        1
    )
}

function Update-LibraryVersion {
    param(
        [string] $Content,
        [string] $Definition,
        [string] $MajorField,
        [string] $MinorField
    )

    $match = [regex]::Match($Definition, '^(?<machine>H5P\.[A-Za-z0-9]+)=(?<version>\d+\.\d+)$')
    if (-not $match.Success) {
        throw "Invalid library version '$Definition'. Use H5P.MachineName=1.4."
    }

    $machineName = $match.Groups['machine'].Value
    $parts = $match.Groups['version'].Value.Split('.')
    $Content = Set-LibraryField $Content $machineName $MajorField $parts[0]
    $Content = Set-LibraryField $Content $machineName $MinorField $parts[1]
    return $Content
}

$content = Get-Content -LiteralPath $converterFile -Raw
$content = Set-AppVersion $content $Version

foreach ($definition in $LibraryVersion) {
    $content = Update-LibraryVersion $content $definition 'target_major' 'target_minor'
}

if (-not $PSCmdlet.ShouldProcess($PSScriptRoot, "release version $Version")) {
    return
}

$utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($converterFile, $content, $utf8WithoutBom)

python -m unittest discover -s tests

if (-not $SkipBuild) {
    & (Join-Path $PSScriptRoot 'build-exe.ps1') -SkipTests
}

if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw "Executable not found: $executable"
}

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$archive = Join-Path $OutputDirectory "$releaseName.zip"
$stagingRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("h5p-convert-to-papijo-windows-release-" + [guid]::NewGuid().ToString('N'))
$stagingDirectory = Join-Path $stagingRoot $releaseName

try {
    New-Item -ItemType Directory -Path $stagingDirectory -Force | Out-Null
    Copy-Item -LiteralPath $executable -Destination $stagingDirectory -Force
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'README.md') -Destination $stagingDirectory -Force
    if (Test-Path -LiteralPath $archive) {
        Remove-Item -LiteralPath $archive -Force
    }
    Compress-Archive -LiteralPath $stagingDirectory -DestinationPath $archive -CompressionLevel Optimal
}
finally {
    if (Test-Path -LiteralPath $stagingRoot) {
        Remove-Item -LiteralPath $stagingRoot -Recurse -Force
    }
}

Write-Host "Created $archive"
