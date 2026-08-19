from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
import unittest

from buoy_search.telemetry_envelope import (
    ENVELOPE_SCHEMA_VERSION,
    MAX_COUNTER,
    MAX_ENVELOPE_BYTES,
    MAX_TIMESTAMP_UNIX_US,
    NAMESPACE_QUERY_SPAN_NAME,
    OBSERVATION_SCHEMA_VERSION,
    ROOT_SPAN_NAME,
    TraceEnvelopeError,
    TraceRows,
    WIDENED_EVENT_NAME,
    _TraceRows,
    decode_trace_envelope_v1,
    encode_trace_envelope_v1,
    sanitize_attribute,
    sanitize_attributes,
    trace_rows_from_spans,
)


_TRACE_ID = "1" * 32
_ROOT_SPAN_ID = "2" * 16
_CHILD_SPAN_ID = "3" * 16
_START = datetime(2026, 8, 19, 12, 0, 0)


def _canonical(value: object, *, allow_nan: bool = False) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=allow_nan,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _attribute_json(value: dict[str, object]) -> str:
    return _canonical(value).decode("ascii")


def _valid_rows(*, widened: bool = True) -> TraceRows:
    root_attributes: dict[str, object] = {
        "buoy.observation.schema_version": 1,
        "buoy.version": "0.5.0",
        "buoy.retrieval.mode": "automatic",
        "buoy.retrieval.outcome": "success",
        "buoy.retrieval.hit_count": 2,
        "buoy.retrieval.namespace_count": 2,
        "buoy.retrieval.initial_fanout": 1,
        "buoy.retrieval.final_fanout": 2 if widened else 1,
        "buoy.retrieval.failure_count": 0,
        "buoy.retrieval.incomplete": False,
        "buoy.retrieval.widened": widened,
        "buoy.evidence.status": "supported",
        "buoy.embedding.model": "BAAI/bge-small-en-v1.5",
        "buoy.embedding.precision": "float32",
        "buoy.retrieval.top_k": 5,
        "buoy.retrieval.candidates": 10,
        "buoy.routing.selection_reason": "high_confidence_semantic",
        "buoy.routing.semantic_score": 0.75,
        "buoy.routing.semantic_margin": 0.25,
    }
    if widened:
        root_attributes["buoy.retrieval.fallback_reason"] = "weak_top1"
    run = (
        _TRACE_ID,
        _ROOT_SPAN_ID,
        _START,
        _START + timedelta(milliseconds=10),
        10.0,
        "automatic",
        "success",
        2,
        2,
        1,
        2 if widened else 1,
        0,
        False,
        widened,
        "weak_top1" if widened else None,
        "supported",
        "BAAI/bge-small-en-v1.5",
        "float32",
        5,
        10,
        "0.5.0",
        1,
    )
    spans = (
        (
            _TRACE_ID,
            _ROOT_SPAN_ID,
            None,
            ROOT_SPAN_NAME,
            _START,
            _START + timedelta(milliseconds=10),
            10.0,
            "OK",
            _attribute_json(root_attributes),
        ),
        (
            _TRACE_ID,
            _CHILD_SPAN_ID,
            _ROOT_SPAN_ID,
            NAMESPACE_QUERY_SPAN_NAME,
            _START + timedelta(milliseconds=1),
            _START + timedelta(milliseconds=2),
            1.0,
            "OK",
            _attribute_json(
                {
                    "buoy.route.rank": 1,
                    "buoy.namespace.status": "ok",
                    "buoy.namespace.hit_count": 2,
                }
            ),
        ),
    )
    events = (
        (
            _TRACE_ID,
            _ROOT_SPAN_ID,
            0,
            WIDENED_EVENT_NAME,
            _START + timedelta(milliseconds=5),
            _attribute_json(
                {
                    "buoy.retrieval.initial_fanout": 1,
                    "buoy.retrieval.final_fanout": 2,
                    "buoy.retrieval.fallback_reason": "weak_top1",
                }
            ),
        ),
    ) if widened else ()
    return TraceRows(run=run, spans=spans, events=events)


