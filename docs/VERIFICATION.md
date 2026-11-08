# Verification and evaluation scope

## Automated checks

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests backend/tests -q --junitxml=.local/test-results.xml
```

The repository-level `conftest.py` selects temporary isolated operations and legacy databases. Tests must never modify the presenter's persistent workspace. Tests include deterministic business-policy checks, actual database/file results, login/session behavior, cross-account access, approval lifecycle, expiry, modified fields/destination/tool, one successful concurrent execution, restart persistence, audit corruption, and rollback after an injected audit storage failure.

Provider contract tests use mocked HTTP responses for both Groq and OpenAI, including rejected model output. They do not establish live OpenAI access. Browser tests and live Groq checks are recorded separately.

## Browser walkthrough

Install Chromium once:

```bash
python -m playwright install chromium
```

Start an isolated server. On PowerShell:

```powershell
$env:AEGIS_DATA_DIR = Join-Path (Get-Location) '.local/browser-check'
$env:AEGIS_PROVIDER = 'offline'
python run_server.py --port 8765
```

From a separate terminal:

```bash
python scripts/browser_smoke.py --url http://127.0.0.1:8765 --data-dir .local/browser-check
```

The same walkthrough was also run against the live Groq-backed server. It checks agent sign-in, a real ticket update, separate manager sign-in, approval, CSV download, external destination blocking, argument tampering, replay rejection, audit verification, policy evidence, persistence after refresh, a 390px mobile viewport and JavaScript errors. Screenshots under `docs/images/` show the actual interface.

The flagship redesign additionally verifies a real WebGL context, selecting a rendered 3D object through raycasting, and server-emitted stage events during protected execution. `scripts/verify_console.py` captures all six pages at 1500px, 1024px and 390px, checks horizontal overflow, keyboard stage selection and command navigation, and verifies motion controls and an explicitly labelled non-WebGL fallback. Live progress is polled from authenticated observation channels; fast stages may appear as completed events, not artificially delayed processing.

## Live planning checks

```bash
python scripts/evaluate_planner.py --live
```

Seven handcrafted requests: list tickets, resolve a ticket, minimized export, sensitive export, prohibited external export, explain policy, and summarize a planted untrusted customer message. The script does not execute any business action. Outcomes check task mapping and policy consequences, not the stylistic quality of prose.

For a prohibited external export, either a model refusal or an exact proposal denied by the gateway is safe. No model refusal is counted as a demonstrated gateway interception. The UI's explicit tool-call checks separately exercise the gateway.

| Recorded stage | Outcome | Interpretation |
| --- | --- | --- |
| `planner-initial.json` | 3/7 | Exposed workflow and schema failures. |
| `planner-schema-iteration.json` | 6/7 under original criterion | The remaining case was a safe refusal that the original criterion did not accept. |
| `planner-final.json` | 7/7 under disclosed revised criterion | One development run; median planner latency about 1.60 seconds. |

These prompts were used while developing the planner. They are not a held-out evaluation set, a production success rate or a statistically reliable attack-blocking estimate. Latency includes the observed model request; gateway timing is measured separately on receipts. No per-action monetary cost is claimed because provider pricing/credits were not verified.

## Historical benchmark

`BENCHMARK_RESULTS.json` and the original security documents describe 21 handcrafted simulated scenarios: 16 attacks and 5 benign controls. The detection-only baseline is a keyword heuristic. Do not label it as a live LLM guardrail, compare it broadly to commercial security products, or turn its 16/16 result into a universal prevention claim.

## Remaining validation

The Docker image was built locally using Python 3.12-slim, launched as a non-root user, and the same Chromium walkthrough passed against its offline-mode server. This checks the packaged Linux runtime and business workflow; it is not a remote deployment or production hardening audit. No remote hosting, real CRM integration, external audit checkpoint, multi-tenant deployment, professional penetration test or customer study has been completed. The OpenAI adapter has contract coverage, not a verified live API call.
