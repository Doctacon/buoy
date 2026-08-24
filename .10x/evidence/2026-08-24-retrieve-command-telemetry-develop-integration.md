Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Relates-To: .10x/tickets/2026-08-24-integrate-retrieve-command-telemetry-into-develop.md, .10x/specs/retrieve-command-telemetry.md, .10x/specs/local-telemetry-v2-storage-and-migration.md

# Retrieve Command Telemetry Develop Integration

## Identity and preflight

The local integration ran on macOS 26.5.1 build 25F80, arm64, with CPython
3.11.10, CPython 3.13.0, and uv 0.11.7. Before mutation,
`git status --short --branch` was clean on
`work/retrieval-command-telemetry-v2`, and `git worktree list` confirmed this
ordinary task worktree and the separate integration-only `develop` worktree.
After `git fetch origin`, the exact identities were:

- ticket-opening commit `88553279099cadde8588fd390ba645da5a1903ab`, tree
  `cca71ac31e3d3c64b983ef394daa348a1e0dbaa5`, sole parent
  `ef756020aab8811e5ac60dde79c2894451683501`;
- accepted telemetry commit `ef756020aab8811e5ac60dde79c2894451683501`,
  tree `6921a5aea677d28e88e356339647b2bd0f0bf497`;
- local `develop` and `origin/develop`, both exactly
  `3eabedd6b1e2c60a2a8be2489327b014d04130fc`, tree
  `885dcd15eb1e6f55b9596f7293aa74e1eaf0ed49`;
- immutable production runtime
  `6bfd0d4cec784cec18e9050bef4a8d0787f354e7`, tree
  `269310974768aafb2d79d62c50f0753d94ac8491`.

No identity differed and `develop` had not advanced. Activation was committed
separately as `c319305eba5dacfdf1c13adabb0ba1244859d5e5`, tree
`69533438610746f04e2b7a58e239891d282d212f`, parent `8855327`.

## Merge and record reconciliation

Exact `develop@3eabedd6` was incorporated without rebase or history rewrite by
merge commit `366069015d0c39912819bd88f9b35f1ec1cb38d2`, tree
`989d3f335013ad9c40ab748154482bc172e608ed`. Its parents, in order, are exact
activation commit `c319305eba5dacfdf1c13adabb0ba1244859d5e5` and exact develop
`3eabedd6b1e2c60a2a8be2489327b014d04130fc`. `git merge-base HEAD develop`
returned exact `3eabedd6`, and `git merge-base --is-ancestor develop HEAD`
passed.

Git reported no textual conflict. The expected semantic record movement still
required explicit reconciliation: the duplicate top-level active stale-test
ticket was removed, the reviewed done ticket from develop was retained, and all
eight telemetry-side references to the old active path were changed to
`.10x/tickets/done/2026-08-20-reconcile-missing-release-checks-test-harness.md`.
The done stale-CI ticket and both cleanup evidence/review sequences from develop
were retained. A complete `.10x` scan found no old active path or reference.
Exact comparison to develop proved the retained cleanup workflow, dynamic-
version test, both cleanup done tickets, and both cleanup evidence/review
sequences are present. Current workflows contain no deleted release-script
reference.

`git diff --exit-code` proved no `src/` byte changed from either pre-merge
`8855327` or accepted telemetry `ef756020`. Source identities at the merge head
are:

- `src/buoy_search/cli.py`:
  `90e7b2ddf7bbde2daaf0ccd78aa2a779d9e61946a8b7f7ae8f3512dec431ebf9`;
- `src/buoy_search/telemetry_envelope.py`:
  `e1681c4c4dab0909270127fbb7b5eeffb7ea99864ca994cda406cac9c6e76b47`;
- `src/buoy_search/data/automatic_routing_confidence_calibration.json`:
  `62ec1fe8cb7e49247c24b633379a6b2553475bc0e25ce846998ea5dd77df8cf5`.

The source package loaded the active schema-3 routing authority, revision
`active-anchor-e559a8aa-v1`, with seven certified namespaces and the exact CLI
receipt above.

## Isolation and command matrix

