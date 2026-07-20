Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Relates-To: .10x/tickets/2026-07-20-measure-crow-plus-bounded-runtime.md, .10x/specs/crow-plus-resource-verification-checkpoint.md, .10x/evidence/2026-07-20-crow-plus-phase-2-immutable-cache-bootstrap.md

# Crow-Plus Phase 3 Bounded Runtime Preflight Failure

## What was observed

The separately approved phase 3 operation stopped at its first failing runtime precondition. One recorded `vm_stat` snapshot computed 3,059,908,608 available bytes from `(free + inactive + speculative) * page_size`, below the required 8,589,934,592-byte start floor by 5,530,025,984 bytes. No child measurement process was started.

Raw normalized artifact:

- `.10x/evidence/.storage/2026-07-20-crow-plus-phase3-preflight-failure.json` (artifact SHA-256 `dc956f581f2d381ab0a265d4473bfdc3963c18da78457bbb6b709ee2d62c686c`).

## Approval provenance

Before preflight and before any model or Hub import, construction, load, tokenization, inference, watchdog/monitor execution, or output observation, the owning ticket was changed from `blocked` to `active` and appended with the user's separate explicit approval of the exact phase 3 contract. The approval is phase 3 only. It grants no phase 4 implementation/source-change or phase 5 indexing/write authority.

## Procedure and command

The repository-mandated status and worktree inspection first confirmed dedicated branch `work/measure-crow-runtime`. The preflight then used this secret-free shell procedure:

```sh
set -euo pipefail
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  HF_HUB_DISABLE_TELEMETRY=1 DO_NOT_TRACK=1 \
  HF_HUB_DISABLE_UPDATE_CHECK=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1
unset HF_TOKEN HUGGING_FACE_HUB_TOKEN || true
command -v python3
which -a python3 python
for p in .venv/bin/python ../turbo-search/.venv/bin/python \
  /Users/crlough/Code/personal/turbo-search/.venv/bin/python; do
  if [ -x "$p" ]; then echo "$p"; fi
done
/usr/sbin/sysctl -n hw.model
/usr/sbin/sysctl -n machdep.cpu.brand_string
/usr/sbin/sysctl -n hw.memsize
/usr/bin/sw_vers -productVersion
/usr/bin/sw_vers -buildVersion
/usr/bin/vm_stat
git status --short --branch
```

The environment controls were exported before the Python environment was located and before any possible model/Hub library import. Token variables were removed without reading their values. The procedure did not import a model, Hub, Turbopuffer, or other project/runtime library.

## Raw preflight observations

Host identity matched the exact checkpoint:

- hardware model: `Mac14,9`;
- processor: `Apple M2 Pro`;
- unified memory: 17,179,869,184 bytes;
- macOS: 26.5.1 (`25F80`).

The raw `vm_stat` snapshot is preserved verbatim in the JSON artifact. The values used by the fixed formula were:

| Value | Observation |
|---|---:|
| Page size | 16,384 bytes |
| Pages free | 3,720 |
| Pages inactive | 178,757 |
| Pages speculative | 4,285 |
| Computed available | 3,059,908,608 bytes |
| Required start floor | 8,589,934,592 bytes |
| Shortfall | 5,530,025,984 bytes |

Calculation: `(3,720 + 178,757 + 4,285) * 16,384 = 3,059,908,608`.

## Immediate-stop result

The available-memory start floor failed. In accordance with the approved immediate-stop contract, execution did not retry, raise a bound, change device or precision, fall back to CPU, alter a batch/input/dependency, or proceed to the measurement child.

The following therefore did not occur after the failure:

- immutable cache re-hash/manifest verification or locked dependency version verification;
- model or Hub library import, tokenization, construction, load, or float16 cast;
- watchdog or in-process MPS monitoring;
- query or document inference and output observation.

No exit signal exists because no child process started. The phase 3 runtime and qualification results are both **fail / not measured** at the available-memory preflight.

## Safety and scope observation

No dependency install, update, or resolution occurred. No source, test, configuration, or lockfile was changed. No credential was read. No model/service network attempt, Turbopuffer or other live-service access, namespace/card/catalog/default/state operation, staging, indexing, delete, or write occurred. No phase 4 implementation/source work was authorized or performed.

## What this supports or challenges

This supports that separate approval was recorded before operation, the exact host identity matched, mandatory environment controls preceded any model-library import, and the procedure stopped at the fixed memory floor without workaround. It challenges phase 3 eligibility on this host snapshot: the operation could not start and produced no model runtime or output measurement.

## Limits and residual risk

The shell command did not capture a machine timestamp alongside the raw `vm_stat` text. The dated artifact and Git history establish when the record was preserved, not an independently machine-stamped acquisition time for the snapshot. The no-import/no-child/no-network/no-live-operation statements are bounded by the recorded procedure, raw artifact, tracked diff, and contemporaneous operator attestation; repository evidence cannot retroactively prove the absence of every unlogged external action.

Because the mandatory floor failed, cache/dependency identity was not reverified in phase 3 and none of the model, tokenizer, MPS, output, sampling, hard-bound, or qualification observations exist. Independent review passed this as accurate failed-attempt evidence, not as a successful measurement. Phase 3 acceptance remains unfulfilled and the owning ticket is blocked. A later attempt requires a fresh revised checkpoint and new separate approval; this evidence authorizes neither retry nor phase 4.
