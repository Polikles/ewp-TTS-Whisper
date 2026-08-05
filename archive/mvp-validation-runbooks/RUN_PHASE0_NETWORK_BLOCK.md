# Run the Phase 0 network-blocked replay

Run this after [`RUN_PHASE0_REPEAT.md`](RUN_PHASE0_REPEAT.md) passes. It proves that the full integrated job succeeds when outbound networking from WSL is blocked by the Windows host, not merely discouraged by library environment variables.

The procedure uses a temporary, named Hyper-V Firewall rule scoped to WSL. Windows remains online. Run the PowerShell steps as Administrator and remove the rule at the mandatory cleanup step even if inference fails.

## 1. Restore the Linux test environment

In WSL, repeat sections 1–3 of [`RUN_PHASE0_INTEGRATED.md`](RUN_PHASE0_INTEGRATED.md). All eleven checks must pass.

Select distinct offline-replay artifacts:

```bash
export EWP_P003_INTEGRATED_JSON="$EWP_PHASE0_SPIKE/evidence/p0-03-integrated-speakers-network-blocked.json"
export EWP_P003_INTEGRATED_TEXT="$EWP_PHASE0_SPIKE/evidence/p0-03-integrated-speakers-network-blocked.txt"
export EWP_P003_INTEGRATED_REPORT="$EWP_PHASE0_SPIKE/evidence/p0-03-integrated-network-blocked-report.json"
```

Keep this WSL shell open. Do not set `HF_TOKEN`.

## 2. Inspect Hyper-V Firewall support

Open a separate **PowerShell as Administrator** window. Run:

```powershell
Get-Command Get-NetFirewallHyperVVMCreator, New-NetFirewallHyperVRule, Remove-NetFirewallHyperVRule
Get-NetFirewallHyperVVMCreator | Where-Object FriendlyName -eq 'WSL'
```

Expected: all three commands exist and the WSL entry reports VM creator ID:

```text
{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}
```

Stop if the cmdlets or WSL creator entry are absent. Do not substitute an unverified firewall mechanism.

Ensure the temporary rule does not already exist:

```powershell
Get-NetFirewallHyperVRule -Name 'EWP-Phase0-Block-WSL-Outbound' -ErrorAction SilentlyContinue
```

Expected: no output. If a rule appears, stop and inspect it rather than overwriting it.

## 3. Create the temporary WSL outbound block

In elevated PowerShell:

```powershell
New-NetFirewallHyperVRule `
    -Name 'EWP-Phase0-Block-WSL-Outbound' `
    -DisplayName 'EWP Phase 0 Block WSL Outbound' `
    -Direction Outbound `
    -VMCreatorId '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' `
    -Protocol Any `
    -Action Block
```

Keep the elevated PowerShell window open for cleanup.

## 4. Prove that WSL outbound HTTPS is blocked

Back in WSL, run:

```bash
if curl --silent --show-error --fail --max-time 8 \
    https://huggingface.co/robots.txt >/dev/null; then
    echo "NETWORK BLOCK: FAIL"
else
    echo "NETWORK BLOCK: PASS"
fi
```

Do not continue unless the result is `NETWORK BLOCK: PASS`. DNS resolution alone does not count; the HTTPS request must fail.

Optionally confirm that the Windows host itself remains online from PowerShell:

```powershell
Test-NetConnection huggingface.co -Port 443
```

## 5. Run the complete blocked replay

While the firewall rule remains active, run section 4 of [`RUN_PHASE0_INTEGRATED.md`](RUN_PHASE0_INTEGRATED.md) unchanged.

Expected: the complete report prints without download attempts, network retries, token requests, or model-loading failures.

Regardless of success or failure, proceed immediately to cleanup before investigating anything else.

## 6. Mandatory firewall cleanup

In the elevated PowerShell window:

```powershell
Remove-NetFirewallHyperVRule -Name 'EWP-Phase0-Block-WSL-Outbound'
Get-NetFirewallHyperVRule -Name 'EWP-Phase0-Block-WSL-Outbound' -ErrorAction SilentlyContinue
```

Expected: the remove command succeeds and the verification command prints nothing.

Back in WSL, prove connectivity was restored:

```bash
curl --silent --show-error --fail --max-time 8 \
    https://huggingface.co/robots.txt >/dev/null \
    && echo "WSL network restored: PASS"
```

If restoration fails, confirm the named rule is absent before changing any other firewall setting.

## 7. Verify and compare offline artifacts

```bash
test -s "$EWP_P003_INTEGRATED_JSON" && echo "blocked-run JSON: present"
test -s "$EWP_P003_INTEGRATED_TEXT" && echo "blocked-run text: present"
test -s "$EWP_P003_INTEGRATED_REPORT" && echo "blocked-run report: present"
sha256sum "$EWP_P003_INTEGRATED_JSON" "$EWP_P003_INTEGRATED_TEXT"
cat "$EWP_P003_INTEGRATED_REPORT"
```

Accepted deterministic hashes from runs 1 and 2:

```text
JSON=03776be4ca8d26afb9813c2713448557adc108295c27043e5ea232897d6203f7
text=c4ca51d75c7416db6a75d1e8d61b2433c1fcbcf0162c6bf48014342ced98e6c1
```

Different hashes require structured comparison but do not justify reconnecting or downloading models during inference.

## Stop point

Send:

```text
Hyper-V Firewall support: PASS / FAIL
network block proof: PASS / FAIL
blocked integrated run: PASS / FAIL
complete sanitized report JSON:
blocked-run JSON and text SHA-256 values:
hashes match accepted runs: YES / NO
temporary firewall rule removed: PASS / FAIL
WSL network restored: PASS / FAIL
warnings or errors:
```

Do not send transcripts, audio, tokens, model files, cache paths, full firewall policy dumps, or environment dumps.

## Primary sources

- [Microsoft Hyper-V Firewall for WSL](https://learn.microsoft.com/windows/security/operating-system-security/network-security/windows-firewall/hyper-v-firewall)
- [Microsoft WSL networking](https://learn.microsoft.com/windows/wsl/networking)
- [Hugging Face Hub offline environment variable](https://huggingface.co/docs/huggingface_hub/en/package_reference/environment_variables)