All validation used mode-0700 root
`/private/tmp/buoy-telemetry-develop-integration.Fcb0hj`, separate temporary
HOME/TMP/XDG/pycache/project-environment paths per runtime, mode-0600 logs,
`UV_OFFLINE=1`, `UV_PYTHON_DOWNLOADS=never`, `PIP_NO_INDEX=1`,
`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, and unset common provider/model
credential variables. `BUOY_TELEMETRY` was empty except inside the controlled
local fake timing fixture. No real home, installed Buoy, provider/model/content,
credential, namespace, catalog, network, GitHub, tag, release, or publication
operation was used.

The exact unfiltered commands, each run through that isolated environment, were:

```text
uv run --offline --frozen --python /opt/homebrew/bin/python3.11 --with pytest python -m pytest -q -p no:cacheprovider
uv run --offline --frozen --python /opt/homebrew/bin/python3.13 --with pytest python -m pytest -q -p no:cacheprovider
```

Both passed without a stale-test exclusion: **1,076 passed, 1,071 subtests
passed, 57 warnings** on each runtime. The warnings are the established lxml
`strip_cdata` deprecation from `tests/test_crawler_exact_host.py`.

The exact authority-derived focused suite was:

```text
uv run --offline --frozen --python /opt/homebrew/bin/python3.11 --with pytest python -m pytest -q -p no:cacheprovider tests/test_retrieve_command_telemetry.py tests/test_local_retrieval_telemetry.py tests/test_telemetry_envelope.py tests/test_telemetry_producer.py tests/test_telemetry_queue.py tests/test_telemetry_store.py tests/test_telemetry_writer.py tests/test_telemetry_cli.py tests/test_telemetry_v2_storage.py
```

It passed **212 tests and 289 subtests**. Retained dynamic-version coverage was
also run explicitly with
`python -m unittest -q tests.test_dynamic_version`: **3/3 passed** on each of
Python 3.11 and 3.13.

Additional exact commands and results:

```text
uv lock --check --offline
uv run --offline --frozen --python <3.11|3.13> python scripts/validate_ranking_contract.py
uv run --offline --frozen --python <3.11|3.13> python scripts/c6_syntax_forecast.py validate
uvx --offline ruff check --select F,E9 tests/test_dynamic_version.py
PYTHONPYCACHEPREFIX=<isolated> python<3.11|3.13> -m py_compile $(git ls-files '*.py')
git diff --check
git diff --check develop...HEAD
```

All passed. Ranking retained 13 datasets, 369 judgments, 90 composite
identities, inventory SHA-256
`e6f97842ec90f0558f51e70f93ea6b8f09f82f63019a27d0738d2b1efb427608`,
and dataset bundle SHA-256
`5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9`
on both runtimes. C6 retained forecast SHA-256
`d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`
on both. PyYAML parsed the complete one-file workflow inventory; structural
inventory, cleanup-path equality to develop, merge topology, record status,
stale-reference absence, source equality, source hashes, active routing load,
empty porcelain, and empty staged-file checks passed.

As already disclosed by the immutable telemetry implementation evidence, a
non-gating broad Ruff diagnostic over all `src` and `tests` reports the same 21
pre-existing F401/F402 findings in unrelated files. The exact integration-owned
Python target from the cleanup evidence passes Ruff. An initial still-broader
inventory including scripts and stored evidence reported 22 findings, adding an
existing unused import in `scripts/evaluate_routing_quality.py`; no unrelated
lint cleanup was made.

## Fresh controlled timing observations

The accepted provider/model-free fixture was run as a separate process for
zero and 500 ms delays at every named seam:

```text
<isolated-python-3.11> tests/fixtures/retrieve_command_timing_probe.py --stage <bootstrap|initialize|routing|pipeline|render> --delay-ms <0|500>
```

Authoritative version-2 command and pipeline columns, not sums of nested spans,
produced:

| Seam | Baseline command / pipeline / bootstrap ms | Delayed command / pipeline / bootstrap ms | Command delta ms | Pipeline delta ms | Bootstrap delta ms |
| --- | --- | --- | ---: | ---: | ---: |
| bootstrap | 330.018 / 0.097 / 307.696 | 870.833 / 0.101 / 847.390 | 540.815 | 0.004 | 539.694 |
| initialization | 333.462 / 0.089 / 311.524 | 840.432 / 0.458 / 315.387 | 506.970 | 0.369 | 3.863 |
| routing | 334.782 / 0.131 / 311.642 | 844.425 / 0.618 / 314.508 | 509.643 | 0.487 | 2.866 |
| pipeline | 329.860 / 0.099 / 308.645 | 839.242 / 507.607 / 308.500 | 509.382 | 507.508 | -0.145 |
| rendering | 333.385 / 0.088 / 312.101 | 836.514 / 0.088 / 306.245 | 503.129 | 0.000 | -5.856 |

Every required delta was within 375-750 ms; every non-pipeline seam retained an
absolute pipeline delta below 25 ms; pipeline span values exactly equaled the
authoritative pipeline column. Both routing observations contained catalog,
two model spans, and select, all before pipeline. Raw JSONL SHA-256 is
`7be0c654f6127230e74591206c8d81c59d5e3b81968e5a229ddba3e06c6a0b21`;
summary SHA-256 is
`990558e1a4e0f2c515ce1ac85189cabbe7945bf2072e06c01b89b256cca15b2b`.

## Exact combined-head distribution and installed smoke

From clean exact merge head `366069015d0c39912819bd88f9b35f1ec1cb38d2`:

```text
uv build --offline --out-dir /private/tmp/buoy-telemetry-develop-integration.Fcb0hj/dist
uv venv --python /opt/homebrew/bin/python3.13 /private/tmp/buoy-telemetry-develop-integration.Fcb0hj/install
uv pip install --offline --python /private/tmp/buoy-telemetry-develop-integration.Fcb0hj/install/bin/python <exact-wheel>
```

The clean build produced:

- 722,185-byte, 77-member wheel
  `/private/tmp/buoy-telemetry-develop-integration.Fcb0hj/dist/buoy_search-0.5.2.dev100+g366069015-py3-none-any.whl`, SHA-256
  `29fde6de9d9e96226731dde9ede987ebc253d4f4e1f8bf8ae03dd601151a284e`;
- 1,269,304-byte, 157-member source distribution
  `/private/tmp/buoy-telemetry-develop-integration.Fcb0hj/dist/buoy_search-0.5.2.dev100+g366069015.tar.gz`, SHA-256
  `398e43cc94a11d1eff70af3cf6d064f2db8ce451a84fab9ac92d5118505830fe`.

Archive names were unique and traversal/link-free, metadata/version and console
entry point were exact, and source/wheel/sdist/installed copies all reproduced
the CLI, envelope, and routing hashes above. The isolated installation passed
`buoy --version`, package CLI help, module help, telemetry management help,
migrate help, absent-home status text/JSON, and absent-home migrate JSON.
Status reported disabled, absent store, and empty v1/v2 queues; migrate returned
`absent`; neither created `.buoy`.

With `BUOY_TELEMETRY=` and `OTEL_SDK_DISABLED=true`, installed explicit preview
returned `dry_run=true`, `api_calls_occurred=false`,
`content_retrieval_occurred=false`, and `credentials_required=false`, emitted
no stderr, and created no `.buoy`. Installed smoke also passed exact tokenizer
count 9, the three accepted routing-canary identities, 65-case routing dataset
and suite hash, and active schema-3 routing authority/receipt load. Installed
smoke JSON SHA-256 is
`61b17ab1c764ffc47a7755e240cfc13144f72a64aafc90b03f31394a38caba68`.

Two local smoke-harness mistakes stopped before an accepted assertion set: the
first shell helper omitted `shift` and tried to execute the temporary HOME path;
the next assertions incorrectly required the intentionally isolated telemetry
command in provider-facing top-level help and used non-current status wording.
A subsequent canary assertion copied one digest incorrectly. Correcting only
those external harness expectations to the existing accepted help/status and
unchanged workflow canary contract produced the passing result above. No
tracked file, package, or product test was changed or weakened.

## Hosted handoff

After the independent local review passed, reviewed records head
`5732beb56ac900860ed185783b0555d28ff2680d` was pushed as branch
`work/retrieval-command-telemetry-v2`. Draft PR #145 was opened explicitly
against `develop`:

- canonical URL: `https://github.com/Doctacon/buoy/pull/145`;
- observed base: `develop@3eabedd6b1e2c60a2a8be2489327b014d04130fc`;
- observed head: `5732beb56ac900860ed185783b0555d28ff2680d`;
- state at creation: open and draft.

