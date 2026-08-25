# Obtain a read-only Hugging Face token for pyannote

EWP Transcriber downloads public ASR and alignment models without an account. Speaker
diarization uses the gated `pyannote/speaker-diarization-community-1` repository, so its
terms must be accepted in a browser and the installer must temporarily receive a Hugging
Face User Access Token. Normal transcription is offline and does not need the token.

Hugging Face changes its interface occasionally. Button wording may differ slightly, but
the security boundary is stable: accept access as the same individual account, create a
read-only token, enter it only at the installer's hidden prompt, and remove or revoke it
when it is no longer needed.

## 1. Create or sign in to a Hugging Face account

Open <https://huggingface.co/> in a browser, create an individual account if necessary,
verify its email address, and sign in.

> Screenshot placeholder HF-01: signed-in Hugging Face home page and account menu.

## 2. Accept the pyannote access conditions

While signed in, open:

<https://huggingface.co/pyannote/speaker-diarization-community-1>

Read the model card, license, contact-information notice, and access conditions. If you
agree, complete any requested fields and select the button that agrees to and submits the
access request. Access is attached to the individual account, not an organization. Do not
continue until the page permits access to the repository files; automatic approval is
normally immediate, but Hugging Face also supports requests that remain pending.

Only this `community-1` repository is required by the current pinned configuration. Older
instructions for other pyannote pipelines or separate segmentation repositories do not
apply unless the configured model changes.

> Screenshot placeholder HF-02: `community-1` conditions before acceptance.
>
> Screenshot placeholder HF-03: repository file access after acceptance.

## 3. Create a read-only token

Open <https://huggingface.co/settings/tokens> and choose **New token**. Give it a distinct
name such as `ewp-transcriber-model-download` and choose the **Read** role. Write access is
not required: the application only downloads immutable model files and never creates or
updates a Hugging Face repository.

Hugging Face also offers fine-grained tokens. An experienced operator may instead create
one limited to read access for the gated pyannote repository, provided it can complete the
selected download. The ordinary **Read** role is the documented general-user path.

Create the token and copy it when displayed. Treat it like a password:

- do not put it directly in a shell command, script, configuration file, screenshot, issue,
  chat message, or shared log;
- do not create a write token;
- do not send the token with test results;
- revoke and replace it immediately if it may have been exposed.

> Screenshot placeholder HF-04: New token form with a distinct name and Read selected.
>
> Screenshot placeholder HF-05: one-time token display, with the token itself obscured.

## 4. Enter the token during model setup

From the repository in WSL, run:

```bash
./scripts/setup-models.sh
```

Confirm the planned downloads. At this prompt:

```text
Hugging Face read token:
```

paste the copied token and press Enter. Nothing appears while typing or pasting; that is
intentional. The script exposes the token only to the gated download process, never passes
it as a command argument, and removes its temporary environment value before diagnostics.

Do not use `export HF_TOKEN=...` for the guided path. If an advanced operator already has
`HF_TOKEN` set, the script uses that process environment without printing it.

> Screenshot placeholder HF-06: terminal at the hidden token prompt, with no token visible.

## 5. Verify and revoke when appropriate

Successful setup ends with `Pinned model preparation completed` and a passing
`transcriber doctor`. Verify that the interactive shell does not retain a token:

```bash
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
```

The downloaded immutable snapshot works offline after setup. The token may therefore be
revoked from <https://huggingface.co/settings/tokens> if it is not needed for reinstalling
or updating model snapshots. Revoking it does not delete local model files.

> Screenshot placeholder HF-07: token management action for revoke/delete.

Official references:

- <https://huggingface.co/pyannote/speaker-diarization-community-1>
- <https://huggingface.co/docs/hub/en/models-gated>
- <https://huggingface.co/docs/hub/en/security-tokens>
