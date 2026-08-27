Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Relates-To: .10x/tickets/done/2026-08-24-validate-provider-invocation-receipt-integration.md, .10x/tickets/done/2026-08-24-implement-private-provider-invocation-receipts.md, .10x/specs/provider-client-invocation-accounting.md, .10x/specs/provider-client-invocation-receipt.md, .10x/reviews/2026-08-24-provider-invocation-receipt-integration-review.md

# Provider Invocation Receipt Integration Closure Evidence

## Exact reviewed identities

The independent final review passed the immutable implementation/source commit
`0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
`9017c4a335938faca80cdded54545df8b79c12f8`, using its committed validation
ledger at records commit `327bcf43b73b5941a0c94ab9fb4aa294456ea498`,
tree `0c187238d8abe09cf0d99aa8fdb53f1a5112900e`.

The source commit's parent is the independently reviewed final-CLI staging
commit `bb32b4f81fbb490472a68e7caaf00d0a4dfab379`, tree
`9d42b419c2240ca53566056940d02e5c84d0baad`. Commit `0b27c4e` changes only the
routing calibration artifact. Records commit `327bcf4` changes only append-only
integration-ticket validation history. Consequently, the reviewed source and
test bytes are identical in the records target and this records-only closure.

Exact reviewed implementation/test identities are:

| Path | Git blob at `0b27c4e` | SHA-256 |
| --- | --- | --- |
| `src/buoy_search/_provider_invocation_receipt.py` | `87f9d06b367710e9de87e26b9b4c97f4165a3963` | `73361cde0ad7fad2906d01c10a7044f1a7ff34d28425e987f4265e7f60404349` |
| `src/buoy_search/retriever.py` | `d87530fb4db81029744273ef27d7f1e0e4ca302c` | `89aeb5db61a1997f127db2ebe651beb9f184d4358e0e0cd3d98921713c9b613d` |
| `src/buoy_search/remote_catalog.py` | `8ec5b5e528407b00d37aab8a4c7e6636b392f9f4` | `3d859a21c257f7edaf113593aa486defdc78d1c89d45367811d0ac9ce991399d` |
| `src/buoy_search/cli.py` | `6ae0296f9b93fb18ecfb069ee2c21225bd0ede19` | `c6b575e160c5379b8a7214b3434a06d47864f0414e1478f44bcddeff313609ce` |
| `src/buoy_search/data/automatic_routing_confidence_calibration.json` | `7d887e1ebd113e3858f4c8efc0cddc23fc5ab3ea` | `79c780a5c3ffebfe5569d463663c30d681cf224aec3ddfb1e03202641b97ed1e` |
| `tests/test_provider_invocation_receipt_core.py` | `d2187c6e48112b2ec7b463a8d0b5dac8c9b3b93f` | `20cb49987088cce52e7c3047690bfd20d572a4cd6ede0b07807332c0fb7f37b6` |
| `tests/test_provider_invocation_receipt_content.py` | `fc304b4d56e51ae5d7b755b7ed0d2e614d11d3d8` | `98bddbcf973ebc06bec427c34f9e6797efb16165ca118215f776c9bffc968e6a` |
| `tests/test_provider_invocation_receipt_catalog.py` | `f57e17a1f2f2c8ca1a9560ed3847c46cb3efcbfc` | `3317fa63baa46938f96df0127d4ec2e9f80785f109d1f0a74fb49715c36955b8` |
| `tests/test_provider_invocation_receipt_integration.py` | `b74681b8f5fbef9efa5b160bfb3fcdcddb397619` | `e9b0775bb608f5ecc6bd60cc924cdb8d8d678f30ef437fe886ddfd9ceaa9543b` |

## Final CLI receipt and artifact-only equality

The exact final CLI SHA-256 is
`c6b575e160c5379b8a7214b3434a06d47864f0414e1478f44bcddeff313609ce`.
`cli.py` is byte-identical between reviewed staging commit `bb32b4f` and final
source commit `0b27c4e`.

The schema-v3 authority was restored from exact
`develop@dd0e155d26af6b0cfbc9872606c5861e0d3b4306`, whose artifact SHA-256 is
`62ec1fe8cb7e49247c24b633379a6b2553475bc0e25ce846998ea5dd77df8cf5`.
Parsed deep equality and an all-line byte comparison proved exactly one changed
JSON leaf, `/receipts/cli_module_sha256`, and exactly one changed text line,
line 57. Its old value was
`90e7b2ddf7bbde2daaf0ccd78aa2a779d9e61946a8b7f7ae8f3512dec431ebf9`;
its new value is the exact CLI hash above. Every other parsed field and text line
is byte-equivalent. The final artifact SHA-256 is
`79c780a5c3ffebfe5569d463663c30d681cf224aec3ddfb1e03202641b97ed1e`.

## Recorded validation controls and exact commands

Validation was credential-removed and strict-offline. The commands unset
`TURBOPUFFER_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`,
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `HF_TOKEN`,
`HUGGING_FACE_HUB_TOKEN`, `BUOY_TELEMETRY`, and `PYTHONPATH`; used private
`HOME`, `TMPDIR`, XDG, Hugging Face, and bytecode roots; and set
`UV_OFFLINE=1`, `UV_PYTHON_DOWNLOADS=never`, `PIP_NO_INDEX=1`,
`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, and `NO_PROXY='*'`.
Python runtimes were CPython 3.11.5 and CPython 3.13.0. Temporary validation
roots were outside the repository and were deleted after the ledger was
committed.

