Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Relates-To: .10x/tickets/done/2026-07-20-bootstrap-crow-plus-immutable-cache.md, .10x/specs/crow-plus-resource-verification-checkpoint.md, .10x/specs/crow-plus-explicit-namespace-pilot.md

# Crow-Plus Phase 2 Immutable Cache Bootstrap

## What was observed

After the user's explicit phase 2 approval was recorded in the owning ticket, the exact public revision `Shuu12121/CodeSearch-ModernBERT-Crow-Plus@96ff525a7aa3bf8bfa90d77337c2b24bd45229af` was reproduced as a 14-regular-file immutable manifest totaling exactly 611,525,163 bytes, transferred into the previously absent dedicated cache root, and verified without importing or executing model or repository code.

Raw normalized artifacts:

- pre-transfer manifest: `.10x/evidence/.storage/2026-07-20-crow-plus-phase2-immutable-manifest.json` (artifact SHA-256 `dca1d2e9c5561e8571a8bd02341e431a22ec220e02023ad79f2de613917e3cca`);
- transfer and post-hash audit: `.10x/evidence/.storage/2026-07-20-crow-plus-phase2-transfer-audit.json` (artifact SHA-256 `159b054f71d3cca4029f3784a79f0719cdc7dd2475bab3f221994fd5a2aaf6e8`).

The normalized pre-transfer manifest's canonical identity hash is `99aa6f73b5baf87adcb80c1383e784f5ec2457ec61eb9e75e7bb7dfd7d98e2cb`. That hash covers the repository, exact revision, sorted paths, advertised sizes, Git object IDs, and LFS metadata. It is distinct from the SHA-256 of the pretty-printed stored JSON artifact.

## Approval provenance

The user directed execution of the approved phase 2 ticket and repeated its exact repository/revision, absent dedicated cache root, 611,525,163-byte transfer ceiling, 768-MiB allocated-cache ceiling, 5-GiB pre/4-GiB post free-disk floors, telemetry/update/no-token boundaries, complete hashing requirement, failure cleanup boundary, exclusions, evidence requirement, and pending-review state. The ticket was changed from `blocked` to `active` and this approval was appended before the first manifest request or file transfer.

This approval is phase 2 only. Phase 3 bounded model loading and measurement remains unauthorized.

## Procedure

1. Ran the repository-mandated `git status --short --branch` and `git worktree list`; the session was on dedicated branch `work/bootstrap-crow-cache` at `16bcbb2`, based on then-current `origin/develop`.
2. Verified `/Users/crlough/Library/Caches/buoy/models/crow-plus-96ff525a7aa3bf8bfa90d77337c2b24bd45229af` was absent. `shutil.disk_usage` reported 34,793,144,320 free bytes at the precondition check, above the 5,368,709,120-byte floor.
3. Set `HF_HUB_DISABLE_TELEMETRY=1`, `DO_NOT_TRACK=1`, `HF_HUB_DISABLE_UPDATE_CHECK=1`, and the additional `HF_HUB_DISABLE_IMPLICIT_TOKEN=1` control before network tooling. Removed `HF_TOKEN` and `HUGGING_FACE_HUB_TOKEN` from the transfer-process environment without reading their values. No Hugging Face Hub or model library was imported.
4. Requested only the exact immutable tree metadata from `https://huggingface.co/api/models/Shuu12121/CodeSearch-ModernBERT-Crow-Plus/tree/96ff525a7aa3bf8bfa90d77337c2b24bd45229af?recursive=true&expand=true` using public HTTPS, no authorization header, and curl with configuration disabled. Parsed the response using the Python standard library, rejected unsafe/duplicate/non-file manifest data, sorted every regular file, and stopped unless the total was exactly 611,525,163 bytes.
5. Created the dedicated cache only after manifest validation. Before each file, checked cumulative advertised bytes against 611,525,163, current free bytes minus the next advertised size against the 4-GiB floor, and current allocated cache bytes plus the next advertised size against 805,306,368. Each exact-revision resolve URL was streamed with curl configuration disabled, `Accept-Encoding: identity`, no authorization header, and token variables absent. The stream was aborted if received bytes exceeded the file's advertised size or the cumulative ceiling.
6. For every file, required exact advertised size; matched non-LFS content to its advertised Git blob SHA-1 and the LFS object to its advertised SHA-256; recorded a SHA-256 for every regular file; fsynced each temporary file; and atomically renamed it into place. On any exception, the procedure was configured to persist failure state and delete only the dedicated incomplete cache root.
7. Performed a second complete read/hash pass over every final regular file, required the final path set and sizes to equal the pre-transfer manifest, measured allocated cache bytes with `/usr/bin/du -sk`, and observed post-transfer free bytes with `shutil.disk_usage`.

