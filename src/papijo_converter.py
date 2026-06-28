from __future__ import annotations

import json
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterable


PAPIJO_DESTINATION_WARNING = (
    "Converted files require the corresponding Papi Jo H5P libraries to be "
    "installed on the destination site before import or use. This app only "
    "converts the .h5p package metadata and content structure; it does not "
    "install Papi Jo libraries into Moodle, WordPress, H5P.com, Lumi, or any "
    "other H5P platform."
)


@dataclass(frozen=True)
class LibraryRule:
    machine_name: str
    label: str
    target: str
    target_major: int
    target_minor: int

    @property
    def display_label(self) -> str:
        return f"{self.label} -> {self.target} {self.target_major}.{self.target_minor}"


LIBRARIES: dict[str, LibraryRule] = {
    "H5P.AdvancedBlanks": LibraryRule(
        "H5P.AdvancedBlanks", "Complex fill the blanks", "H5P.AdvancedBlanksPapiJo", 1, 4
    ),
    "H5P.Dialogcards": LibraryRule(
        "H5P.Dialogcards", "Dialog Cards", "H5P.DialogcardsPapiJo", 1, 17
    ),
    "H5P.DragQuestion": LibraryRule(
        "H5P.DragQuestion", "Drag and Drop", "H5P.DragQuestionPapiJo", 1, 14
    ),
    "H5P.DragText": LibraryRule(
        "H5P.DragText", "Drag the Words", "H5P.DragTextPapiJo", 1, 1
    ),
    "H5P.MarkTheWords": LibraryRule(
        "H5P.MarkTheWords", "Mark the Words", "H5P.MarkTheWordsPapiJo", 1, 1
    ),
    "H5P.MultiMediaChoice": LibraryRule(
        "H5P.MultiMediaChoice", "Multimedia Choice", "H5P.MultiMediaChoicePapiJo", 0, 4
    ),
    "H5P.QuestionSet": LibraryRule(
        "H5P.QuestionSet", "Question Set", "H5P.QuestionSetPapiJo", 1, 21
    ),
}


@dataclass(frozen=True)
class ConversionResult:
    source: Path
    converted: bool
    output: Path | None = None
    library: str | None = None
    message: str = ""


class ConversionError(Exception):
    pass


def find_h5p_files(folder: Path) -> list[Path]:
    return sorted(path for path in folder.iterdir() if path.is_file() and path.suffix.lower() == ".h5p")


def convert_files(
    sources: Iterable[Path],
    output_dir: Path,
    selected_libraries: Iterable[str] | None = None,
) -> list[ConversionResult]:
    output_dir.mkdir(parents=True, exist_ok=True)
    selected = set(selected_libraries or LIBRARIES.keys())
    return [convert_file(Path(source), output_dir, selected) for source in sources]


def convert_file(source: Path, output_dir: Path, selected_libraries: set[str]) -> ConversionResult:
    if source.suffix.lower() != ".h5p":
        return ConversionResult(source=source, converted=False, message="not an .h5p file.")

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(source, "r") as archive:
            names = archive.namelist()
            if "h5p.json" not in names:
                raise ConversionError("missing h5p.json.")

            manifest = _read_json(archive, "h5p.json")
            machine = manifest.get("mainLibrary")
            if not isinstance(machine, str) or not machine:
                raise ConversionError("invalid h5p.json.")

            if machine not in LIBRARIES:
                return ConversionResult(
                    source=source,
                    converted=False,
                    library=machine,
                    message=f"{machine} is not supported for conversion.",
                )
            if machine not in selected_libraries:
                return ConversionResult(
                    source=source,
                    converted=False,
                    library=machine,
                    message=f"{LIBRARIES[machine].label} was not selected.",
                )

            rule = LIBRARIES[machine]
            if not _replace_dependency(manifest, rule):
                return ConversionResult(
                    source=source,
                    converted=False,
                    library=machine,
                    message=f"could not find the {machine} dependency in h5p.json.",
                )

            manifest["mainLibrary"] = rule.target
            content = None
            if "content/content.json" in names:
                content = _read_json(archive, "content/content.json")
                if machine == "H5P.QuestionSet":
                    _convert_question_set_content(content)
                elif machine == "H5P.Dialogcards":
                    _convert_dialog_cards_content(content)

            output = _unique_output_path(output_dir, source.stem + "-papijo.h5p")
            _write_converted_archive(archive, output, manifest, content)
            return ConversionResult(
                source=source,
                converted=True,
                output=output,
                library=machine,
                message=f"converted {rule.label}.",
            )
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError, ConversionError) as exc:
        return ConversionResult(source=source, converted=False, message=str(exc))


