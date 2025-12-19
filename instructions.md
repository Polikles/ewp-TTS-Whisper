
[draft of the instructions for the usage of the script]

It is important to keep in mind that low audio quality may influence accuracy of timestamps. The same goes for recordings of varying quality for different speakers, e.g. if one speaker was recorded locally, and the other via an online call

Files for a single episode should not be longer than 1 hour. The longer the file, the higher chance of memory or processing issues.

Script was build and tested on workstation with RTX 3090 (24GB VRAM), 14700k, 96GB RAM 6600MT

script is designed to handle already preprocessed and edited files.

Designed workflow for podcast with transcript is as follows:
1. record audio (each speaker on their own track)
2. edit audio recordings to eliminate noise, gasps, mistakes, repetitions, etc. Don't forget to normalize volume. Multi-track edit is recommended
3. export edited audio as .wav mono files - one file per track/speaker
4. keep naming conventions [episode]_[speaker].wav e.g. S0E01_John.wav
5. keep episodes separated - one (sub)catalog for one episode
6. Use the script - it will scan for the catalog for all .wav files that have no matching .txt or .srt transcript
7. The script will generate per-word and per-sentence timestamps for each speaker, as well as combined transcript for all speakers. The expected structure is: [timestamp] [name] [transcript]
8. The last step is manual validation and fixes, especially for names and moments where two or more people spoke at the same time (the order of speakers may get mixed in the transcript in such cases)

