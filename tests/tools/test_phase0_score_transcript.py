from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[2] / "tools" / "phase0_score_transcript.py"
)
SPEC = importlib.util.spec_from_file_location("phase0_score_transcript", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
SCORER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SCORER
SPEC.loader.exec_module(SCORER)


class NormalizeTranscriptTests(unittest.TestCase):
    def test_ignores_case_punctuation_and_line_layout(self) -> None:
        reference = "To jest ŁÓDŹ.\nCzy działa?"
        hypothesis = "to jest łódź — czy działa"

        self.assertEqual(
            SCORER.normalize_transcript(reference),
            SCORER.normalize_transcript(hypothesis),
        )

    def test_preserves_polish_diacritics_and_number_forms(self) -> None:
        self.assertNotEqual(
            SCORER.normalize_transcript("pomyślę 15"),
            SCORER.normalize_transcript("pomysle piętnaście"),
        )


class ScoreTests(unittest.TestCase):
    def test_reports_zero_for_formatting_only_differences(self) -> None:
        report = SCORER.score("Ala ma kota.\nNaprawdę!", "ala ma kota naprawdę")

        self.assertEqual(report["wer"], 0.0)
        self.assertEqual(report["cer"], 0.0)

    def test_reports_word_substitution_and_deletion(self) -> None:
        report = SCORER.score("jeden dwa trzy cztery", "jeden zły cztery")

        self.assertEqual(report["wer"], 0.5)
        self.assertEqual(report["word_errors"]["substitutions"], 1)
        self.assertEqual(report["word_errors"]["deletions"], 1)
        self.assertEqual(report["word_errors"]["insertions"], 0)

    def test_rejects_empty_normalized_reference(self) -> None:
        with self.assertRaisesRegex(ValueError, "reference transcript is empty"):
            SCORER.score("...", "tekst")


class JsonHypothesisTests(unittest.TestCase):
    def test_extracts_only_ordered_segment_text(self) -> None:
        document = {
            "segments": [
                {
                    "start": 10.0,
                    "end": 11.0,
                    "speaker": "SPEAKER_01",
                    "text": "Pierwsze zdanie.",
                },
                {
                    "start": 11.0,
                    "end": 12.0,
                    "speaker": "SPEAKER_00",
                    "text": "Drugie zdanie!",
                },
            ]
        }

        extracted = SCORER.extract_segment_text(json.dumps(document))

        self.assertEqual(extracted, "Pierwsze zdanie. Drugie zdanie!")
        report = SCORER.score("pierwsze zdanie drugie zdanie", extracted)
        self.assertEqual(report["wer"], 0.0)
        self.assertEqual(report["cer"], 0.0)

    def test_rejects_json_without_segments(self) -> None:
        with self.assertRaisesRegex(ValueError, "'segments' list"):
            SCORER.extract_segment_text("{}")


if __name__ == "__main__":
    unittest.main()