def _read_json(archive: zipfile.ZipFile, name: str) -> Any:
    with archive.open(name, "r") as handle:
        return json.loads(handle.read().decode("utf-8-sig"))


def _replace_dependency(manifest: dict[str, Any], rule: LibraryRule) -> bool:
    for key in ("preloadedDependencies", "dynamicDependencies", "editorDependencies"):
        dependencies = manifest.get(key)
        if not isinstance(dependencies, list):
            continue
        for dependency in dependencies:
            if not isinstance(dependency, dict):
                continue
            if dependency.get("machineName") == rule.machine_name:
                dependency["machineName"] = rule.target
                dependency["majorVersion"] = rule.target_major
                dependency["minorVersion"] = rule.target_minor
                return True
    return False


def _convert_question_set_content(content: Any) -> None:
    mapping = {
        machine: f"{rule.target} {rule.target_major}.{rule.target_minor}"
        for machine, rule in LIBRARIES.items()
        if machine != "H5P.QuestionSet"
    }
    _replace_library_references(content, mapping)


def _replace_library_references(value: Any, mapping: dict[str, str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "library" and isinstance(child, str):
                machine = child.strip().split(" ", 1)[0]
                if machine in mapping:
                    value[key] = mapping[machine]
                    continue
            _replace_library_references(child, mapping)
    elif isinstance(value, list):
        for child in value:
            _replace_library_references(child, mapping)


def _convert_dialog_cards_content(content: Any) -> None:
    _wrap_dialog_media(content)


def _wrap_dialog_media(value: Any) -> None:
    if isinstance(value, dict):
        dialogs = value.get("dialogs")
        if isinstance(dialogs, list):
            for dialog in dialogs:
                if not isinstance(dialog, dict):
                    continue
                if "image" in dialog and "imageMedia" not in dialog:
                    dialog["imageMedia"] = {"image": dialog.pop("image")}
                    if "imageAltText" in dialog:
                        dialog["imageMedia"]["imageAltText"] = dialog.pop("imageAltText")
                if "audio" in dialog and "audioMedia" not in dialog:
                    dialog["audioMedia"] = {"audio": dialog.pop("audio")}
        for child in value.values():
            _wrap_dialog_media(child)
    elif isinstance(value, list):
        for child in value:
            _wrap_dialog_media(child)


def _write_converted_archive(
    source_archive: zipfile.ZipFile,
    output: Path,
    manifest: dict[str, Any],
    content: Any,
) -> None:
    library_dirs = _archive_library_dirs(source_archive)
    with TemporaryDirectory() as temp_dir:
        temp_output = Path(temp_dir) / "converted.h5p"
        with zipfile.ZipFile(temp_output, "w", compression=zipfile.ZIP_DEFLATED) as converted:
            for info in source_archive.infolist():
                name = info.filename.replace("\\", "/")
                if info.is_dir() or _is_archive_library_file(name, library_dirs):
                    continue
                if name == "h5p.json":
                    data = _json_bytes(manifest)
                elif name == "content/content.json" and content is not None:
                    data = _json_bytes(content)
                else:
                    data = source_archive.read(info.filename)
                converted.writestr(name, data)
        shutil.move(str(temp_output), output)


def _archive_library_dirs(archive: zipfile.ZipFile) -> set[str]:
    library_dirs: set[str] = set()
    for name in archive.namelist():
        normalized = name.replace("\\", "/").rstrip("/")
        if normalized.count("/") == 1 and normalized.endswith("/library.json"):
            library_dirs.add(normalized.rsplit("/", 1)[0])
    return library_dirs


def _is_archive_library_file(name: str, library_dirs: set[str]) -> bool:
    top_level = name.split("/", 1)[0]
    return top_level in library_dirs


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, indent=2, separators=(",", ": ")).encode("utf-8")


def _unique_output_path(output_dir: Path, filename: str) -> Path:
    output = output_dir / filename
    if not output.exists():
        return output

    stem = output.stem
    suffix = output.suffix
    counter = 2
    while True:
        candidate = output_dir / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
