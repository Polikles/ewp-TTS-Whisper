# Export Formats

## 1. Principle

An export is a deterministic transformation of a selected transcript source. In v0.1
the source is raw `results.json`; planned v0.2.0 revision-aware export first resolves raw
canonical text or a compatible revision into `EffectiveTranscript`. Exporting must not
run WhisperX, pyannote, or open source audio.

## 2. TXT

Filename:

```text
<job_id>_transcript.txt
```

Rules:

- no timestamps;
- UTF-8;
- one sentence per line;
- with multiple speakers, each block starts with `Name:`;
- a speaker change starts a new block;
- consecutive sentences by the same speaker remain in the same block;
- with one speaker, the label is omitted;
- no stylistic or LLM correction.

Common abbreviations such as `m.in.`, `np.`, `tzw.`, `tys.`, and `vs.`, and address
tokens ending in `.pl`, `.eu`, `.com`, or `.edu`, do not create a sentence boundary
merely because they end with a period. Regression examples include `etykawpetli.pl` and
`ethicsintheloop.eu`.

Example:

```text
Jan:
This is the first sentence.
This is the second sentence.

Anna:
This is Anna's reply.
```

## 3. Optional `segments.json`

Filename:

```text
<job_id>_segments.json
```

This is a lightweight derived format containing timestamped speaker turns, overlap
metadata, speaker identities, text, and canonical word IDs. It is not the source of
truth and can be rebuilt from `results.json`.

Its primary role is downstream interchange without exposing the full canonical processing
record: synchronized HTML/player navigation, searchable transcript indexing, corpus QA,
and selecting candidate audio regions for future speech-recognition or voice-cloning
datasets. It is not itself a voice-cloning dataset and contains no audio; exact word
timestamps remain in canonical JSON.

For corrected transcripts it is rebuilt from the exact canonical result plus the
selected revision. Revision JSON intentionally stores corrected tokens and canonical
word mappings rather than duplicating this derived segment structure.

## 4. SRT and VTT

Filenames:

```text
<job_id>_subtitles.srt
<job_id>_subtitles.vtt
```

The MVP produces plain-text subtitles without depending on colors or CSS. Speaker
coloring is not portable between target platforms and remains a Version 2 feature.

Format roles:

- canonical `results.json` is the internal timed source of truth;
- SRT is the conservative interchange format for YouTube and other platforms where
  plain captions and broad compatibility matter;
- WebVTT is the preferred native browser `<track>` format and is also useful where a
  hosting platform accepts VTT;
- a custom synchronized web transcript should be rendered as accessible HTML from
  canonical or derived segments JSON. Its sentence controls can seek the media player
  using stored start times, and CSS can color speakers without changing the portable
  caption files;
- TXT is a reading and editorial export, not a timing authority.

YouTube accepts both SRT and WebVTT, but supports only limited WebVTT formatting. A
formatting-loss notice is therefore not evidence of broken text or timestamps. Spotify
accepts timed SRT or VTT transcript uploads where the feature is available. Podcasting
2.0 permits multiple transcript links, so a publisher can expose a readable transcript
and timed captions together. Platform behavior must still be qualified against the
actual publishing account and player before release.

## 5. Default `youtube` cue preset

```toml
max_lines = 2
target_chars_per_line = 42
max_chars_per_line = 50
min_duration_ms = 1000
max_duration_ms = 7000
target_chars_per_second = 17
max_chars_per_second = 20
min_gap_ms = 80
max_merge_gap_ms = 1200
min_words_per_cue = 4
speaker_labels = "on-change"
```

All values are configurable.

The 42-character value is the preferred line-length target; 50 characters is a hard
ceiling, not the normal goal. The exporter may use the additional width when it produces
a more coherent cue or avoids an isolated one-line fragment. Neither SRT, WebVTT, nor
YouTube requires a 46-character limit.

Inside a continuous same-speaker turn that needs multiple cues, a one-line cue should
appear only as the final cue. Nonfinal cues are rebalanced toward two lines using timed
words from their continuation. A one-line cue remains valid when it is the entire speaker
turn, when it ends the turn, when surrounding silence separates it from the continuation,
or when hard duration, reading-speed, or line limits leave no valid two-line split.

## 6. Segmentation rules

Preferred split boundaries, in order:

1. sentence end;
2. natural phrase boundary;
3. comma, semicolon, or dash;
4. before a conjunction;
5. character limit as a fallback.

The algorithm SHOULD NOT:

- split words;
- leave one short word alone on the second line;
- split proper names unnecessarily;
- exceed two lines;
- combine ordinary utterances from different speakers in one cue;
- extend a cue into the next speaker's speech.

## 7. Cue timing

Base timing:

```text
start = start of the first word
end = end of the last word
```

A cue shorter than `min_duration_ms` may be extended only into available silence, by at most 300 ms, and without overlapping the next cue.

Adjacent fragments from the same speaker may be merged across up to
`max_merge_gap_ms` when the combined cue still satisfies duration, reading-speed, and
line limits. The default 1.2-second window preserves short rhetorical pauses while
avoiding isolated one- or two-word cues.

`min_words_per_cue` is a soft balancing target for fragments created while splitting one
continuous canonical segment. When a capacity boundary would strand a shorter beginning
or ending fragment, words are shifted across that boundary if both resulting cues still
meet all hard limits. A genuinely short punctuated sentence remains independent, as does
a short utterance separated from surrounding speech by silence or a speaker change.

With `speaker_labels = "on-change"`, label width is reserved only for the first cue after
the change. Continuation cues may use the full line capacity. Polish connective words
such as `i`, `że`, `z`, `bo`, `w`, `na`, and `to` should not end a cue or the first
visible line when a valid neighboring boundary exists. These are linguistic preferences
rather than hard constraints: accurate timing, speaker separation, and maximum cue
limits take priority.

Fast speech is divided into more cues. The previous cue is not extended at the expense of the next utterance.

## 8. Speaker labels

Modes:

- `on-change` — default;
- `always`;
- `never`.

`on-change` means:

- a label at the beginning when multiple speakers exist;
- a label after every speaker change;
- no repeated label in consecutive cues belonging to the same continuous turn.

An overlap exported as two lines should always include labels for both speakers.

## 9. Punctuation and sentences

TXT and subtitles use canonical transcript text. The sentence segmenter should:

- support common Polish and English abbreviations;
- use ASR punctuation;
- use a longer pause when punctuation is ambiguous;
- preserve interrupted sentences;
- not assume that a raw WhisperX segment is a sentence.

## 10. Validation

- no overlapping cues except explicit overlap handling;
- increasing timestamps;
- valid SRT numbering;
- `WEBVTT` header;
- no empty cues;
- limits are satisfied, or a warning is recorded when the physical speech rate makes compliance impossible.

## 11. Correction workflow boundary

TXT, SRT, and VTT must not be corrected independently because their text, sentence
boundaries, speaker labels, and timestamps would drift apart. The canonical result remains
immutable evidence. Planned v0.2.0 stores correction as a separate full-snapshot revision
linked to the exact canonical result hash and regenerates all derived formats from one
`EffectiveTranscript`.

Manual correction uses `EWP-REVIEW 1` plus anchored token alignment. Reviewers edit normal
text and speaker attribution; they do not maintain timestamps or a separate sentence
model. Corrected punctuation drives the existing sentence splitter. Merge/split/insert/
delete mappings inherit timing from canonical words at runtime, with warnings for
ambiguous cases. See [13 - Transcript revisions](13-transcript-revisions.md).

Revision-aware export adds `--revision none|latest|PATH`. Omitting the selector remains
raw/canonical behavior for backward compatibility.
