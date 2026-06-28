# H5P Convert to Papi Jo - Windows Standalone

Standalone Windows converter for exported `.h5p` packages. It converts supported
official H5P content packages to their Papi Jo library equivalents without
requiring WordPress or Moodle.

Important: converted files require the corresponding Papi Jo H5P libraries to be
installed on the destination H5P platform before import or use. This app only
converts package metadata and content structure; it does not install Papi Jo
libraries into Moodle, WordPress, H5P.com, Lumi, or any other H5P platform.

## Supported Source Libraries

- Complex fill the blanks
- Dialog Cards
- Drag and Drop
- Drag the Words
- Mark the Words
- Multimedia Choice
- Question Set

Question Set conversions also update supported nested H5P library references.
Dialog Cards conversions move legacy image and audio fields into the Papi Jo
media structure.

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

## Test

```powershell
python -m unittest discover -s tests
```

## Safety

Source `.h5p` files are never modified. Converted files are written to the
selected output folder using a `-papijo.h5p` suffix.