The exact final receipt suite command on each runtime was:

```sh
python -m unittest -q \
  tests.test_provider_invocation_receipt_core \
  tests.test_provider_invocation_receipt_content \
  tests.test_provider_invocation_receipt_catalog \
  tests.test_provider_invocation_receipt_integration
```

It passed 91/91 in 0.673 seconds on Python 3.11.5 and 91/91 in 0.514 seconds on
Python 3.13.0. Exact log SHA-256 values were respectively
`674d11a1ce996ee3a0b39c08713c6aa583756ae29aa660a32ce98a18f3c8c24e`
and `fcca4c538c5a76977ef5af6071d91302fca426bb70a543242b93fedfa23a0749`.

The exact broader 20-module command on each runtime was:

```sh
python -m unittest -q \
  tests.test_provider_invocation_receipt_core \
  tests.test_provider_invocation_receipt_content \
  tests.test_provider_invocation_receipt_catalog \
  tests.test_provider_invocation_receipt_integration \
  tests.test_retriever \
  tests.test_multi_namespace_retrieval \
  tests.test_remote_catalog \
  tests.test_cli \
  tests.test_apply_cli \
  tests.test_catalog_cli \
  tests.test_automatic_routing \
  tests.test_automatic_routing_after_apply \
  tests.test_routing_activation_cli \
  tests.test_routing_quality \
  tests.test_routing_quality_runner \
  tests.test_retrieval_evidence \
  tests.test_retrieve_command_telemetry \
  tests.test_local_retrieval_telemetry \
  tests.test_telemetry_envelope \
  tests.test_telemetry_producer
```

It passed 535/535 in 30.025 seconds on Python 3.11.5 and 535/535 in 28.114
seconds on Python 3.13.0. Exact log SHA-256 values were respectively
`7cb37240da6f405b724f6e07f75c50b2a35484ea3585bc63be5955172d41e156`
and `9b73416a8219cf8d231fdcf325d09cbf6b1fc18416969b257e70c8caaae7f9ef`.

The exact full-repository command on each runtime was:

```sh
python -m unittest discover -s tests -p 'test_*.py' -q
```

At exact source commit `0b27c4e`, it passed 1,167/1,167 in 96.361 seconds on
Python 3.11.5 and 1,167/1,167 in 91.726 seconds on Python 3.13.0. Exact log
SHA-256 values were respectively
`ccc086f9d83fdee5f9ba33572ad76c253902e225ef3ad628e048fe9a4e0c9185`
and `275a548a63c06a972e699ff0602dd45be4ea2caf1e7a9098ca2ce18fa30d969d`.
Only established fake plan-cleanup warnings and the lxml `strip_cdata`
deprecation appeared.

Additional exact successful commands were:

```sh
uv lock --check --offline
python scripts/validate_ranking_contract.py
python scripts/c6_syntax_forecast.py validate
python -c 'import py_compile, subprocess; paths=subprocess.check_output(["git","ls-files","*.py"],text=True).splitlines(); [py_compile.compile(path,doraise=True) for path in paths]; print(len(paths))'
uvx --offline ruff check --select E9 src tests
git diff --check
git diff --check develop...HEAD
git diff --check --cached
```

The frozen lock resolved 157 packages. Each runtime retained 13 ranking
datasets, 13 folds, 369 judgments, and 90 composite identities with exact bundle
SHA-256 `5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9`.
Each runtime retained C6 forecast SHA-256
`d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`
and compiled all 110 tracked Python files. Ruff E9 and all diff checks passed.

