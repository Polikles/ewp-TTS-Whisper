# Run v0.3 local-LLM correction benchmark

Use this operator runbook to generate correction candidates through LM Studio. It does
not send audio: it sends transcript text from canonical `*_results.json` files.

The private corpus, generated candidates, resume state, and logs must remain outside Git.
Do not run all 24 episodes until the three-case pilot has been reviewed.

## 0. Preconditions

Run from the repository checkout:

```bash
cd "$HOME/transkrypcje/ewp-transcripts"
git pull --ff-only
uv sync --locked
make check
```

In LM Studio, load exactly `qwen2.5-14b-instruct`. For the first baseline, use the
Q8_0 model with 32K context and temperature zero. Keep the LM Studio developer log open.

Set paths for this machine. `EWP_CORPUS_ROOT` must be the private benchmark directory
that contains `1 canonical outputs` and `3 apply`. The endpoint may be loopback, LAN, VPN,
or a Tailscale-like address; non-loopback endpoints require the explicit CLI opt-in below.
These variables are interpreted by Bash, not by `transcriber`, so use a WSL path such as
`/mnt/c/Users/name/...`; a `C:\Users\...` value will not work in `test`, `find`, or loops.

```bash
export EWP_CORPUS_ROOT="/absolute/path/to/private benchmark"
export EWP_LM_ENDPOINT="http://100.99.201.120:1234/v1"
export EWP_LM_MODEL="qwen2.5-14b-instruct"
export EWP_LM_RUN="$(mktemp -d "$HOME/ewp-qwen14b-q8-XXXXXXXX")"
set -o pipefail

mkdir -p "$EWP_LM_RUN/revisions" "$EWP_LM_RUN/resume" "$EWP_LM_RUN/logs"
chmod 700 "$EWP_LM_RUN" "$EWP_LM_RUN/revisions" "$EWP_LM_RUN/resume" "$EWP_LM_RUN/logs"
printf 'run=%s\n' "$EWP_LM_RUN"
```

Verify the paths and model identity without printing transcript contents:

```bash
test -d "$EWP_CORPUS_ROOT/1 canonical outputs" && echo "canonical corpus: present"
test -d "$EWP_CORPUS_ROOT/3 apply" && echo "manual gold: present"

curl -fsS "$EWP_LM_ENDPOINT/models" | uv run --locked python -c \
  'import json,sys; print("\n".join(item["id"] for item in json.load(sys.stdin)["data"]))'
```

The exact value of `EWP_LM_MODEL` must appear. Stop if it does not.

## 1. Freeze input evidence

Record hashes and repository state. This evidence contains paths and hashes, not transcript
text:

```bash
git log -1 --oneline | tee "$EWP_LM_RUN/logs/repository.txt"
git status --short | tee -a "$EWP_LM_RUN/logs/repository.txt"

find "$EWP_CORPUS_ROOT/1 canonical outputs" -maxdepth 1 -type f \
  -name '*_results*.json' -print0 | sort -z | xargs -0 sha256sum \
  > "$EWP_LM_RUN/logs/canonical-sha256.txt"

find "$EWP_CORPUS_ROOT/3 apply" -maxdepth 1 -type f \
  -name '*_revision_*.json' ! -name '*_audit.json' -print0 | sort -z | xargs -0 sha256sum \
  > "$EWP_LM_RUN/logs/manual-gold-sha256.txt"

wc -l "$EWP_LM_RUN/logs/canonical-sha256.txt" \
  "$EWP_LM_RUN/logs/manual-gold-sha256.txt"
```

Expected canonical count for the current private corpus is 24. More than 24 manual
revisions is valid because earlier accepted revisions are retained as history; the latest
compatible revision is gold.

## 2. Three-case pilot

The initial pilot covers the shortest result (`s0e00`), a medium result (`S0E06`), and the
longest result (`S2E9`). Run each case first with `--preview`. A successful preview writes
validated private resume entries but does not publish a revision.

```bash
for result in \
  "$EWP_CORPUS_ROOT/1 canonical outputs/s0e00_results.json" \
  "$EWP_CORPUS_ROOT/1 canonical outputs/S0E06_results.json" \
  "$EWP_CORPUS_ROOT/1 canonical outputs/S2E9_results.json"
do
  name="$(basename "$result" .json)"
  /usr/bin/time -v -o "$EWP_LM_RUN/logs/${name}.preview.time.txt" \
    uv run --locked transcriber revise correct "$result" \
      --model "$EWP_LM_MODEL" \
      --endpoint "$EWP_LM_ENDPOINT" \
      --allow-remote-endpoint \
      --consent once \
      --preview \
      --resume-dir "$EWP_LM_RUN/resume" \
    2>&1 | tee "$EWP_LM_RUN/logs/${name}.preview.txt" || break
done
```