The PR description preserves the exact accepted source hashes, local validation
counts, Hatch-VCS boundary, privacy/external-effect limits, and mandatory hosted
Python 3.11, Python 3.13, and dependent build/smoke gates. No `main`, tag,
Release, publication, installed-tool, provider/model/content/credential/catalog,
or unrelated GitHub operation occurred.

## Exact-head hosted timing failure

Draft PR #145 exact head `67e129170199d7740847a924537211e208b6a219`
triggered CI run `32761209125` against unchanged
`develop@3eabedd6b1e2c60a2a8be2489327b014d04130fc`. Both runtime jobs passed
checkout, dependency sync, and the ranking/C6 static-validator step, then
failed at the first command-delta assertion in
`test_controlled_subprocess_probe_attributes_all_phase_delays`:

- Python 3.11 job `97540448298`: observed command delta
  `330.61740100000003 ms`, below the `375.0 ms` lower bound for a real 500 ms
  injected delay; 1,076 tests ran in 138.438 seconds with this sole failure.
- Python 3.13 job `97540447983`: observed command delta `309.929979 ms`, below
  the same lower bound; 1,076 tests ran in 131.672 seconds with this sole
  failure.
- Dependent distribution job `97541351303` was skipped.

The test's deterministic process order identifies both failures as the first,
bootstrap pair: it launches a zero-delay bootstrap subprocess first and the
500 ms subprocess second, then checks bootstrap before every other named seam.
Thus the authoritative delta subtracts the first cold import/bootstrap cost
from a warmer delayed process. Concurrent hosted matrix activity can amplify
that first-process cost. The hosted log records the resulting delta but not
the individual baseline and delayed JSON observations, so it cannot quantify
the two components independently. This evidence supports warming the same
zero-delay local-fake path before authoritative observations and using a larger
real delay; it does not support lowering the proportional bound.

