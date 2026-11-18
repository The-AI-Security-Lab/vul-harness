#!/usr/bin/env python3
import importlib.util
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("ssm_runtime.py")
SPEC = importlib.util.spec_from_file_location("ssm_runtime", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class SharedRuntimeTests(unittest.TestCase):
    def test_repository_root_and_assets_are_inside_repository(self):
        self.assertEqual(MODULE.REPOSITORY_ROOT.name, "vul-harness")
        for path in MODULE.asset_paths("lab-c"):
            self.assertTrue(path.is_file(), path)
            self.assertTrue(str(path).startswith(str(MODULE.REPOSITORY_ROOT)))

    def test_bootstrap_commands_use_integrity_checks_and_ssm_safe_loopback_layout(self):
        commands = MODULE.build_commands("lab-d", "base")
        joined = "\n".join(commands)
        self.assertIn("sha256sum", joined)
        self.assertIn(MODULE.COMPOSE_VERSION, joined)
        self.assertIn("docker compose", joined)
        self.assertIn("/opt/vulharness/scenarios/php2shell", joined)
        self.assertNotIn("ssh ", joined)
        self.assertNotIn("0.0.0.0:8080", joined)

    def test_remediation_transfers_the_lab_d_update_override(self):
        joined = "\n".join(MODULE.build_commands("lab-d", "remediate"))
        self.assertIn("compose.lab-d.update.yaml", joined)
        self.assertIn("docker compose -f '/opt/vulharness/scenarios/php2shell/labs/aws/lab-d/compose.lab-d.yaml' -f", joined)

    def test_ssm_runtime_reports_request_wait_and_success_without_aws(self):
        responses = iter(
            [
                {"Command": {"CommandId": "cmd-test"}},
                {"Status": "InProgress"},
                {"Status": "Success", "StandardOutputContent": "ok"},
            ]
        )
        stderr = StringIO()
        with redirect_stderr(stderr), patch.object(
            MODULE, "find_instance", return_value="i-test"
        ), patch.object(MODULE, "build_commands", return_value=["true"]), patch.object(
            MODULE, "aws_call", side_effect=lambda *args: next(responses)
        ), patch.object(MODULE.time, "sleep"):
            MODULE.run("profile", "region", "aws-cli", "vh-test", "lab-c", "base", 3, 0)
        output = stderr.getvalue()
        self.assertIn("STARTED", output)
        self.assertIn("REQUESTED", output)
        self.assertIn("WAITING", output)
        self.assertIn("SSM command=cmd-test lab=lab-c", output)
        self.assertTrue(output.rstrip().endswith("OK"))

    def test_ssm_runtime_reports_bounded_timeout(self):
        responses = iter(
            [
                {"Command": {"CommandId": "cmd-timeout"}},
                {"Status": "InProgress"},
                {"Status": "InProgress"},
            ]
        )
        stderr = StringIO()
        with redirect_stderr(stderr), patch.object(
            MODULE, "find_instance", return_value="i-test"
        ), patch.object(MODULE, "build_commands", return_value=["true"]), patch.object(
            MODULE, "aws_call", side_effect=lambda *args: next(responses)
        ), patch.object(MODULE.time, "sleep"):
            with self.assertRaises(MODULE.RuntimeErrorWithEvidence):
                MODULE.run("profile", "region", "aws-cli", "vh-test", "lab-c", "base", 2, 0)
        self.assertIn("exhausted bounded polling", stderr.getvalue())

    def test_reset_reports_reset_operation_and_separates_runtime_verification(self):
        responses = iter(
            [
                {"Command": {"CommandId": "cmd-reset"}},
                {"Status": "Success"},
            ]
        )
        stderr = StringIO()
        stdout = StringIO()
        with redirect_stderr(stderr), redirect_stdout(stdout), patch.object(
            MODULE, "find_instance", return_value="i-test"
        ), patch.object(MODULE, "build_commands", return_value=["true"]), patch.object(
            MODULE, "aws_call", side_effect=lambda *args: next(responses)
        ):
            MODULE.run(
                "profile",
                "region",
                "aws-cli",
                "vh-test",
                "lab-d",
                "base",
                2,
                0,
                operation_name="reset",
            )
        self.assertIn("reset lab-d deployment=vh-test", stderr.getvalue())
        self.assertIn("SSM command execution: Success", stdout.getvalue())
        self.assertIn("Reset result:", stdout.getvalue())
        self.assertIn("Runtime verification and vulnerability classification were not performed", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