An initial Python-standard-library HTTPS attempt to retrieve tree metadata stopped before receiving a manifest because that Python installation could not verify its local CA chain (`CERTIFICATE_VERIFY_FAILED`). No cache root existed and no file transfer began. The successful retry used system curl's verified TLS path; certificate verification was not disabled.

## Immutable manifest and verified hashes

| Path | Bytes | SHA-256 |
|---|---:|---|
| `.gitattributes` | 1,519 | `11ad7efa24975ee4b0c3c3a38ed18737f0658a5f75a0a96787b576a78a023361` |
| `1_Pooling/config.json` | 296 | `d02ebf56344d20f773449b15d0c10ee9a86a9178f3b3c9bfecb8b87d4350ce38` |
| `README.md` | 10,959 | `311dc88b29eb04efc7d32003de39ad000c3ffc0fb96eeaff42a65ac78a7ee7ca` |
| `added_tokens.json` | 73 | `3d576798cdfa41e23257a4821b0b46a26ddc72c350c9ecf2e02e1dabdb6880e2` |
| `config.json` | 1,295 | `ef7c2d946fbee3d6e54c55c4e4bcfdc5d3d66dea4c271623af8ace80fe95ed72` |
| `config_sentence_transformers.json` | 205 | `d2808824cba6c46dd429a5d0a40d7e7dc969bf89759d5de132af90549e0272cf` |
| `merges.txt` | 462,431 | `1ca39c8d071acdf5f7a73ad437ba6787d96e71f737e0e250dc17e9b7c69dddd2` |
| `model.safetensors` | 606,681,112 | `801a2a2608009baa7e661ca6a6206734f39954cf8a4af85409ffc70705094c68` |
| `modules.json` | 229 | `8f4b264b80206c830bebbdcae377e137925650a433b689343a63bdc9b3145460` |
| `sentence_bert_config.json` | 54 | `883e03a457df81d352c233ff7d86df2449a869c5784ecadbab38d312f8682972` |
| `special_tokens_map.json` | 964 | `d19e5e1b2decfcbdb8f60673b82cf25c042d43439cdf2bb00638cbcb257125df` |
| `tokenizer.json` | 3,560,202 | `625524dc6b1e903bccad3970f3f925874658d8dd480016f8b77ae0686c1b1d27` |
| `tokenizer_config.json` | 2,151 | `15d01a959ffad423e1cc3f39180f686fff44321f4fd7fb25a8d589c708e8a341` |
| `vocab.json` | 803,673 | `ec480bd911eda41bdcb0532b20f6b18e7120a318bcfb9a1cfcb46676f954f7a6` |
| **Total** | **611,525,163** | — |

The stored raw audit also records every advertised Git/LFS object hash and its successful comparison. The second post-transfer SHA-256 pass matched the transfer-time hashes for all 14 files.

## Bound observations

- Cache root absent before transfer: yes.
- Free bytes at initial precondition check: 34,793,144,320; required at least 5,368,709,120.
- Free bytes at transfer start: 34,815,438,848; required at least 5,368,709,120.
- Manifest bytes before transfer: 611,525,163; required exactly 611,525,163.
- Received/transferred file bytes: 611,525,163; ceiling 611,525,163.
- Final regular-file bytes: 611,525,163 across exactly 14 files.
- Final allocated cache bytes: 626,688,000; ceiling 805,306,368.
- Post-transfer free bytes: 34,192,142,336; required at least 4,294,967,296.
- Dedicated cache root: `/Users/crlough/Library/Caches/buoy/models/crow-plus-96ff525a7aa3bf8bfa90d77337c2b24bd45229af` only.

## What this supports or challenges

This supports successful completion of the immutable-file bootstrap operation within every approved phase 2 byte, allocation, disk, identity, public-access, and telemetry boundary. It supports that the dedicated local snapshot's complete regular-file path/size/hash set matches the exact public revision manifest.

It does not support model compatibility, construction, loading, tokenization, inference, output behavior, runtime resource use, source changes, staging, namespace access, indexing, or writes. Those operations did not occur.

## Safety and scope observation

No dependency was installed, updated, resolved, or imported from an unapproved environment. No model library, Hub library, model, or repository code was imported, constructed, loaded, or run. No model, Hub, Turbopuffer, or other runtime-service token or credential was supplied or read. No source, test, configuration, dependency, or lockfile was touched. No Turbopuffer, remote namespace, card, catalog, default, applied state, staging, indexing, delete, or write operation occurred. The model-operation network surface was limited to exact public revision metadata and its 14 exact revision files; task-required Git fetch/push and pull-request creation are repository workflow operations, not model/runtime operations.

## Limits and residual risk

Independent review is still required before this active ticket can close. The cache is verified as immutable bytes only; phase 3 remains separately approval-gated and unauthorized. Success here must not be interpreted as permission to import, construct, load, tokenize with, or run the model.