Raw downloaded artifacts are under
`/private/tmp/buoy-pr145-ci-fail-67e1291.ntr38Q`:

- `run.json`: SHA-256
  `3583b1e42bcd8a1748d6cf23952d327ffe3477d298f2ed406fc462ff2f19ca8b`;
- `check-runs.json`: SHA-256
  `65567ba8ba7d5dc39368fa6f7f18e9c075be838cad21cb466dc7d7c3f54692e9`;
- `run.log`: SHA-256
  `c7a486e303d423d212cbd3002686ac90778062ce76aed228bc05c29190321d72`;
- `failed.log`: SHA-256
  `5cad596e551b5b0ef688ae5a45ec89baf8475d5ce4cf7b6a812dbc2944f69578`.

Recording and inspecting these artifacts performed no provider, model,
content, credential, catalog, installed-tool, package-publication, release,
tag, `main`, or real-home mutation. The ticket is blocked pending bounded test
repair, repeated local dual-runtime validation, independent repair review, a
new pushed exact head, and hosted exact-head checks.

## Bounded hosted-timing repair and validation

The failed hosted state was recorded first in records-only commit
`7346fdca703e41bb5b8b2ed0c7a6a6ebf3a7c580`, tree
`6f12a0563cf2abf1231f2f5d8192899bf2681283`, with sole parent exact failed PR
head `67e129170199d7740847a924537211e208b6a219`. The bounded test repair is
commit `75f65b0b41b2bc74126bd5304f92116d77a9bbac`, tree
`e720c59b03c3c4d5cac0c8b3db640a4d4c1ef6b0`. It changes only
`tests/test_retrieve_command_telemetry.py` and the active ticket: one
zero-delay bootstrap subprocess is discarded as a warm-up before authoritative
observations; the real injected delay is 2,000 ms; the existing proportional
75%-150% bounds and 25 ms non-pipeline bound remain exact; and subtest failure
diagnostics carry the stage, raw pair, and command/pipeline deltas. Every named
bootstrap, initialization, routing, pipeline, and render seam still receives
its own baseline and delayed local-fake subprocess observation. Command,
pipeline, bootstrap, routing-stage membership, and routing-before-pipeline
attribution remain asserted. The fixture and all production `src/` bytes are
unchanged.

### Repeated concurrent timing observations

Python 3.11.10 and 3.13.0 each ran the complete repaired timing test three
times, concurrently across runtimes to model matrix contention. Each runtime
passed 3/3. The external recording harness captured the test's discarded
warm-up and all authoritative fixture JSON without changing test behavior.
The exact command/pipeline observations and deltas were:

