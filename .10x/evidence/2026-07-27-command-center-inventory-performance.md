Status: recorded
Created: 2026-07-27
Updated: 2026-07-27
Relates-To: .10x/tickets/2026-07-27-validate-command-center-inventory-performance.md, .10x/tickets/2026-07-27-command-center-inventory-performance-plan.md, .10x/specs/command-center-summary-inventory-performance.md, .10x/specs/command-center-managed-plan-cache-invalidation.md, .10x/specs/command-center-blocking-route-threading.md

# Command Center Inventory Performance Aggregate Validation

## What was observed

The final integrated implementation from branch `work/command-center-inventory-performance` was validated against base `01f2d19432c4bc77e9d6bd7ab8a657b5f4583521`. The exact committed default benchmark driver ran from clean implementation commit `607bae7ec55766acf46eb1c3cd42a0162e4236b3` with no tracked changes. Final integration commit `4cb793bf` was then repaired under the same open validation ticket after two independent reviews found missing descriptor-capability gating, completion-based cache expiry, and insufficiently reproducible release evidence. The repair commit is necessarily identified by the execution handoff because a commit cannot contain its own hash.

On the same host and exact fixture as the baseline, warm summary p50 fell from 671.639–688.501 ms to 0.018–0.141 ms. Dashboard, Plans, and Namespaces exceeded the required 5× observational improvement by 4,844.9×, 38,250.1×, and 6,532.5× respectively. Process-cold summaries still rebuild the snapshot and measured 365.065–371.328 ms. Selected-plan routes retained complete per-call verification and remain linear in the selected 100,100-row delta; their warm p50 was 2,899.825–2,937.950 ms, about 12.0–13.2% below baseline but intentionally not cached or claimed subsecond.

The final structural sequence `Dashboard → Namespaces → Plans` performed one plan scan, one state scan, five read-only state connections, zero applied-row object constructions, no legacy descendant traversal, and zero delta payload opens. The default 1.0-second locked process-local summary cache is nonpersistent and non-authorizing; successful managed publication invalidates it in-process, while external changes may remain invisible until TTL expiry. Direct misses refresh once. Selected detail/chunk/stale access continues complete identity/schema/logical/source/baseline/payload verification on every request.

## Exact host and fixture

Host:

- OS: macOS 26.5.1 (`macOS-26.5.1-arm64-arm-64bit-Mach-O`)
- Architecture: arm64
- Logical CPUs: 10
- Python: 3.13.0
- DuckDB: 1.5.4

Fixture:

- 1,000 summary-qualified schema-v2 plans, each exactly 131,072 bytes.
- 999 fixed delta sentinels plus one valid selected delta with 100 changed upserts and 100,000 stale rows.
- One schema-v1 boundary with 32 levels, 100 bucket directories, and 5,000 page files.
- One 100,003-row applied state and four 257-row states: 101,031 total state rows across five databases.
- One process-cold call and five same-service warm calls per surface, each in its own fresh worker; OS filesystem caches were not dropped.
- Wall time used `time.perf_counter`; warm p50 is the median of five; peak RSS is process-wide `ru_maxrss` normalized to bytes.
- The fixture lived under a system temporary directory and was removed automatically. No raw benchmark output was retained in the repository.

## Before/after measurements

### Summary inventory

| Surface | Baseline cold (ms) | Baseline warm ×5 (ms) | Baseline p50 (ms) / RSS (bytes) | Final cold (ms) | Final warm ×5 (ms) | Final p50 (ms) / RSS (bytes) | Warm speedup |
|---|---:|---|---:|---:|---|---:|---:|
| Dashboard | 704.402 | 686.041, 694.687, 677.469, 676.771, 678.291 | 678.291 / 264,306,688 | 371.328 | 0.144, 0.131, 0.126, 0.192, 0.140 | 0.140 / 75,366,400 | 4,844.9× |
| Plans | 696.778 | 692.411, 688.501, 690.231, 676.684, 685.421 | 688.501 / 295,845,888 | 365.065 | 0.035, 0.018, 0.016, 0.020, 0.015 | 0.018 / 74,809,344 | 38,250.1× |
| Namespaces | 698.993 | 690.446, 677.361, 673.250, 685.911, 709.920 | 685.911 / 296,517,632 | 366.690 | 0.114, 0.102, 0.099, 0.106, 0.105 | 0.105 / 74,629,120 | 6,532.5× |
| Namespace detail | 693.740 | 674.002, 668.422, 671.639, 668.571, 677.227 | 671.639 / 253,181,952 | 365.771 | 0.154, 0.143, 0.140, 0.141, 0.140 | 0.141 / 74,842,112 | 4,763.4× |

