#!/usr/bin/env python3
import importlib.util
import json
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("aws_evaluate.py")
SPEC = importlib.util.spec_from_file_location("aws_evaluate", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class AwsEvaluateTests(unittest.TestCase):
    def test_empty_region_is_rejected_before_aws_calls(self):
        with patch.object(MODULE.Aws, "call") as aws_call:
            with self.assertRaises(SystemExit) as raised:
                MODULE.main(
                    [
                        "--profile",
                        "test-profile",
                        "--region",
                        "",
                        "--method",
                        "aws-cli",
                        "--deployment-id",
                        "vh-test",
                    ]
                )
        self.assertEqual(raised.exception.code, 2)
        aws_call.assert_not_called()

    def test_inventory_api_failure_has_clean_actionable_error(self):
        stdout = StringIO()
        stderr = StringIO()
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(
                MODULE.Aws,
                "call",
                side_effect=MODULE.AwsEvaluationError("Invalid endpoint: https://ec2..amazonaws.com"),
            ):
                with redirect_stderr(stderr), redirect_stdout(stdout):
                    code = MODULE.main(
                        [
                            "--profile",
                            "test-profile",
                            "--region",
                            "us-east-1",
                            "--method",
                            "aws-cli",
                            "--deployment-id",
                            "vh-test",
                            "--evidence-dir",
                            directory,
                        ]
                    )
        self.assertEqual(code, 1)
        self.assertIn("AWS inventory/evaluation collection failed", stderr.getvalue())
        self.assertIn("verify the AWS profile, Region, permissions, and deployment scope", stderr.getvalue())
        self.assertNotIn("Traceback", stdout.getvalue() + stderr.getvalue())

    def test_definitions_cover_required_stages(self):
        definitions = json.loads((MODULE_PATH.parent / "evaluations.json").read_text())
        ids = {item["id"] for item in definitions["evaluations"]}
        self.assertTrue({"INF-001", "INF-016", "GD-001", "GD-012", "RUN-001", "RUN-012", "PHP-001", "PHP-012"} <= ids)
        scopes = {item["id"]: item.get("scope", "deployment") for item in definitions["evaluations"]}
        self.assertEqual(scopes["INF-009"], "lab")
        self.assertEqual(scopes["RUN-001"], "lab")
        self.assertEqual(scopes["RUN-010"], "deployment")
        self.assertEqual(scopes["PHP-010"], "lab")

    def test_filters_are_method_and_deployment_scoped(self):
        filters = MODULE.common_filters("vh-test", "terraform")
        self.assertIn("Name=tag:VulHarnessDeployment,Values=vh-test", filters)
        self.assertIn("Name=tag:VulHarnessDeploymentMethod,Values=terraform", filters)

    def test_empty_inventory_fails_closed(self):
        results = []
        inventory = {key: [] for key in ("vpcs", "vpc_endpoints", "subnets", "route_tables", "internet_gateways", "security_groups", "instances", "volumes", "network_interfaces")}
        MODULE.evaluate_infrastructure(None, inventory, "vh-test", "aws-cli", results)
        by_id = {item.evaluation_id: item for item in results}
        self.assertEqual(by_id["INF-001"].status, "FAIL")
        self.assertEqual(by_id["INF-002"].status, "FAIL")
        self.assertEqual(by_id["INF-011"].status, "SKIP")

    def test_result_is_machine_readable(self):
        result = MODULE.Result("INF-001", "PASS", "two instances", "2", "inventory.json")
        payload = result.as_dict()
        self.assertEqual(payload["evaluation_id"], "INF-001")
        self.assertEqual(payload["result_id"], "INF-001")
        self.assertEqual(payload["status"], "PASS")
        self.assertIn("evidence_location", payload)

    def test_protected_instance_check_requires_local_configuration(self):
        results = []
        MODULE.evaluate_protected_instance(results, [{"InstanceId": "i-example"}], "inventory.json", None, "protected instance is not in deployment inventory")
        self.assertEqual(results[0].status, "SKIP")
        self.assertEqual(results[0].skip_classification, "configuration_missing")

    def test_lab_and_phase_scoping_prevents_duplicate_result_ids(self):
        runtime = {
            "schema_version": "1.0",
            "php_version": "8.4.27",
            "sapi": "fpm-fcgi",
            "observed_at": "2026-11-10T00:00:00Z",
        }
        results = []
        MODULE.add_php_results(results, "lab-c", "remediated", runtime, "containers", "images", "lab-c.txt")
        MODULE.add_php_results(results, "lab-d", "remediated", runtime, "containers", "images", "lab-d.txt")
        MODULE.validate_result_identities(results)
        result_ids = {item.result_id for item in results}
        self.assertEqual(len(result_ids), len(results))
        self.assertFalse(any(item.evaluation_id in {"PHP-006", "PHP-007", "PHP-008", "PHP-010"} and item.lab_id == "lab-c" for item in results))
        self.assertEqual(sum(item.evaluation_id == "PHP-006" for item in results), 1)
        self.assertEqual(sum(item.evaluation_id == "PHP-007" for item in results), 1)
        self.assertEqual(sum(item.evaluation_id == "PHP-008" for item in results), 1)
        self.assertEqual(sum(item.evaluation_id == "PHP-010" for item in results), 1)
        self.assertEqual(next(item for item in results if item.evaluation_id == "PHP-006").result_id, "PHP-006:lab-d:remediated")

    def test_duplicate_result_identity_is_rejected(self):
        results = [
            MODULE.Result("RUN-001", "PASS", "installed", "yes", "a", lab_id="lab-c", phase="initial"),
            MODULE.Result("RUN-001", "PASS", "installed", "yes", "b", lab_id="lab-c", phase="initial"),
        ]
        with self.assertRaises(MODULE.AwsEvaluationError):
            MODULE.validate_result_identities(results)

    def test_runtime_markers_are_bounded_and_phase_expectations_are_explicit(self):
        output = "__VULHARNESS_PS__\nweb running\n__VULHARNESS_RUNTIME__\n{\"php_version\":\"8.4.27\"}\n"
        self.assertEqual(MODULE.parse_marker(output, "PS"), "web running")
        self.assertEqual(MODULE.parse_marker(output, "RUNTIME"), '{"php_version":"8.4.27"}')
        self.assertEqual(MODULE.expected_php_version("lab-d", "initial"), "8.4.26")
        self.assertEqual(MODULE.expected_php_version("lab-d", "remediated"), "8.4.27")
        self.assertEqual(MODULE.expected_php_version("lab-d", "reset"), "8.4.26")

    def test_runtime_markers_remain_parseable_after_non_newline_json(self):
        output = "__VULHARNESS_CONFIG__\n{\"services\":{}}__VULHARNESS_IMAGES__\n[]\n"
        self.assertEqual(MODULE.parse_marker(output, "CONFIG"), '{"services":{}}')
        self.assertEqual(MODULE.parse_marker(output, "IMAGES"), "[]")

    def test_running_services_with_healthy_checks_are_ready(self):
        ps_output = json.dumps([
            {"Service": "web", "State": "running", "Health": "healthy"},
            {"Service": "php-fpm", "State": "running", "Health": "healthy"},
        ])
        config_output = json.dumps({
            "services": {
                "web": {"healthcheck": {"test": ["CMD", "true"]}},
                "php-fpm": {"healthcheck": {"test": ["CMD", "true"]}},
            }
        })
        assessment = MODULE.assess_compose_runtime(ps_output, config_output)
        self.assertEqual(assessment["service_status"], "PASS")
        self.assertEqual(assessment["health_status"], "PASS")
        self.assertEqual(assessment["readiness"], "READY")

    def test_stopped_service_is_not_ready(self):
        ps_output = json.dumps([
            {"Service": "web", "State": "running", "Health": ""},
            {"Service": "php-fpm", "State": "exited", "Health": ""},
        ])
        config_output = json.dumps({"services": {"web": {}, "php-fpm": {}}})
        assessment = MODULE.assess_compose_runtime(ps_output, config_output)
        self.assertEqual(assessment["service_status"], "FAIL")
        self.assertEqual(assessment["readiness"], "NOT READY")

    def test_missing_service_is_not_ready(self):
        ps_output = json.dumps([{"Service": "web", "State": "running", "Health": ""}])
        config_output = json.dumps({"services": {"web": {}, "php-fpm": {}}})
        assessment = MODULE.assess_compose_runtime(ps_output, config_output)
        self.assertEqual(assessment["service_status"], "FAIL")
        self.assertIn("php-fpm", assessment["service_observed"])
        self.assertEqual(assessment["readiness"], "NOT READY")

    def test_unhealthy_service_is_not_ready(self):
        ps_output = json.dumps([
            {"Service": "web", "State": "running", "Health": "healthy"},
            {"Service": "php-fpm", "State": "running", "Health": "unhealthy"},
        ])
        config_output = json.dumps({
            "services": {
                "web": {"healthcheck": {"test": ["CMD", "true"]}},
                "php-fpm": {"healthcheck": {"test": ["CMD", "true"]}},
            }
        })
        assessment = MODULE.assess_compose_runtime(ps_output, config_output)
        self.assertEqual(assessment["service_status"], "PASS")
        self.assertEqual(assessment["health_status"], "FAIL")
        self.assertEqual(assessment["readiness"], "RUNNING; HEALTH FAILED")

    def test_running_services_without_health_checks_are_not_marked_ready(self):
        ps_output = json.dumps([
            {"Service": "web", "State": "running", "Health": ""},
            {"Service": "php-fpm", "State": "running", "Health": ""},
        ])
        config_output = json.dumps({"services": {"web": {}, "php-fpm": {}}})
        assessment = MODULE.assess_compose_runtime(ps_output, config_output)
        self.assertEqual(assessment["service_status"], "PASS")
        self.assertEqual(assessment["health_status"], "SKIP")
        self.assertEqual(assessment["health_skip"], "healthcheck_not_configured")
        self.assertEqual(assessment["readiness"], "RUNNING; HEALTH UNVERIFIED")

    def test_lifecycle_manifest_turns_collected_evidence_into_results(self):
        results = []
        lifecycle = {
            "schema_version": "1.0",
            "repeated_deployment": {"status": "PASS", "observed": "same tagged resources reused"},
            "partial_recovery": {"status": "PASS", "observed": "only missing Lab D was created"},
            "unrelated_resource_protection": {"status": "PASS", "observed": "protected instance absent"},
            "repeated_bootstrap": {"status": "PASS", "observed": "second SSM bootstrap succeeded"},
            "interruption_recovery": {"status": "FAIL", "observed": "not run"},
            "repeated_remediation": {"status": "PASS", "observed": "second remediation succeeded"},
        }
        MODULE.add_lifecycle_results(results, lifecycle, "lifecycle.json")
        by_id = {item.evaluation_id: item for item in results}
        self.assertEqual(by_id["INF-011"].status, "PASS")
        self.assertEqual(by_id["INF-012"].status, "PASS")
        self.assertEqual(by_id["RUN-011"].status, "FAIL")
        self.assertEqual(by_id["PHP-009"].status, "PASS")
        self.assertEqual(by_id["PHP-009"].result_id, "PHP-009:lab-d:remediated")

    def test_missing_lifecycle_manifest_is_a_coverage_gap(self):
        results = []
        MODULE.add_lifecycle_results(results, None, "inventory.json")
        self.assertTrue(results)
        self.assertTrue(all(item.skip_classification == "coverage_gap" for item in results))

    def test_cleanup_absence_passes_only_when_exact_inventory_is_empty(self):
        class FakeAws:
            def call(self, service, *args):
                if service == "iam" and args[0] == "get-role":
                    return {}
                if service == "iam" and args[0] == "get-instance-profile":
                    return {}
                raise AssertionError((service, args))

        inventory = {key: [] for key in ("vpcs", "subnets", "route_tables", "internet_gateways", "security_groups", "instances", "volumes", "network_interfaces")}
        results = []
        MODULE.evaluate_cleanup_absence(FakeAws(), inventory, "vh-test", "aws-cli", results, "inventory.json")
        by_id = {item.evaluation_id: item for item in results}
        self.assertEqual(by_id["INF-014"].status, "PASS")
        inventory["vpcs"].append({"VpcId": "vpc-residual"})
        results = []
        MODULE.evaluate_cleanup_absence(FakeAws(), inventory, "vh-test", "aws-cli", results, "inventory.json")
        self.assertEqual(results[0].status, "FAIL")
        self.assertEqual(results[0].failure_classification, "RESIDUAL_RESOURCES")

        inventory = {key: [] for key in ("vpcs", "subnets", "route_tables", "internet_gateways", "security_groups", "instances", "volumes", "network_interfaces")}
        inventory["instances"].append({"InstanceId": "i-terminated", "State": {"Name": "terminated"}})
        results = []
        MODULE.evaluate_cleanup_absence(FakeAws(), inventory, "vh-test", "aws-cli", results, "inventory.json")
        self.assertEqual(results[0].status, "PASS")

    def test_cleanup_absence_classifies_external_vpc_dependency(self):
        class FakeAws:
            def call(self, service, *args):
                if service == "iam" and args[0] in {"get-role", "get-instance-profile"}:
                    return {}
                raise AssertionError((service, args))

        inventory = {
            "vpcs": [{"VpcId": "vpc-owned", "Tags": []}],
            "vpc_endpoints": [{
                "VpcEndpointId": "vpce-external",
                "ServiceName": "com.amazonaws.us-east-1.guardduty-data",
                "Tags": [{"Key": "GuardDutyManaged", "Value": "true"}],
            }],
            "subnets": [{"SubnetId": "subnet-owned"}],
            "route_tables": [],
            "internet_gateways": [],
            "security_groups": [],
            "instances": [],
            "volumes": [],
            "network_interfaces": [],
        }
        results = []
        MODULE.evaluate_cleanup_absence(FakeAws(), inventory, "vh-test", "aws-cli", results, "inventory.json")
        by_id = {item.evaluation_id: item for item in results}
        self.assertEqual(by_id["INF-014"].status, "FAIL")
        self.assertEqual(by_id["INF-014"].failure_classification, "BLOCKED_BY_EXTERNAL_DEPENDENCY")

    def test_guardduty_inventory_fails_closed_for_missing_cleanup_evidence(self):
        results = []
        inventory = {"vpcs": [{"VpcId": "vpc-owned"}], "vpc_endpoints": [{
            "VpcEndpointId": "vpce-gd",
            "VpcId": "vpc-owned",
            "ServiceName": "com.amazonaws.us-east-1.guardduty-data",
            "Tags": [{"Key": "GuardDutyManaged", "Value": "true"}],
        }]}
        MODULE.evaluate_guardduty_inventory(results, inventory, "inventory.json")
        by_id = {item.evaluation_id: item for item in results}
        self.assertEqual(by_id["GD-001"].status, "PASS")
        self.assertEqual(by_id["GD-003"].status, "PASS")
        self.assertEqual(by_id["GD-005"].status, "SKIP")
        self.assertEqual(by_id["GD-005"].skip_classification, "conditional_guardduty_evidence")

    def test_ssm_poll_reports_bounded_wait_and_terminal_state(self):
        class FakeAws:
            def __init__(self):
                self.responses = iter([{"Status": "InProgress"}, {"Status": "Success"}])

            def call(self, service, *args):
                self.assert_service = service
                return next(self.responses)

        stderr = StringIO()
        with redirect_stderr(stderr), patch.object(MODULE.time, "sleep"):
            result = MODULE.poll_ssm(FakeAws(), "cmd-test", "i-test", 2, 0)
        self.assertEqual(result["Status"], "Success")
        self.assertIn("WAITING", stderr.getvalue())
        self.assertIn("status=Success", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