Both privacy warnings are expected for the configured non-loopback endpoint. Any error,
retry exhaustion, unexpected model identity, or malformed response stops the pilot. Do not
weaken validation or edit resume JSON.

LM Studio's developer log displays full API request and response payloads, including
private transcript text. Treat that log as private corpus data. Do not enable or share it
on a shared machine, and clear it according to the local retention policy after collecting
only the non-content evidence required by this runbook.

After all previews pass, publish the three immutable candidates. These commands must reuse
the validated resume entries, so LM Studio should log no new completion requests:

```bash
for result in \
  "$EWP_CORPUS_ROOT/1 canonical outputs/s0e00_results.json" \
  "$EWP_CORPUS_ROOT/1 canonical outputs/S0E06_results.json" \
  "$EWP_CORPUS_ROOT/1 canonical outputs/S2E9_results.json"
do
  name="$(basename "$result" .json)"
  uv run --locked transcriber revise correct "$result" \
    --model "$EWP_LM_MODEL" \
    --endpoint "$EWP_LM_ENDPOINT" \
    --allow-remote-endpoint \
    --consent once \
    --output-dir "$EWP_LM_RUN/revisions" \
    --resume-dir "$EWP_LM_RUN/resume" \
    2>&1 | tee "$EWP_LM_RUN/logs/${name}.apply.txt" || break
done
```

Verify artifacts without displaying private text:

```bash
find "$EWP_LM_RUN/resume" "$EWP_LM_RUN/revisions" -maxdepth 1 -type f \
  -printf '%m %p\n' | sort
sha256sum "$EWP_LM_RUN/revisions"/*_revision_001.json \
  > "$EWP_LM_RUN/logs/candidate-sha256.txt"
cat "$EWP_LM_RUN/logs/candidate-sha256.txt"
```

Resume entries, revisions, and lock files must be mode `600`. Send the command summaries,
timing files, candidate hashes, and whether apply caused any new LM Studio request. Do not
send revision JSON or transcript text through an unapproved channel.

## 3. Pilot review gate

Before the full run, compare each candidate with the latest compatible manual revision.
The automated benchmark report will measure lexical errors, but a human sample must also
check that the model:

- fixes obvious ASR errors and proper-name spelling;
- preserves wording, repetitions, fillers, self-corrections, and speaking mistakes;
- does not polish style, paraphrase, summarize, or invent text;
- preserves speaker attribution unless the source provides clear evidence for a change;
- supplies an auditable proposed-change list.

Record observed harmful changes separately. Do not manually repair candidate revisions;
they are immutable model outputs and benchmark evidence.

## 4. Full-corpus candidate generation

Run this section only after the pilot is accepted. Use a new run directory for every model,
quantization, prompt, or parameter change. Never mix candidates from different configurations.

The current CLI processes one canonical result at a time. The loop is deliberately
sequential, isolates logs per episode, and continues only while every preceding case passes:

```bash
while IFS= read -r -d '' result
do
  name="$(basename "$result" .json)"
  /usr/bin/time -v -o "$EWP_LM_RUN/logs/${name}.time.txt" \
    uv run --locked transcriber revise correct "$result" \
      --model "$EWP_LM_MODEL" \
      --endpoint "$EWP_LM_ENDPOINT" \
      --allow-remote-endpoint \
      --consent once \
      --output-dir "$EWP_LM_RUN/revisions" \
      --resume-dir "$EWP_LM_RUN/resume" \
    2>&1 | tee "$EWP_LM_RUN/logs/${name}.txt" || break
done < <(
  find "$EWP_CORPUS_ROOT/1 canonical outputs" -maxdepth 1 -type f \
    -name '*_results*.json' -print0 | sort -z
)
```

The three pilot cases should reuse their resume state and existing identical revisions.
Check LM Studio logs for unexpected repeat calls. Then verify counts and permissions:

```bash
find "$EWP_LM_RUN/revisions" -maxdepth 1 -type f \
  -name '*_revision_*.json' | wc -l

find "$EWP_LM_RUN/resume" "$EWP_LM_RUN/revisions" -type f \
  ! -perm 600 -print

sha256sum "$EWP_LM_RUN/revisions"/*_revision_*.json \
  > "$EWP_LM_RUN/logs/candidate-sha256.txt"
```

Expected revision count is 24 and the permission check should print nothing.

## 5. Scoring status

Candidate generation is runnable now. The strict correction benchmark core already checks
canonical hashes, revision compatibility, latest-gold lineage, WER/CER, word-error reduction,
and excess errors. The operator-facing manifest builder and report command are not yet
shipped, so do not hand-write a 24-case manifest or claim final benchmark scores.

After candidate generation, preserve the complete run directory. The next implementation
slice will build and audit its exact-hash manifest, generate the non-secret aggregate report,
and add the manual harmful-change review table. Local models are benchmarked separately;
OpenRouter remains blocked until explicit paid-run authorization and a later cloud runbook.