### Selected full verification

These calls are deliberately separate from summary performance. Each call completely verifies the selected delta before returning a bounded result window.

| Surface | Baseline cold (ms) | Baseline warm ×5 (ms) | Baseline p50 (ms) / RSS (bytes) | Final cold (ms) | Final warm ×5 (ms) | Final p50 (ms) / RSS (bytes) | Warm change |
|---|---:|---|---:|---:|---|---:|---:|
| Plan detail | 3,347.904 | 3,329.753, 3,338.324, 3,323.781, 3,317.235, 3,321.163 | 3,323.781 / 304,627,712 | 2,936.719 | 2,883.040, 2,899.899, 2,899.825, 2,907.812, 2,899.063 | 2,899.825 / 196,427,776 | 12.8% lower |
| Changed page 1 (`offset=0`, `limit=50`) | 4,085.209 | 3,338.170, 3,355.035, 3,331.466, 3,350.765, 3,305.817 | 3,338.170 / 358,858,752 | 3,582.395 | 2,967.214, 2,947.569, 2,909.537, 2,937.950, 2,883.611 | 2,937.950 / 259,588,096 | 12.0% lower |
| Changed later (`offset=50`, `limit=50`) | 4,067.524 | 3,335.544, 3,368.601, 3,320.289, 3,334.753, 3,348.582 | 3,335.544 / 355,991,552 | 3,610.365 | 2,966.664, 2,926.716, 2,929.290, 2,936.512, 2,957.944 | 2,936.512 / 261,423,104 | 12.0% lower |
| Near-end stale (`offset=99,950`, `limit=50`) | 4,165.951 | 3,405.128, 3,385.210, 3,363.135, 3,374.436, 3,374.122 | 3,374.436 / 359,104,512 | 3,682.128 | 2,929.302, 2,961.312, 2,913.244, 2,943.179, 2,911.750 | 2,929.302 / 259,735,552 | 13.2% lower |

## Structural result

```json
{"applied_row_objects":0,"artifact_walk_directories":1002,"delta_builtin_opens":0,"delta_duckdb_connections":0,"delta_io_opens":0,"delta_os_opens":0,"legacy_descendants_traversed":false,"plan_scans":1,"state_connections":5,"state_scans":1,"state_walk_directories":11,"summary_delta_payload_open_count":0,"summary_delta_payload_opened":false,"summary_sequence":["dashboard","namespaces","plans"]}
```

## Required commands and exact results

1. `uv run python scripts/benchmark_command_center_inventory.py`
   - Passed from clean commit `607bae7e`. All eight post-timing result validators passed; fixture and timing values are recorded above. The output's provider/source/plan/apply zero values are a hardcoded side-effect inventory, not runtime counters. Absence of those effects is attested from the fixture-only procedure and external-side-effect inventory below; structural scan/connection/delta-open values are instrumented.
2. `git diff --check && uv sync --locked && uv lock --check`
   - Passed before validation. Core sync resolved 157 lock entries and removed optional FastAPI/Starlette/Uvicorn.
3. `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate_ranking_contract.py`
   - Passed in 0.08s: 13 datasets/folds, 90 composite identities, 369 judgments, dataset bundle SHA-256 `5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9`.
4. `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/c6_syntax_forecast.py validate`
   - Passed in 0.23s at forecast SHA-256 `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`; tokenizer readiness remained false at the established checkpoint.
5. `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q`
   - The first run executed 791 tests in 92.902s and failed one release/public-surface test because latest `main` had removed `images/buoy.svg` while the active brand/package contract, `pyproject.toml`, CI archive inventory, and test still required it. The bounded repair restored `images/buoy.svg` byte-for-byte from `src/buoy_search/command_center_static/buoy.svg`; both SHA-256 values are `f791c77f25e202a0556d2688ec9180e7d78c983f220f84b097c1fdc8894edcef`.
   - The complete rerun passed all 791 tests in 83.887s with 35 skips. Expected safe cleanup, hostile-host argparse, fake-provider, and upstream lxml diagnostics were non-failing.
