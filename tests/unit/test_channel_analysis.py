"""Tests for incremental PCM frame decoding."""

import struct

import pytest

from ewp_transcripts.domain.errors import ChannelAnalysisError
from ewp_transcripts.media.channel_analysis import _pcm16_stereo_samples


def test_pcm_frames_are_reassembled_across_arbitrary_chunks() -> None:
    encoded = b"".join(
        struct.pack("<hh", left, right)
        for left, right in [(-100, 100), (200, -200), (32767, -32768)]
    )
    chunks = [encoded[:1], encoded[1:5], encoded[5:10], encoded[10:]]

    assert list(_pcm16_stereo_samples(chunks)) == [
        (-100, 100),
        (200, -200),
        (32767, -32768),
    ]


def test_incomplete_pcm_frame_is_rejected() -> None:
    with pytest.raises(ChannelAnalysisError, match="incomplete"):
        list(_pcm16_stereo_samples([b"\x00\x01\x02"]))
