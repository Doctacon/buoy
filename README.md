<p align="center">
  <img src="images/buoy.svg" alt="Buoy" width="160">
</p>

# Buoy

*Search that stays anchored to the source.* [![CI](https://github.com/Doctacon/buoy/actions/workflows/ci.yml/badge.svg)](https://github.com/Doctacon/buoy/actions/workflows/ci.yml) [![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Buoy turns websites, public GitHub repositories, local documents, and prepared
database tables into a Turbopuffer search index that returns relevant passages
with citations.

## Quick start

You need Python 3.11 or newer, `uv`, Git, and a
[Turbopuffer](https://turbopuffer.com/) account. Install Buoy from GitHub:

```bash
uv tool install "git+https://github.com/Doctacon/buoy.git@v0.6.4"
```

Set your Turbopuffer API key, then plan a source, apply it, and search it:

```bash
export TURBOPUFFER_API_KEY=...

buoy plan <source>
buoy apply
buoy retrieve "<question>"
```

## Learn more

- [Index a source](docs/indexing.md)
- [Retrieve with automatic routing](docs/retrieval.md)
- [Inspect local retrieval telemetry](docs/telemetry.md)
- [Evaluate search quality](docs/evaluation.md)
- [Migrate from an earlier version](docs/migrating-to-buoy.md)
- [Contribute to Buoy](CONTRIBUTING.md)
- [Release Buoy](docs/releasing.md)

Buoy is licensed under the [Apache License 2.0](LICENSE).