6. `uv sync --locked --extra ui`
   - Passed; installed locked FastAPI 0.139.2, Starlette 1.3.1, and Uvicorn 0.51.0.
7. `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests/test_applied_state.py tests/test_command_center_local.py tests/test_command_center_api.py tests/test_command_center_jobs.py tests/test_planning_service.py tests/test_release_automation.py -q`
   - Passed all 169 focused applied-state/local/API/jobs/planning/release tests in 19.144s. The known Starlette TestClient/httpx deprecation warning was non-failing.
8. `cd web && npm ci`
   - Passed under available Node 24.6.0/npm 11.5.1: 214 packages installed, 215 audited. The established React Router advisory reported two high findings; its applicability/no-action disposition remains owned by `.10x/evidence/2026-07-24-react-router-advisory-no-action.md`.
9. `cd web && npm test -- --run`
   - Passed one Vitest file and all 37 tests in 2.11s.
10. `cd web && npm run build`
    - Passed TypeScript and Vite 7.3.6: 42 modules; `index.html` 0.63 kB, CSS 10.66 kB, JavaScript 278.77 kB.
11. Appendix A HTML/static synchronization command
    - Passed. Build output was byte-synchronized. References `/buoy.svg`, `/assets/index-D34KCjuB.js`, and `/assets/index-Amu9gKyT.css` all resolve. SHA-256: index `c4129e00430f8378c89ae550bf72c860bd170d64158d1b78e13dd472a9855833`; JavaScript `734e5bb9acbeb0cc98e9da4e53c6fba81b15be1df34b59bbdfc98d3bbd63a74c`; CSS `fd57c4f2b1319313451571398931ad5b20c8707cdc3f931cd88d993d3c1bd815`; SVG `f791c77f25e202a0556d2688ec9180e7d78c983f220f84b097c1fdc8894edcef`.
12. `rm -rf dist && uv build --out-dir dist`
    - Repair-time run passed; built `buoy_search-0.4.1.dev113+g4cb793bf3.d20260728-py3-none-any.whl` and matching sdist. The earlier clean implementation archive was `dev112+g607bae7ec`.
13. Appendix B standard-library archive inventory command
    - Passed. Wheel: 69 entries, including index, Buoy SVG, and exactly one hashed JavaScript/CSS asset. Sdist: 159 entries, including docs, benchmark driver, restored public SVG, and intended frontend source/build inputs. Both archives contained zero `node_modules` entries.
14. Appendix C isolated installed-wheel command
    - Passed. Package/static roots resolved below `/private/tmp/buoy-command-center-wheel-target.zOsC36`; `/api/v1/health`, `/api/v1/dashboard`, `/api/v1/plans`, `/api/v1/namespaces`, and `/` each returned HTTP 200. Empty summary counts/lists were exact, packaged HTML contained `Buoy`, and the trap removed the target.
15. Appendix D Safari WebDriver probe
    - `safaridriver --version` returned `Included with Safari 26.5 (21624.2.5.11.4)` and `/status` returned `ready=true`. Session creation returned `session not created`: `You must enable 'Allow remote automation' in the Developer section of Safari Settings to control Safari via WebDriver.` The setting was not mutated; no browser product assertion was accepted.
16. `rm -rf dist web/node_modules && uv sync --locked && uv lock --check`
    - Passed. Optional UI packages were removed and the default locked core environment was restored.
17. Appendix E isolated core-import command
    - Passed. Imports resolved to this worktree's `src/buoy_search/__init__.py` and `src/buoy_search/cli.py`; FastAPI/Uvicorn specs and all enumerated optional/API/job/provider/model modules were absent.
18. Appendix F final artifact-inventory command
    - Passed. Exactly 876 tracked paths were inspected; staged files, generated directories, and tracked private/generated artifacts were each empty. `dist` and `web/node_modules` were absent.

## Post-review repair validation

