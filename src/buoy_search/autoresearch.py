"""One-shot config-only autoresearch runner for repository search evals.

The runner executes exactly one registered experiment. It never mutates source,
local applied state, or turbopuffer namespaces. Fixture mode is fully local;
live mode is retrieval-only through the existing eval harness.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Mapping, Sequence

from buoy_search.config import RuntimeConfig, load_config
from buoy_search.evals import (
    EvalCase,
    EvalRunResult,
    RepoEvalScore,
    aggregate_repo_scores,
    hit_summary,
    load_eval_cases,
    score_hits,
    score_repo_hits,
)
from buoy_search.retriever import RetrievalOptions, ranking_defaults_for_namespace

DEFAULT_MODE = "fixture"
ALLOWED_MODES = {"fixture", "live"}
FORBIDDEN_FIELD_NAMES = {
    "apply",
    "approve",
    "delete",
    "delete_namespace",
    "delete_stale",
    "namespace_delete",
    "namespace_create",
    "create_namespace",
    "live_write",
    "live_writes",
    "write",
    "writes",
    "upsert",
    "upserts",
    "patch",
    "code_changes",
    "source_mutation",
    "mutate_source",
}
FORBIDDEN_COMMAND_TOKENS = {
    "apply",
    "--approve",
    "--delete-stale",
    "delete-namespace",
    "delete_namespace",
    "upsert",
    "write",
}


class AutoresearchExperimentError(ValueError):
    """Raised when an autoresearch experiment definition is invalid or unsafe."""


@dataclass(frozen=True)
class AutoresearchExperiment:
    """Validated config-only repo search eval experiment."""

    experiment_id: str
    question: str
    hypothesis: str
    dataset_path: Path
    mode: str
    config: RuntimeConfig
    retrieval_options: RetrievalOptions
    fixture_hits: dict[str, list[dict[str, object]]]
    output_path: Path | None
    notes: str

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object], *, base_dir: Path) -> "AutoresearchExperiment":
        validate_no_forbidden_fields(payload)
        experiment_id = required_string(payload, "experiment_id")
        question = required_string(payload, "question")
        hypothesis = required_string(payload, "hypothesis")
        dataset_path = resolve_path(required_string(payload, "dataset_path"), base_dir=base_dir)
        mode = optional_string(payload, "mode") or DEFAULT_MODE
        if mode not in ALLOWED_MODES:
            raise AutoresearchExperimentError(f"mode must be one of {sorted(ALLOWED_MODES)}, got {mode!r}.")

        config = runtime_config_from_payload(mapping_field(payload, "config", required=True))
        options = retrieval_options_from_payload(
            mapping_field(payload, "retrieval_options", required=True),
            namespace=config.namespace,
        )
        fixture_hits = fixture_hits_from_payload(payload.get("fixture_hits"))
        output_path_value = optional_string(payload, "output_path")
        notes = optional_string(payload, "notes") or ""

        if mode == "fixture" and not fixture_hits:
            raise AutoresearchExperimentError("fixture mode requires non-empty fixture_hits.")
        if mode == "live" and fixture_hits:
            raise AutoresearchExperimentError("live mode must not include fixture_hits; it runs retrieval-only live evals.")

        return cls(
            experiment_id=experiment_id,
            question=question,
            hypothesis=hypothesis,
            dataset_path=dataset_path,
            mode=mode,
            config=config,
            retrieval_options=options,
            fixture_hits=fixture_hits,
            output_path=resolve_path(output_path_value, base_dir=base_dir) if output_path_value else None,
            notes=notes,
        )

    def plan_dict(self, *, out_dir: Path) -> dict[str, object]:
        return {
            "command": "autoresearch",
            "runner": "buoy_search.autoresearch",
            "one_shot": True,
            "config_only": True,
            "experiment_id": self.experiment_id,
            "question": self.question,
            "hypothesis": self.hypothesis,
            "mode": self.mode,
            "dataset_path": str(self.dataset_path),
            "out_dir": str(out_dir),
            "safety": {
                "source_mutation_allowed": False,
                "live_writes_allowed": False,
                "namespace_management_allowed": False,
                "state_mutation_allowed": False,
                "live_mode_scope": "retrieval-only",
            },
            "config": {
                "region": self.config.region,
                "namespace": self.config.namespace,
                "embedding_model": self.config.embedding_model,
            },
            "retrieval_options": {
                "top_k": self.retrieval_options.top_k,
                "candidates": self.retrieval_options.candidates,
                "doc_kind": self.retrieval_options.doc_kind,
                "ranking_mode": self.retrieval_options.ranking_mode,
                "ranking_profile": self.retrieval_options.ranking_profile,
                "ranking_pool": self.retrieval_options.ranking_pool,
                "ranking_aggregation": self.retrieval_options.ranking_aggregation,
            },
            "notes": self.notes,
        }


def required_string(payload: Mapping[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise AutoresearchExperimentError(f"Experiment must include non-empty string {field_name!r}.")
    return value.strip()


def optional_string(payload: Mapping[str, object], field_name: str) -> str | None:
    value = payload.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise AutoresearchExperimentError(f"Experiment field {field_name!r} must be a string when provided.")
    cleaned = value.strip()
    return cleaned or None


def mapping_field(payload: Mapping[str, object], field_name: str, *, required: bool) -> Mapping[str, object]:
    value = payload.get(field_name)
    if value is None and not required:
        return {}
    if not isinstance(value, Mapping):
        raise AutoresearchExperimentError(f"Experiment must include object {field_name!r}.")
    return value


def resolve_path(value: str, *, base_dir: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base_dir / path)


def runtime_config_from_payload(payload: Mapping[str, object]) -> RuntimeConfig:
    base = load_config()
    region = string_or_default(payload, "region", base.region)
    namespace = string_or_default(payload, "namespace", base.namespace)
    embedding_model = string_or_default(payload, "embedding_model", base.embedding_model)
    return RuntimeConfig(region=region, namespace=namespace, embedding_model=embedding_model)


def retrieval_options_from_payload(payload: Mapping[str, object], *, namespace: str) -> RetrievalOptions:
    defaults = ranking_defaults_for_namespace(namespace)
    return RetrievalOptions(
        top_k=positive_int_field(payload, "top_k"),
        candidates=positive_int_field(payload, "candidates"),
        doc_kind=optional_string(payload, "doc_kind"),
        ranking_mode=string_or_default(payload, "ranking_mode", str(defaults["ranking_mode"])),
        ranking_profile=string_or_default(payload, "ranking_profile", str(defaults["ranking_profile"])).replace("-", "_"),
        ranking_pool=positive_int_field(payload, "ranking_pool", default=int(defaults["ranking_pool"])),
        ranking_aggregation=string_or_default(payload, "ranking_aggregation", str(defaults["ranking_aggregation"])).replace("-", "_"),
    )


def string_or_default(payload: Mapping[str, object], field_name: str, default: str) -> str:
    value = payload.get(field_name)
    if value is None:
        return default
    if not isinstance(value, str) or not value.strip():
        raise AutoresearchExperimentError(f"Config field {field_name!r} must be a non-empty string.")
    return value.strip()


def positive_int_field(payload: Mapping[str, object], field_name: str, *, default: int | None = None) -> int:
    value = payload.get(field_name)
    if value is None and default is not None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AutoresearchExperimentError(f"Retrieval option {field_name!r} must be a positive integer.")
    return value


def fixture_hits_from_payload(value: object) -> dict[str, list[dict[str, object]]]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise AutoresearchExperimentError("fixture_hits must be an object mapping case ids to hit lists.")
    result: dict[str, list[dict[str, object]]] = {}
    for case_id, hits in value.items():
        if not isinstance(case_id, str) or not case_id:
            raise AutoresearchExperimentError("fixture_hits keys must be non-empty case id strings.")
        if not isinstance(hits, list) or not all(isinstance(hit, Mapping) for hit in hits):
            raise AutoresearchExperimentError(f"fixture_hits for case {case_id!r} must be a list of hit objects.")
        result[case_id] = [dict(hit) for hit in hits]
    return result


def validate_no_forbidden_fields(value: object, *, path: str = "experiment") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            normalized = key_text.strip().casefold().replace("-", "_")
            if normalized in FORBIDDEN_FIELD_NAMES:
                raise AutoresearchExperimentError(
                    f"Unsafe experiment field {path}.{key_text} is forbidden for config-only autoresearch."
                )
            validate_no_forbidden_fields(child, path=f"{path}.{key_text}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_no_forbidden_fields(child, path=f"{path}[{index}]")
    elif isinstance(value, str) and path_is_command_like(path):
        tokens = {token.strip().casefold() for token in value.replace("\n", " ").split()}
        if tokens & FORBIDDEN_COMMAND_TOKENS:
            raise AutoresearchExperimentError(
                f"Unsafe experiment text at {path} mentions forbidden command token(s): {sorted(tokens & FORBIDDEN_COMMAND_TOKENS)}."
            )


def path_is_command_like(path: str) -> bool:
    tail = path.rsplit(".", 1)[-1].split("[", 1)[0].strip().casefold().replace("-", "_")
    return tail in {"command", "commands", "script", "scripts", "argv", "planned_argv", "shell", "run"}


def load_experiment(path: Path) -> AutoresearchExperiment:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise AutoresearchExperimentError("Experiment definition must be a JSON object.")
    return AutoresearchExperiment.from_mapping(payload, base_dir=Path.cwd())


def run_experiment(experiment: AutoresearchExperiment, *, out_dir: Path) -> dict[str, object]:
    cases = load_eval_cases(experiment.dataset_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = experiment.plan_dict(out_dir=out_dir)
    (out_dir / "plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True), encoding="utf-8")

    if experiment.mode == "fixture":
        eval_result = run_fixture_evals(cases, experiment=experiment)
    else:
        from buoy_search.evals import run_live_evals

        eval_result = run_live_evals(cases, config=experiment.config, options=experiment.retrieval_options)

    result = build_result(experiment=experiment, eval_result=eval_result, out_dir=out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    (out_dir / "report.md").write_text(render_report(result), encoding="utf-8")
    return result


def run_fixture_evals(cases: Sequence[EvalCase], *, experiment: AutoresearchExperiment) -> EvalRunResult:
    reports: list[dict[str, object]] = []
    passed = 0
    repo_scores: list[RepoEvalScore] = []
    for case in cases:
        hits = experiment.fixture_hits.get(case.id, [])
        if case.judgments:
            score = score_repo_hits(case, hits[: experiment.retrieval_options.top_k])
            repo_scores.append(score)
        else:
            score = score_hits(case, hits[: experiment.retrieval_options.top_k])
        if score.passed:
            passed += 1
        reports.append(
            {
                **case.to_dict(),
                "status": "passed" if score.passed else "failed",
                "fusion": "fixture",
                "top_hits": [hit_summary(hit, rank) for rank, hit in enumerate(hits[: experiment.retrieval_options.top_k], start=1)],
                "score": score.to_dict(),
            }
        )
    return EvalRunResult(
        cases=reports,
        passed=passed,
        total=len(cases),
        dry_run=True,
        region=experiment.config.region,
        namespace=experiment.config.namespace,
        top_k=experiment.retrieval_options.top_k,
        candidates=experiment.retrieval_options.candidates,
        embedding_model=experiment.config.embedding_model,
        ranking_mode=experiment.retrieval_options.ranking_mode,
        ranking_profile=experiment.retrieval_options.ranking_profile,
        ranking_pool=experiment.retrieval_options.ranking_pool,
        ranking_aggregation=experiment.retrieval_options.ranking_aggregation,
        repo_metrics=aggregate_repo_scores(repo_scores) if repo_scores else None,
    )


def build_result(*, experiment: AutoresearchExperiment, eval_result: EvalRunResult, out_dir: Path) -> dict[str, object]:
    eval_payload = eval_result.to_dict()
    if experiment.mode == "fixture":
        total = int(eval_payload.get("total") or 0)
        passed = int(eval_payload.get("passed") or 0)
        eval_payload.update(
            {
                "dry_run": True,
                "credentials_required": False,
                "turbopuffer_api_calls": False,
                "api_calls_occurred": False,
                "failed": total - passed,
                "not_run": 0,
                "pass_rate": passed / total if total else 0.0,
            }
        )
    repo_metrics = eval_payload.get("repo_metrics") if isinstance(eval_payload.get("repo_metrics"), Mapping) else {}
    score = float(repo_metrics.get("repo_search_score", 0.0)) if isinstance(repo_metrics, Mapping) else 0.0
    status = "passed" if eval_payload.get("failed") == 0 else "failed"
    return {
        "command": "autoresearch",
        "experiment_id": experiment.experiment_id,
        "question": experiment.question,
        "hypothesis": experiment.hypothesis,
        "mode": experiment.mode,
        "status": status,
        "score": score,
        "repo_metrics": dict(repo_metrics) if isinstance(repo_metrics, Mapping) else {},
        "result_row": {
            "experiment_id": experiment.experiment_id,
            "score": score,
            "status": status,
            "mode": experiment.mode,
            "top_k": experiment.retrieval_options.top_k,
            "candidates": experiment.retrieval_options.candidates,
            "doc_kind": experiment.retrieval_options.doc_kind,
            "notes": experiment.notes,
        },
        "artifacts": {
            "plan_path": str(out_dir / "plan.json"),
            "result_path": str(out_dir / "result.json"),
            "report_path": str(out_dir / "report.md"),
        },
        "safety": {
            "config_only": True,
            "source_mutation_allowed": False,
            "live_writes_allowed": False,
            "namespace_management_allowed": False,
            "state_mutation_allowed": False,
            "turbopuffer_api_calls": experiment.mode == "live",
        },
        "experiment": experiment.plan_dict(out_dir=out_dir),
        "eval": eval_payload,
    }


def render_report(result: Mapping[str, object]) -> str:
    eval_payload = result.get("eval") if isinstance(result.get("eval"), Mapping) else {}
    repo_metrics = result.get("repo_metrics") if isinstance(result.get("repo_metrics"), Mapping) else {}
    lines = [
        f"# Autoresearch Experiment {result.get('experiment_id')}",
        "",
        "## Summary",
        "",
        f"- Status: `{result.get('status')}`",
        f"- Mode: `{result.get('mode')}`",
        f"- Composite repo search score: `{float(result.get('score') or 0.0):.3f}`",
        f"- Total cases: `{eval_payload.get('total', 0)}`",
        f"- Passed cases: `{eval_payload.get('passed', 0)}`",
        "",
        "## Scientific contract",
        "",
        f"- Question: {result.get('question')}",
        f"- Hypothesis: {result.get('hypothesis')}",
        "",
        "## Component metrics",
        "",
    ]
    if repo_metrics:
        for name in ("ndcg_at_10", "recall_at_10", "mrr_at_10", "precision_at_5", "repo_search_score"):
            lines.append(f"- {name}: `{float(repo_metrics.get(name, 0.0)):.6f}`")
    else:
        lines.append("- No graded repo metrics were produced.")
    lines.extend(["", "## Cases", ""])
    cases = eval_payload.get("cases") if isinstance(eval_payload.get("cases"), list) else []
    for case in cases:
        if not isinstance(case, Mapping):
            continue
        score = case.get("score") if isinstance(case.get("score"), Mapping) else {}
        lines.extend(
            [
                f"### {case.get('id')}",
                "",
                f"- Status: `{case.get('status')}`",
                f"- Question: {case.get('question')}",
                f"- Matched rank: `{score.get('matched_rank')}`",
                f"- Repo score: `{float(score.get('repo_search_score') or 0.0):.6f}`",
                "",
            ]
        )
        top_hits = case.get("top_hits") if isinstance(case.get("top_hits"), list) else []
        if top_hits:
            lines.append("Top hits:")
            for hit in top_hits:
                if isinstance(hit, Mapping):
                    locator = hit.get("url") or hit.get("repo_path") or hit.get("path") or hit.get("section_path") or "no locator"
                    lines.append(f"- {hit.get('rank')}. {hit.get('title') or 'Untitled'} — {locator}")
            lines.append("")
    lines.extend(
        [
            "## Safety",
            "",
            "This runner executes one config-only trial. It does not mutate source code, local applied state, turbopuffer rows, or namespaces.",
            "Live mode, when selected, is retrieval-only through the existing eval harness.",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m buoy_search.autoresearch",
        description="Run exactly one config-only repository search autoresearch experiment.",
    )
    parser.add_argument("--experiment", type=Path, required=True, help="Path to one experiment JSON definition.")
    parser.add_argument("--out", type=Path, default=None, help="Output directory for plan.json, result.json, and report.md.")
    parser.add_argument("--json", action="store_true", help="Print result JSON to stdout.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        experiment = load_experiment(args.experiment)
        out_dir = args.out or experiment.output_path
        if out_dir is None:
            raise AutoresearchExperimentError("Output directory is required; pass --out or set output_path in the experiment.")
        result = run_experiment(experiment, out_dir=out_dir)
    except (AutoresearchExperimentError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Wrote autoresearch result to {result['artifacts']['result_path']}")
        print(f"Composite repo search score: {float(result['score']):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
