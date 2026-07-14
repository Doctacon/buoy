"""Lightweight retrieval smoke/eval harness for configured site namespaces."""

from __future__ import annotations

from dataclasses import dataclass
import json
from math import log2
from pathlib import Path
from typing import Mapping, Sequence
from urllib.parse import unquote, urlparse

from buoy_search.config import RuntimeConfig
from buoy_search.retriever import HybridRetriever, RetrievalOptions, SearchHit

DEFAULT_EVAL_DATASET = Path(__file__).with_name("data") / "scrapling_retrieval_smoke_evals.json"
NDCG_K = 10
RECALL_K = 10
MRR_K = 10
PRECISION_K = 5
REPO_SEARCH_SCORE_WEIGHTS = {
    "ndcg_at_10": 0.55,
    "recall_at_10": 0.20,
    "mrr_at_10": 0.15,
    "precision_at_5": 0.10,
}


@dataclass(frozen=True)
class EvalJudgment:
    """One graded source relevance judgment for repository retrieval evals."""

    grade: int
    repo_path: str | None = None
    url: str | None = None
    section_path: str | None = None
    reason: str | None = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object], *, case_id: str) -> "EvalJudgment":
        grade = payload.get("grade")
        if isinstance(grade, bool) or not isinstance(grade, int) or grade < 0 or grade > 3:
            raise ValueError(f"Eval case {case_id!r} has a judgment with invalid grade; expected integer 0..3.")
        repo_path = optional_string(payload, "repo_path", case_id=case_id)
        url = optional_string(payload, "url", case_id=case_id)
        section_path = optional_string(payload, "section_path", case_id=case_id)
        reason = optional_string(payload, "reason", case_id=case_id)
        if not repo_path and not url:
            raise ValueError(f"Eval case {case_id!r} has a judgment without repo_path or url.")
        return cls(
            grade=grade,
            repo_path=repo_path,
            url=url,
            section_path=section_path,
            reason=reason,
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"grade": self.grade}
        if self.repo_path:
            payload["repo_path"] = self.repo_path
        if self.url:
            payload["url"] = self.url
        if self.section_path:
            payload["section_path"] = self.section_path
        if self.reason:
            payload["reason"] = self.reason
        return payload


@dataclass(frozen=True)
class EvalCase:
    """One hand-authored retrieval smoke question and expected source hints."""

    id: str
    question: str
    expected_urls: tuple[str, ...]
    expected_topics: tuple[str, ...]
    judgments: tuple[EvalJudgment, ...] = ()

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> "EvalCase":
        expected_urls = payload.get("expected_urls") or []
        expected_topics = payload.get("expected_topics") or []
        judgments_payload = payload.get("judgments") or []
        if not isinstance(payload.get("id"), str) or not isinstance(payload.get("question"), str):
            raise ValueError("Eval cases must include string id and question fields.")
        case_id = str(payload["id"])
        if not isinstance(expected_urls, list) or not all(isinstance(value, str) for value in expected_urls):
            raise ValueError(f"Eval case {case_id!r} has invalid expected_urls.")
        if not isinstance(expected_topics, list) or not all(isinstance(value, str) for value in expected_topics):
            raise ValueError(f"Eval case {case_id!r} has invalid expected_topics.")
        if not isinstance(judgments_payload, list):
            raise ValueError(f"Eval case {case_id!r} has invalid judgments; expected a list.")
        if not all(isinstance(value, Mapping) for value in judgments_payload):
            raise ValueError(f"Eval case {case_id!r} has invalid judgments; every judgment must be an object.")
        judgments = tuple(EvalJudgment.from_mapping(value, case_id=case_id) for value in judgments_payload)
        if not expected_urls and not expected_topics and not judgments:
            raise ValueError(f"Eval case {case_id!r} must include expected hints or graded judgments.")
        return cls(
            id=case_id,
            question=str(payload["question"]),
            expected_urls=tuple(expected_urls),
            expected_topics=tuple(expected_topics),
            judgments=judgments,
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "question": self.question,
            "expected_urls": list(self.expected_urls),
            "expected_topics": list(self.expected_topics),
        }
        if self.judgments:
            payload["judgments"] = [judgment.to_dict() for judgment in self.judgments]
        return payload


@dataclass(frozen=True)
class EvalScore:
    """Scoring result for one legacy eval case."""

    passed: bool
    matched_url: str | None = None
    matched_topic: str | None = None
    matched_rank: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "matched_url": self.matched_url,
            "matched_topic": self.matched_topic,
            "matched_rank": self.matched_rank,
        }