- Focused gate: `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_command_center_inventory_benchmark tests.test_applied_state tests.test_command_center_local tests.test_command_center_api -q` passed 87 tests in 7.976s with the known non-failing Starlette warning.
- The first repair-time full discovery ran 795 tests in 86.688s and found one benchmark-harness compatibility failure: its temporary `os.open` tracer did not mirror `os.supports_dir_fd`, so the new capability gate isolated the fixture states. The bounded harness repair mirrors/restores only that advertised capability during tracing. The complete rerun `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q` passed all 795 tests in 86.292s with 36 core-environment skips.
- The exact benchmark command was rerun after repair with output redirected to `/tmp/command-center-repair-benchmark.json`, asserted, summarized, and removed. Warm p50: Dashboard 0.144 ms, Plans 0.021 ms, Namespaces 0.116 ms, namespace detail 0.151 ms; selected complete verification 3,051.480–3,077.451 ms. Structural results remained exactly the JSON above. These repair observations do not replace the preserved clean-commit benchmark table.
- Ranking/C6 validators passed unchanged at dataset SHA-256 `5a79f58aaca87a2d4f7cbec68fdcfbbf041131821587f8aba74a86daca99d9` and forecast SHA-256 `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`.
- `cd web && npm ci && npm test -- --run && npm run build` passed: 214 packages installed, 37 tests passed, and the same 42-module synchronized build was produced. The separately owned advisory remained unchanged.
- A preliminary Safari helper attempt using `-p 0` failed its local port-discovery assertion before any session request. Appendix D is the corrected probe using an OS-selected then explicitly supplied port; it reached the driver and returned the recorded platform-setting error.

## Exact reproducible release commands

### Appendix A — HTML/static hashes

```bash
git diff --exit-code -- src/buoy_search/command_center_static
PYTHONDONTWRITEBYTECODE=1 uv run python - <<'PY'
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
root = Path('src/buoy_search/command_center_static')
class Refs(HTMLParser):
    def __init__(self): super().__init__(); self.paths = []
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        self.paths += [values[k] for k in ('href', 'src') if values.get(k, '').startswith('/')]
p = Refs(); p.feed((root / 'index.html').read_text())
assert p.paths == ['/buoy.svg', '/assets/index-D34KCjuB.js', '/assets/index-Amu9gKyT.css']
files = [root / 'index.html', *(root / value[1:] for value in p.paths)]
assert all(path.is_file() for path in files)
print('\n'.join(f'{path} {sha256(path.read_bytes()).hexdigest()}' for path in files))
PY
```

### Appendix B — archive inventory

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python - <<'PY'
from pathlib import Path
import tarfile, zipfile
wheel = next(Path('dist').glob('*.whl')); sdist = next(Path('dist').glob('*.tar.gz'))
with zipfile.ZipFile(wheel) as archive: wn = archive.namelist()
with tarfile.open(sdist, 'r:gz') as archive: sn = archive.getnames()
js = [n for n in wn if '/command_center_static/assets/index-' in n and n.endswith('.js')]
css = [n for n in wn if '/command_center_static/assets/index-' in n and n.endswith('.css')]
assert len(wn) == 69 and len(sn) == 159 and len(js) == len(css) == 1
assert any(n.endswith('/command_center_static/index.html') for n in wn)
assert any(n.endswith('/command_center_static/buoy.svg') for n in wn)
for suffix in ('/docs/command-center.md', '/scripts/benchmark_command_center_inventory.py', '/images/buoy.svg', '/web/src/App.tsx', '/web/package-lock.json'):
    assert any(n.endswith(suffix) for n in sn), suffix
