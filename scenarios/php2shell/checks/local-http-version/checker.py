#!/usr/bin/env python3
"""Deterministic PHP2Shell runtime evidence collection and assessment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import ipaddress
import json
from pathlib import Path
import re
import socket
from typing import Any, Callable, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


TARGET_CONFIG_PATH = Path(__file__).with_name("targets.json")
DEFAULT_TARGET_ID = "lab-a"
EXPECTED_SAPI = "fpm-fcgi"
DEFAULT_TIMEOUT_SECONDS = 3.0
MAX_RESPONSE_BYTES = 16_384
MAX_CONFIG_BYTES = 65_536

CVES = ("CVE-2026-109618", "CVE-2026-109619")
FIXED_RELEASES = {
    "8.2": "8.2.35",
    "8.3": "8.3.36",
    "8.4": "8.4.27",
    "8.5": "8.5.12",
}

FIXED = "fixed_upstream_version"
POTENTIALLY_AFFECTED = "potentially_affected_upstream_version"
INCONCLUSIVE = "inconclusive"

EXPLOITABILITY_STATEMENT = (
    "Application exploitability was not assessed. This check compares only the "
    "observed serving PHP version with documented upstream fixed releases."
)

_EXPECTED_FIELDS = {"schema_version", "php_version", "sapi", "observed_at"}
_VERSION_PATTERN = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_TARGET_ID_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?$")


class ConfigurationError(Exception):
    """A target registry is missing or violates the local-only contract."""


class EvidenceError(Exception):
    """A controlled failure to collect or validate runtime evidence."""

    def __init__(self, code: str, message: str, *, operational: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.operational = operational


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


@dataclass(frozen=True)
class TargetConfig:
    identifier: str
    endpoint: str


@dataclass(frozen=True)
class RuntimeEvidence:
    php_version: str
    sapi: str
    observed_at: str


@dataclass(frozen=True)
class Assessment:
    cve: str
    result: str
    fixed_release: Optional[str]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "result": self.result,
            "fixed_release": self.fixed_release,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class CheckReport:
    target: TargetConfig
    php_version: Optional[str]
    sapi: Optional[str]
    observed_at: Optional[str]
    assessments: tuple[Assessment, ...]
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    operational_error: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target.identifier,
            "target": self.target.endpoint,
            "evidence_source": self.target.endpoint,
            "observed_at": self.observed_at,
            "php_version": self.php_version,
            "sapi": self.sapi,
            "assessments": {
                assessment.cve: assessment.to_dict()
                for assessment in self.assessments
            },
            "application_exploitability": {
                "assessed": False,
                "statement": EXPLOITABILITY_STATEMENT,
            },
            "error": (
                None
                if self.error_code is None
                else {"code": self.error_code, "message": self.error_message}
            ),
        }


Collector = Callable[[TargetConfig], RuntimeEvidence]


def _validate_endpoint(endpoint: str) -> None:
    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
    except ValueError as exc:
        raise ConfigurationError(f"Invalid target endpoint {endpoint!r}.") from exc

    if parsed.scheme != "http":
        raise ConfigurationError("Target endpoints must use plain HTTP on loopback.")
    if parsed.username is not None or parsed.password is not None:
        raise ConfigurationError("Target endpoints must not include credentials.")
    if parsed.hostname is None or port is None:
        raise ConfigurationError("Target endpoints require a literal host and explicit port.")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError as exc:
        raise ConfigurationError("Target endpoints require a literal loopback IP address.") from exc
    if not address.is_loopback:
        raise ConfigurationError("Target endpoints must use a loopback IP address.")
    if parsed.path != "/" or parsed.fragment:
        raise ConfigurationError("Target endpoints must use the approved runtime evidence path.")
    if sorted(parse_qsl(parsed.query, keep_blank_values=True)) != [
        ("format", "json"),
        ("inspect", "1"),
    ]:
        raise ConfigurationError(
            "Target endpoints must use exactly '?inspect=1&format=json'."
        )


def parse_target_config(payload: Any) -> tuple[TargetConfig, ...]:
    """Validate a small, explicit registry of authorized local runtime targets."""

    if not isinstance(payload, dict) or set(payload) != {"targets"}:
        raise ConfigurationError("Target configuration must contain only 'targets'.")
    entries = payload["targets"]
    if not isinstance(entries, list) or not entries:
        raise ConfigurationError("Target configuration requires a non-empty target list.")

    targets = []
    identifiers = set()
    endpoints = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"id", "endpoint"}:
            raise ConfigurationError("Each target requires exactly 'id' and 'endpoint'.")
        identifier = entry["id"]
        endpoint = entry["endpoint"]
        if not isinstance(identifier, str) or _TARGET_ID_PATTERN.fullmatch(identifier) is None:
            raise ConfigurationError(
                "Target IDs must be 1-32 lowercase letters, digits, or hyphens."
            )
        if not isinstance(endpoint, str):
            raise ConfigurationError("Target endpoints must be strings.")
        _validate_endpoint(endpoint)
        if identifier in identifiers:
            raise ConfigurationError(f"Duplicate target ID {identifier!r}.")
        if endpoint in endpoints:
            raise ConfigurationError(f"Duplicate target endpoint {endpoint!r}.")
        identifiers.add(identifier)
        endpoints.add(endpoint)
        targets.append(TargetConfig(identifier=identifier, endpoint=endpoint))
    return tuple(targets)


def load_targets(path: Path = TARGET_CONFIG_PATH) -> tuple[TargetConfig, ...]:
    """Read and validate the bounded local target registry."""

    try:
        with path.open("rb") as config_file:
            body = config_file.read(MAX_CONFIG_BYTES + 1)
    except OSError as exc:
        raise ConfigurationError(f"Unable to read target configuration: {exc}") from exc
    if len(body) > MAX_CONFIG_BYTES:
        raise ConfigurationError("Target configuration exceeds the size limit.")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError("Target configuration is not valid UTF-8 JSON.") from exc
    return parse_target_config(payload)


def target_by_id(targets: Sequence[TargetConfig], identifier: str) -> TargetConfig:
    for target in targets:
        if target.identifier == identifier:
            return target
    raise ConfigurationError(f"Unknown target {identifier!r}.")


def _inconclusive_assessments(reason: str) -> tuple[Assessment, ...]:
    return tuple(
        Assessment(cve=cve, result=INCONCLUSIVE, fixed_release=None, reason=reason)
        for cve in CVES
    )


def _parse_version(value: str) -> Optional[tuple[int, int, int]]:
    match = _VERSION_PATTERN.fullmatch(value)
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def _validate_observed_at(value: str) -> None:
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise EvidenceError(
            "unexpected_response",
            "The runtime evidence contains an invalid observation timestamp.",
        ) from exc
    if parsed.tzinfo is None:
        raise EvidenceError(
            "unexpected_response",
            "The runtime evidence observation timestamp has no timezone.",
        )


def parse_runtime_document(payload: Any) -> RuntimeEvidence:
    """Validate the versioned raw-facts document returned by a PHP lab."""

    if not isinstance(payload, dict):
        raise EvidenceError(
            "unexpected_response", "The runtime evidence response is not a JSON object."
        )
    if set(payload) != _EXPECTED_FIELDS:
        raise EvidenceError(
            "unexpected_response",
            "The runtime evidence response does not match schema version 1.",
        )
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise EvidenceError(
            "unexpected_response", "The runtime evidence schema version is unsupported."
        )

    php_version = payload["php_version"]
    sapi = payload["sapi"]
    observed_at = payload["observed_at"]
    if not isinstance(php_version, str) or not php_version.strip():
        raise EvidenceError("missing_version", "The runtime evidence contains no PHP version.")
    if not isinstance(sapi, str) or not sapi.strip():
        raise EvidenceError("missing_sapi", "The runtime evidence contains no SAPI.")
    if not isinstance(observed_at, str) or not observed_at.strip():
        raise EvidenceError(
            "unexpected_response", "The runtime evidence contains no observation timestamp."
        )

    _validate_observed_at(observed_at)
    return RuntimeEvidence(
        php_version=php_version.strip(), sapi=sapi.strip(), observed_at=observed_at
    )


def collect_runtime_evidence(
    target: TargetConfig, *, timeout: float = DEFAULT_TIMEOUT_SECONDS
) -> RuntimeEvidence:
    """Collect bounded JSON evidence from one validated local endpoint."""

    _validate_endpoint(target.endpoint)
    request = Request(
        target.endpoint,
        headers={"Accept": "application/json", "User-Agent": "VulHarness-Stage2/2"},
        method="GET",
    )
    opener = build_opener(_NoRedirectHandler())

    try:
        with opener.open(request, timeout=timeout) as response:
            status = getattr(response, "status", response.getcode())
            if status != 200:
                raise EvidenceError(
                    "http_error",
                    f"The runtime evidence endpoint returned HTTP {status}.",
                    operational=True,
                )
            content_type = response.headers.get_content_type()
            if content_type != "application/json":
                raise EvidenceError(
                    "unexpected_response",
                    f"Expected application/json but received {content_type!r}.",
                )
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        raise EvidenceError(
            "http_error",
            f"The runtime evidence endpoint returned HTTP {exc.code}.",
            operational=True,
        ) from exc
    except (socket.timeout, TimeoutError) as exc:
        raise EvidenceError(
            "timeout",
            f"The runtime evidence request exceeded {timeout:g} seconds.",
            operational=True,
        ) from exc
    except URLError as exc:
        if isinstance(exc.reason, (socket.timeout, TimeoutError)):
            raise EvidenceError(
                "timeout",
                f"The runtime evidence request exceeded {timeout:g} seconds.",
                operational=True,
            ) from exc
        raise EvidenceError(
            "target_unavailable",
            f"The authorized local target {target.identifier!r} is unavailable.",
            operational=True,
        ) from exc
    except OSError as exc:
        raise EvidenceError(
            "target_unavailable",
            f"The authorized local target {target.identifier!r} is unavailable.",
            operational=True,
        ) from exc

    if len(body) > MAX_RESPONSE_BYTES:
        raise EvidenceError(
            "unexpected_response",
            f"The runtime evidence response exceeds {MAX_RESPONSE_BYTES} bytes.",
        )
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(
            "unexpected_response", "The runtime evidence response is not valid UTF-8 JSON."
        ) from exc
    return parse_runtime_document(payload)


def assess_runtime(target: TargetConfig, evidence: RuntimeEvidence) -> CheckReport:
    """Compare raw runtime evidence with documented fixed releases."""

    observed_version = _parse_version(evidence.php_version)
    if observed_version is None:
        reason = "The observed PHP version is malformed or unverifiable."
        return CheckReport(
            target=target,
            php_version=evidence.php_version,
            sapi=evidence.sapi,
            observed_at=evidence.observed_at,
            assessments=_inconclusive_assessments(reason),
            error_code="invalid_version",
            error_message=reason,
        )

    if evidence.sapi != EXPECTED_SAPI:
        reason = f"Expected serving SAPI {EXPECTED_SAPI!r} but observed {evidence.sapi!r}."
        return CheckReport(
            target=target,
            php_version=evidence.php_version,
            sapi=evidence.sapi,
            observed_at=evidence.observed_at,
            assessments=_inconclusive_assessments(reason),
            error_code="unexpected_sapi",
            error_message=reason,
        )

    branch = f"{observed_version[0]}.{observed_version[1]}"
    fixed_release = FIXED_RELEASES.get(branch)
    if fixed_release is None:
        reason = f"PHP branch {branch} is not covered by the documented thresholds."
        return CheckReport(
            target=target,
            php_version=evidence.php_version,
            sapi=evidence.sapi,
            observed_at=evidence.observed_at,
            assessments=_inconclusive_assessments(reason),
        )

    fixed_version = _parse_version(fixed_release)
    assert fixed_version is not None
    if observed_version >= fixed_version:
        result = FIXED
        reason = (
            f"Observed PHP {evidence.php_version} is at or above the {fixed_release} "
            f"fixed release for branch {branch}."
        )
    else:
        result = POTENTIALLY_AFFECTED
        reason = (
            f"Observed PHP {evidence.php_version} is below the {fixed_release} "
            f"fixed release for branch {branch}; vendor backports were not assessed."
        )

    assessments = tuple(
        Assessment(cve=cve, result=result, fixed_release=fixed_release, reason=reason)
        for cve in CVES
    )
    return CheckReport(
        target=target,
        php_version=evidence.php_version,
        sapi=evidence.sapi,
        observed_at=evidence.observed_at,
        assessments=assessments,
    )


def run_check(
    target: TargetConfig, collector: Collector = collect_runtime_evidence
) -> CheckReport:
    """Collect and assess one target while preserving expected failures as evidence."""

    try:
        evidence = collector(target)
    except EvidenceError as exc:
        return CheckReport(
            target=target,
            php_version=None,
            sapi=None,
            observed_at=None,
            assessments=_inconclusive_assessments(exc.message),
            error_code=exc.code,
            error_message=exc.message,
            operational_error=exc.operational,
        )
    return assess_runtime(target, evidence)


def run_checks(
    targets: Sequence[TargetConfig], collector: Collector = collect_runtime_evidence
) -> tuple[CheckReport, ...]:
    return tuple(run_check(target, collector) for target in targets)


def summary_result(report: CheckReport) -> str:
    results = {assessment.result for assessment in report.assessments}
    if POTENTIALLY_AFFECTED in results:
        return POTENTIALLY_AFFECTED
    if INCONCLUSIVE in results:
        return INCONCLUSIVE
    return FIXED


def exit_code_for(report: CheckReport) -> int:
    """Map one deterministic report to a documented process exit code."""

    if report.operational_error:
        return 3
    result = summary_result(report)
    if result == POTENTIALLY_AFFECTED:
        return 1
    if result == INCONCLUSIVE:
        return 2
    return 0


def exit_code_for_reports(reports: Sequence[CheckReport]) -> int:
    return max((exit_code_for(report) for report in reports), default=0)