An AST command parsed every Python file under `src` and `scripts`, selected
calls whose function name is `read_remote_catalog`, and asserted exactly 14
callers with exactly one `_invocation_observer` keyword caller:
`src/buoy_search/cli.py:1643`. Both runtimes then ran this strict source check:

```sh
PYTHONPATH=/private/tmp/buoy-provider-receipt-final/checkout/src /private/tmp/buoy-provider-receipt-final/runtime311/bin/python -c 'from buoy_search.routing_quality import load_routing_confidence_calibration; value=load_routing_confidence_calibration(); assert value.schema_version == 3 and value.mode == "active" and value.receipts.cli_module_sha256 == "c6b575e160c5379b8a7214b3434a06d47864f0414e1478f44bcddeff313609ce"'
PYTHONPATH=/private/tmp/buoy-provider-receipt-final/checkout/src /private/tmp/buoy-provider-receipt-final/runtime313/bin/python -c 'from buoy_search.routing_quality import load_routing_confidence_calibration; value=load_routing_confidence_calibration(); assert value.schema_version == 3 and value.mode == "active" and value.receipts.cli_module_sha256 == "c6b575e160c5379b8a7214b3434a06d47864f0414e1478f44bcddeff313609ce"'
```

Both runtimes accepted the new receipt and loaded routing revision
`active-anchor-e559a8aa-v1`. Replacing only the artifact with exact `develop`
authority caused both runtimes to reject it with exact generic diagnostic
`Routing activation source receipt 'cli_module_sha256' is incompatible.` The
same new-accept/old-reject result passed in the isolated installed package, for
six strict receipt checks total.

## Build and package identities

The exact clean build command was:

```sh
uv build --offline --out-dir /private/tmp/buoy-provider-receipt-final/dist
```

It produced:

| Distribution | Bytes | Members | SHA-256 |
| --- | ---: | ---: | --- |
| `buoy_search-0.5.2.dev87+g0b27c4eaa-py3-none-any.whl` | 730,602 | 78 | `42a4ba1be691de541c17df1e3d9858e3bf88e7a7b758461f7ccc19b899533f87` |
| `buoy_search-0.5.2.dev87+g0b27c4eaa.tar.gz` | 1,301,691 | 162 | `f8f1dfbf5337e04141e7f69ce6e9f658174302b1255cc99f22d958e32e010a5d` |

Build-log SHA-256 was
`89f93a26a5c2f209fcb1c46149ca8d9619683da6c7af0565b6c50f33b9fcb605`.
Members were unique and path/link-safe; the sdist contained no `.10x` member.
Wheel and sdist metadata version was exactly `0.5.2.dev87+g0b27c4eaa`; the sole
console entry point was exactly `buoy = buoy_search.entrypoint:main`.
Source, wheel, and sdist reproduced the five production hashes in the identity
table above.

The exact installation command was:

```sh
uv pip install --offline --python /private/tmp/buoy-provider-receipt-final/install/bin/python /private/tmp/buoy-provider-receipt-final/dist/buoy_search-0.5.2.dev87+g0b27c4eaa-py3-none-any.whl
```

It resolved and installed 107 cached packages, including exact candidate
`buoy-search==0.5.2.dev87+g0b27c4eaa`. The installed package reproduced exact
CLI, artifact, private-receipt, remote-catalog, and retriever hashes; reported
the exact version and entry point; loaded `active-anchor-e559a8aa-v1`; passed
`buoy --version`, executable help, and module help; and passed this provider-free
preview command:

```sh
/private/tmp/buoy-provider-receipt-final/install/bin/buoy retrieve 'offline package receipt smoke' --namespace receipt-smoke --dry-run --json
```

The preview had empty stderr and asserted exactly four fields: `dry_run=true`,
`api_calls_occurred=false`, `content_retrieval_occurred=false`, and
`credentials_required=false`; it created no `.buoy` path. Install-log SHA-256
was `8dc7cb052eb82dce67ea4366ffe7ca5b0f051123d053adef47af07399b35fd17`;
preview-output SHA-256 was
`6c3d5270a1755394c1126ced9ee3966c4ac85501c5d3b271a69cc5b5832ffa59`.

## Preserved failed harness history

Failures were not hidden or converted to product defects:

- An initial Python 3.11 `uv run --offline --frozen --python <3.11> --with
  pytest python -m pytest -q -p no:cacheprovider <20 modules>` stopped before
  collection because strict-offline resolution lacked cached `torch==2.12.1`.