| Python | Rep | Seam | Command baseline -> delayed (delta) ms | Pipeline baseline -> delayed (delta) ms | Bootstrap delta ms |
| --- | ---: | --- | --- | --- | ---: |
| 3.11 | 1 | bootstrap | 120.778 -> 2160.792 (2040.014) | 0.097 -> 0.123 (0.026) | 2039.795 |
| 3.11 | 1 | initialize | 121.178 -> 2135.430 (2014.252) | 0.096 -> 1.071 (0.975) | 1.993 |
| 3.11 | 1 | routing | 121.638 -> 2128.731 (2007.093) | 0.140 -> 1.731 (1.591) | -0.473 |
| 3.11 | 1 | pipeline | 123.174 -> 2128.813 (2005.639) | 0.099 -> 2009.405 (2009.306) | -4.400 |
| 3.11 | 1 | render | 120.703 -> 2129.719 (2009.016) | 0.104 -> 0.092 (-0.012) | -0.292 |
| 3.11 | 2 | bootstrap | 121.703 -> 2159.903 (2038.200) | 0.094 -> 0.094 (0.000) | 2038.163 |
| 3.11 | 2 | initialize | 119.372 -> 2126.433 (2007.061) | 0.091 -> 0.849 (0.758) | 4.081 |
| 3.11 | 2 | routing | 122.973 -> 2130.350 (2007.377) | 0.132 -> 1.184 (1.052) | -2.516 |
| 3.11 | 2 | pipeline | 121.492 -> 2130.904 (2009.412) | 0.096 -> 2010.848 (2010.752) | -1.401 |
| 3.11 | 2 | render | 124.457 -> 2127.970 (2003.513) | 0.101 -> 0.122 (0.021) | -2.182 |
| 3.11 | 3 | bootstrap | 122.844 -> 2165.928 (2043.084) | 0.093 -> 0.097 (0.004) | 2043.364 |
| 3.11 | 3 | initialize | 122.238 -> 2129.633 (2007.395) | 0.100 -> 0.393 (0.293) | -2.794 |
| 3.11 | 3 | routing | 121.830 -> 2124.156 (2002.326) | 0.151 -> 0.486 (0.335) | -0.033 |
| 3.11 | 3 | pipeline | 121.878 -> 2131.127 (2009.249) | 0.104 -> 2007.978 (2007.874) | 1.490 |
| 3.11 | 3 | render | 122.948 -> 2128.367 (2005.419) | 0.097 -> 0.094 (-0.003) | -0.701 |
| 3.13 | 1 | bootstrap | 135.178 -> 2137.692 (2002.514) | 0.079 -> 0.082 (0.003) | 2001.749 |
| 3.13 | 1 | initialize | 131.945 -> 2136.218 (2004.273) | 0.079 -> 0.206 (0.127) | -4.114 |
| 3.13 | 1 | routing | 130.343 -> 2140.051 (2009.708) | 0.111 -> 0.197 (0.086) | 2.348 |
| 3.13 | 1 | pipeline | 133.360 -> 2127.877 (1994.517) | 0.087 -> 2001.269 (2001.182) | -5.866 |
| 3.13 | 1 | render | 133.056 -> 2130.142 (1997.086) | 0.089 -> 0.078 (-0.011) | -6.439 |
| 3.13 | 2 | bootstrap | 134.890 -> 2138.137 (2003.247) | 0.079 -> 0.084 (0.005) | 2003.192 |
| 3.13 | 2 | initialize | 134.407 -> 2133.960 (1999.553) | 0.080 -> 0.228 (0.148) | -6.484 |
| 3.13 | 2 | routing | 134.259 -> 2138.744 (2004.485) | 0.114 -> 0.279 (0.165) | -2.679 |
| 3.13 | 2 | pipeline | 133.195 -> 2143.373 (2010.178) | 0.087 -> 2010.346 (2010.259) | 0.395 |
| 3.13 | 2 | render | 133.749 -> 2132.942 (1999.193) | 0.089 -> 0.079 (-0.010) | -7.541 |
| 3.13 | 3 | bootstrap | 133.717 -> 2142.160 (2008.443) | 0.077 -> 0.086 (0.009) | 2008.172 |
| 3.13 | 3 | initialize | 135.396 -> 2142.659 (2007.263) | 0.075 -> 0.195 (0.120) | -1.116 |
| 3.13 | 3 | routing | 134.978 -> 2136.727 (2001.749) | 0.119 -> 0.199 (0.080) | -0.687 |
| 3.13 | 3 | pipeline | 139.455 -> 2137.134 (1997.679) | 0.090 -> 2005.427 (2005.337) | -6.842 |
| 3.13 | 3 | render | 134.436 -> 2139.646 (2005.210) | 0.119 -> 0.082 (-0.037) | -2.123 |

