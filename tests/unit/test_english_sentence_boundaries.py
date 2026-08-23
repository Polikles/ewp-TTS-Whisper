"""Regression tests for English punctuation around closing quotation marks."""

from ewp_transcripts.exporters.transcript import split_sentences


def test_english_period_before_closing_quote_splits_after_quote() -> None:
    assert split_sentences('He said "This works." Then he left.') == (
        'He said "This works."',
        "Then he left.",
    )


def test_polish_period_after_closing_quote_still_splits_normally() -> None:
    assert split_sentences("Powiedział „To działa”. Potem wyszedł.") == (
        "Powiedział „To działa”.",
        "Potem wyszedł.",
    )


def test_legal_case_v_abbreviation_does_not_end_sentence() -> None:
    assert split_sentences("Battle v. Microsoft was an important case. Next topic.") == (
        "Battle v. Microsoft was an important case.",
        "Next topic.",
    )