assert not any('node_modules' in n.split('/') for n in [*wn, *sn])
print(wheel.name, len(wn), js, css, sdist.name, len(sn), 'node_modules=0')
PY
```

### Appendix C — installed-wheel smoke

```bash
target="$(mktemp -d /tmp/buoy-command-center-wheel-target.XXXXXX)" && trap 'rm -rf "$target"' EXIT
uv pip install --no-deps --target "$target" dist/*.whl
TARGET="$target" PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -I <<'PY'
import os, sys, tempfile
from pathlib import Path
target = Path(os.environ['TARGET']).resolve(strict=True); sys.path.insert(0, str(target))
from fastapi.testclient import TestClient
import buoy_search
from buoy_search.command_center_api import create_app
assert Path(buoy_search.__file__).resolve().is_relative_to(target)
static = target / 'buoy_search' / 'command_center_static'
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp).resolve(strict=True)
    with TestClient(create_app(artifacts_root=root/'artifacts', state_root=root/'state', static_root=static), base_url='http://localhost') as client:
        responses = {p: client.get(p) for p in ('/api/v1/health', '/api/v1/dashboard', '/api/v1/plans', '/api/v1/namespaces', '/')}
assert all(r.status_code == 200 for r in responses.values())
assert responses['/api/v1/dashboard'].json()['plan_count'] == 0
assert responses['/api/v1/plans'].json()['items'] == responses['/api/v1/namespaces'].json()['items'] == []
assert 'Buoy' in responses['/'].text
print(Path(buoy_search.__file__).resolve().parent, static.resolve(), {p: r.status_code for p, r in responses.items()})
PY
```

### Appendix D — Safari probe

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python - <<'PY'
import json, socket, subprocess, tempfile, time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
version = subprocess.run(['/usr/bin/safaridriver', '--version'], check=True, capture_output=True, text=True).stdout.strip()
with socket.socket() as probe: probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
with tempfile.TemporaryDirectory() as tmp, (Path(tmp)/'driver.log').open('w') as log:
    driver = subprocess.Popen(['/usr/bin/safaridriver', '-p', str(port)], stdout=log, stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic() + 5; status = None
        while time.monotonic() < deadline:
            try:
                with urlopen(f'http://127.0.0.1:{port}/status', timeout=1) as response: status = json.load(response)
                break
            except URLError: time.sleep(.05)
        assert status and status['value']['ready'] is True
        request = Request(f'http://127.0.0.1:{port}/session', data=b'{"capabilities":{"alwaysMatch":{"browserName":"safari"}}}', headers={'Content-Type':'application/json'}, method='POST')
        try:
            with urlopen(request, timeout=10) as response: session = json.load(response)
        except HTTPError as exc: session = json.load(exc)
        print(version, json.dumps(status), json.dumps(session))
    finally: driver.terminate(); driver.wait(timeout=5)
PY
```

### Appendix E — core import isolation

```bash
rm -rf dist web/node_modules && uv sync --locked && uv lock --check
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -I <<'PY'
import importlib.util, sys
import buoy_search, buoy_search.cli
assert importlib.util.find_spec('fastapi') is importlib.util.find_spec('uvicorn') is None
for module in ('buoy_search.command_center_api', 'buoy_search.command_center_jobs', 'buoy_search.bigquery_relation', 'buoy_search.snowflake_relation', 'turbopuffer', 'sentence_transformers', 'transformers'):
    assert module not in sys.modules, module
print(buoy_search.__file__, buoy_search.cli.__file__, 'forbidden_modules=[]')
PY
```

### Appendix F — final artifact inventory

```bash
git diff --check && uv lock --check
test -z "$(git diff --cached --name-only)" && test ! -e dist && test ! -e web/node_modules
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -I <<'PY'
from pathlib import PurePosixPath
import subprocess
tracked = [n for n in subprocess.run(['git','ls-files','-z'], check=True, capture_output=True).stdout.decode().split('\0') if n]
forbidden = []
for name in tracked:
    path = PurePosixPath(name); parts = set(path.parts)
    if path.suffix in {'.duckdb','.db','.sqlite','.log','.prof'} or 'node_modules' in parts or path.parts[:1] == ('dist',) or '.buoy' in parts or '.turbo-search' in parts: forbidden.append(name)
assert forbidden == []
print(f'tracked={len(tracked)} staged=0 generated_directories=0 private_or_generated=0')
PY
```

## Documentation and changed files

`docs/command-center.md` now states the `plan.json` traversal leaf, aggregate read-only state summaries, locked 1.0-second process-local TTL, immediate managed invalidation, bounded external visibility, one-refresh misses, nonpersistent/non-authorizing cache scope, and continued complete selected verification with explicit linear-cost/no-universal-subsecond limits. README already links the canonical packaged SVG and accurately describes Command Center installation/scope, so no README change was needed.

Final integration and review-repair files are:

- `src/buoy_search/applied_state.py`
- `src/buoy_search/command_center_local.py`
- `scripts/benchmark_command_center_inventory.py`
- `tests/test_applied_state.py`
- `tests/test_command_center_local.py`
- `tests/test_command_center_api.py`
- `docs/command-center.md`
- `images/buoy.svg` (mechanical restoration of a pre-existing latest-main package/public-surface defect)
- `.10x/evidence/2026-07-27-command-center-inventory-performance.md`
- `.10x/tickets/2026-07-27-validate-command-center-inventory-performance.md`
- `.10x/tickets/2026-07-27-command-center-inventory-performance-plan.md`

The repair regressions cover absent `O_NOFOLLOW`, absent `O_DIRECTORY`, missing `dir_fd` support, `os.open` raising `NotImplementedError`, isolated service/API safe-state behavior, and a rebuild lasting exactly the TTL while an external plan appears after its scan.

## Deviations, defects, and limits

- Pre-existing defect repaired: hosted-main commit `7dbf0feb` removed `images/buoy.svg` but did not update the still-active brand/package/CI/test contract. The final child restored only an identical copy; no spec, package configuration, CI workflow, or other asset changed.
- Installed-wheel exploratory deviation: the first smoke used Darwin's lexical `/tmp` path and correctly failed the managed-root identity guard because the physical root is `/private/tmp`. The accepted rerun resolved the temporary root first and all installed-wheel endpoints passed. No source repair was needed.
- Browser deviation: Safari was installed, but a real WebDriver session was unavailable without changing the operator's disabled “Allow remote automation” setting. The setting was left untouched; jsdom frontend tests and real installed-wheel FastAPI/static smoke passed, but no graphical browser claim is made.
- The available local Node was 24.6.0, not CI's pinned 24.18.0. The immutable CI convention remains pinned to 24.18.0; local install/test/build passed.
- Selected verification is intentionally linear in selected delta rows and remains about 2.90–2.94 seconds warm p50 for this 100,100-row fixture. This is the principal residual performance cost and is not hidden by summary caching.
- The summary cache is process-local, nonpersistent, non-authorizing, and may remain stale for at most the TTL after external-process changes. A crash after durable managed success but before callback execution has the same bounded stale window.
- Worker-pool exhaustion under many simultaneous blocking calls remains outside the one-blocked-call threading contract.
- Cold means process-cold, not OS-cache-cold. RSS is process-wide. Five warm calls are a small observational sample and are not portable CI thresholds.
- The npm React Router advisory and Starlette/lxml warnings are pre-existing and separately documented; no dependency or product scope was widened here.

## External-side-effect attestation

No live crawl, clone, source adapter, database provider, remote refresh/search, turbopuffer, embedding/model, apply, catalog/namespace mutation, push, merge, PR, publish, or release operation ran. The benchmark's hardcoded provider/source/plan/apply inventory agrees with this procedure-based attestation but is not runtime instrumentation. API/provider/source tests used fakes or temporary local artifacts. Package, benchmark, installed-wheel, local server, and attempted browser-driver files lived only in system temporary directories and were removed. No generated benchmark database/tree/profile/raw log, distribution, `node_modules`, credential, private path, or local state is committed.

## Remaining final-review repairs

A later final review found two integrity gaps and one validation-race gap in commit `def12172`: a forced direct-miss request could reuse a concurrently rebuilt snapshot even when that snapshot's rebuild-start expiry had elapsed; `_summary_bound_path` leaked the just-opened descriptor if its first `os.fstat()` raised; and the frontend persisted-event test could dereference `FakeEventSource.instances[0]` before the effect constructed it. The bounded repair under the still-open validation ticket:

- reuses a concurrent replacement snapshot only while its rebuild-start expiry is still live; an expired replacement is rebuilt under the existing lock;
- adds a deterministic direct-miss/concurrent-slow-rebuild schedule in which the concurrent scan completes before an external plan appears, its TTL elapses while it still owns the lock, and the waiting forced miss performs exactly one further scan and discovers the plan (three scans total: prime, concurrent rebuild, forced refresh);
- closes a descriptor immediately when its initial `fstat` fails and proves the descriptor is invalid afterward; and
- changes only `web/src/App.test.tsx` to wait for the single `FakeEventSource` instance before the existing dereference. No product frontend code changed.

### Repair validation results

- `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_command_center_local.CompactDeltaInventoryTests.test_direct_miss_refreshes_after_concurrent_rebuild_expires tests.test_applied_state.AppliedStateStoreTests.test_summary_reader_closes_descriptor_when_initial_fstat_fails -v` passed 2 tests in 0.880s.
- `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_command_center_inventory_benchmark tests.test_applied_state tests.test_command_center_local tests.test_command_center_api -q` passed 89 tests in 7.875s with 36 expected core-environment UI skips.
- Core full discovery passed 797 tests in 85.055s with 36 expected skips. After `uv sync --locked --extra ui`, the six-module focused basket passed 175 tests in 22.600s and UI-enabled full discovery passed 797 tests in 85.590s with no skips.
- Ranking and C6 validation passed unchanged at dataset bundle SHA-256 `5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9` and forecast SHA-256 `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`.
- Targeted compilation, `git diff --check`, and `uv lock --check` passed.
- The exact benchmark rerun passed. Warm p50 milliseconds were Dashboard `0.137`, Plans `0.016`, Namespaces `0.118`, namespace detail `0.141`, plan detail `2974.111`, changed page 1 `2981.829`, changed later page `3016.995`, and near-end stale `2995.965`. Structural output remained exactly one plan scan, one state scan, five state connections, zero applied-row objects, no legacy descendants, and zero delta opens. The first result-extraction helper used the wrong top-level JSON key (`timings`) and failed with `KeyError`; the benchmark itself had succeeded, and a complete rerun with the correct `measurements` key produced the recorded values and removed its temporary output.
- After the test-only race repair, 20 repeated full frontend runs passed 37/37 each. A further 30 repeated focused persisted-event runs passed 1/1 each with 36 filtered tests, and 10 repeated full runs passed 37/37 each. Two consecutive `npm run build` executions each built the same 42 modules; `git diff --exit-code -- src/buoy_search/command_center_static` passed and the four packaged static hashes remained unchanged.
- `uv build --out-dir dist` passed with a 69-entry wheel and 159-entry sdist, one hashed JavaScript asset, one hashed CSS asset, and zero archive `node_modules` entries. Isolated installation returned HTTP 200 for health, dashboard, plans, namespaces, and static root. Core sync removed the three UI packages; isolated core imports excluded FastAPI, Uvicorn, API/jobs, optional database adapters, turbopuffer, and model modules. The first import attempt occurred after the required generated `_version.py` cleanup and therefore failed as expected; a temporary rebuild regenerated it, the import-isolation check passed, and both `dist` and generated `_version.py` were removed again.

### Mechanically derived generated-artifact and exclusion inventory

The earlier Appendix F statement `generated_directories=0` was broader than its procedure: that command inspected tracked names and asserted two paths only. It is superseded for this final repair by an explicit filesystem walk. The accepted command pruned exactly `.git` (VCS metadata) and `.venv` (the task's explicit non-venv exclusion), then searched the rest of the worktree for exactly `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`, `*.pyc`, `src/buoy_search/_version.py`, `.pi-subagents/artifacts/`, `dist/`, and `web/node_modules/`. It separately classified all 876 `git ls-files` paths against the same target rules before accepting deletion safety. Final output was:

```text
examined_root=.
excluded_roots={.git: VCS metadata, .venv: explicitly exempt virtual environment}
target_patterns=[.pytest_cache/, .ruff_cache/, non-.venv __pycache__/, non-.venv *.pyc, src/buoy_search/_version.py, .pi-subagents/artifacts/, dist/, web/node_modules/]
remaining_targets=[]
tracked_target_overlap=[]
tracked_paths=876
```

This is a bounded claim about the enumerated generated targets and stated exclusions, not a claim that every possible generated-file convention was inferred. `git diff --check`, `uv lock --check`, an empty staged-name check, and final status also passed; only the five intentional source/test files plus this evidence and the two open ticket progress records were modified before commit.
