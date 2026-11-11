#!/usr/bin/env python3
"""Evaluate the three documented PHP2Shell Lab B remediation states."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys
from typing import Callable, Optional, Sequence


PHP2SHELL_DIR = Path(__file__).resolve().parents[2]
CHECKER_DIR = PHP2SHELL_DIR / "checks" / "local-http-version"
LAB_B_DIR = PHP2SHELL_DIR / "labs" / "local" / "lab-b"
if str(CHECKER_DIR) not in sys.path:
    sys.path.insert(0, str(CHECKER_DIR))

import checker  # noqa: E402


LAB_B_TARGET_ID = "lab-b"
FIXED_IMAGE = (
    "php:8.4.27-fpm-bookworm@"
    "sha256:b75642e8c89c321039f351466134df951576fb0f7017117b3931e9a19b908d6c"
)
MAX_INSPECTION_OUTPUT = 16_384
INSPECTION_TIMEOUT_SECONDS = 5.0

STATE_EXPECTATIONS = {
    "before": ("8.4.26", checker.POTENTIALLY_AFFECTED),
    "config-only": ("8.4.26", checker.POTENTIALLY_AFFECTED),
    "after": ("8.4.27", checker.FIXED),
}


class InspectionError(Exception):
    """A fixed read-only Docker inspection could not produce usable evidence."""


@dataclass(frozen=True)
class EvaluationCheck:
    name: str
    passed: bool
    observed: str
    expected: str


@dataclass(frozen=True)
class EvaluationResult:
    state: str
    report: checker.CheckReport
    expected_version: str
    expected_classification: str
    checks: tuple[EvaluationCheck, ...]

    @property
    def passed(self) -> bool:
        return all(item.passed for item in self.checks)


def _run_inspection(command: Sequence[str]) -> str:
    """Run one fixed read-only command in the Lab B directory."""

    try:
        completed = subprocess.run(
            list(command),
            cwd=LAB_B_DIR,
            capture_output=True,
            check=False,
            text=True,
            timeout=INSPECTION_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise InspectionError(f"Inspection command is unavailable: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise InspectionError("Read-only Docker inspection timed out.") from exc
    except OSError as exc:
        raise InspectionError(f"Read-only Docker inspection failed: {exc}") from exc

    output = completed.stdout.strip()
    error = completed.stderr.strip()
    if len(output.encode("utf-8")) > MAX_INSPECTION_OUTPUT:
        raise InspectionError("Read-only Docker inspection output exceeded its limit.")
    if completed.returncode != 0:
        detail = error[:500] if error else f"exit code {completed.returncode}"
        raise InspectionError(f"Read-only Docker inspection failed: {detail}")
    return output


def inspect_desired_fixed_image() -> str:
    """Resolve the merged fixed Compose model without deploying it."""

    output = _run_inspection(
        (
            "docker",
            "compose",
            "-f",
            "compose.lab-b.yaml",
            "-f",
            "compose.lab-b.update.yaml",
            "config",
            "--images",
        )
    )
    images = [line.strip() for line in output.splitlines() if line.strip()]
    if FIXED_IMAGE in images:
        return FIXED_IMAGE
    php_images = [image for image in images if image.startswith("php:")]
    return php_images[0] if php_images else "unavailable"


def inspect_running_php_image() -> str:
    """Read the configured image reference from Lab B's running PHP-FPM container."""

    container_output = _run_inspection(
        (
            "docker",
            "compose",
            "-f",
            "compose.lab-b.yaml",
            "ps",
            "-q",
            "php-fpm",
        )
    )
    container_ids = [line.strip() for line in container_output.splitlines() if line.strip()]
    if len(container_ids) != 1 or re.fullmatch(r"[0-9a-f]{12,64}", container_ids[0]) is None:
        raise InspectionError("Lab B does not have exactly one inspectable PHP-FPM container.")
    image = _run_inspection(
        (
            "docker",
            "inspect",
            "--format",
            "{{.Config.Image}}",
            container_ids[0],
        )
    )
    return image.strip() or "unavailable"


def collect_lab_b_report() -> checker.CheckReport:
    targets = checker.load_targets()
    target = checker.target_by_id(targets, LAB_B_TARGET_ID)
    return checker.run_check(target)


