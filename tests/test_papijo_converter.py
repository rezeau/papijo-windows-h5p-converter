from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from papijo_converter import LIBRARIES, _convert_drag_text_tips, convert_file


def _write_h5p(path: Path, manifest: dict, content: dict | None = None) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("h5p.json", json.dumps(manifest))
        if content is not None:
            archive.writestr("content/content.json", json.dumps(content))
        archive.writestr("H5P.DragText-1.10/library.json", "{}")
        archive.writestr("content/example.txt", "keep me")


class ConverterTests(unittest.TestCase):
    def test_drag_text_tip_conversion_leaves_colons_outside_expressions_unchanged(self) -> None:
        self.assertEqual(
            _convert_drag_text_tips("Instruction: choose *Paris:Capital of France*."),
            "Instruction: choose *Paris::Capital of France*.",
        )

    def test_drag_text_tip_conversion_handles_multiple_expressions(self) -> None:
        self.assertEqual(
            _convert_drag_text_tips("*Paris:France* and *Rome:Italy*"),
            "*Paris::France* and *Rome::Italy*",
        )

    def test_drag_text_tip_conversion_does_not_double_convert(self) -> None:
        self.assertEqual(
            _convert_drag_text_tips("*Paris::Capital of France*"),
            "*Paris::Capital of France*",
        )

    def test_drag_text_tip_conversion_preserves_feedback_syntax(self) -> None:
        self.assertEqual(
            _convert_drag_text_tips(r"*Madrid:Spain\+Correct: yes\-Incorrect: no*"),
            r"*Madrid::Spain\+Correct: yes\-Incorrect: no*",
        )
        self.assertEqual(
            _convert_drag_text_tips(r"*Lisbon\+Correct: yes\-Incorrect: no*"),
            r"*Lisbon\+Correct: yes\-Incorrect: no*",
        )

    def test_library_label_displays_target_version(self) -> None:
        label = LIBRARIES["H5P.Dialogcards"].display_label

        self.assertEqual(
            label,
            "Dialog Cards -> H5P.DialogcardsPapiJo 1.17",
        )

    def test_converts_drag_text_manifest_content_and_removes_bundled_libraries(self) -> None:
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
            content = {
                "textField": (
                    "Instruction: choose *Paris:Capital of France* and *Rome:Italy*. "
                    "Already converted: *Berlin::Capital of Germany*. "
                    r"Feedback: *Madrid:Capital of Spain\+Correct: yes\-Incorrect: no*. "
                    r"No tip: *Lisbon\+Correct: yes\-Incorrect: no*."
                )
            }
            _write_h5p(source, manifest, content)

            result = convert_file(source, output_dir, {"H5P.DragText"})

            self.assertTrue(result.converted)
            self.assertEqual(result.output.name, "drag-DragTextPapiJo.h5p")
            with zipfile.ZipFile(result.output) as archive:
                converted_manifest = json.loads(archive.read("h5p.json"))
                self.assertEqual(converted_manifest["mainLibrary"], "H5P.DragTextPapiJo")
                self.assertEqual(converted_manifest["preloadedDependencies"][0]["minorVersion"], 3)
                converted_content = json.loads(archive.read("content/content.json"))
                self.assertEqual(
                    converted_content["textField"],
                    (
                        "Instruction: choose *Paris::Capital of France* and *Rome::Italy*. "
                        "Already converted: *Berlin::Capital of Germany*. "
                        r"Feedback: *Madrid::Capital of Spain\+Correct: yes\-Incorrect: no*. "
                        r"No tip: *Lisbon\+Correct: yes\-Incorrect: no*."
                    ),
                )
                self.assertNotIn("H5P.DragText-1.10/library.json", archive.namelist())
                self.assertEqual(archive.read("content/example.txt"), b"keep me")

    def test_converts_timeline_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "history-tour-3.h5p"
            output_dir = root / "out"
            manifest = {
                "mainLibrary": "H5P.Timeline",
                "preloadedDependencies": [
                    {"machineName": "H5P.Timeline", "majorVersion": 1, "minorVersion": 1},
                    {"machineName": "TimelineJS", "majorVersion": 1, "minorVersion": 1},
                ],
            }
            content = {
                "timeline": {
                    "headline": "History tour",
                    "text": "<div>Intro</div>",
                    "language": "fr",
                    "date": [
                        {
                            "headline": "First stop",
                            "text": "<div>Arrived</div>",
                            "startDate": "2026,7,8",
                            "asset": {"media": "https://example.com/image.jpg", "caption": "A caption"},
                        }
                    ],
                }
            }
            _write_h5p(source, manifest, content)

            result = convert_file(source, output_dir, {"H5P.Timeline"})

            self.assertTrue(result.converted)
            self.assertEqual(result.output.name, "history-tour-NDLATimelinePapiJo.h5p")
            with zipfile.ZipFile(result.output) as archive:
                converted_manifest = json.loads(archive.read("h5p.json"))
                converted_content = json.loads(archive.read("content/content.json"))
                self.assertEqual(converted_manifest["mainLibrary"], "H5P.NDLATimelinePapiJo")
                self.assertEqual(
                    converted_manifest["preloadedDependencies"][1],
                    {"machineName": "H5P.NDLATimelinePapiJo", "majorVersion": 0, "minorVersion": 2},
                )
                self.assertEqual(converted_content["language"], "fr")
                self.assertEqual(converted_content["titleSlide"]["title"], "History tour")
                self.assertEqual(converted_content["timelineItems"][0]["title"], "First stop")
                self.assertEqual(converted_content["timelineItems"][0]["startDate"], "2026-7-8")

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
            content = {
                "questions": [
                    {
                        "library": "H5P.DragText 1.10",
                        "params": {"textField": "Instruction: choose *Paris:France*."},
                    },
                ]
            }
            _write_h5p(source, manifest, content)

            result = convert_file(source, output_dir, {"H5P.QuestionSet"})

            self.assertTrue(result.converted)
            self.assertEqual(result.output.name, "dynamics-quiz-QuestionSetPapiJo.h5p")
            with zipfile.ZipFile(result.output) as archive:
                converted_content = json.loads(archive.read("content/content.json"))
                question = converted_content["questions"][0]
                self.assertEqual(question["library"], "H5P.DragTextPapiJo 1.3")
                self.assertEqual(
                    question["params"]["textField"],
                    "Instruction: choose *Paris::France*.",
                )


if __name__ == "__main__":
    unittest.main()