All 30 command deltas were within the retained 1,500-3,000 ms bounds. All six
pipeline-delay deltas were within those bounds. Every one of the 24
non-pipeline deltas had absolute value at most 1.591 ms, below the unchanged 25
ms bound. All six bootstrap-delay deltas were within the proportional bounds;
every routing pair retained catalog/model/select membership and ordering before
the pipeline.

### Complete repair-head validation

After the timing repetitions, both complete suites ran concurrently in fresh
repair-root `UV_PROJECT_ENVIRONMENT` directories using the same successful
integration form, ambient configured uv cache, offline/frozen resolution, no
checkout `PYTHONPATH`, isolated HOME/TMP/XDG config/XDG data/pycache, and unset
credentials:

```text
uv run --offline --frozen --python /opt/homebrew/bin/python3.11 --with pytest python -m pytest -q -p no:cacheprovider
uv run --offline --frozen --python /opt/homebrew/bin/python3.13 --with pytest python -m pytest -q -p no:cacheprovider
```

Python 3.11 passed **1,076 tests and 1,076 subtests** in 130.13 seconds; Python
3.13 passed **1,076 tests and 1,076 subtests** in 126.94 seconds. Each retained
57 established lxml warnings. The authority-derived integrated telemetry suite
on Python 3.11 passed **212 tests and 294 subtests** in 35.33 seconds. The five
additional subtests relative to the earlier integration evidence are the five
named timing-seam diagnostics, not added behavior.

`uv lock --check --offline`; focused Ruff `F,E9` over the repaired test,
fixture, and retained dynamic-version test; dual-runtime ranking validation;
dual-runtime C6 validation; and dual-runtime compilation of every tracked
Python file all passed. Ranking retained 13 datasets, 369 judgments, 90
composite identities, inventory SHA-256
`e6f97842ec90f0558f51e70f93ea6b8f09f82f63019a27d0738d2b1efb427608`,
and dataset bundle SHA-256
`5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9`.
C6 retained forecast SHA-256
`d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`.
Diff hygiene, empty staged diff, exact `origin/develop` merge-base, and source
equality to both failed head `67e1291` and accepted telemetry `ef756020`
passed. Accepted source SHA-256 identities remain exact:

- CLI: `90e7b2ddf7bbde2daaf0ccd78aa2a779d9e61946a8b7f7ae8f3512dec431ebf9`;
- envelope: `e1681c4c4dab0909270127fbb7b5eeffb7ea99864ca994cda406cac9c6e76b47`;
- routing artifact:
  `62ec1fe8cb7e49247c24b633379a6b2553475bc0e25ce846998ea5dd77df8cf5`.

Two earlier harness executions are explicitly discarded and prove no product
failure. The first pointed `UV_OFFLINE` at an empty isolated cache while using
an old validation venv, so only the three dynamic-version tests failed to
resolve their pinned Hatch build requirements; its logs are retained as
`discarded-empty-cache-old-venv-full-3.11.log` and
`discarded-empty-cache-old-venv-full-3.13.log`. The second 3.11 diagnostic used
an old exact-wheel venv together with checkout `PYTHONPATH`, so clone metadata
resolved the repair head while module imports resolved stale
`0.5.2.dev100+g366069015`; it is retained as
`discarded-old-wheel-venv-pypath-dynamic-3.11.log`. Neither harness represented
the repository's supported isolated command. The fresh exact-form runs above
executed all dynamic-version and timing tests and passed.

### Repair artifact identities and limits

All repair artifacts are under mode-0700
`/private/tmp/buoy-timing-repair-validation.d04ZXI`. The top-level manifest is
`SHA256SUMS`, SHA-256
`2d1b72abe2cdc61eb17e763fedeaa3938449b2cdbad02d69052c82ef0c710d48`.
Key files are:

- timing 3.11 JSONL/log:
  `9ff4f9431a182cfb8c6b3568873f3ed72f99b847b9cfc191b293528e4d46e83d` /
  `fc7b2a02be48f23d2e63fa77e34f1054b55010f43e9dfa486fb583e3fad63324`;
