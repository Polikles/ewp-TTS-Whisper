# Offline-mode preparation and verification

Offline verification happens after every selected model has been downloaded explicitly and one online smoke run has succeeded.

## 1. Preserve local resources

Record the exact model IDs, revisions, and cache paths used by the successful online run. Do not clear or relocate the cache before the offline test.

## 2. Enable library offline modes

At minimum, the spike should test:

```bash
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
```

The final application will set appropriate library controls from its resolved configuration. These shell variables are for the dependency spike only.

## 3. Remove token access for the test

```bash
unset HF_TOKEN
```

An offline transcription must not require a token after all gated resources are present locally.

## 4. Block network access

Environment variables are not sufficient proof. Repeat the smoke case while outbound network access for WSL is disabled or blocked by the test environment.

Required outcome:

- ASR, alignment, and diarization load from local resources;
- no network retry or fallback occurs;
- missing resources produce a clear error rather than a download attempt;
- no token is printed or serialized.

Source: [Hugging Face Hub environment variables](https://huggingface.co/docs/huggingface_hub/en/package_reference/environment_variables).
