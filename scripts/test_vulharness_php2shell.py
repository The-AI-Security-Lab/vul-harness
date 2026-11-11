import importlib.util
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/vulharness-php2shell.py"
SPEC = importlib.util.spec_from_file_location("vulharness_php2shell", MODULE_PATH)
assert SPEC and SPEC.loader
harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(harness)


def args_for(*argv):
    args = harness.build_parser().parse_args(argv)
    harness.validate(args)
    return args


class HarnessContractTests(unittest.TestCase):
    def test_help_is_available_without_an_environment(self):
        self.assertEqual(harness.main(["help"]), 0)

    def test_rejects_local_aws_method_combination(self):
        stream = io.StringIO()
        with redirect_stderr(stream):
            code = harness.main(["status", "--env", "local", "--method", "aws-cli"])
        self.assertEqual(code, harness.EXIT_USAGE)
        self.assertIn("valid only with --env aws", stream.getvalue())

    def test_mutating_operations_require_operation_specific_approval(self):
        with self.assertRaises(harness.HarnessError):
            args_for("setup", "--env", "local")
        with self.assertRaises(harness.HarnessError):
            args_for("cleanup", "--env", "local", "--lab", "lab-a")
        args_for("cleanup", "--env", "local", "--lab", "lab-a", "--dry-run")

    def test_unsupported_aws_lab_operation_is_rejected(self):
        with self.assertRaises(harness.HarnessError):
            args_for(
                "remediate",
                "--env",
                "aws",
                "--method",
                "aws-cli",
                "--deployment-id",
                "vh-cli-test-a1b2c3d4",
                "--lab",
                "lab-c",
                "--approve",
                "remediate",
            )
        with self.assertRaises(harness.HarnessError):
            args_for("dashboard", "--env", "aws", "--method", "aws-cli")

    def test_local_setup_plan_uses_only_named_compose_projects(self):
        args = args_for("setup", "--env", "local", "--approve", "setup")
        plan = harness.local_plan(args, "setup")
        commands = [step[1] for step in plan]
        self.assertEqual(len(commands), 4)
        self.assertIn("compose.lab-a.yaml", " ".join(commands[0]))
        self.assertIn("compose.lab-b.yaml", " ".join(commands[1]))
        self.assertIn("compose.lab-b.update.yaml", " ".join(commands[1]))
        self.assertNotIn("docker compose down", " ".join(" ".join(cmd) for cmd in commands))

    def test_local_remediation_uses_the_update_override(self):
        args = args_for("remediate", "--env", "local", "--lab", "lab-b", "--approve", "remediate")
        plan = harness.local_remediation_plan()
        self.assertTrue(all("compose.lab-b.update.yaml" in " ".join(step[1]) for step in plan))
        self.assertEqual(plan[-1][1][-3:], ["--force-recreate", "php-fpm", "web"])

    def test_local_cleanup_is_exactly_one_named_lab(self):
        args = args_for("cleanup", "--env", "local", "--lab", "lab-b", "--dry-run")
        plan = harness.local_plan(args, "cleanup")
        self.assertEqual(len(plan), 1)
        self.assertIn("compose.lab-b.yaml", " ".join(plan[0][1]))
        self.assertEqual(plan[0][1][-1], "ps")
        confirmed = args_for("cleanup", "--env", "local", "--lab", "lab-b", "--approve", "cleanup")
        self.assertEqual(harness.local_plan(confirmed, "cleanup")[0][1][-1], "down")
        with self.assertRaises(harness.HarnessError):
            args_for("cleanup", "--env", "local", "--dry-run")

    def test_aws_setup_preserves_an_explicit_deployment_id(self):
        args = args_for(
            "setup",
            "--env",
            "aws",
            "--method",
            "aws-cli",
            "--deployment-id",
            "vh-cli-test-a1b2c3d4",
            "--approve",
            "setup",
        )
        with patch.object(harness, "aws_preflight_plan", return_value=[]), patch.object(
            harness, "write_metadata"
        ), patch.object(harness, "run_plan", return_value=0) as run_plan:
            self.assertEqual(harness.run_aws(args), 0)
        plan = run_plan.call_args.args[2]
        command = plan[0][1]
        self.assertIn("--deployment-id", command)
        self.assertIn("vh-cli-test-a1b2c3d4", command)
        self.assertEqual(command[-1], "deploy")
        self.assertEqual([step[0] for step in plan[-2:]], ["SSM bootstrap lab-c", "SSM bootstrap lab-d"])

    def test_environment_deployment_identity_is_accepted_and_new_ids_get_expiry(self):
        deployment_id = "vh-cli-test-a1b2c3d4"
        with patch.dict(harness.os.environ, {"VULHARNESS_DEPLOYMENT_ID": deployment_id}, clear=False):
            args = harness.build_parser().parse_args(["status", "--env", "aws", "--method", "aws-cli"])
        self.assertEqual(args.deployment_id, deployment_id)

        with patch.dict(harness.os.environ, {"VULHARNESS_DEPLOYMENT_ID": ""}, clear=False):
            args = args_for("setup", "--env", "aws", "--method", "aws-cli", "--approve", "setup")
            with patch.object(harness, "aws_preflight_plan", return_value=[]), patch.object(
                harness, "write_metadata"
            ), patch.object(harness, "run_plan", return_value=0):
                harness.run_aws(args)
        self.assertRegex(args.expires_at, r"^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_repeated_setup_calls_with_same_identity_do_not_generate_duplicates(self):
        deployment_id = "vh-tf-test-deadbeef"
        first = args_for(
            "setup", "--env", "aws", "--method", "terraform", "--deployment-id", deployment_id, "--approve", "setup"
        )
        second = args_for(
            "setup", "--env", "aws", "--method", "terraform", "--deployment-id", deployment_id, "--approve", "setup"
        )
        with patch.object(harness, "aws_preflight_plan", return_value=[]), patch.object(
            harness, "write_metadata"
        ), patch.object(harness, "run_plan", return_value=0) as run_plan:
            harness.run_aws(first)
            first_command = run_plan.call_args.args[2][0][1]
            harness.run_aws(second)
            second_command = run_plan.call_args.args[2][0][1]
        self.assertEqual(first_command, second_command)

    def test_aws_runtime_actions_are_lab_d_only_and_scoped(self):
        args = args_for(
            "remediate",
            "--env",
            "aws",
            "--method",
            "cloudformation",
            "--deployment-id",
            "vh-cfn-test-a1b2c3d4",
            "--lab",
            "lab-d",
            "--approve",
            "remediate",
        )
        command = harness.aws_runtime_plan(args, "remediate")[0][1]
        self.assertEqual(command[command.index("--lab-id") + 1], "lab-d")
        self.assertIn("--deployment-id", command)

    def test_each_aws_method_keeps_an_independent_wrapper_boundary(self):
        wrapper_markers = {"aws-cli": "/cli/", "cloudformation": "/cloudformation/", "terraform": "/terraform/"}
        for method in harness.AWS_METHODS:
            args = args_for(
                "status",
                "--env",
                "aws",
                "--method",
                method,
                "--deployment-id",
                f"vh-{method.replace('-', '')}-test-a1b2c3d4",
            )
            command = harness.aws_wrapper_plan(args, "status")[0][1]
            self.assertIn(wrapper_markers[method], str(harness.wrapper_path(method)))
            self.assertIn("--deployment-id", command)
            self.assertEqual(command[-1], "status")

    def test_aws_evaluator_has_phase_and_absence_modes(self):
        args = args_for(
            "assess",
            "--env",
            "aws",
            "--method",
            "aws-cli",
            "--deployment-id",
            "vh-cli-test-a1b2c3d4",
            "--phase",
            "remediated",
        )
        command = harness.aws_evaluator_plan(args, include_ssm=True)[0][1]
        self.assertIn("--phase", command)
        self.assertIn("remediated", command)
        self.assertIn("--include-ssm", command)

        absence = args_for(
            "verify",
            "--env",
            "aws",
            "--method",
            "terraform",
            "--deployment-id",
            "vh-tf-test-deadbeef",
            "--expect-absent",
        )
        absence_command = harness.aws_evaluator_plan(absence, include_ssm=False)[0][1]
        self.assertIn("--expect-absent", absence_command)
        self.assertNotIn("--include-ssm", absence_command)

    def test_cleanup_keeps_guardduty_authorization_explicit(self):
        args = args_for(
            "cleanup",
            "--env",
            "aws",
            "--method",
            "aws-cli",
            "--deployment-id",
            "vh-cli-test-a1b2c3d4",
            "--dry-run",
        )
        command = harness.aws_wrapper_plan(args, "cleanup")[0][1]
        self.assertNotIn("--allow-guardduty-cleanup", command)
        self.assertIn("--dry-run", command)

    def test_json_operation_reports_child_failure_without_running_live_aws(self):
        args = args_for(
            "status",
            "--env",
            "aws",
            "--method",
            "aws-cli",
            "--deployment-id",
            "vh-cli-test-a1b2c3d4",
            "--output",
            "json",
        )
        failed = {"label": "status", "returncode": 2, "ok": False, "command": ["mock"]}
        stream = io.StringIO()
        with redirect_stdout(stream), patch.object(harness, "execute", return_value=failed):
            self.assertEqual(harness.run_aws(args), harness.EXIT_BLOCKED)
        payload = json.loads(stream.getvalue())
        self.assertIn("status", payload["recovery_commands"][0])
        self.assertIn("cleanup --dry-run", payload["recovery_commands"][1])


if __name__ == "__main__":
    unittest.main()
