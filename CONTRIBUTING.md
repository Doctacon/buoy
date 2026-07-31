# Contributing

Buoy's boundary is one source to one reviewed Turbopuffer index. Keep
cross-source catalog, routing, evidence, ontology, and operator-console work in
[Kite](https://github.com/Doctacon/kite).

Use Python 3.11 or newer and the locked environment:

```bash
uv sync --locked --python 3.13
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate_ranking_contract.py
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/c6_syntax_forecast.py validate
uv lock --check
```

Keep changes narrow and update the document that owns any changed user
contract. Preserve plan, row-ID, namespace, and DuckDB state compatibility
unless a reviewed migration explicitly changes them.

Development work starts on `work/*` from current `develop`, passes independent
review and evidence gates, and enters `develop` and `main` only through their
protected pull-request workflows. Do not self-merge.

Never commit credentials, generated `_version.py`, build output, local state, or
plan artifacts. Provider mutation and release publication require separately
approved work.