- Three subsequent Python 3.11 535-test harness attempts reported respectively
  two failures/errors, one failure, and one failure because a reused editable
  environment or environment-clearing subprocess resolved the wrong or no
  source package. A clean dependency bridge plus editable install of the exact
  copied source repaired only the harness and yielded the recorded 535/535 pass.
- The first Python 3.11 full-repository command reported 1,164 passes and three
  dynamic-version failures because an isolated empty UV cache lacked
  `hatchling==1.31.0` and `hatch-vcs==0.5.0`. Using the established offline
  package cache repaired only dependency discovery and yielded 1,167/1,167.
- `uvx --offline ruff check --select F,E9` reported seven pre-existing F401
  imports in Python bytes already independently reviewed at `bb32b4f`. The
  gating E9 command passed. No unauthorized source cleanup changed those bytes.

## Integration acceptance-criterion mapping

1. **Explicit/automatic live and preview — satisfied.** Integration tests
   `173-336` prove explicit preview has no call, explicit live has null catalog,
   automatic preview is terminal catalog-only, and automatic live separates
   catalog and content families.
2. **Caller isolation — satisfied.** Tests `607-639`, the exact AST inventory,
   and source inspection prove 14 callers with only automatic CLI passing the
   capability. Default/direct/apply/catalog-management/evaluation callers remain
   argument-free and unobserved.
3. **Terminal authority and unknown handling — satisfied.** Core/integration
   tests cover pre-exit, never-run/incomplete workers, observer faults, invalid
   models, and terminal exception handoff; missing or incomplete state is null.
4. **Lifecycle/concurrency/identity — satisfied.** Both cancellation classes,
   named control-flow values, custom non-`Exception` `BaseException`, ordinary
   exceptions, nested/independent contexts, concurrent workers, leases,
   restoration, and identical exception behavior are asserted.
5. **Aggregate matrices — satisfied.** Core/catalog tables enforce all ordered
   prerequisites, per-category bounds, ambiguous-state rejection, exact 40,002
   composition, and adjacent overflow.
6. **Privacy — satisfied.** Exact canonical bytes and generic diagnostics reject
   every specified query/argv/identifier/content/path/credential/URL/payload/
   billing/error/time/ID/ambient-context sentinel.
7. **Private/default-off/nonpersistent/nontelemetry — satisfied.** Package,
   parser, environment, persistence, retention, and telemetry-v2 source audits
   find no widened surface.
8. **Provider/model/store-free validation — satisfied.** Exact 91/91, 535/535,
   and 1,167/1,167 dual-runtime evidence is recorded above under strict-offline,
   credential-removed controls.
9. **CLI receipt/package reproduction — satisfied.** Exact one-leaf/one-line
   artifact equality, old/new strict validation, archives, and isolated install
   are recorded above.
10. **Fresh independent exact-candidate review — satisfied.** The final PASS is
    durably recorded at
    `.10x/reviews/2026-08-24-provider-invocation-receipt-integration-review.md`.

## Aggregate parent mapping and active-spec coherence

All five parent-plan criteria are satisfied: each predecessor has exact closure
evidence and PASS review; the integrated fake suites cover every governed
boundary and failure mode; diff/source review finds no public/env/persistence/
telemetry-v2 or unrelated production widening; dual-runtime full/artifact/build/
install validation passed; and independent final review passed the exact source
and records targets against both active specifications.

The active accounting and lifecycle specs remain regeneration-grade and match
the reviewed implementation. Exact content/catalog expression boundaries,
L1 -> metadata -> C1 -> C2 -> L2 aggregate validation, cancellation precedence,
terminal authority, canonicalization, privacy, default-off activation, worker
leases, and observer-failure isolation are not narrowed or contradicted.

## Procedure for records-only closure

Closure inspection used read-only Git status/log/tree/diff/blob/hash/search and
exact source/record reads. It did not rerun tests. It verified reviewed source
and records identities, all child evidence/reviews, every integration and parent
criterion, active-spec coherence, review lineage, package evidence, and the
live-canary dependency owner. Closure edits only `.10x` records and ticket
paths; they preserve exact reviewed source, test, and routing-artifact bytes.

## Limits

This evidence is fake-only and application-boundary-only. It does not prove live
provider behavior, SDK-internal retries, physical wire sends, billing, cost, or
rate-limit use. Those limits remain explicitly owned by the separately gated
one-time live canary ticket. The independent reviews were read-only and did not
rerun validation. Raw temporary validation logs/builds were deleted after their
hashes and bounded outcomes were committed, so this record preserves the exact
reported identities and commands rather than claiming retained raw artifacts.