def evaluate_state(
    state: str,
    report: checker.CheckReport,
    *,
    desired_image: Optional[str] = None,
    desired_error: Optional[str] = None,
    running_image: Optional[str] = None,
    running_error: Optional[str] = None,
) -> EvaluationResult:
    """Compare checker evidence and state-specific read-only evidence with expectations."""

    expected_version, expected_classification = STATE_EXPECTATIONS[state]
    checks = [
        EvaluationCheck(
            "Lab B target",
            report.target.identifier == LAB_B_TARGET_ID,
            report.target.identifier,
            LAB_B_TARGET_ID,
        ),
        EvaluationCheck(
            "runtime evidence",
            report.error_code is None,
            report.error_code or "available",
            "available",
        ),
        EvaluationCheck(
            "HTTP-observed PHP version",
            report.php_version == expected_version,
            report.php_version or "unavailable",
            expected_version,
        ),
    ]

    assessments = {item.cve: item for item in report.assessments}
    for cve in checker.CVES:
        assessment = assessments.get(cve)
        observed = assessment.result if assessment is not None else "missing"
        checks.append(
            EvaluationCheck(
                f"{cve} classification",
                observed == expected_classification,
                observed,
                expected_classification,
            )
        )

    if state == "config-only":
        observed = desired_error or desired_image or "unavailable"
        checks.append(
            EvaluationCheck(
                "merged desired PHP-FPM image",
                desired_error is None and desired_image == FIXED_IMAGE,
                observed,
                FIXED_IMAGE,
            )
        )
    elif state == "after":
        observed = running_error or running_image or "unavailable"
        checks.append(
            EvaluationCheck(
                "running PHP-FPM image",
                running_error is None and running_image == FIXED_IMAGE,
                observed,
                FIXED_IMAGE,
            )
        )

    return EvaluationResult(
        state=state,
        report=report,
        expected_version=expected_version,
        expected_classification=expected_classification,
        checks=tuple(checks),
    )


def render_result(result: EvaluationResult) -> str:
    lines = [
        "VulHarness PHP2Shell remediation lifecycle evaluation",
        f"State: {result.state}",
        f"Result: {'PASS' if result.passed else 'FAIL'}",
        f"Evidence endpoint: {result.report.target.endpoint}",
        f"Observation timestamp: {result.report.observed_at or 'unavailable'}",
        f"Observed PHP version: {result.report.php_version or 'unavailable'}",
        f"Expected PHP version: {result.expected_version}",
        f"Expected classification: {result.expected_classification}",
        "Checks:",
    ]
    for item in result.checks:
        status = "PASS" if item.passed else "FAIL"
        lines.append(
            f"  [{status}] {item.name}: observed {item.observed}; expected {item.expected}"
        )
    if result.report.error_code:
        lines.append(
            f"Evidence error: {result.report.error_code}: {result.report.error_message}"
        )
    if result.state == "config-only":
        lines.append(
            "State limitation: before and config-only have the same HTTP runtime evidence; "
            "the read-only merged Compose inspection is the additional config-only signal."
        )
    lines.extend(
        [
            "Application exploitability assessed: no",
            "Limitation: PASS verifies this exercise's version and state evidence only; it "
            "does not establish exploitability or complete vulnerability remediation.",
        ]
    )
    return "\n".join(lines)


def exit_code_for(result: EvaluationResult) -> int:
    return 0 if result.passed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate one documented PHP2Shell Lab B remediation state."
    )
    parser.add_argument("--state", required=True, choices=tuple(STATE_EXPECTATIONS))
    return parser


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    report_provider: Callable[[], checker.CheckReport] = collect_lab_b_report,
    desired_image_reader: Callable[[], str] = inspect_desired_fixed_image,
    running_image_reader: Callable[[], str] = inspect_running_php_image,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = report_provider()
    except checker.ConfigurationError as exc:
        print(f"Evaluation setup failed: {exc}")
        return 1

    desired_image = None
    desired_error = None
    running_image = None
    running_error = None
    if args.state == "config-only":
        try:
            desired_image = desired_image_reader()
        except InspectionError as exc:
            desired_error = str(exc)
    elif args.state == "after":
        try:
            running_image = running_image_reader()
        except InspectionError as exc:
            running_error = str(exc)

    result = evaluate_state(
        args.state,
        report,
        desired_image=desired_image,
        desired_error=desired_error,
        running_image=running_image,
        running_error=running_error,
    )
    print(render_result(result))
    return exit_code_for(result)


if __name__ == "__main__":
    raise SystemExit(main())
