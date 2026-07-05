from __future__ import annotations

import argparse
from pathlib import Path

from papijo_converter import APP_VERSION, LIBRARIES, PAPIJO_DESTINATION_WARNING, convert_files, find_h5p_files


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert H5P packages to their Papi Jo equivalents.")
    parser.add_argument("--version", action="version", version=f"Papi Jo Windows H5P Converter {APP_VERSION}")
    parser.add_argument("input", type=Path, help="Input .h5p file or folder containing .h5p files.")
    parser.add_argument("output", type=Path, help="Folder where converted .h5p files will be written.")
    parser.add_argument(
        "--library",
        action="append",
        choices=sorted(LIBRARIES.keys()),
        help="Source library to convert. Repeat to select several. Defaults to all supported libraries.",
    )
    args = parser.parse_args()

    print(PAPIJO_DESTINATION_WARNING)
    print()

    if args.input.is_dir():
        sources = find_h5p_files(args.input)
    elif args.input.is_file():
        sources = [args.input]
    else:
        print(f"Input not found: {args.input}")
        return 2

    if not sources:
        print("Cannot find any .h5p files in the selected input.")
        return 1

    results = convert_files(sources, args.output, args.library)
    converted = 0
    for result in results:
        status = "OK" if result.converted else "WARNING"
        target = f" -> {result.output}" if result.output else ""
        print(f"[{status}] {result.source.name}{target}: {result.message}")
        converted += int(result.converted)

    if not converted:
        print("Cannot find any H5P file which can be converted to a Papi Jo version in the selected input.")
        return 1

    print(f"Converted {converted} of {len(results)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
