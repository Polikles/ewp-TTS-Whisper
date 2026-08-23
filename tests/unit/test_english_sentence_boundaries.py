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
