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

    def test_converts_mark_the_words_legacy_score_points_behaviour(self) -> None:
        cases = [
            (
                "enabled",
                {"showScorePoints": True, "enableRetry": False},
                {"enableRetry": False, "displayTicksMode": "ticksAndScorepoints"},
                "Send answer",
            ),
            (
                "disabled",
                {"showScorePoints": False},
                {"displayTicksMode": "ticksOnly"},
                None,
            ),
            (
                "missing",
                {"enableRetry": True},
                {"enableRetry": True},
                None,
            ),
            (
                "existing-target",
                {"showScorePoints": False, "displayTicksMode": "ticksAbove"},
                {"displayTicksMode": "ticksAbove"},
                None,
            ),
            (
                "non-object-behaviour",
                "leave unchanged",
                "leave unchanged",
                None,
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "out"
            for name, behaviour, expected_behaviour, submit_text in cases:
                with self.subTest(name=name):
                    source = root / f"mark-{name}.h5p"
                    manifest = {
                        "mainLibrary": "H5P.MarkTheWords",
                        "preloadedDependencies": [
                            {
                                "machineName": "H5P.MarkTheWords",
                                "majorVersion": 1,
                                "minorVersion": 11,
                            }
                        ],
                    }
                    content = {
                        "textField": "Mark the *correct* word.",
                        "behaviour": behaviour,
                        "unrelated": {"keep": "unchanged"},
                    }
                    if submit_text is not None:
                        content["submitAnswerButton"] = submit_text
                    _write_h5p(source, manifest, content)

                    result = convert_file(source, output_dir, {"H5P.MarkTheWords"})

                    self.assertTrue(result.converted)
                    with zipfile.ZipFile(result.output) as archive:
                        converted_manifest = json.loads(archive.read("h5p.json"))
                        converted_content = json.loads(archive.read("content/content.json"))

                    self.assertEqual(
                        converted_manifest["preloadedDependencies"][0],
                        {
                            "machineName": "H5P.MarkTheWordsPapiJo",
                            "majorVersion": 1,
                            "minorVersion": 2,
                        },
                    )
                    self.assertEqual(converted_content["behaviour"], expected_behaviour)
                    self.assertNotIn("showScorePoints", converted_content["behaviour"])
                    self.assertEqual(converted_content["unrelated"], {"keep": "unchanged"})
                    if submit_text is None:
                        self.assertNotIn("submitAnswerButton", converted_content)
                    else:
                        self.assertEqual(converted_content["submitAnswerButton"], submit_text)

    def test_timeline_is_not_supported(self) -> None:
        self.assertNotIn("H5P.Timeline", LIBRARIES)

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
            _write_h5p(source, manifest, {"timeline": {}})

            result = convert_file(source, output_dir, set(LIBRARIES))

            self.assertFalse(result.converted)
            self.assertIsNone(result.output)
            self.assertEqual(result.library, "H5P.Timeline")
            self.assertEqual(result.message, "H5P.Timeline is not supported for conversion.")
            self.assertEqual(list(output_dir.iterdir()), [])

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

    def test_question_set_rewrites_nested_content_and_used_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "dynamics-quiz-14.h5p"
            output_dir = root / "out"
            manifest = {
                "mainLibrary": "H5P.QuestionSet",
                "preloadedDependencies": [
                    {"machineName": "H5P.QuestionSet", "majorVersion": 1, "minorVersion": 21},
                    {"machineName": "H5P.MarkTheWords", "majorVersion": 1, "minorVersion": 11},
                    {"machineName": "H5P.TrueFalse", "majorVersion": 1, "minorVersion": 8},
                    {
                        "machineName": "H5P.MultiMediaChoice",
                        "majorVersion": 0,
                        "minorVersion": 3,
                    },
                    {"machineName": "H5P.Dialogcards", "majorVersion": 1, "minorVersion": 9},
                ],
                "dynamicDependencies": [
                    {"machineName": "H5P.DragText", "majorVersion": 1, "minorVersion": 10},
                    {"machineName": "H5P.DragQuestion", "majorVersion": 1, "minorVersion": 15},
                ],
                "editorDependencies": [
                    {"machineName": "H5P.AdvancedBlanks", "majorVersion": 1, "minorVersion": 0},
                ],
            }
            content = {
                "questions": [
                    {
                        "library": "H5P.MarkTheWords 1.11",
                        "params": {
                            "textField": "Mark the *answer*.",
                            "behaviour": {"showScorePoints": False},
                        },
                    },
                    {
                        "library": "H5P.DragText 1.10",
                        "params": {"textField": "Instruction: choose *Paris:France*."},
                    },
                    {"library": "H5P.DragQuestion 1.15", "params": {}},
                    {"library": "H5P.AdvancedBlanks 1.0", "params": {}},
                    {"library": "H5P.TrueFalse 1.8", "params": {}},
                    {"library": "H5P.Dialogcards 1.9", "params": {}},
                ]
            }
            _write_h5p(source, manifest, content)

            result = convert_file(source, output_dir, {"H5P.QuestionSet"})

            self.assertTrue(result.converted)
            self.assertEqual(result.output.name, "dynamics-quiz-QuestionSetPapiJo.h5p")
            with zipfile.ZipFile(result.output) as archive:
                converted_manifest = json.loads(archive.read("h5p.json"))
                converted_content = json.loads(archive.read("content/content.json"))

                self.assertEqual(
                    converted_manifest["preloadedDependencies"],
                    [
                        {
                            "machineName": "H5P.QuestionSetPapiJo",
                            "majorVersion": 1,
                            "minorVersion": 23,
                        },
                        {
                            "machineName": "H5P.MarkTheWordsPapiJo",
                            "majorVersion": 1,
                            "minorVersion": 2,
                        },
                        {"machineName": "H5P.TrueFalse", "majorVersion": 1, "minorVersion": 8},
                        {
                            "machineName": "H5P.MultiMediaChoice",
                            "majorVersion": 0,
                            "minorVersion": 3,
                        },
                        {"machineName": "H5P.Dialogcards", "majorVersion": 1, "minorVersion": 9},
                    ],
                )
                self.assertEqual(
                    converted_manifest["dynamicDependencies"],
                    [
                        {
                            "machineName": "H5P.DragTextPapiJo",
                            "majorVersion": 1,
                            "minorVersion": 3,
                        },
                        {
                            "machineName": "H5P.DragQuestionPapiJo",
                            "majorVersion": 1,
                            "minorVersion": 14,
                        },
                    ],
                )
                self.assertEqual(
                    converted_manifest["editorDependencies"],
                    [
                        {
                            "machineName": "H5P.AdvancedBlanksPapiJo",
                            "majorVersion": 1,
                            "minorVersion": 4,
                        }
                    ],
                )

                (
                    mark_the_words,
                    drag_text,
                    drag_question,
                    advanced_blanks,
                    true_false,
                    dialog_cards,
                ) = converted_content["questions"]
                self.assertEqual(mark_the_words["library"], "H5P.MarkTheWordsPapiJo 1.2")
                self.assertEqual(
                    mark_the_words["params"]["behaviour"],
                    {"displayTicksMode": "ticksOnly"},
                )
                self.assertEqual(drag_text["library"], "H5P.DragTextPapiJo 1.3")
                self.assertEqual(
                    drag_text["params"]["textField"],
                    "Instruction: choose *Paris::France*.",
                )
                self.assertEqual(drag_question["library"], "H5P.DragQuestionPapiJo 1.14")
                self.assertEqual(advanced_blanks["library"], "H5P.AdvancedBlanksPapiJo 1.4")
                self.assertEqual(true_false["library"], "H5P.TrueFalse 1.8")
                self.assertEqual(dialog_cards["library"], "H5P.Dialogcards 1.9")

                converted_dependency_versions = {
                    dependency["machineName"]: (
                        dependency["majorVersion"],
                        dependency["minorVersion"],
                    )
                    for key in (
                        "preloadedDependencies",
                        "dynamicDependencies",
                        "editorDependencies",
                    )
                    for dependency in converted_manifest[key]
                }
                for question in (mark_the_words, drag_text, drag_question, advanced_blanks):
                    machine, version = question["library"].split(" ", 1)
                    self.assertEqual(
                        converted_dependency_versions[machine],
                        tuple(int(part) for part in version.split(".")),
                    )


if __name__ == "__main__":
    unittest.main()