def _valid_object(*, widened: bool = True) -> dict[str, object]:
    return json.loads(encode_trace_envelope_v1(_valid_rows(widened=widened)))


def _replace_tuple_value(
    values: tuple[object, ...],
    index: int,
    value: object,
) -> tuple[object, ...]:
    changed = list(values)
    changed[index] = value
    return tuple(changed)


def _fake_context(trace_id: int, span_id: int) -> SimpleNamespace:
    return SimpleNamespace(trace_id=trace_id, span_id=span_id)


def _fake_status(name: str = "OK") -> SimpleNamespace:
    return SimpleNamespace(status_code=SimpleNamespace(name=name))


class CanonicalEnvelopeTests(unittest.TestCase):
    def assertObjectRejected(
        self,
        value: object,
        reason: str,
    ) -> None:
        with self.assertRaises(TraceEnvelopeError) as raised:
            decode_trace_envelope_v1(_canonical(value))
        self.assertEqual(raised.exception.reason, reason)
        self.assertEqual(str(raised.exception), reason)

    def test_constants_alias_and_sanitizer_are_compatible_and_bounded(self) -> None:
        self.assertIs(_TraceRows, TraceRows)
        self.assertEqual(ENVELOPE_SCHEMA_VERSION, 1)
        self.assertEqual(OBSERVATION_SCHEMA_VERSION, 1)
        self.assertEqual(
            sanitize_attributes(
                {
                    "buoy.retrieval.hit_count": MAX_COUNTER,
                    "buoy.routing.semantic_score": 1,
                    "buoy.route.rank": 1,
                    "query.text": "PRIVATE_QUERY_SENTINEL",
                }
            ),
            {
                "buoy.retrieval.hit_count": MAX_COUNTER,
                "buoy.routing.semantic_score": 1.0,
                "buoy.route.rank": 1,
            },
        )
        for key, value in (
            ("buoy.retrieval.hit_count", True),
            ("buoy.retrieval.hit_count", MAX_COUNTER + 1),
            ("buoy.route.rank", 0),
            ("buoy.routing.semantic_score", float("nan")),
            ("buoy.routing.semantic_score", float("inf")),
            ("buoy.version", "bad/version"),
            ("buoy.reranker.revision", "A" * 40),
            ("unknown", "PRIVATE_SENTINEL"),
        ):
            with self.subTest(key=key, value=value):
                self.assertIsNone(sanitize_attribute(key, value))

    def test_round_trip_is_exact_canonical_ascii_and_naive_utc_rows(self) -> None:
        rows = _valid_rows()

        payload = encode_trace_envelope_v1(rows)
        decoded = decode_trace_envelope_v1(payload)

        self.assertLessEqual(len(payload), MAX_ENVELOPE_BYTES)
        self.assertEqual(payload, _canonical(json.loads(payload)))
        self.assertFalse(payload.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(payload.endswith(b"\n"))
        payload.decode("ascii")
        self.assertEqual(decoded, rows)
        self.assertIsNone(decoded.run[2].tzinfo)
        self.assertEqual(encode_trace_envelope_v1(decoded), payload)

    def test_row_attributes_must_already_be_canonical_json_objects(self) -> None:
        rows = _valid_rows()
        root = _replace_tuple_value(
            rows.spans[0],
            8,
            json.dumps(json.loads(rows.spans[0][8]), sort_keys=True),
        )
        changed = TraceRows(
            run=rows.run,
            spans=(root, *rows.spans[1:]),
            events=rows.events,
        )

        with self.assertRaises(TraceEnvelopeError) as raised:
            encode_trace_envelope_v1(changed)
        self.assertEqual(raised.exception.reason, "invalid_value")

    def test_rows_require_exact_tuple_shapes_and_naive_datetimes(self) -> None:
        rows = _valid_rows()
        cases = (
            TraceRows(run=rows.run[:-1], spans=rows.spans, events=rows.events),
            TraceRows(run=list(rows.run), spans=rows.spans, events=rows.events),
            TraceRows(run=rows.run, spans=list(rows.spans), events=rows.events),
            TraceRows(
                run=_replace_tuple_value(
                    rows.run,
                    2,
                    rows.run[2].replace(tzinfo=timezone.utc),
                ),
                spans=rows.spans,
                events=rows.events,
            ),
        )
        for changed in cases:
            with self.subTest(changed=changed):
                with self.assertRaises(TraceEnvelopeError):
                    encode_trace_envelope_v1(changed)

    def test_exact_maximum_timestamp_round_trips(self) -> None:
        instant = datetime.max
        root_attributes = {
            "buoy.observation.schema_version": 1,
            "buoy.version": "0.5.0",
            "buoy.retrieval.mode": "explicit_single",
            "buoy.retrieval.outcome": "success",
            "buoy.retrieval.hit_count": 0,
            "buoy.retrieval.namespace_count": 0,
            "buoy.retrieval.initial_fanout": 0,
            "buoy.retrieval.final_fanout": 0,
            "buoy.retrieval.failure_count": 0,
            "buoy.retrieval.incomplete": False,
            "buoy.retrieval.widened": False,
            "buoy.embedding.model": "custom",
            "buoy.embedding.precision": "custom",
            "buoy.retrieval.top_k": 0,
            "buoy.retrieval.candidates": 0,
        }
        run = (
            _TRACE_ID,
            _ROOT_SPAN_ID,
            instant,
            instant,
            0.0,
            "explicit_single",
            "success",
            0,
            0,
            0,
            0,
            0,
            False,
            False,
            None,
            None,
            "custom",
            "custom",
            0,
            0,
            "0.5.0",
            1,
        )
        root = (
            _TRACE_ID,
            _ROOT_SPAN_ID,
            None,
            ROOT_SPAN_NAME,
            instant,
            instant,
            0.0,
            "OK",
            _attribute_json(root_attributes),
        )
        rows = TraceRows(run=run, spans=(root,), events=())

        decoded = decode_trace_envelope_v1(encode_trace_envelope_v1(rows))

        self.assertEqual(decoded.run[2], instant)
        self.assertEqual(
            json.loads(encode_trace_envelope_v1(rows))["run"][
                "started_at_unix_us"
            ],
            MAX_TIMESTAMP_UNIX_US,
        )

    def test_encoder_enforces_the_global_byte_bound(self) -> None:
        rows = _valid_rows()
        child_attributes = _attribute_json(
            {
                "buoy.rerank.applied": True,
                "buoy.rerank.candidates_before_dedupe": MAX_COUNTER,
                "buoy.rerank.candidates_after_dedupe": MAX_COUNTER,
                "buoy.reranker.model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
                "buoy.reranker.revision": "a" * 40,
                "buoy.error.type": "unexpected_error",
            }
        )
        children = tuple(
            (
                _TRACE_ID,
                f"{index:016x}",
                _ROOT_SPAN_ID,
                "buoy.rerank",
                _START + timedelta(milliseconds=1),
                _START + timedelta(milliseconds=2),
                1.0,
                "ERROR",
                child_attributes,
            )
            for index in range(1, 256)
        )
        oversized = TraceRows(
            run=rows.run,
            spans=(rows.spans[0], *children),
            events=rows.events,
        )

        with self.assertRaises(TraceEnvelopeError) as raised:
            encode_trace_envelope_v1(oversized)
        self.assertEqual(raised.exception.reason, "oversized")

    def test_decoder_rejects_oversized_before_parsing(self) -> None:
        with self.assertRaises(TraceEnvelopeError) as raised:
            decode_trace_envelope_v1(b"x" * (MAX_ENVELOPE_BYTES + 1))
        self.assertEqual(raised.exception.reason, "oversized")

    def test_invalid_utf8_is_distinct_and_content_free(self) -> None:
        sentinel = b"PRIVATE_SENTINEL\xff"
        with self.assertRaises(TraceEnvelopeError) as raised:
            decode_trace_envelope_v1(sentinel)
        self.assertEqual(raised.exception.reason, "invalid_utf8")
        self.assertNotIn("PRIVATE_SENTINEL", str(raised.exception))

    def test_bom_trailing_data_and_malformed_json_are_rejected(self) -> None:
        payload = encode_trace_envelope_v1(_valid_rows())
        for changed in (
            b"\xef\xbb\xbf" + payload,
            payload + b"\n",
            payload + b"{}",
            payload[:-1],
        ):
            with self.subTest(changed=changed[-8:]):
                with self.assertRaises(TraceEnvelopeError) as raised:
                    decode_trace_envelope_v1(changed)
                self.assertIn(
                    raised.exception.reason,
                    {"invalid_json", "noncanonical_json"},
                )

    def test_duplicate_keys_are_rejected_at_every_object_depth(self) -> None:
        payload = encode_trace_envelope_v1(_valid_rows())
        top_duplicate = payload.replace(
            b'{"envelope_schema_version":1,',
            b'{"envelope_schema_version":1,"envelope_schema_version":1,',
            1,
        )
        nested_duplicate = payload.replace(
            b'"duration_ms":10.0,',
            b'"duration_ms":10.0,"duration_ms":10.0,',
            1,
        )
        for changed in (top_duplicate, nested_duplicate):
            with self.subTest(changed=changed[:80]):
                with self.assertRaises(TraceEnvelopeError) as raised:
                    decode_trace_envelope_v1(changed)
                self.assertEqual(raised.exception.reason, "invalid_json")

    def test_nan_and_infinities_are_rejected(self) -> None:
        value = _valid_object()
        run = value["run"]
        assert isinstance(run, dict)
        for nonfinite in (float("nan"), float("inf"), float("-inf")):
            changed = deepcopy(value)
            changed_run = changed["run"]
            assert isinstance(changed_run, dict)
            changed_run["duration_ms"] = nonfinite
            with self.subTest(nonfinite=nonfinite):
                with self.assertRaises(TraceEnvelopeError) as raised:
                    decode_trace_envelope_v1(
                        _canonical(changed, allow_nan=True)
                    )
                self.assertEqual(raised.exception.reason, "invalid_value")

    def test_huge_integer_and_exponent_are_bounded_before_materialization(self) -> None:
        payload = encode_trace_envelope_v1(_valid_rows())
        huge_integer = payload.replace(
            b'"duration_ms":10.0',
            b'"duration_ms":' + (b"9" * 5_000),
            1,
        )
        huge_exponent = payload.replace(
            b'"duration_ms":10.0',
            b'"duration_ms":1e309',
            1,
        )
        for changed in (huge_integer, huge_exponent):
            with self.subTest(size=len(changed)):
                with self.assertRaises(TraceEnvelopeError) as raised:
                    decode_trace_envelope_v1(changed)
                self.assertEqual(raised.exception.reason, "invalid_value")

    def test_noncanonical_whitespace_and_key_order_are_rejected(self) -> None:
        value = _valid_object()
        pretty = json.dumps(value, indent=2, sort_keys=True).encode("utf-8")
        reversed_value = dict(reversed(tuple(value.items())))
        insertion_order = json.dumps(
            reversed_value,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
        self.assertNotEqual(insertion_order, _canonical(value))
        for changed in (b" " + _canonical(value), pretty, insertion_order):
            with self.subTest(changed=changed[:40]):
                with self.assertRaises(TraceEnvelopeError) as raised:
                    decode_trace_envelope_v1(changed)
                self.assertEqual(raised.exception.reason, "noncanonical_json")


class EnvelopeShapeAndValueTests(unittest.TestCase):
    def assertObjectRejected(
        self,
        value: object,
        reason: str,
    ) -> None:
        with self.assertRaises(TraceEnvelopeError) as raised:
            decode_trace_envelope_v1(_canonical(value))
        self.assertEqual(raised.exception.reason, reason)

    def test_top_level_and_record_keys_are_exact(self) -> None:
        value = _valid_object()
        cases: list[tuple[object, str]] = []
        missing_top = deepcopy(value)
        missing_top.pop("events")
        cases.append((missing_top, "invalid_shape"))
        unknown_top = deepcopy(value)
        unknown_top["payload"] = "PRIVATE_SENTINEL"
        cases.append((unknown_top, "invalid_shape"))
        missing_run = deepcopy(value)
        missing_run["run"].pop("outcome")
        cases.append((missing_run, "invalid_shape"))
        unknown_span = deepcopy(value)
        unknown_span["spans"][0]["resource"] = "PRIVATE_SENTINEL"
        cases.append((unknown_span, "invalid_shape"))
        unknown_event = deepcopy(value)
        unknown_event["events"][0]["message"] = "PRIVATE_SENTINEL"
        cases.append((unknown_event, "invalid_shape"))
        for changed, reason in cases:
            with self.subTest(reason=reason):
                self.assertObjectRejected(changed, reason)

    def test_versions_are_exact_and_booleans_never_satisfy_integers(self) -> None:
        wrong_envelope = _valid_object()
        wrong_envelope["envelope_schema_version"] = 2
        self.assertObjectRejected(wrong_envelope, "unsupported_envelope_version")

        for location, key, value in (
            ("top", "observation_schema_version", True),
            ("run", "observation_schema_version", 2),
            ("run", "hit_count", True),
            ("run", "started_at_unix_us", True),
        ):
            changed = _valid_object()
            target = changed if location == "top" else changed[location]
            target[key] = value
            with self.subTest(location=location, key=key):
                self.assertObjectRejected(changed, "invalid_value")

    def test_scalar_types_enums_and_numeric_bounds_are_exact(self) -> None:
        mutations = (
            ("retrieval_mode", 1),
            ("retrieval_mode", "AUTO"),
            ("hit_count", -1),
            ("hit_count", MAX_COUNTER + 1),
            ("started_at_unix_us", -1),
            ("ended_at_unix_us", MAX_TIMESTAMP_UNIX_US + 1),
            ("duration_ms", -0.01),
            ("buoy_version", "bad/version"),
        )
        for key, invalid in mutations:
            changed = _valid_object()
            changed["run"][key] = invalid
            with self.subTest(key=key, invalid=invalid):
                self.assertObjectRejected(changed, "invalid_value")

    def test_ids_are_lowercase_fixed_width_and_nonzero(self) -> None:
        for key, invalid in (
            ("trace_id", "0" * 32),
            ("trace_id", "A" * 32),
            ("trace_id", "1" * 31),
            ("root_span_id", "0" * 16),
            ("root_span_id", "2" * 17),
        ):
            changed = _valid_object()
            changed["run"][key] = invalid
            with self.subTest(key=key, invalid=invalid):
                self.assertObjectRejected(changed, "invalid_value")

    def test_span_and_event_collection_bounds_are_exact(self) -> None:
        no_spans = _valid_object()
        no_spans["spans"] = []
        self.assertObjectRejected(no_spans, "invalid_shape")

        too_many_spans = _valid_object()
        too_many_spans["spans"] = [
            deepcopy(too_many_spans["spans"][0]) for _ in range(257)
        ]
        # The byte bound is checked before parsing/shape validation, and this
        # exact-shape 257-span payload necessarily crosses that tighter bound.
        self.assertObjectRejected(too_many_spans, "oversized")

        too_many_events = _valid_object()
        too_many_events["events"].append(deepcopy(too_many_events["events"][0]))
        self.assertObjectRejected(too_many_events, "invalid_shape")

    def test_span_specific_attribute_allowlists_reject_forgery(self) -> None:
        cases = []
        root_unknown = _valid_object()
        root_unknown["spans"][0]["attributes"]["query.text"] = (
            "PRIVATE_QUERY_SENTINEL"
        )
        cases.append((root_unknown, "invalid_shape"))
        child_root_key = _valid_object()
        child_root_key["spans"][1]["attributes"]["buoy.retrieval.mode"] = (
            "automatic"
        )
        cases.append((child_root_key, "invalid_shape"))
        nested = _valid_object()
        nested["spans"][1]["attributes"]["buoy.route.rank"] = [1]
        cases.append((nested, "invalid_value"))
        for changed, reason in cases:
            with self.subTest(changed=changed["spans"][1]["attributes"]):
                self.assertObjectRejected(changed, reason)

        excessive = _valid_object()
        excessive["spans"][0]["attributes"] = {
            f"private_{index}": index for index in range(65)
        }
        self.assertObjectRejected(excessive, "invalid_shape")

    def test_event_attributes_are_exact_and_governed(self) -> None:
        missing = _valid_object()
        missing["events"][0]["attributes"].pop(
            "buoy.retrieval.fallback_reason"
        )
        self.assertObjectRejected(missing, "invalid_shape")

        extra = _valid_object()
        extra["events"][0]["attributes"]["query"] = "PRIVATE_SENTINEL"
        self.assertObjectRejected(extra, "invalid_shape")

        invalid = _valid_object()
        invalid["events"][0]["attributes"][
            "buoy.retrieval.fallback_reason"
        ] = "PRIVATE_SENTINEL"
        self.assertObjectRejected(invalid, "invalid_value")

    def test_status_event_index_and_attribute_values_are_exact(self) -> None:
        cases = []
        status = _valid_object()
        status["spans"][0]["status_code"] = "SUCCESS"
        cases.append(status)
        index = _valid_object()
        index["events"][0]["event_index"] = True
        cases.append(index)
        rank = _valid_object()
        rank["spans"][1]["attributes"]["buoy.route.rank"] = 0
        cases.append(rank)
        for changed in cases:
            with self.subTest(changed=changed):
                self.assertObjectRejected(changed, "invalid_value")


class EnvelopeGraphTests(unittest.TestCase):
    def assertGraphRejected(self, value: object) -> None:
        with self.assertRaises(TraceEnvelopeError) as raised:
            decode_trace_envelope_v1(_canonical(value))
        self.assertEqual(raised.exception.reason, "invalid_graph")

    def test_root_and_direct_child_graph_is_exact(self) -> None:
        cases = []
        duplicate = _valid_object()
        duplicate["spans"][1]["span_id"] = _ROOT_SPAN_ID
        cases.append(duplicate)
        second_root = _valid_object()
        second_root["spans"][1]["name"] = ROOT_SPAN_NAME
        second_root["spans"][1]["parent_span_id"] = None
        second_root["spans"][1]["attributes"] = deepcopy(
            second_root["spans"][0]["attributes"]
        )
        cases.append(second_root)
        wrong_parent = _valid_object()
        wrong_parent["spans"][1]["parent_span_id"] = "4" * 16
        cases.append(wrong_parent)
        wrong_trace = _valid_object()
        wrong_trace["spans"][1]["trace_id"] = "5" * 32
        cases.append(wrong_trace)
        wrong_root = _valid_object()
        wrong_root["run"]["root_span_id"] = "6" * 16
        cases.append(wrong_root)
        for changed in cases:
            with self.subTest(changed=changed):
                self.assertGraphRejected(changed)

    def test_spans_and_events_must_be_in_canonical_order(self) -> None:
        changed = _valid_object()
        changed["spans"] = list(reversed(changed["spans"]))
        self.assertGraphRejected(changed)

    def test_timestamps_are_nested_and_durations_agree(self) -> None:
        before_root = _valid_object()
        before_root["spans"][1]["started_at_unix_us"] = (
            before_root["run"]["started_at_unix_us"] - 1
        )
        self.assertGraphRejected(before_root)

        after_root = _valid_object()
        after_root["events"][0]["occurred_at_unix_us"] = (
            after_root["run"]["ended_at_unix_us"] + 1
        )
        self.assertGraphRejected(after_root)

        duration = _valid_object()
        duration["spans"][1]["duration_ms"] = 1.002
        self.assertGraphRejected(duration)

        run_duration = _valid_object()
        run_duration["run"]["duration_ms"] = 10.002
        run_duration["spans"][0]["duration_ms"] = 10.002
        self.assertGraphRejected(run_duration)

    def test_run_timing_and_every_summary_must_equal_the_root(self) -> None:
        timing = _valid_object()
        timing["run"]["started_at_unix_us"] += 1
        self.assertGraphRejected(timing)

        summary = _valid_object()
        summary["run"]["hit_count"] = 1
        self.assertGraphRejected(summary)

        optional_absent = _valid_object(widened=False)
        optional_absent["spans"][0]["attributes"][
            "buoy.retrieval.fallback_reason"
        ] = "weak_top1"
        self.assertGraphRejected(optional_absent)

        required_absent = _valid_object()
        required_absent["spans"][0]["attributes"].pop(
            "buoy.embedding.precision"
        )
        self.assertGraphRejected(required_absent)

    def test_widening_event_ownership_and_summary_are_exact(self) -> None:
        missing = _valid_object()
        missing["events"] = []
        self.assertGraphRejected(missing)

        unexpected = _valid_object(widened=False)
        unexpected["events"] = deepcopy(_valid_object()["events"])
        self.assertGraphRejected(unexpected)

        wrong_owner = _valid_object()
        wrong_owner["events"][0]["span_id"] = _CHILD_SPAN_ID
        self.assertGraphRejected(wrong_owner)

        mismatch = _valid_object()
        mismatch["events"][0]["attributes"][
            "buoy.retrieval.final_fanout"
        ] = 1
        self.assertGraphRejected(mismatch)

    def test_incomplete_and_fanout_relationships_are_exact(self) -> None:
        incomplete = _valid_object()
        incomplete["run"]["failure_count"] = 1
        incomplete["spans"][0]["attributes"][
            "buoy.retrieval.failure_count"
        ] = 1
        self.assertGraphRejected(incomplete)

        final_too_large = _valid_object()
        final_too_large["run"]["namespace_count"] = 1
        final_too_large["spans"][0]["attributes"][
            "buoy.retrieval.namespace_count"
        ] = 1
        self.assertGraphRejected(final_too_large)

        failures_too_large = _valid_object(widened=False)
        failures_too_large["run"]["failure_count"] = 2
        failures_too_large["run"]["incomplete"] = True
        failures_too_large["spans"][0]["attributes"].update(
            {
                "buoy.retrieval.failure_count": 2,
                "buoy.retrieval.incomplete": True,
            }
        )
        self.assertGraphRejected(failures_too_large)


class SpanConversionPrivacyTests(unittest.TestCase):
    def test_span_conversion_discards_ambient_and_prohibited_data(self) -> None:
        sentinel = "PRIVATE_QUERY_PATH_CREDENTIAL_SENTINEL"
        trace_id = int(_TRACE_ID, 16)
        root_span_id = int(_ROOT_SPAN_ID, 16)
        child_span_id = int(_CHILD_SPAN_ID, 16)
        start_ns = 1_700_000_000_000_000_000
        end_ns = start_ns + 10_000_000
        root_attributes = {
            "buoy.observation.schema_version": 1,
            "buoy.version": "0.5.0",
            "buoy.retrieval.mode": "automatic",
            "buoy.retrieval.outcome": "success",
            "buoy.retrieval.hit_count": 2,
            "buoy.retrieval.namespace_count": 2,
            "buoy.retrieval.initial_fanout": 1,
            "buoy.retrieval.final_fanout": 2,
            "buoy.retrieval.failure_count": 0,
            "buoy.retrieval.incomplete": False,
            "buoy.retrieval.widened": True,
            "buoy.retrieval.fallback_reason": "weak_top1",
            "buoy.evidence.status": "supported",
            "buoy.embedding.model": "BAAI/bge-small-en-v1.5",
            "buoy.embedding.precision": "float32",
            "buoy.retrieval.top_k": 5,
            "buoy.retrieval.candidates": 10,
            "query.text": sentinel,
            "process.command_args": sentinel,
            "api_key": sentinel,
            "path": sentinel,
        }
        unknown_event = SimpleNamespace(
            name="exception",
            timestamp=start_ns + 2_000_000,
            attributes={"exception.message": sentinel},
        )
        widened_event = SimpleNamespace(
            name=WIDENED_EVENT_NAME,
            timestamp=start_ns + 5_000_000,
            attributes={
                "buoy.retrieval.initial_fanout": 1,
                "buoy.retrieval.final_fanout": 2,
                "buoy.retrieval.fallback_reason": "weak_top1",
                "query": sentinel,
            },
        )
        root = SimpleNamespace(
            name=ROOT_SPAN_NAME,
            context=_fake_context(trace_id, root_span_id),
            parent=None,
            start_time=start_ns,
            end_time=end_ns,
            status=_fake_status(),
            attributes=root_attributes,
            events=(unknown_event, widened_event),
            resource={"process.command_args": sentinel},
            instrumentation_scope=SimpleNamespace(name=sentinel),
            links=(SimpleNamespace(attributes={"query": sentinel}),),
        )
        child = SimpleNamespace(
            name=NAMESPACE_QUERY_SPAN_NAME,
            context=_fake_context(trace_id, child_span_id),
            parent=_fake_context(trace_id, root_span_id),
            start_time=start_ns + 1_000_000,
            end_time=start_ns + 2_000_000,
            status=_fake_status(),
            attributes={
                "buoy.route.rank": 1,
                "buoy.namespace.status": "ok",
                "buoy.namespace.hit_count": 2,
                "buoy.retrieval.mode": "automatic",
                "namespace": sentinel,
            },
            events=(),
        )
        ambient = SimpleNamespace(
            name=NAMESPACE_QUERY_SPAN_NAME,
            context=_fake_context(int("4" * 32, 16), int("5" * 16, 16)),
            parent=_fake_context(int("4" * 32, 16), int("6" * 16, 16)),
            start_time=start_ns,
            end_time=end_ns,
            status=_fake_status(),
            attributes={"query": sentinel},
            events=(),
        )
        prohibited_name = SimpleNamespace(
            name=sentinel,
            context=_fake_context(trace_id, int("7" * 16, 16)),
            parent=_fake_context(trace_id, root_span_id),
            start_time=start_ns,
            end_time=end_ns,
            status=_fake_status(),
            attributes={"query": sentinel},
            events=(),
        )

        rows = trace_rows_from_spans(
            (ambient, child, prohibited_name, root),
            root_span_id=root_span_id,
        )
        payload = encode_trace_envelope_v1(rows)

        self.assertNotIn(sentinel.encode("ascii"), payload)
        self.assertEqual(len(rows.spans), 2)
        self.assertEqual(rows.spans[0][3], ROOT_SPAN_NAME)
        self.assertEqual(rows.events[0][2], 0)
        child_attributes = json.loads(rows.spans[1][8])
        self.assertNotIn("buoy.retrieval.mode", child_attributes)
        self.assertEqual(
            set(child_attributes),
            {
                "buoy.route.rank",
                "buoy.namespace.status",
                "buoy.namespace.hit_count",
            },
        )

    def test_decoder_rejects_forged_private_values_instead_of_sanitizing(self) -> None:
        sentinel = "PRIVATE_CONTENT_SENTINEL"
        forged = _valid_object()
        forged["spans"][0]["attributes"]["content"] = sentinel
        payload = _canonical(forged)
        self.assertIn(sentinel.encode("ascii"), payload)

        with self.assertRaises(TraceEnvelopeError) as raised:
            decode_trace_envelope_v1(payload)

        self.assertEqual(raised.exception.reason, "invalid_shape")
        self.assertNotIn(sentinel, str(raised.exception))

    def test_conversion_rejects_invalid_trace_graph_after_sanitizing(self) -> None:
        rows = _valid_rows()
        root_attributes = json.loads(rows.spans[0][8])
        root_attributes.pop("buoy.retrieval.outcome")
        root = _replace_tuple_value(
            rows.spans[0],
            8,
            _attribute_json(root_attributes),
        )
        invalid = TraceRows(
            run=rows.run,
            spans=(root, *rows.spans[1:]),
            events=rows.events,
        )

        with self.assertRaises(TraceEnvelopeError) as raised:
            encode_trace_envelope_v1(invalid)

        self.assertEqual(raised.exception.reason, "invalid_graph")


if __name__ == "__main__":
    unittest.main()
