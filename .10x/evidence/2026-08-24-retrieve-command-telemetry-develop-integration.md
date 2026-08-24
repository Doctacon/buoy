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
required explicit reconciliation: the duplicate active
`.10x/tickets/2026-08-20-reconcile-missing-release-checks-test-harness.md` was
removed, the reviewed done ticket from develop was retained, and all eight
telemetry-side references to the old active path were changed to
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