@dataclass(frozen=True)
class RepoEvalScore:
    """Composite graded repository retrieval score for one eval case."""

    ndcg_at_10: float
    recall_at_10: float
    mrr_at_10: float
    precision_at_5: float
    repo_search_score: float
    matched_rank: int | None
    matched_judgments: tuple[dict[str, object], ...]

    @property
    def passed(self) -> bool:
        return self.matched_rank is not None

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "matched_rank": self.matched_rank,
            "ndcg_at_10": self.ndcg_at_10,
            "recall_at_10": self.recall_at_10,
            "mrr_at_10": self.mrr_at_10,
            "precision_at_5": self.precision_at_5,
            "repo_search_score": self.repo_search_score,
            "matched_judgments": list(self.matched_judgments),
        }


@dataclass(frozen=True)
class EvalRunResult:
    """Structured report for a retrieval smoke/eval run."""

    cases: list[dict[str, object]]
    passed: int
    total: int
    dry_run: bool
    region: str
    namespace: str
    top_k: int
    candidates: int
    embedding_model: str
    ranking_mode: str
    ranking_profile: str
    ranking_pool: int
    ranking_aggregation: str
    repo_metrics: dict[str, float] | None = None

    def to_dict(self) -> dict[str, object]:
        pass_rate = self.passed / self.total if self.total and not self.dry_run else 0.0
        payload: dict[str, object] = {
            "command": "evals",
            "dry_run": self.dry_run,
            "credentials_required": not self.dry_run,
            "turbopuffer_api_calls": not self.dry_run,
            "api_calls_occurred": not self.dry_run,
            "region": self.region,
            "namespace": self.namespace,
            "embedding_model": self.embedding_model,
            "top_k": self.top_k,
            "candidates": self.candidates,
            "ranking_mode": self.ranking_mode,
            "ranking_profile": self.ranking_profile,
            "ranking_pool": self.ranking_pool,
            "ranking_aggregation": self.ranking_aggregation,
            "total": self.total,
            "passed": self.passed,
            "failed": 0 if self.dry_run else self.total - self.passed,
            "not_run": self.total if self.dry_run else 0,
            "pass_rate": pass_rate,
            "cases": self.cases,
        }
        if self.repo_metrics is not None:
            payload["repo_metrics"] = dict(self.repo_metrics)
        return payload


def optional_string(payload: Mapping[str, object], field_name: str, *, case_id: str) -> str | None:
    value = payload.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Eval case {case_id!r} has invalid {field_name}; expected string.")
    cleaned = value.strip()
    return cleaned or None


