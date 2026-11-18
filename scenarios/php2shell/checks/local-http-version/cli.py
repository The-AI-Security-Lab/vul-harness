#!/usr/bin/env python3
"""Command-line interface for deterministic PHP2Shell runtime checks."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional, Sequence

from checker import (
    CheckReport,
    Collector,
    ConfigurationError,
    DEFAULT_TARGET_ID,
    EXPLOITABILITY_STATEMENT,
    TargetConfig,
    collect_runtime_evidence,
    exit_code_for_reports,
    load_targets,
    run_checks,
    target_by_id,
)


def progress(message: str, status: str) -> None:
    print(f"[VulHarness] PHP2Shell | local checker | {message} {status}", file=sys.stderr, flush=True)


def render_human(report: CheckReport) -> str:
    lines = [
        "VulHarness PHP2Shell version check",
        f"Runtime ID: {report.target.identifier}",
        f"Evidence source: {report.target.endpoint}",
        f"Observation timestamp: {report.observed_at or 'unavailable'}",
        f"Observed PHP version: {report.php_version or 'unavailable'}",
        f"Observed SAPI: {report.sapi or 'unavailable'}",
    ]
    for assessment in report.assessments:
        fixed = (
            f"; fixed release {assessment.fixed_release}"
            if assessment.fixed_release
            else ""
        )
        lines.append(f"{assessment.cve}: {assessment.result}{fixed}")
        lines.append(f"  {assessment.reason}")
    if report.error_code:
        lines.append(f"Evidence error: {report.error_code}: {report.error_message}")
    lines.extend(
        [
            "Application exploitability assessed: no",
            f"Limitation: {EXPLOITABILITY_STATEMENT}",
        ]
    )
    return "\n".join(lines)


def build_parser(targets: Sequence[TargetConfig]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check configured authorized local PHP runtimes against fixed releases."
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--target",
        choices=[target.identifier for target in targets],
        default=DEFAULT_TARGET_ID,
        help=f"configured runtime ID (default: {DEFAULT_TARGET_ID})",
    )
    selection.add_argument(
        "--all", action="store_true", help="check every configured local runtime"
    )
    parser.add_argument(
        "--json", action="store_true", help="write deterministic report JSON"
    )
    return parser


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    configured_targets: Optional[Sequence[TargetConfig]] = None,
    collector: Collector = collect_runtime_evidence,
) -> int:
    try:
        targets = (
            tuple(configured_targets)
            if configured_targets is not None
            else load_targets()
        )
        if not targets:
            raise ConfigurationError("No targets are configured.")
        args = build_parser(targets).parse_args(argv)
        selected = targets if args.all else (target_by_id(targets, args.target),)
    except ConfigurationError as exc:
        print(f"Target configuration error: {exc}", file=sys.stderr)
        return 4

    selected_ids = ", ".join(target.identifier for target in selected)
    progress(f"checking targets={selected_ids}", "STARTED")
    reports = run_checks(selected, collector)
    if args.json:
        payload = (
            reports[0].to_dict()
            if len(reports) == 1
            else {"results": [report.to_dict() for report in reports]}
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("\n\n".join(render_human(report) for report in reports))
    code = exit_code_for_reports(reports)
    progress(f"checked targets={selected_ids} exit_code={code}", "OK" if code == 0 else "FAILED")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
