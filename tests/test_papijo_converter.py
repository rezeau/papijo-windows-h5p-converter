from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from papijo_converter import LIBRARIES, convert_file


def _write_h5p(path: Path, manifest: dict, content: dict | None = None) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("h5p.json", json.dumps(manifest))
        if content is not None:
            archive.writestr("content/content.json", json.dumps(content))
        archive.writestr("H5P.DragText-1.10/library.json", "{}")
        archive.writestr("content/example.txt", "keep me")


class ConverterTests(unittest.TestCase):
    def test_library_label_displays_target_version(self) -> None:
        label = LIBRARIES["H5P.Dialogcards"].display_label

        self.assertEqual(
            label,
            "Dialog Cards -> H5P.DialogcardsPapiJo 1.17",
        )

    def test_converts_manifest_and_removes_bundled_libraries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "drag-14.h5p"
            output_dir = root / "out"
            manifest = {
                "mainLibrary": "H5P.DragText",
                "preloadedDependencies": [
                    {"machineName": "H5P.DragText", "majorVersion": 1, "minorVersion": 10}
                ],
            }
            _write_h5p(source, manifest)

            result = convert_file(source, output_dir, {"H5P.DragText"})

            self.assertTrue(result.converted)
            self.assertEqual(result.output.name, "drag-DragTextPapiJo.h5p")
            with zipfile.ZipFile(result.output) as archive:
                converted_manifest = json.loads(archive.read("h5p.json"))
                self.assertEqual(converted_manifest["mainLibrary"], "H5P.DragTextPapiJo")
                self.assertEqual(converted_manifest["preloadedDependencies"][0]["minorVersion"], 1)
                self.assertNotIn("H5P.DragText-1.10/library.json", archive.namelist())
                self.assertEqual(archive.read("content/example.txt"), b"keep me")

    def test_dialogcards_wraps_legacy_media(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "fish-id-herbivores-9.h5p"
            output_dir = root / "out"
            manifest = {
                "mainLibrary": "H5P.Dialogcards",
                "preloadedDependencies": [
                    {"machineName": "H5P.Dialogcards", "majorVersion": 1, "minorVersion": 9}
                ],
            }
            content = {
                "dialogs": [
                    {
                        "image": {"path": "images/cat.jpg"},
                        "imageAltText": "cat",
                        "audio": [{"path": "audios/cat.mp3"}],
                    }
                ]
            }
            _write_h5p(source, manifest, content)

            result = convert_file(source, output_dir, {"H5P.Dialogcards"})

            self.assertTrue(result.converted)
            self.assertEqual(result.output.name, "fish-id-herbivores-DialogCardsPapiJo.h5p")
            with zipfile.ZipFile(result.output) as archive:
                converted_content = json.loads(archive.read("content/content.json"))
                dialog = converted_content["dialogs"][0]
                self.assertNotIn("image", dialog)
                self.assertNotIn("audio", dialog)
                self.assertEqual(dialog["imageMedia"]["imageAltText"], "cat")
                self.assertEqual(dialog["audioMedia"]["audio"][0]["path"], "audios/cat.mp3")

    def test_question_set_rewrites_nested_libraries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "dynamics-quiz-14.h5p"
            output_dir = root / "out"
            manifest = {
                "mainLibrary": "H5P.QuestionSet",
                "preloadedDependencies": [
                    {"machineName": "H5P.QuestionSet", "majorVersion": 1, "minorVersion": 21}
                ],
            }
            content = {"questions": [{"library": "H5P.DragText 1.10", "params": {}}]}
            _write_h5p(source, manifest, content)

            result = convert_file(source, output_dir, {"H5P.QuestionSet"})

            self.assertTrue(result.converted)
            self.assertEqual(result.output.name, "dynamics-quiz-QuestionSetPapiJo.h5p")
            with zipfile.ZipFile(result.output) as archive:
                converted_content = json.loads(archive.read("content/content.json"))
                self.assertEqual(converted_content["questions"][0]["library"], "H5P.DragTextPapiJo 1.1")


if __name__ == "__main__":
    unittest.main()
