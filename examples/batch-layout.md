# Example Directory Layouts

## Separate episodes

```text
season01/
  S01E01.wav
  S01E02.mp3
  S01E03.mp4
```

## Speaker groups

```text
season01/
  S01E04-jan.wav
  S01E04-anna.wav
  S01E05_mono_normalized-jan.wav
  S01E05_mono_normalized-marta.wav
```

Default outputs:

```text
season01/
  output-ewp-transcripts/
    S01E01_results.json
    S01E01_transcript.txt
    S01E01_subtitles.srt
    S01E01_subtitles.vtt
    S01E04_results.json
    S01E04_transcript.txt
    S01E04_subtitles.srt
    S01E04_subtitles.vtt
```

## Subdirectories

```text
podcast/
  season01/
  season02/
```

Running against `podcast/` without `--recursive` ignores files inside `season01` and `season02`.