def load_eval_cases(dataset_path: Path | None = None) -> list[EvalCase]:
    """Load and validate retrieval smoke/graded eval cases from JSON."""

    path = dataset_path or DEFAULT_EVAL_DATASET
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, Mapping):
        payload = payload.get("cases")
    if not isinstance(payload, list):
        raise ValueError("Retrieval eval dataset must be a JSON list or an object with a cases list.")
    cases = [EvalCase.from_mapping(item) for item in payload if isinstance(item, Mapping)]
    if len(cases) != len(payload):
        raise ValueError("Every retrieval eval dataset entry must be an object.")
    if not cases:
        raise ValueError("Retrieval eval dataset must contain at least one case.")
    ids = [case.id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Retrieval eval case ids must be unique.")
    return cases


def score_hits(case: EvalCase, hits: Sequence[SearchHit | Mapping[str, object]]) -> EvalScore:
    """Pass when an expected URL or topic hint appears in top-k hits."""

    expected_urls = [value.casefold() for value in case.expected_urls if value]
    expected_topics = [value.casefold() for value in case.expected_topics if value]
    for rank, hit in enumerate(hits, start=1):
        url = hit_field(hit, "url").casefold()
        for expected_url in expected_urls:
            if expected_url in url:
                return EvalScore(passed=True, matched_url=expected_url, matched_rank=rank)

        searchable = " ".join(
            hit_field(hit, field)
            for field in ("title", "url", "section_path", "content", "path")
        ).casefold()
        for expected_topic in expected_topics:
            if expected_topic in searchable:
                return EvalScore(passed=True, matched_topic=expected_topic, matched_rank=rank)
    return EvalScore(passed=False)


def score_repo_hits(case: EvalCase, hits: Sequence[SearchHit | Mapping[str, object]]) -> RepoEvalScore:
    """Score graded repository judgments with NDCG/Recall/MRR/Precision composite metrics."""

    judgments = dedupe_relevant_judgments(case.judgments)
    if not judgments:
        return RepoEvalScore(
            ndcg_at_10=0.0,
            recall_at_10=0.0,
            mrr_at_10=0.0,
            precision_at_5=0.0,
            repo_search_score=0.0,
            matched_rank=None,
            matched_judgments=(),
        )

    dcg, ndcg_matches = dcg_for_hits(judgments, hits[:NDCG_K])
    ideal_dcg = dcg_for_grades(sorted((judgment.grade for judgment in judgments), reverse=True)[:NDCG_K])
    ndcg_at_10 = dcg / ideal_dcg if ideal_dcg else 0.0

    recall_matches = matched_judgment_keys(judgments, hits[:RECALL_K])
    recall_at_10 = len(recall_matches) / len(judgments)

    matched_rank = first_relevant_rank(judgments, hits[:MRR_K])
    mrr_at_10 = 1.0 / matched_rank if matched_rank is not None else 0.0

    precision_at_5 = precision_at_k(judgments, hits, PRECISION_K)
    repo_search_score = clamp_score_100(
        100.0
        * (
            REPO_SEARCH_SCORE_WEIGHTS["ndcg_at_10"] * ndcg_at_10
            + REPO_SEARCH_SCORE_WEIGHTS["recall_at_10"] * recall_at_10
            + REPO_SEARCH_SCORE_WEIGHTS["mrr_at_10"] * mrr_at_10
            + REPO_SEARCH_SCORE_WEIGHTS["precision_at_5"] * precision_at_5
        )
    )
    return RepoEvalScore(
        ndcg_at_10=ndcg_at_10,
        recall_at_10=recall_at_10,
        mrr_at_10=mrr_at_10,
        precision_at_5=precision_at_5,
        repo_search_score=repo_search_score,
        matched_rank=matched_rank,
        matched_judgments=tuple(ndcg_matches),
    )


def aggregate_repo_scores(scores: Sequence[RepoEvalScore]) -> dict[str, float]:
    """Average graded repo metrics across cases."""

    if not scores:
        return {
            "ndcg_at_10": 0.0,
            "recall_at_10": 0.0,
            "mrr_at_10": 0.0,
            "precision_at_5": 0.0,
            "repo_search_score": 0.0,
        }
    return {
        "ndcg_at_10": sum(score.ndcg_at_10 for score in scores) / len(scores),
        "recall_at_10": sum(score.recall_at_10 for score in scores) / len(scores),
        "mrr_at_10": sum(score.mrr_at_10 for score in scores) / len(scores),
        "precision_at_5": sum(score.precision_at_5 for score in scores) / len(scores),
        "repo_search_score": clamp_score_100(sum(score.repo_search_score for score in scores) / len(scores)),
    }


def clamp_score_100(value: float) -> float:
    return max(0.0, min(100.0, value))


def dcg_for_hits(judgments: Sequence[EvalJudgment], hits: Sequence[SearchHit | Mapping[str, object]]) -> tuple[float, list[dict[str, object]]]:
    used_keys: set[str] = set()
    dcg = 0.0
    matches: list[dict[str, object]] = []
    for rank, hit in enumerate(hits, start=1):
        judgment = best_unmatched_judgment_for_hit(judgments, hit, used_keys)
        if judgment is None:
            continue
        key = judgment_key(judgment)
        used_keys.add(key)
        dcg += relevance_gain(judgment.grade) / log2(rank + 1)
        matches.append({"rank": rank, "grade": judgment.grade, "key": key})
    return dcg, matches


def dcg_for_grades(grades: Sequence[int]) -> float:
    return sum(relevance_gain(grade) / log2(rank + 1) for rank, grade in enumerate(grades, start=1))


def relevance_gain(grade: int) -> int:
    return (2**grade) - 1


def matched_judgment_keys(judgments: Sequence[EvalJudgment], hits: Sequence[SearchHit | Mapping[str, object]]) -> set[str]:
    used_keys: set[str] = set()
    for hit in hits:
        judgment = best_unmatched_judgment_for_hit(judgments, hit, used_keys)
        if judgment is not None:
            used_keys.add(judgment_key(judgment))
    return used_keys


def first_relevant_rank(judgments: Sequence[EvalJudgment], hits: Sequence[SearchHit | Mapping[str, object]]) -> int | None:
    for rank, hit in enumerate(hits, start=1):
        if best_unmatched_judgment_for_hit(judgments, hit, set()) is not None:
            return rank
    return None


def precision_at_k(judgments: Sequence[EvalJudgment], hits: Sequence[SearchHit | Mapping[str, object]], k: int) -> float:
    top_hits = list(hits[:k])
    if not top_hits:
        return 0.0
    used_keys: set[str] = set()
    matched = 0
    for hit in top_hits:
        judgment = best_unmatched_judgment_for_hit(judgments, hit, used_keys)
        if judgment is not None:
            used_keys.add(judgment_key(judgment))
            matched += 1
    return matched / len(top_hits)


def dedupe_relevant_judgments(judgments: Sequence[EvalJudgment]) -> list[EvalJudgment]:
    by_key: dict[str, EvalJudgment] = {}
    for judgment in judgments:
        if judgment.grade <= 0:
            continue
        key = judgment_key(judgment)
        existing = by_key.get(key)
        if existing is None or judgment.grade > existing.grade:
            by_key[key] = judgment
    return sorted(by_key.values(), key=lambda judgment: (-judgment.grade, judgment_key(judgment)))


def best_unmatched_judgment_for_hit(
    judgments: Sequence[EvalJudgment],
    hit: SearchHit | Mapping[str, object],
    used_keys: set[str],
) -> EvalJudgment | None:
    candidates = [
        judgment
        for judgment in judgments
        if judgment_key(judgment) not in used_keys and judgment_matches_hit(judgment, hit)
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda judgment: (-judgment.grade, judgment_key(judgment)))[0]


def judgment_key(judgment: EvalJudgment) -> str:
    if judgment.repo_path:
        return f"repo_path:{normalize_repo_path(judgment.repo_path)}"
    if judgment.url:
        return f"url:{normalize_url(judgment.url)}"
    return f"section_path:{normalize_section(judgment.section_path or '')}"


def judgment_matches_hit(judgment: EvalJudgment, hit: SearchHit | Mapping[str, object]) -> bool:
    locator_matches = False
    if judgment.url:
        locator_matches = normalized_url_matches(judgment.url, hit)
    if judgment.repo_path and not locator_matches:
        locator_matches = repo_path_matches(judgment.repo_path, hit)
    if not locator_matches:
        return False
    if judgment.section_path:
        hit_section = normalize_section(hit_field(hit, "section_path"))
        expected_section = normalize_section(judgment.section_path)
        return bool(hit_section) and (expected_section in hit_section or hit_section in expected_section)
    return True


def normalized_url_matches(expected_url: str, hit: SearchHit | Mapping[str, object]) -> bool:
    expected = normalize_url(expected_url)
    actual = normalize_url(hit_field(hit, "url"))
    return bool(expected and actual) and (expected in actual or actual in expected)


def repo_path_matches(expected_repo_path: str, hit: SearchHit | Mapping[str, object]) -> bool:
    expected = normalize_repo_path(expected_repo_path)
    if not expected:
        return False
    candidates = repo_path_candidates(hit)
    return expected in candidates


def repo_path_candidates(hit: SearchHit | Mapping[str, object]) -> set[str]:
    candidates = {
        normalize_repo_path(hit_field(hit, "repo_path")),
        normalize_repo_path(hit_field(hit, "path")),
    }
    source_metadata = hit_value(hit, "source_metadata")
    if isinstance(source_metadata, Mapping):
        candidates.add(normalize_repo_path(str(source_metadata.get("repo_path") or "")))
    attributes = hit_value(hit, "attributes")
    if isinstance(attributes, Mapping):
        candidates.add(normalize_repo_path(str(attributes.get("repo_path") or "")))
        nested_metadata = attributes.get("source_metadata")
        if isinstance(nested_metadata, Mapping):
            candidates.add(normalize_repo_path(str(nested_metadata.get("repo_path") or "")))
    url_path = normalize_url_path_suffix(hit_field(hit, "url"))
    candidates.update(repo_path_suffixes(url_path))
    return {candidate for candidate in candidates if candidate}


def repo_path_suffixes(url_path: str) -> set[str]:
    if not url_path:
        return set()
    parts = [part for part in url_path.split("/") if part]
    suffixes = {"/".join(parts[index:]) for index in range(len(parts))}
    if "blob" in parts:
        blob_index = parts.index("blob")
        if len(parts) > blob_index + 2:
            suffixes.add("/".join(parts[blob_index + 2 :]))
    if "tree" in parts:
        tree_index = parts.index("tree")
        if len(parts) > tree_index + 2:
            suffixes.add("/".join(parts[tree_index + 2 :]))
    return {normalize_repo_path(suffix) for suffix in suffixes if suffix}


def hit_value(hit: SearchHit | Mapping[str, object], field_name: str) -> object:
    if isinstance(hit, Mapping):
        if field_name in hit:
            return hit.get(field_name)
        attributes = hit.get("attributes")
        if isinstance(attributes, Mapping) and field_name in attributes:
            return attributes.get(field_name)
        source_metadata = hit.get("source_metadata")
        if isinstance(source_metadata, Mapping) and field_name in source_metadata:
            return source_metadata.get(field_name)
        return None
    return getattr(hit, field_name, None)


def hit_field(hit: SearchHit | Mapping[str, object], field_name: str) -> str:
    value = hit_value(hit, field_name)
    return str(value or "")


def normalize_url(value: str) -> str:
    cleaned = unquote(value.strip())
    if not cleaned:
        return ""
    parsed = urlparse(cleaned)
    if parsed.scheme or parsed.netloc:
        netloc = parsed.netloc.casefold()
        path = normalize_url_path_suffix(parsed.path)
        return f"{netloc}/{path}".rstrip("/")
    return cleaned.rstrip("/").casefold()


def normalize_url_path_suffix(value: str) -> str:
    return normalize_repo_path(unquote(urlparse(value).path if "://" in value else value))


def normalize_repo_path(value: str) -> str:
    return unquote(value.strip()).replace("\\", "/").strip("/")


def normalize_section(value: str) -> str:
    return " ".join(value.casefold().split())


def hit_summary(hit: SearchHit | Mapping[str, object], rank: int) -> dict[str, object]:
    return {
        "rank": rank,
        "title": hit_field(hit, "title"),
        "url": hit_field(hit, "url"),
        "path": hit_field(hit, "path"),
        "repo_path": hit_field(hit, "repo_path"),
        "section_path": hit_field(hit, "section_path"),
    }


def build_dry_run_eval_report(
    cases: Sequence[EvalCase],
    *,
    config: RuntimeConfig,
    options: RetrievalOptions,
) -> EvalRunResult:
    """Return a no-credential listing of eval cases and expected hints."""

    listed_cases = [
        {
            **case.to_dict(),
            "status": "not_run",
            "top_hits": [],
            "score": EvalScore(passed=False).to_dict(),
        }
        for case in cases
    ]
    return EvalRunResult(
        cases=listed_cases,
        passed=0,
        total=len(cases),
        dry_run=True,
        region=config.region,
        namespace=config.namespace,
        top_k=options.top_k,
        candidates=options.candidates,
        embedding_model=config.embedding_model,
        ranking_mode=options.ranking_mode,
        ranking_profile=options.ranking_profile,
        ranking_pool=options.ranking_pool,
        ranking_aggregation=options.ranking_aggregation,
    )


def run_live_evals(
    cases: Sequence[EvalCase],
    *,
    config: RuntimeConfig,
    options: RetrievalOptions,
) -> EvalRunResult:
    """Run live retrieval for every eval case and score top-k source hints."""

    retriever = HybridRetriever.from_config(config)
    reports: list[dict[str, object]] = []
    passed = 0
    repo_scores: list[RepoEvalScore] = []
    for case in cases:
        result = retriever.retrieve(case.question, options)
        if case.judgments:
            score = score_repo_hits(case, result.hits[: options.top_k])
            repo_scores.append(score)
        else:
            score = score_hits(case, result.hits[: options.top_k])
        if score.passed:
            passed += 1
        reports.append(
            {
                **case.to_dict(),
                "status": "passed" if score.passed else "failed",
                "fusion": result.fusion,
                "top_hits": [hit_summary(hit, rank) for rank, hit in enumerate(result.hits[: options.top_k], start=1)],
                "score": score.to_dict(),
            }
        )
    return EvalRunResult(
        cases=reports,
        passed=passed,
        total=len(cases),
        dry_run=False,
        region=config.region,
        namespace=config.namespace,
        top_k=options.top_k,
        candidates=options.candidates,
        embedding_model=config.embedding_model,
        ranking_mode=options.ranking_mode,
        ranking_profile=options.ranking_profile,
        ranking_pool=options.ranking_pool,
        ranking_aggregation=options.ranking_aggregation,
        repo_metrics=aggregate_repo_scores(repo_scores) if repo_scores else None,
    )
