"""Tests for non-destructive translation artifact publication."""

from pathlib import Path
from uuid import uuid4

from ewp_transcripts.domain.translation import TranslationParent, load_transcript_translation
from ewp_transcripts.translation_review_format import load_translation_review
from ewp_transcripts.translation_review_service import prepare_translation_review
from ewp_transcripts.translation_service import build_manual_translation
from ewp_transcripts.translation_storage import (
    publish_next_translation,
    publish_translation_review,
)

ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "examples/results.example.json"


def _completed_review():
    review = prepare_translation_review(RESULT, target_language="pl")
    return review.model_copy(
        update={
            "units": tuple(
                unit.model_copy(update={"target_text": f"Tłumaczenie {index}."})
                for index, unit in enumerate(review.units, start=1)
            )
        }
    )


def test_review_publication_is_language_qualified_and_non_destructive(tmp_path: Path) -> None:
    review = prepare_translation_review(RESULT, target_language="pl")

    first = publish_translation_review(review, output_directory=tmp_path)
    second = publish_translation_review(review, output_directory=tmp_path)

    assert first.name == "S01E01_pl.translation.review.txt"
    assert second.name == "S01E01_pl.translation.review_v002.txt"
    assert load_translation_review(first) == review


def test_translation_publication_allocates_immutable_numbers(tmp_path: Path) -> None:
    translation = build_manual_translation(_completed_review())

    first, first_path = publish_next_translation(translation, output_directory=tmp_path)
    second, second_path = publish_next_translation(translation, output_directory=tmp_path)

    assert first.translation_number == 1
    assert second.translation_number == 2
    assert first_path.name == "S01E01_pl_translation_001.json"
    assert second_path.name == "S01E01_pl_translation_002.json"
    assert load_transcript_translation(second_path) == second


def test_child_translation_numbers_after_parent_in_separate_directory(tmp_path: Path) -> None:
    translation = build_manual_translation(_completed_review()).model_copy(
        update={
            "parent_translation": TranslationParent(
                translation_id=uuid4(),
                translation_number=7,
                sha256="a" * 64,
                filename="S01E01_pl_translation_007.json",
            )
        }
    )

    child, child_path = publish_next_translation(translation, output_directory=tmp_path)

    assert child.translation_number == 8
    assert child_path.name == "S01E01_pl_translation_008.json"
