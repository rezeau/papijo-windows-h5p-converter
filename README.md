# Papi Jo Windows H5P Converter

Standalone Windows converter for exported `.h5p` packages. It converts supported
official H5P content packages to their Papi Jo library equivalents without
requiring WordPress or Moodle.

Important: converted files require the corresponding Papi Jo H5P libraries to be
installed on the destination H5P platform before import or use. This app only
converts package metadata and content structure; it does not install Papi Jo
libraries into Moodle, WordPress, H5P.com, Lumi, or any other H5P platform.

## Supported Source Libraries

- Complex fill the blanks -> `H5P.AdvancedBlanksPapiJo 1.4`
- Dialog Cards -> `H5P.DialogcardsPapiJo 1.17`
- Drag and Drop -> `H5P.DragQuestionPapiJo 1.14`
- Drag the Words -> `H5P.DragTextPapiJo 1.1`
- Mark the Words -> `H5P.MarkTheWordsPapiJo 1.1`
- Multimedia Choice -> `H5P.MultiMediaChoicePapiJo 0.4`
- Question Set -> `H5P.QuestionSetPapiJo 1.21`
- Timeline -> `H5P.NDLATimelinePapiJo 0.2`

Question Set conversions also update supported nested H5P library references.
Dialog Cards conversions move legacy image and audio fields into the Papi Jo
media structure.
Timeline conversions replace the `H5P.Timeline` main library and `TimelineJS`
dependency with `H5P.NDLATimelinePapiJo`, and convert `content/content.json`
using the conversion logic from
`tools\convert-timeline-to-papijo.php`.

## Run From Source

Install Python 3.11 or newer for Windows, then run:

```powershell
python .\src\papijo_converter_app.py
```

## Command Line Batch Conversion

```powershell
python .\src\papijo_converter_cli.py .\input-folder .\converted
```

To convert selected libraries only:

```powershell
python .\src\papijo_converter_cli.py .\input-folder .\converted --library H5P.Dialogcards --library H5P.QuestionSet
```

## Build A Windows EXE

Install PyInstaller, then run:

```powershell
.\build-exe.ps1
```

The executable will be created in `dist\`.

To skip tests during a rebuild:

```powershell
.\build-exe.ps1 -SkipTests
```

## Author Release Helper

Use `release.ps1` to update the app version, update Papi Jo target dependency
versions, rebuild the `.exe`, and create a release ZIP in `releases\`.

```powershell
.\release.ps1 -Version 0.1.1
```

Update Papi Jo target dependency versions written into converted packages:

```powershell
.\release.ps1 -Version 0.1.2 -LibraryVersion 'H5P.Dialogcards=1.18'
```

You may repeat `-LibraryVersion` for several libraries. The format is
`H5P.MachineName=major.minor`, using the original H5P machine name on the left
and the Papi Jo target major/minor version on the right.

## Test

```powershell
python -m unittest discover -s tests
```

## Safety

Source `.h5p` files are never modified. Converted files are written to the
selected output folder. If a source filename ends with a dash and number, that
number is removed and the converted Papi Jo library name is appended. For
example, `dynamics-quiz-14.h5p` becomes
`dynamics-quiz-QuestionSetPapiJo.h5p`.
