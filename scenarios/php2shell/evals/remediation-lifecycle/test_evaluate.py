#!/usr/bin/env python3
"""Deterministic tests for the PHP2Shell remediation lifecycle evaluation."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import unittest
from unittest.mock import patch

import evaluate


OBSERVED_AT = "2026-11-08T12:00:00+00:00"
LAB_B = evaluate.checker.TargetConfig(
    "lab-b", "http://127.0.0.1:8082/?inspect=1&format=json"
)


def report(version: str) -> evaluate.checker.CheckReport:
    evidence = evaluate.checker.RuntimeEvidence(version, "fpm-fcgi", OBSERVED_AT)
    return evaluate.checker.assess_runtime(LAB_B, evidence)


class RemediationEvaluationTests(unittest.TestCase):
    def test_correct_before_state(self) -> None:
        result = evaluate.evaluate_state("before", report("8.4.26"))
        self.assertTrue(result.passed)
        self.assertEqual(evaluate.exit_code_for(result), 0)

    def test_correct_configuration_only_state(self) -> None:
        result = evaluate.evaluate_state(
            "config-only", report("8.4.26"), desired_image=evaluate.FIXED_IMAGE
        )
        self.assertTrue(result.passed)

    def test_correct_after_state(self) -> None:
        result = evaluate.evaluate_state(
            "after", report("8.4.27"), running_image=evaluate.FIXED_IMAGE
        )
        self.assertTrue(result.passed)

    def test_wrong_version_fails(self) -> None:
        result = evaluate.evaluate_state("before", report("8.4.27"))
        self.assertFalse(result.passed)
        self.assertEqual(evaluate.exit_code_for(result), 1)

    def test_unreachable_runtime_fails_inconclusively(self) -> None:
        def unavailable(target):
            del target
            raise evaluate.checker.EvidenceError(
                "target_unavailable", "Lab B is unavailable.", operational=True
            )

        result = evaluate.evaluate_state(
            "before", evaluate.checker.run_check(LAB_B, unavailable)
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.report.error_code, "target_unavailable")
        self.assertTrue(
            all(
                item.result == evaluate.checker.INCONCLUSIVE
                for item in result.report.assessments
            )
        )

    def test_missing_and_malformed_evidence_fail(self) -> None:
        def missing(target):
            del target
            return evaluate.checker.parse_runtime_document({"schema_version": 1})

        missing_result = evaluate.evaluate_state(
            "before", evaluate.checker.run_check(LAB_B, missing)
        )
        malformed_result = evaluate.evaluate_state("before", report("not-a-version"))
        self.assertFalse(missing_result.passed)
        self.assertFalse(malformed_result.passed)
        self.assertEqual(missing_result.report.error_code, "unexpected_response")
        self.assertEqual(malformed_result.report.error_code, "invalid_version")

    def test_configuration_or_running_image_mismatch_fails(self) -> None:
        config_result = evaluate.evaluate_state(
            "config-only", report("8.4.26"), desired_image="php:8.4.26-fpm-bookworm"
        )
        after_result = evaluate.evaluate_state(
            "after", report("8.4.27"), running_image="php:8.4.26-fpm-bookworm"
        )
        self.assertFalse(config_result.passed)
        self.assertFalse(after_result.passed)

    def test_failure_exit_is_nonzero(self) -> None:
        result = evaluate.evaluate_state("after", report("8.4.26"))
        self.assertNotEqual(evaluate.exit_code_for(result), 0)

    def test_cli_returns_nonzero_for_failed_state(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            exit_code = evaluate.main(
                ["--state", "before"], report_provider=lambda: report("8.4.27")
            )
        self.assertEqual(exit_code, 1)
        self.assertIn("Result: FAIL", output.getvalue())

    @patch.object(evaluate, "_run_inspection")
    def test_config_inspection_uses_merged_read_only_model(self, run_inspection) -> None:
        run_inspection.return_value = f"nginx:1.30.6\n{evaluate.FIXED_IMAGE}\n"
        self.assertEqual(evaluate.inspect_desired_fixed_image(), evaluate.FIXED_IMAGE)
        command = run_inspection.call_args.args[0]
        self.assertEqual(command[-2:], ("config", "--images"))
        self.assertIn("compose.lab-b.update.yaml", command)

    @patch.object(evaluate, "_run_inspection")
    def test_running_image_inspection_is_read_only(self, run_inspection) -> None:
        container_id = "a" * 64
        run_inspection.side_effect = [container_id, evaluate.FIXED_IMAGE]
        self.assertEqual(evaluate.inspect_running_php_image(), evaluate.FIXED_IMAGE)
        first_command = run_inspection.call_args_list[0].args[0]
        second_command = run_inspection.call_args_list[1].args[0]
        self.assertEqual(first_command[-3:], ("ps", "-q", "php-fpm"))
        self.assertEqual(second_command[:2], ("docker", "inspect"))


if __name__ == "__main__":
    unittest.main()
