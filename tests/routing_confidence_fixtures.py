from __future__ import annotations

import json
from pathlib import Path
import tempfile

from buoy_search.catalog import ROUTING_MODEL, ROUTING_MODEL_REVISION
from buoy_search.cross_encoder import CROSS_ENCODER_MODEL, CROSS_ENCODER_REVISION
from buoy_search.routing_quality import (
    ROUTING_CALIBRATION_ID,
    ROUTING_CALIBRATION_SCHEMA_VERSION,
    ROUTING_COLLECT_CALIBRATION_REVISION,
    ROUTING_CONFIDENCE_FEATURE_CONTRACT,
    ROUTING_CONFIDENCE_MARGIN_FIELD,
    ROUTING_CONFIDENCE_SCORE_FIELD,
    ROUTING_MAX_EXAMPLES,
    ROUTING_PROJECTION_CONTRACT,
    ROUTING_SCHEMA_CONTRACT,
    ROUTING_SHORTLIST_LIMIT,
    RoutingConfidenceCalibration,
    load_routing_confidence_calibration,
)


def collect_calibration_payload() -> dict[str, object]:
    return {
        "schema_version": ROUTING_CALIBRATION_SCHEMA_VERSION,
        "calibration_id": ROUTING_CALIBRATION_ID,
        "calibration_revision": ROUTING_COLLECT_CALIBRATION_REVISION,
        "mode": "collect",
        "owner_approved": False,
        "score_floor": None,
        "margin_floor": None,
        "bindings": {
            "routing_model": ROUTING_MODEL,
            "routing_model_revision": ROUTING_MODEL_REVISION,
            "routing_reranker_model": CROSS_ENCODER_MODEL,
            "routing_reranker_revision": CROSS_ENCODER_REVISION,
            "schema_contract": ROUTING_SCHEMA_CONTRACT,
            "projection": ROUTING_PROJECTION_CONTRACT,
            "shortlist_limit": ROUTING_SHORTLIST_LIMIT,
            "max_examples": ROUTING_MAX_EXAMPLES,
            "feature_contract": ROUTING_CONFIDENCE_FEATURE_CONTRACT,
            "score_field": ROUTING_CONFIDENCE_SCORE_FIELD,
            "margin_field": ROUTING_CONFIDENCE_MARGIN_FIELD,
            "canary_suite_sha256": None,
            "catalog_projection_sha256": None,
        },
        "certification": {
            "passed": False,
            "case_count": 0,
            "verdict_sha256": None,
        },
    }


def load_collect_routing_confidence_fixture() -> RoutingConfidenceCalibration:
    """Load schema-v1 collect authority through test-only path injection."""

    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "collect-calibration.json"
        path.write_text(json.dumps(collect_calibration_payload()), encoding="utf-8")
        return load_routing_confidence_calibration(path)
