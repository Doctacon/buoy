import hashlib
import json
from importlib.resources import files
from buoy_search.indexing.treatment_token_budget import exact_token_count, load_pinned_tokenizer
from buoy_search.evals.routing_quality import (
    DEFAULT_ROUTING_CALIBRATION,
    DEFAULT_ROUTING_CANARY_DIR,
    load_routing_confidence_calibration,
    load_routing_quality_dataset,
)

assert exact_token_count(load_pinned_tokenizer(), "Buoy release tokenizer smoke.") == 9
expected = {
    "rentptr.json": "5a39c38d302cbc5c6d758b1e48d4456456a4357248f559a6cf56e0234742f4f5",
    "salesforce.json": "32106e02d877788e676cdb3db3f7a3567f57f96fa009a7a558b82ca1d407d13d",
    "whiteboxgeo.json": "5558a4e8a786f0a5553ba0237ebf8248a5d576bd1937ffd69cf9af66a8ac0916",
}
assert tuple(sorted(path.name for path in DEFAULT_ROUTING_CANARY_DIR.iterdir())) == tuple(sorted(expected))
assert {
    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
    for path in DEFAULT_ROUTING_CANARY_DIR.iterdir()
} == expected
dataset = load_routing_quality_dataset()
assert len(dataset.cases) == 65
assert dataset.suite_sha256 == "0e648b1222298b443439aa8b85527048b54f51b7ef2518956d43cd6bee2981e5"
authority = load_routing_confidence_calibration()
assert authority.mode in {"collect", "active"}
assert authority.mode == json.loads(DEFAULT_ROUTING_CALIBRATION.read_bytes())["mode"]
promotion_baskets = json.loads(
    files("buoy_search").joinpath("data/repo_ranking_promotion_baskets.json").read_bytes()
)
assert promotion_baskets == {"baskets": [], "schema_version": 1}
if authority.mode == "active":
    assert authority.owner_approved is True
    assert authority.certification_passed is True
    assert authority.receipts is not None