- timing 3.13 JSONL/log:
  `66bd162be06da16d4ed68b492f07a9ef79303c9dd1e16291142ce6f3f01e44e8` /
  `59639ab1225c9beed5b2b27c941b502e786dcff0314fbcf5e73ddf9b4d150a22`;
- exact timing summary:
  `a7e79e198792db4c09ab6f5743106fb0304c0ee3164efed650322e807e84f8f9`;
- full 3.11/3.13 logs:
  `cbdc65f71764a5ad377898237897c1987d786af092030b21097555b362f8b54a` /
  `0f0ce378553199116df04e2c4fef7254187d6c00caa138af51e62576126c6019`;
- integrated telemetry:
  `e594ae00825c7143c726f7be0489b7eaa8baf9885ab639c786d5a6e903d79505`;
- lock/Ruff, validators 3.11/3.13, compile, and diff/identity:
  `bed4cf1996410f36aee7acfb56440b0b209430fe68b9864c541333f4b58a1839`,
  `dc5f8ac93affb900a5aea832cec838d98729fffb3c622768bacb3f6f9edc95b9`,
  `41c48e24b8619180ec2c5d21efabb30b813b6b1f2d2d3f704f8fb5aa286cea75`,
  `0891dac94420024638bce1563f85228168c0ffc47048f7da0196bda1cb71407a`,
  and `14d81ce1bf6aafe79cf6c3ea189e779e4930b7f0f81739a3200ac943911965f2`;
- discarded harness logs 3.11/3.13/diagnostic:
  `957d1398ceb1d5c1ed7dbdd99cd4c372011ffd77ca9bc5f2b284f65a887e4d10`,
  `ee470a3774d7ae8d504850b63f3640c7133aaf356e9f44113620e72e0f9dd1e2`,
  and `08b95835f55d976c2a2b6986ae9b4b96d0dbe0b01e623a81c0d7f1ba2c28ec54`.

Validation was local macOS arm64, offline/cache-backed, and concurrent only
across the two local runtime processes. It used no network resolution, real
home, real `.buoy`, installed Buoy replacement, provider, model, content,
credential, namespace, catalog, telemetry store, package publication, release,
tag, `main`, GitHub mutation, push, or merge. Ticket remains active for fresh
independent repair review, push, hosted exact-new-head CI including dependent
distribution, closure, and dedicated integration.

## Raw artifacts, limits, and remaining gates

All logs and distributions are under mode-0700
`/private/tmp/buoy-telemetry-develop-integration.Fcb0hj`. The 33-entry,
mode-0600 relative manifest is
`/private/tmp/buoy-telemetry-develop-integration.Fcb0hj/SHA256SUMS`, SHA-256
`d1888207935e9d4afa3ea7e7f31e30601dd5efd9f2b03a815b62f2c7914920d6`.
Key test-log identities are:

- Python 3.11 full: `37e40bfc886e10bf84727ba0054ea5b542a78daed8c520a80738a83d6b0741c8`;
- Python 3.13 full: `608e3ed21661a7a420875512ce208c7d770f5e18f1b3c49476cc6e9c7ff1d39f`;
- integrated telemetry: `8d3ad27ba0ae9fcd2ad115a1b72d5be9177d85722ee103a6a77bb5010b2a5f23`;
- Python 3.11/3.13 validators:
  `a00e6ec0ac412cc54441673fe46cbef1bb306f1879619eda43092c36ce3a7312` /
  `fb0f383647ca0ee28968d669fca33c50de653eda9b1168ff62e47a64713097f6`;
- package build: `90bb121cb8822ef88567455ac4d14d1f6828f9cfc8366f73a6457ada52b2bd68`;
- archive inspection: `5480c1085cc8e91b3722c49a83a78904b7365978774d24f2054350102483f384`.

This is one macOS arm64 offline/cache-backed observation. It does not establish
other-filesystem or hardware-power-loss behavior and does not replace hosted
Ubuntu exact-head CI. No network-backed dependency resolution or live provider,
model, content, credential, namespace, catalog, real telemetry store, real
home, installed-tool, GitHub, release, publication, `main`, tag, or merge
operation occurred. Independent review, push/PR creation, hosted exact-head
Python 3.11/3.13/build checks, ticket closure, and dedicated squash integration
remain parent-owned gates. The ticket therefore remains active.
