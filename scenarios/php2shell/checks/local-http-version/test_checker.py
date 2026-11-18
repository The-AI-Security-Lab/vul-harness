#!/usr/bin/env python3
"""Lightweight deterministic tests for the local runtime inventory."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import unittest

import checker
import cli
import dashboard


OBSERVED_AT = "2026-11-08T12:00:00+00:00"
LAB_A = checker.TargetConfig(
    "lab-a", "http://127.0.0.1:8080/?inspect=1&format=json"
)
LAB_B = checker.TargetConfig(
    "lab-b", "http://127.0.0.1:8082/?inspect=1&format=json"
)
LAB_C = checker.TargetConfig(
    "lab-c", "http://127.0.0.1:8083/?inspect=1&format=json"
)


def evidence(version: str, sapi: str = checker.EXPECTED_SAPI) -> checker.RuntimeEvidence:
    return checker.RuntimeEvidence(version, sapi, OBSERVED_AT)


def collector_for(mapping):
    def collect(target: checker.TargetConfig) -> checker.RuntimeEvidence:
        value = mapping[target.identifier]
        if isinstance(value, Exception):
            raise value
        return value

    return collect


class AssessmentTests(unittest.TestCase):
    def test_documented_fixed_thresholds(self) -> None:
        self.assertEqual(
            checker.FIXED_RELEASES,
            {
                "8.2": "8.2.35",
                "8.3": "8.3.36",
                "8.4": "8.4.27",
                "8.5": "8.5.12",
            },
        )

    def test_fixed_lab_a_runtime(self) -> None:
        report = checker.assess_runtime(LAB_A, evidence("8.4.27"))
        self.assertEqual({item.result for item in report.assessments}, {checker.FIXED})
        self.assertEqual(checker.exit_code_for(report), 0)

    def test_older_lab_b_runtime(self) -> None:
        report = checker.assess_runtime(LAB_B, evidence("8.4.26"))
        self.assertEqual(
            {item.result for item in report.assessments},
            {checker.POTENTIALLY_AFFECTED},
        )
        self.assertEqual(checker.exit_code_for(report), 1)

    def test_unsupported_and_malformed_versions_are_inconclusive(self) -> None:
        unsupported = checker.assess_runtime(LAB_A, evidence("8.1.99"))
        malformed = checker.assess_runtime(LAB_A, evidence("not-a-version"))
        self.assertEqual(checker.summary_result(unsupported), checker.INCONCLUSIVE)
        self.assertEqual(malformed.error_code, "invalid_version")
        self.assertEqual(checker.summary_result(malformed), checker.INCONCLUSIVE)

    def test_unexpected_sapi_is_inconclusive(self) -> None:
        report = checker.assess_runtime(LAB_A, evidence("8.4.27", "cli"))
        self.assertEqual(report.error_code, "unexpected_sapi")
        self.assertEqual(checker.summary_result(report), checker.INCONCLUSIVE)

    def test_malformed_runtime_document_is_inconclusive(self) -> None:
        def collector(target: checker.TargetConfig) -> checker.RuntimeEvidence:
            del target
            return checker.parse_runtime_document({"schema_version": 1})

        report = checker.run_check(LAB_A, collector)
        self.assertEqual(report.error_code, "unexpected_response")
        self.assertEqual(checker.summary_result(report), checker.INCONCLUSIVE)


class TargetRegistryTests(unittest.TestCase):
    def test_two_and_three_configured_targets(self) -> None:
        two = checker.parse_target_config(
            {
                "targets": [
                    {"id": LAB_A.identifier, "endpoint": LAB_A.endpoint},
                    {"id": LAB_B.identifier, "endpoint": LAB_B.endpoint},
                ]
            }
        )
        three = checker.parse_target_config(
            {
                "targets": [
                    {"id": target.identifier, "endpoint": target.endpoint}
                    for target in (LAB_A, LAB_B, LAB_C)
                ]
            }
        )
        self.assertEqual(len(two), 2)
        self.assertEqual([target.identifier for target in three], ["lab-a", "lab-b", "lab-c"])

    def test_duplicate_and_unsafe_targets_are_rejected(self) -> None:
        duplicate = {
            "targets": [
                {"id": "lab-a", "endpoint": LAB_A.endpoint},
                {"id": "lab-a", "endpoint": LAB_B.endpoint},
            ]
        }
        unsafe = {
            "targets": [
                {
                    "id": "remote",
                    "endpoint": "http://192.0.2.10:8080/?inspect=1&format=json",
                }
            ]
        }
        with self.assertRaises(checker.ConfigurationError):
            checker.parse_target_config(duplicate)
        with self.assertRaises(checker.ConfigurationError):
            checker.parse_target_config(unsafe)

    def test_unapproved_path_and_query_are_rejected(self) -> None:
        for endpoint in (
            "http://127.0.0.1:8080/other?inspect=1&format=json",
            "http://127.0.0.1:8080/?inspect=1&format=html",
            "http://localhost:8080/?inspect=1&format=json",
        ):
            with self.subTest(endpoint=endpoint), self.assertRaises(
                checker.ConfigurationError
            ):
                checker.parse_target_config(
                    {"targets": [{"id": "target", "endpoint": endpoint}]}
                )

    def test_unknown_target_is_rejected(self) -> None:
        with self.assertRaises(checker.ConfigurationError):
            checker.target_by_id((LAB_A, LAB_B), "missing")


class InventoryTests(unittest.TestCase):
    def test_one_unreachable_target_does_not_hide_other_results(self) -> None:
        unavailable = checker.EvidenceError(
            "target_unavailable", "Lab B is unavailable.", operational=True
        )
        reports = checker.run_checks(
            (LAB_A, LAB_B, LAB_C),
            collector_for(
                {
                    "lab-a": evidence("8.4.27"),
                    "lab-b": unavailable,
                    "lab-c": evidence("8.5.12"),
                }
            ),
        )
        self.assertEqual(len(reports), 3)
        self.assertEqual(checker.summary_result(reports[0]), checker.FIXED)
        self.assertEqual(reports[1].error_code, "target_unavailable")
        self.assertEqual(checker.summary_result(reports[2]), checker.FIXED)

    def test_desired_fixed_config_does_not_change_observed_old_runtime(self) -> None:
        desired_image = "php:8.4.27-fpm-bookworm"
        report = checker.run_check(
            LAB_B, collector_for({"lab-b": evidence("8.4.26")})
        )
        self.assertIn("8.4.27", desired_image)
        self.assertEqual(checker.summary_result(report), checker.POTENTIALLY_AFFECTED)

    def test_redeployed_fixed_runtime_is_observed_fixed(self) -> None:
        report = checker.run_check(
            LAB_B, collector_for({"lab-b": evidence("8.4.27")})
        )
        self.assertEqual(checker.summary_result(report), checker.FIXED)


class InterfaceTests(unittest.TestCase):
    def test_cli_defaults_to_lab_a(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            exit_code = cli.main(
                [],
                configured_targets=(LAB_A, LAB_B),
                collector=collector_for(
                    {"lab-a": evidence("8.4.27"), "lab-b": evidence("8.4.26")}
                ),
            )
        self.assertEqual(exit_code, 0)
        self.assertIn("Runtime ID: lab-a", output.getvalue())
        self.assertNotIn("Runtime ID: lab-b", output.getvalue())

    def test_cli_target_selection_and_json(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            exit_code = cli.main(
                ["--target", "lab-b", "--json"],
                configured_targets=(LAB_A, LAB_B),
                collector=collector_for(
                    {"lab-a": evidence("8.4.27"), "lab-b": evidence("8.4.26")}
                ),
            )
        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["target_id"], "lab-b")
        self.assertEqual(payload["php_version"], "8.4.26")

    def test_cli_all_returns_each_runtime(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            exit_code = cli.main(
                ["--all", "--json"],
                configured_targets=(LAB_A, LAB_B, LAB_C),
                collector=collector_for(
                    {
                        "lab-a": evidence("8.4.27"),
                        "lab-b": evidence("8.4.26"),
                        "lab-c": evidence("8.5.12"),
                    }
                ),
            )
        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(
            [item["target_id"] for item in payload["results"]],
            ["lab-a", "lab-b", "lab-c"],
        )

    def test_cli_unknown_target_is_rejected(self) -> None:
        error_output = StringIO()
        with redirect_stderr(error_output), self.assertRaises(SystemExit) as raised:
            cli.main(["--target", "missing"], configured_targets=(LAB_A, LAB_B))
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("invalid choice", error_output.getvalue())

    def test_dashboard_renders_multiple_rows_and_disabled_actions(self) -> None:
        reports = checker.run_checks(
            (LAB_A, LAB_B),
            collector_for({"lab-a": evidence("8.4.27"), "lab-b": evidence("8.4.26")}),
        )
        page = dashboard.render_page((LAB_A, LAB_B), reports)
        self.assertIn("Discovered PHP Runtimes", page)
        self.assertIn("lab-a", page)
        self.assertIn("lab-b", page)
        self.assertIn(checker.FIXED, page)
        self.assertIn(checker.POTENTIALLY_AFFECTED, page)
        self.assertEqual(page.count("aria-disabled=\"true\""), 2)
        self.assertNotIn('action="/remediate"', page)

    def test_dashboard_empty_state_lists_configured_targets(self) -> None:
        page = dashboard.render_page((LAB_A, LAB_B))
        self.assertIn("No observations yet", page)
        self.assertIn("Check Runtimes", page)
        self.assertEqual(page.count("not checked"), 6)


if __name__ == "__main__":
    unittest.main()
