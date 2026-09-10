Status: active
Created: 2026-08-29
Updated: 2026-09-10

# Reproducible Installed-Wheel Evidence Binds Version, Lock, and Cleanup

A one-time successful wheel lifecycle is not durably reproducible when package identity comes from calendar-sensitive VCS metadata or dependencies resolve from ambient cache contents.

A replayable provider-free installed-wheel validation should:

1. set and assert the distribution-specific setuptools-scm/Hatch VCS version override;
2. set and assert a fixed `SOURCE_DATE_EPOCH`, UTC, locale, and Python hash seed;
3. assert the exact lockfile and package-manager identities;
4. export the frozen runtime graph from the lock with hashes;
5. synchronize exact dependencies offline with required hashes;
6. install the exact local wheel offline with `--no-index --no-deps`;
7. assert the complete installed package/runtime identity;
8. build twice under identical controls and compare artifact bytes/hashes;
9. retain only bounded privacy-safe lifecycle facts; and
10. verify zero process survivors, remove every temporary root, and execute literal absence checks.

An offline cache is transport only. Missing hash-matching artifacts should fail closed; cache contents must not choose versions or package identity.

## Editable metadata is not wheel identity

A reused uv editable environment can retain earlier VCS version/dependency
metadata after the source checkout changes. Source imports/help passing do not
prove that installed metadata reflects the current commit or optional pin.
Inspect both; refresh the project installation if source-command verification
requires current metadata. Do not reinterpret stale metadata as an application
regression or use that environment as clean-wheel evidence.

Final installed acceptance must separately identify a non-editable wheel origin,
installed package/module/protocol versions, artifact digest, and packaged bytes.
Bind the tested artifact to its source commit, not to a later record-only commit
whose VCS-derived version would differ. The MCP investigation demonstrates this
separation in `.10x/evidence/2026-09-10-buoy-mcp-installation.md`; its retained-byte
validation does not claim deterministic rebuilding of the artifact.
