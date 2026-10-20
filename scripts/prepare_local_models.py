#!/usr/bin/env python3
"""Compatibility wrapper; prefer ``buoy setup --download-models`` after install.

For a transferable cache on a connected staging machine:
    python scripts/prepare_local_models.py --download --cache-dir ./hf-cache
"""

from buoy_search.cli.setup import main

if __name__ == "__main__":
    raise SystemExit(main())
