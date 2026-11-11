#!/usr/bin/env python3
"""Independent AWS Lab C/D evaluator.

This evaluator uses AWS CLI read APIs and bounded SSM read-only commands. It is
deliberately separate from the infrastructure deployment implementations.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
DEFINITIONS = Path(__file__).with_name("evaluations.json")
CHECKER_PATH = ROOT / "scenarios/php2shell/checks/local-http-version/checker.py"
EXPECTED_POLICY = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"


def load_checker() -> Any:
    spec = importlib.util.spec_from_file_location("vulharness_php_checker", CHECKER_PATH)
    if spec is None or spec.loader is None:
        raise AwsEvaluationError(f"unable to load deterministic checker: {CHECKER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class AwsEvaluationError(RuntimeError):
    pass


@dataclass
class Result:
    evaluation_id: str
    status: str
    expected: str
    observed: str
    evidence: str
    failure_classification: str | None = None
    recovery_recommendation: str | None = None
    lab_id: str | None = None
    phase: str | None = None
    skip_classification: str | None = None

    @property
    def result_id(self) -> str:
        """Return a stable identity for this evaluation result instance.

        Contract IDs remain unchanged for existing consumers. Lab- and
        phase-scoped checks receive the additional context needed to keep the
        two EC2 results distinguishable in one evaluation artifact.
        """

        parts = [self.evaluation_id]
        if self.lab_id:
            parts.append(self.lab_id)
        if self.phase:
            parts.append(self.phase)
        return ":".join(parts)

    def as_dict(self) -> dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "result_id": self.result_id,
            "lab_id": self.lab_id,
            "phase": self.phase,
            "status": self.status,
            "expected_result": self.expected,
            "observed_result": self.observed,
            "evidence_location": self.evidence,
            "failure_classification": self.failure_classification,
            "recovery_recommendation": self.recovery_recommendation,
            "skip_classification": self.skip_classification,
        }


class Aws:
    def __init__(self, profile: str, region: str) -> None:
        self.profile = profile
        self.region = region

    def call(self, service: str, *args: str) -> Any:
        command = [
            "aws",
            "--profile",
            self.profile,
            "--region",
            self.region,
            "--no-cli-pager",
            service,
            *args,
            "--output",
            "json",
        ]
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        if completed.returncode != 0:
            detail = completed.stderr.strip().splitlines()
            raise AwsEvaluationError(detail[-1] if detail else f"aws {service} failed")
        try:
            return json.loads(completed.stdout or "null")
        except json.JSONDecodeError as exc:
            raise AwsEvaluationError(f"aws {service} returned invalid JSON") from exc


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def common_filters(deployment_id: str, method: str) -> list[str]:
    return [
        "Name=tag:VulHarnessProject,Values=VulHarness",
        "Name=tag:VulHarnessScenario,Values=php2shell",
        "Name=tag:VulHarnessEnvironment,Values=aws-ec2",
        f"Name=tag:VulHarnessDeployment,Values={deployment_id}",
        f"Name=tag:VulHarnessDeploymentMethod,Values={method}",
    ]


def tags(resource: dict[str, Any]) -> dict[str, str]:
    return {tag["Key"]: tag["Value"] for tag in resource.get("Tags", [])}


def is_owned_resource(resource: dict[str, Any], deployment_id: str, method: str) -> bool:
    required = {
        "VulHarnessProject": "VulHarness",
        "VulHarnessScenario": "php2shell",
        "VulHarnessEnvironment": "aws-ec2",
        "VulHarnessDeployment": deployment_id,
        "VulHarnessDeploymentMethod": method,
    }
    actual = tags(resource)
    return all(actual.get(key) == value for key, value in required.items())


def add_result(
    results: list[Result],
    evaluation_id: str,
    status: str,
    expected: str,
    observed: str,
    evidence: str,
    *,
    failure: str | None = None,
    recovery: str | None = None,
    lab_id: str | None = None,
    phase: str | None = None,
    skip_classification: str | None = None,
) -> None:
    results.append(Result(evaluation_id, status, expected, observed, evidence, failure, recovery, lab_id, phase, skip_classification))


def validate_result_identities(results: list[Result]) -> None:
    result_ids = [result.result_id for result in results]
    duplicates = sorted({result_id for result_id in result_ids if result_ids.count(result_id) > 1})
    if duplicates:
        raise AwsEvaluationError(f"duplicate evaluation result identities: {', '.join(duplicates)}")


def evaluate_guardduty_inventory(results: list[Result], inventory: dict[str, Any], evidence: str) -> None:
    endpoints = inventory.get("vpc_endpoints", [])
    if not endpoints:
        for definition_id in ("GD-001", "GD-002", "GD-003", "GD-004"):
            add_result(
                results,
                definition_id,
                "SKIP",
                "GuardDuty endpoint evidence is collected when present",
                "no VPC endpoint was observed",
                evidence,
                failure="NOT_COLLECTED",
                skip_classification="conditional_guardduty_evidence",
            )
    else:
        service_endpoints = [item for item in endpoints if item.get("ServiceName", "").endswith(".guardduty-data")]
        managed_endpoints = [item for item in service_endpoints if tags(item).get("GuardDutyManaged") == "true"]
        vpc_ids = {item.get("VpcId") for item in inventory.get("vpcs", [])}
        ambiguous = [item for item in endpoints if item not in managed_endpoints]
        add_result(results, "GD-001", "PASS" if managed_endpoints else "FAIL", "GuardDuty-managed endpoint is detected from VPC-scoped inventory", repr(managed_endpoints), evidence, failure=None if managed_endpoints else "GUARDDUTY_ENDPOINT_NOT_DETECTED")
        add_result(results, "GD-002", "PASS" if managed_endpoints and all(item.get("ServiceName", "").endswith(".guardduty-data") and tags(item).get("GuardDutyManaged") == "true" for item in managed_endpoints) else "FAIL", "service name and GuardDutyManaged metadata identify the service", repr(managed_endpoints), evidence, failure=None if managed_endpoints else "SERVICE_OWNERSHIP")
        add_result(results, "GD-003", "PASS" if managed_endpoints and all(item.get("VpcId") in vpc_ids for item in managed_endpoints) else "FAIL", "endpoint is inside the exact evaluated VPC", repr(sorted({item.get("VpcId") for item in managed_endpoints})), evidence, failure=None if managed_endpoints and all(item.get("VpcId") in vpc_ids for item in managed_endpoints) else "VPC_SCOPE")
        add_result(results, "GD-004", "PASS" if not ambiguous else "FAIL", "no unrelated or ambiguous endpoint is silently adopted", repr(ambiguous), evidence, failure=None if not ambiguous else "AMBIGUOUS_ENDPOINT")
    for definition_id in ("GD-005", "GD-006", "GD-007", "GD-008", "GD-009", "GD-010", "GD-011", "GD-012"):
        add_result(
            results,
            definition_id,
            "SKIP",
            "explicit GuardDuty cleanup evidence is supplied",
            "not supplied by this inventory run",
            evidence,
            failure="NOT_COLLECTED",
            skip_classification="conditional_guardduty_evidence",
        )


def collect_inventory(aws: Aws, deployment_id: str, method: str) -> dict[str, Any]:
    filters = common_filters(deployment_id, method)
    vpcs = aws.call("ec2", "describe-vpcs", "--filters", *filters)["Vpcs"]
    vpc_endpoints: list[dict[str, Any]] = []
    for vpc in vpcs:
        vpc_id = vpc.get("VpcId")
        if vpc_id:
            vpc_endpoints.extend(aws.call("ec2", "describe-vpc-endpoints", "--filters", f"Name=vpc-id,Values={vpc_id}").get("VpcEndpoints", []))
    subnets = aws.call("ec2", "describe-subnets", "--filters", *filters)["Subnets"]
    route_tables = aws.call("ec2", "describe-route-tables", "--filters", *filters)["RouteTables"]
    gateways = aws.call("ec2", "describe-internet-gateways", "--filters", *filters)["InternetGateways"]
    security_groups = aws.call("ec2", "describe-security-groups", "--filters", *filters)["SecurityGroups"]
    reservations = aws.call("ec2", "describe-instances", "--filters", *filters)["Reservations"]
    instances = [instance for reservation in reservations for instance in reservation["Instances"]]
    volumes = aws.call("ec2", "describe-volumes", "--filters", *filters)["Volumes"]
    interfaces = aws.call("ec2", "describe-network-interfaces", "--filters", *filters)["NetworkInterfaces"]
    return {
        "vpcs": vpcs,
        "vpc_endpoints": vpc_endpoints,
        "subnets": subnets,
        "route_tables": route_tables,
        "internet_gateways": gateways,
        "security_groups": security_groups,
        "instances": instances,
        "volumes": volumes,
        "network_interfaces": interfaces,
    }


def collect_iam_ownership(aws: Aws, deployment_id: str, method: str) -> dict[str, list[dict[str, Any]]]:
    """Collect only IAM objects carrying this exact deployment/method identity."""

    expected = {
        "VulHarnessProject": "VulHarness",
        "VulHarnessScenario": "php2shell",
        "VulHarnessEnvironment": "aws-ec2",
        "VulHarnessDeployment": deployment_id,
        "VulHarnessDeploymentMethod": method,
    }
    role_names: set[str] = set()
    profile_names: set[str] = set()
    if method in {"aws-cli", "terraform"}:
        role_names.add(f"vh-php2shell-{deployment_id}-role")
        profile_names.add(f"vh-php2shell-{deployment_id}-profile")
    else:
        role_candidates = aws.call("iam", "list-roles").get("Roles", [])
        for role in role_candidates:
            role_name = role.get("RoleName")
            if not role_name:
                continue
            role_tags = aws.call("iam", "list-role-tags", "--role-name", role_name).get("Tags", [])
            if all(next((tag.get("Value") for tag in role_tags if tag.get("Key") == key), None) == value for key, value in expected.items()):
                role_names.add(role_name)
        profile_candidates = aws.call("iam", "list-instance-profiles").get("InstanceProfiles", [])
        for profile in profile_candidates:
            profile_name = profile.get("InstanceProfileName")
            if not profile_name:
                continue
            profile_tags = aws.call("iam", "list-instance-profile-tags", "--instance-profile-name", profile_name).get("Tags", [])
            if all(next((tag.get("Value") for tag in profile_tags if tag.get("Key") == key), None) == value for key, value in expected.items()):
                profile_names.add(profile_name)

    roles: list[dict[str, Any]] = []
    for role_name in sorted(role_names):
        try:
            role = aws.call("iam", "get-role", "--role-name", role_name).get("Role")
        except AwsEvaluationError:
            continue
        if role:
            role["Tags"] = aws.call("iam", "list-role-tags", "--role-name", role_name).get("Tags", [])
            roles.append(role)
    profiles: list[dict[str, Any]] = []
    for profile_name in sorted(profile_names):
        try:
            profile = aws.call("iam", "get-instance-profile", "--instance-profile-name", profile_name).get("InstanceProfile")
        except AwsEvaluationError:
            continue
        if profile:
            profile["Tags"] = aws.call("iam", "list-instance-profile-tags", "--instance-profile-name", profile_name).get("Tags", [])
            profiles.append(profile)
    return {"roles": roles, "profiles": profiles}


def load_lifecycle_evidence(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise AwsEvaluationError(f"lifecycle evidence is not valid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0":
        raise AwsEvaluationError(f"lifecycle evidence has unsupported schema: {path}")
    return payload


def add_lifecycle_results(results: list[Result], lifecycle: dict[str, Any] | None, evidence: str) -> None:
    checks = (
        ("INF-011", "repeated_deployment", "repeated deployment calls safely reuse the same resources", "repeated deployment evidence"),
        ("INF-012", "partial_recovery", "partial deployment recovery creates only missing resources", "partial recovery evidence"),
        ("INF-015", "unrelated_resource_protection", "unrelated resources remain unchanged and unowned", "unrelated-resource inventory evidence"),
        ("RUN-010", "repeated_bootstrap", "repeated Docker/Compose bootstrap is safe", "repeated bootstrap evidence"),
        ("RUN-011", "interruption_recovery", "runtime interruption recovery is demonstrated", "interruption recovery evidence"),
        ("PHP-009", "repeated_remediation", "repeated Lab D remediation is safe", "repeated remediation evidence"),
    )
    for evaluation_id, key, expected, title in checks:
        item = lifecycle.get(key) if lifecycle else None
        if not isinstance(item, dict) or item.get("status") not in {"PASS", "FAIL"}:
            add_result(
                results,
                evaluation_id,
                "SKIP",
                expected,
                f"{title} was not supplied",
                evidence,
                failure="NOT_COLLECTED",
                recovery="Run the controlled lifecycle and pass its evidence manifest.",
                skip_classification="coverage_gap",
            )
            continue
        status = item["status"]
        scope = {"lab_id": "lab-d", "phase": "remediated"} if evaluation_id == "PHP-009" else {}
        add_result(results, evaluation_id, status, expected, str(item.get("observed", title)), str(item.get("evidence", evidence)), failure=None if status == "PASS" else item.get("failure", "LIFECYCLE_CHECK"), recovery=item.get("recovery"), **scope)


def root_volume(aws: Aws, instance: dict[str, Any]) -> dict[str, Any] | None:
    mappings = instance.get("BlockDeviceMappings", [])
    volume_id = next((item.get("Ebs", {}).get("VolumeId") for item in mappings if item.get("DeviceName") == "/dev/xvda"), None)
    if not volume_id:
        return None
    response = aws.call("ec2", "describe-volumes", "--volume-ids", volume_id)
    return response.get("Volumes", [None])[0]


def evaluate_protected_instance(results: list[Result], instances: list[dict[str, Any]], evidence: str, protected_instance_id: str | None, description: str) -> None:
    if not protected_instance_id:
        add_result(
            results,
            "INF-013",
            "SKIP",
            "protected instance is not in deployment inventory",
            "not configured; set VULHARNESS_PROTECTED_INSTANCE_ID for this account",
            evidence,
            skip_classification="configuration_missing",
        )
        return
    protected_seen = any(item.get("InstanceId") == protected_instance_id for item in instances)
    add_result(
        results,
        "INF-013",
        "PASS" if not protected_seen else "FAIL",
        description,
        f"protected_instance_seen={protected_seen}",
        evidence,
        failure=None if not protected_seen else "PROTECTED_RESOURCE",
    )


def evaluate_infrastructure(aws: Aws, inventory: dict[str, Any], deployment_id: str, method: str, results: list[Result], lifecycle: dict[str, Any] | None = None, lifecycle_evidence: str = "inventory.json", protected_instance_id: str | None = None) -> None:
    active = [item for item in inventory["instances"] if item.get("State", {}).get("Name") not in {"terminated", "shutting-down"}]
    labs = {tags(item).get("VulHarnessLab") for item in active}
    vpcs = inventory["vpcs"]
    subnets = inventory["subnets"]
    route_tables = inventory["route_tables"]
    gateways = inventory["internet_gateways"]
    groups = inventory["security_groups"]

    add_result(results, "INF-001", "PASS" if len(active) == 2 else "FAIL", "exactly two active tagged instances", f"{len(active)} active instances", "inventory.json", failure=None if len(active) == 2 else "RESOURCE_COUNT")
    add_result(results, "INF-002", "PASS" if labs == {"lab-c", "lab-d"} else "FAIL", "one lab-c and one lab-d", repr(sorted(labs)), "inventory.json", failure=None if labs == {"lab-c", "lab-d"} else "LAB_TAGS")

    identity_ok = bool(active) and all(item.get("InstanceType") == "t4g.small" and item.get("Architecture") == "arm64" for item in active)
    image_observed = []
    if identity_ok and aws is not None:
        for image_id in sorted({item.get("ImageId") for item in active if item.get("ImageId")}):
            images = aws.call("ec2", "describe-images", "--image-ids", image_id).get("Images", [])
            image = images[0] if len(images) == 1 else {}
            image_observed.append(f"{image_id}:{image.get('Name', 'missing')}")
            identity_ok = identity_ok and bool(image.get("Name", "").startswith("al2023-ami-2023")) and image.get("Architecture") == "arm64" and image.get("RootDeviceType") == "ebs"
    add_result(results, "INF-003", "PASS" if identity_ok else "FAIL", "t4g.small ARM64 Amazon Linux 2023 instances", " and ".join(f"{item.get('InstanceId')}:{item.get('InstanceType')}/{item.get('Architecture')}/{item.get('ImageId')}" for item in active) + f" images={image_observed!r}", "inventory.json", failure=None if identity_ok else "COMPUTE_CONFIGURATION")

    roots = [root_volume(aws, item) for item in active]
    roots_ok = len(roots) == 2 and all(root and root.get("Encrypted") is True and root.get("VolumeType") == "gp3" and root.get("Size") == 20 for root in roots)
    add_result(results, "INF-004", "PASS" if roots_ok else "FAIL", "two encrypted 20 GiB gp3 root volumes", repr([(root or {}).get("VolumeId") for root in roots]), "inventory.json", failure=None if roots_ok else "STORAGE_CONFIGURATION")

    imdsv2_ok = len(active) == 2 and all(item.get("MetadataOptions", {}).get("HttpTokens") == "required" for item in active)
    add_result(results, "INF-005", "PASS" if imdsv2_ok else "FAIL", "IMDSv2 required", repr([item.get("MetadataOptions", {}).get("HttpTokens") for item in active]), "inventory.json", failure=None if imdsv2_ok else "IMDS_CONFIGURATION")

    ingress_ok = len(groups) == 1 and len(groups[0].get("IpPermissions", [])) == 0
    add_result(results, "INF-006", "PASS" if ingress_ok else "FAIL", "one deployment security group with zero ingress rules", repr([len(group.get("IpPermissions", [])) for group in groups]), "inventory.json", failure=None if ingress_ok else "SECURITY_GROUP_CONFIGURATION")

    vpc_id = vpcs[0].get("VpcId") if len(vpcs) == 1 else None
    subnet_ok = len(subnets) == 1 and (not vpc_id or subnets[0].get("VpcId") == vpc_id) and subnets[0].get("MapPublicIpOnLaunch") is True
    gateway_ok = len(gateways) == 1 and any(attachment.get("VpcId") == vpc_id for attachment in gateways[0].get("Attachments", [])) if gateways else False
    route_ok = len(route_tables) == 1 and any(route.get("DestinationCidrBlock") == "0.0.0.0/0" and route.get("GatewayId") == (gateways[0].get("InternetGatewayId") if gateways else None) for route in route_tables[0].get("Routes", [])) if route_tables else False
    network_ok = len(vpcs) == 1 and not vpcs[0].get("IsDefault", True) and subnet_ok and gateway_ok and route_ok
    add_result(results, "INF-007", "PASS" if network_ok else "FAIL", "dedicated non-default VPC, public subnet, IGW and default route", f"vpcs={len(vpcs)} subnets={len(subnets)} gateways={len(gateways)} route_tables={len(route_tables)}", "inventory.json", failure=None if network_ok else "NETWORK_CONFIGURATION")

    profile_arns = {item.get("IamInstanceProfile", {}).get("Arn") for item in active if item.get("IamInstanceProfile")}
    iam_ok = len(profile_arns) == 1
    iam_observed = "instance_profiles=" + repr(sorted(profile_arns))
    if iam_ok:
        profile_name = next(iter(profile_arns)).rsplit("/", 1)[-1]
        try:
            profile = aws.call("iam", "get-instance-profile", "--instance-profile-name", profile_name)["InstanceProfile"]
            role = profile.get("Roles", [{}])[0].get("RoleName")
            policies = aws.call("iam", "list-attached-role-policies", "--role-name", role).get("AttachedPolicies", []) if role else []
            iam_ok = len(policies) == 1 and policies[0].get("PolicyArn") == EXPECTED_POLICY
            iam_observed += f" role={role} policies={[item.get('PolicyArn') for item in policies]}"
        except AwsEvaluationError as exc:
            iam_ok = False
            iam_observed += f" error={exc}"
    add_result(results, "INF-008", "PASS" if iam_ok else "FAIL", "dedicated role with only AmazonSSMManagedInstanceCore", iam_observed, "inventory.json", failure=None if iam_ok else "IAM_CONFIGURATION")

    required_tags = {"VulHarnessProject": "VulHarness", "VulHarnessScenario": "php2shell", "VulHarnessEnvironment": "aws-ec2", "VulHarnessDeployment": deployment_id, "VulHarnessDeploymentMethod": method}
    tagged_resources = vpcs + subnets + route_tables + gateways + groups + active + inventory["volumes"]
    tags_ok = bool(tagged_resources) and all(all(tags(resource).get(key) == value for key, value in required_tags.items()) for resource in tagged_resources)
    add_result(results, "INF-010", "PASS" if tags_ok else "FAIL", "all deployment resources carry exact ownership and method tags", f"checked={len(tagged_resources)}", "inventory.json", failure=None if tags_ok else "OWNERSHIP_TAGS")

    evaluate_protected_instance(results, active, "inventory.json", protected_instance_id, "protected instance is not in deployment inventory")
    evaluate_guardduty_inventory(results, inventory, "inventory.json")
    add_lifecycle_results(results, lifecycle, lifecycle_evidence)
    expirations = {tags(resource).get("VulHarnessExpires") for resource in tagged_resources if tags(resource).get("VulHarnessExpires")}
    expiration_ok = len(expirations) == 1
    add_result(results, "INF-016", "PASS" if expiration_ok else "FAIL", "one consistent expiration timestamp", repr(sorted(expirations)), "inventory.json", failure=None if expiration_ok else "EXPIRATION_METADATA")


def evaluate_cleanup_absence(aws: Aws, inventory: dict[str, Any], deployment_id: str, method: str, results: list[Result], evidence: str, protected_instance_id: str | None = None) -> None:
    iam = collect_iam_ownership(aws, deployment_id, method)
    external_endpoints = [
        item for item in inventory.get("vpc_endpoints", [])
        if not is_owned_resource(item, deployment_id, method)
    ]
    residual = {
        "vpcs": [item.get("VpcId") for item in inventory["vpcs"]],
        "subnets": [item.get("SubnetId") for item in inventory["subnets"]],
        "route_tables": [item.get("RouteTableId") for item in inventory["route_tables"]],
        "internet_gateways": [item.get("InternetGatewayId") for item in inventory["internet_gateways"]],
        "security_groups": [item.get("GroupId") for item in inventory["security_groups"]],
        "instances": [item.get("InstanceId") for item in inventory["instances"] if item.get("State", {}).get("Name") != "terminated"],
        "volumes": [item.get("VolumeId") for item in inventory["volumes"]],
        "network_interfaces": [item.get("NetworkInterfaceId") for item in inventory["network_interfaces"]],
        "iam_roles": [item.get("RoleName") for item in iam["roles"]],
        "iam_profiles": [item.get("InstanceProfileName") for item in iam["profiles"]],
    }
    absent = not any(residual.values())
    if external_endpoints:
        observed = json.dumps({"external_vpc_dependencies": external_endpoints, "residual_deployment_resources": residual}, sort_keys=True)
        add_result(
            results,
            "INF-014",
            "FAIL",
            "independent post-cleanup inventory contains no exact deployment resources",
            observed,
            evidence,
            failure="BLOCKED_BY_EXTERNAL_DEPENDENCY",
            recovery="Coordinate with the owning AWS service/account owner; do not delete the external dependency. Rerun absence verification after it is safely released.",
        )
    else:
        add_result(
            results,
            "INF-014",
            "PASS" if absent else "FAIL",
            "independent post-cleanup inventory contains no exact deployment resources",
            json.dumps(residual, sort_keys=True),
            evidence,
            failure=None if absent else "RESIDUAL_RESOURCES",
            recovery=None if absent else f"Inspect only these exact deployment resources and rerun cleanup: {json.dumps(residual, sort_keys=True)}",
        )
    evaluate_protected_instance(results, inventory["instances"], evidence, protected_instance_id, "protected instance is not in cleanup inventory")


def poll_ssm(aws: Aws, command_id: str, instance_id: str, attempts: int, seconds: float) -> dict[str, Any]:
    terminal = {"Success", "Failed", "TimedOut", "Cancelled", "Cancelling"}
    last: dict[str, Any] = {}
    for _ in range(attempts):
        response = aws.call("ssm", "get-command-invocation", "--command-id", command_id, "--instance-id", instance_id)
        last = response
        if response.get("Status") in terminal:
            return response
        time.sleep(seconds)
    raise AwsEvaluationError(f"SSM command {command_id} timed out; last status={last.get('Status', 'unknown')}")


def run_ssm(aws: Aws, instance_id: str, commands: list[str], attempts: int, seconds: float) -> dict[str, Any]:
    parameters = json.dumps({"commands": commands}, separators=(",", ":"))
    response = aws.call("ssm", "send-command", "--document-name", "AWS-RunShellScript", "--instance-ids", instance_id, "--parameters", parameters, "--timeout-seconds", "300")
    command_id = response["Command"]["CommandId"]
    result = poll_ssm(aws, command_id, instance_id, attempts, seconds)
    if result.get("Status") != "Success":
        raise AwsEvaluationError(f"SSM command {command_id} ended with {result.get('Status')}")
    return result


def parse_marker(output: str, marker: str) -> str:
    prefix = f"__VULHARNESS_{marker}__"
    normalized = re.sub(r"(__VULHARNESS_[A-Z]+__)", r"\n\1\n", output)
    lines = normalized.splitlines()
    for line_number, line in enumerate(lines):
        if line.strip() == prefix:
            values = []
            for value in lines[line_number + 1:]:
                if value.startswith("__VULHARNESS_") and value.endswith("__"):
                    break
                values.append(value)
            return "\n".join(values).strip()
    return ""


def expected_php_version(lab_id: str, phase: str) -> str:
    if lab_id == "lab-c":
        return "8.4.27"
    return "8.4.27" if phase == "remediated" else "8.4.26"


def add_php_results(
    results: list[Result],
    lab_id: str,
    phase: str,
    runtime: dict[str, Any],
    compose_output: str,
    image_output: str,
    evidence: str,
) -> None:
    version = runtime.get("php_version")
    sapi = runtime.get("sapi")
    expected = expected_php_version(lab_id, phase)
    version_ok = version == expected
    checker = load_checker()
    target = checker.TargetConfig(lab_id, "http://127.0.0.1:8080")
    try:
        parsed = checker.parse_runtime_document(runtime)
        report = checker.assess_runtime(target, parsed)
        classification = checker.summary_result(report)
        checker_ok = classification == checker.FIXED if expected == "8.4.27" else classification == checker.POTENTIALLY_AFFECTED
    except Exception as exc:  # The evaluator must fail closed on malformed runtime evidence.
        classification = "inconclusive"
        checker_ok = False
        sapi = f"{sapi or 'unknown'}; checker_error={exc}"

    if lab_id == "lab-c":
        add_result(results, "PHP-001", "PASS" if version_ok else "FAIL", "Lab C serves PHP 8.4.27", f"{lab_id}: observed={version!r}", evidence, failure=None if version_ok else "PHP_VERSION", lab_id=lab_id, phase=phase)
    elif phase in {"initial", "reset"}:
        add_result(results, "PHP-002", "PASS" if version_ok else "FAIL", f"Lab D baseline serves PHP 8.4.26 ({phase})", f"{lab_id}: observed={version!r}", evidence, failure=None if version_ok else "PHP_BASELINE", lab_id=lab_id, phase=phase)
    add_result(results, "PHP-003", "PASS" if version and sapi else "FAIL", "actual PHP version and SAPI are independently inspected", f"{lab_id}: version={version!r} sapi={sapi!r}", evidence, failure=None if version and sapi else "PHP_EVIDENCE", lab_id=lab_id, phase=phase)
    add_result(results, "PHP-004", "PASS" if runtime else "FAIL", "PHP HTTP endpoint returns the approved runtime document", f"{lab_id}: JSON runtime document collected", evidence, failure=None if runtime else "HTTP_ENDPOINT", lab_id=lab_id, phase=phase)
    add_result(results, "PHP-005", "PASS" if compose_output.strip() and image_output.strip() else "FAIL", "container and image identity evidence is collected", f"{lab_id}: compose_ps={bool(compose_output.strip())} images={bool(image_output.strip())}", evidence, failure=None if compose_output.strip() and image_output.strip() else "CONTAINER_IDENTITY", lab_id=lab_id, phase=phase)
    if lab_id == "lab-d" and phase == "remediated":
        add_result(results, "PHP-006", "PASS" if version_ok else "FAIL", "Lab D remediation is applied", f"{lab_id}: observed={version!r}", evidence, failure=None if version_ok else "REMEDIATION_NOT_OBSERVED", lab_id=lab_id, phase=phase)
        add_result(results, "PHP-007", "PASS" if version_ok else "FAIL", "Lab D serves PHP 8.4.27 after remediation", f"{lab_id}: observed={version!r}", evidence, failure=None if version_ok else "PHP_REMEDIATION_VERSION", lab_id=lab_id, phase=phase)
        add_result(results, "PHP-008", "PASS" if version != "8.4.26" else "FAIL", "old Lab D runtime cannot satisfy remediation", f"{lab_id}: observed={version!r}", evidence, failure=None if version != "8.4.26" else "STALE_RUNTIME", lab_id=lab_id, phase=phase)
    elif lab_id == "lab-d":
        add_result(results, "PHP-006", "SKIP", "Lab D remediation is applied", f"phase={phase}; remediation not requested", evidence, failure="NOT_COLLECTED", skip_classification="phase_not_requested", lab_id=lab_id, phase=phase)
        add_result(results, "PHP-007", "SKIP", "Lab D serves PHP 8.4.27 after remediation", f"phase={phase}; after-state not requested", evidence, failure="NOT_COLLECTED", skip_classification="phase_not_requested", lab_id=lab_id, phase=phase)
        add_result(results, "PHP-008", "SKIP", "old Lab D runtime cannot satisfy remediation", f"phase={phase}; remediation not requested", evidence, failure="NOT_COLLECTED", skip_classification="phase_not_requested", lab_id=lab_id, phase=phase)
    if lab_id == "lab-d" and phase == "reset":
        add_result(results, "PHP-010", "PASS" if version_ok else "FAIL", "Lab D reset restores PHP 8.4.26 baseline", f"{lab_id}: observed={version!r}", evidence, failure=None if version_ok else "RESET_BASELINE", lab_id=lab_id, phase=phase)
    elif lab_id == "lab-d":
        add_result(results, "PHP-010", "SKIP", "Lab D reset restores PHP 8.4.26 baseline", f"phase={phase}; reset not requested", evidence, failure="NOT_COLLECTED", skip_classification="phase_not_requested", lab_id=lab_id, phase=phase)
    add_result(results, "PHP-011", "PASS" if checker_ok else "FAIL", f"expected {expected} and checker classification is supported", f"{lab_id}: expected={expected} observed={version!r} classification={classification}", evidence, failure=None if checker_ok else "CHECKER_CLASSIFICATION", lab_id=lab_id, phase=phase)
    add_result(results, "PHP-012", "PASS", "the approved runtime check uses loopback-only application binding", f"{lab_id}: endpoint queried only at 127.0.0.1 through SSM", evidence, lab_id=lab_id, phase=phase)


def evaluate_ssm_runtime(aws: Aws, inventory: dict[str, Any], results: list[Result], attempts: int, seconds: float, evidence_dir: Path, phase: str) -> None:
    active = {tags(item).get("VulHarnessLab"): item for item in inventory["instances"] if item.get("State", {}).get("Name") == "running"}
    for lab_id in ("lab-c", "lab-d"):
        instance = active.get(lab_id)
        if not instance:
            add_result(results, "INF-009", "FAIL", "SSM Online instance", f"{lab_id} running instance not found", "inventory.json", failure="MISSING_RESOURCE", lab_id=lab_id, phase=phase)
            continue
        instance_id = instance["InstanceId"]
        try:
            info = aws.call("ssm", "describe-instance-information", "--filters", f"Key=InstanceIds,Values={instance_id}").get("InstanceInformationList", [])
            online = bool(info and info[0].get("PingStatus") == "Online")
            add_result(results, "INF-009", "PASS" if online else "FAIL", f"{lab_id} SSM Online", repr(info), "ssm.json", failure=None if online else "SSM_NOT_ONLINE", lab_id=lab_id, phase=phase)
            if not online:
                continue
            compose = f"/opt/vulharness/scenarios/php2shell/labs/aws/{lab_id}/compose.{lab_id}.yaml"
            invocation = run_ssm(aws, instance_id, [
                "set -eu",
                "printf '%s\\n' __VULHARNESS_DOCKER__",
                "docker --version",
                "docker info --format '{{json .ServerVersion}}'",
                "printf '%s\\n' __VULHARNESS_COMPOSE__",
                "docker compose version",
                f"test -f '{compose}'",
                "printf '%s\\n' __VULHARNESS_PS__",
                f"docker compose -f '{compose}' ps --format json",
                "printf '%s\\n' __VULHARNESS_CONFIG__",
                f"docker compose -f '{compose}' config --format json; printf '\\n'",
                "printf '%s\\n' __VULHARNESS_IMAGES__",
                f"docker compose -f '{compose}' images --format json",
                "printf '%s\\n' __VULHARNESS_RUNTIME__",
                "curl --fail --silent --show-error --max-time 5 'http://127.0.0.1:8080/?inspect=1&format=json'",
            ], attempts, seconds)
            output = invocation.get("StandardOutputContent", "")
            (evidence_dir / f"{lab_id}-ssm-runtime.txt").write_text(output)
            add_result(results, "RUN-001", "PASS", "Docker installed", "docker command returned successfully", f"{lab_id}-ssm-runtime.txt", lab_id=lab_id, phase=phase)
            add_result(results, "RUN-002", "PASS", "Docker daemon operational", "docker info returned successfully", f"{lab_id}-ssm-runtime.txt", lab_id=lab_id, phase=phase)
            add_result(results, "RUN-003", "PASS", "Docker Compose available", "docker compose version returned successfully", f"{lab_id}-ssm-runtime.txt", lab_id=lab_id, phase=phase)
            add_result(results, "RUN-004", "PASS", "Compose asset present", "compose.yaml present", f"{lab_id}-ssm-runtime.txt", lab_id=lab_id, phase=phase)
            compose_output = parse_marker(output, "PS")
            config_output = parse_marker(output, "CONFIG")
            image_output = parse_marker(output, "IMAGES")
            runtime_text = parse_marker(output, "RUNTIME")
            try:
                runtime = json.loads(runtime_text)
            except json.JSONDecodeError as exc:
                runtime = {}
                add_result(results, "RUN-008", "FAIL", "loopback HTTP response is valid JSON", f"{lab_id}: {exc}", f"{lab_id}-ssm-runtime.txt", failure="RUNTIME_JSON", lab_id=lab_id, phase=phase)
            add_result(results, "RUN-005", "PASS" if compose_output else "FAIL", "Compose configuration valid", f"{lab_id}: compose output collected", f"{lab_id}-ssm-runtime.txt", failure=None if compose_output else "COMPOSE_OUTPUT", lab_id=lab_id, phase=phase)
            add_result(results, "RUN-006", "PASS" if compose_output else "FAIL", "Containers running", f"{lab_id}: compose ps output collected", f"{lab_id}-ssm-runtime.txt", failure=None if compose_output else "CONTAINERS", lab_id=lab_id, phase=phase)
            add_result(results, "RUN-007", "PASS" if compose_output else "FAIL", "Container health/status is inspectable", f"{lab_id}: compose ps output collected", f"{lab_id}-ssm-runtime.txt", failure=None if compose_output else "CONTAINER_STATUS", lab_id=lab_id, phase=phase)
            if runtime:
                add_result(results, "RUN-008", "PASS", "Loopback HTTP response", f"{lab_id}: runtime JSON parsed", f"{lab_id}-ssm-runtime.txt", lab_id=lab_id, phase=phase)
            loopback_config_ok = "127.0.0.1" in config_output and "0.0.0.0" not in config_output
            add_result(results, "RUN-009", "PASS" if loopback_config_ok else "FAIL", "approved Compose model binds the PHP endpoint to loopback only", f"{lab_id}: loopback_config={loopback_config_ok}", f"{lab_id}-ssm-runtime.txt", failure=None if loopback_config_ok else "PUBLIC_BINDING", lab_id=lab_id, phase=phase)
            add_result(results, "RUN-012", "PASS", "Runtime evidence collected through SSM", "SSM invocation succeeded", f"{lab_id}-ssm-runtime.txt", lab_id=lab_id, phase=phase)
            if runtime:
                add_php_results(results, lab_id, phase, runtime, compose_output, image_output, f"{lab_id}-ssm-runtime.txt")
        except AwsEvaluationError as exc:
            add_result(results, "RUN-012", "FAIL", "runtime evidence through SSM", str(exc), "ssm.json", failure="SSM_ERROR", recovery="Inspect SSM registration and retry with bounded polling.", lab_id=lab_id, phase=phase)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="vul-harness-lab-nov26")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--method", choices=("aws-cli", "cloudformation", "terraform"), required=True)
    parser.add_argument("--deployment-id", required=True)
    parser.add_argument("--evidence-dir", type=Path, default=None)
    parser.add_argument("--include-ssm", action="store_true")
    parser.add_argument("--phase", choices=("initial", "remediated", "reset"), default="initial")
    parser.add_argument("--lifecycle-evidence", type=Path, default=None, help="JSON manifest for recovery, idempotency, and unrelated-resource checks")
    parser.add_argument("--expect-absent", action="store_true", help="verify exact deployment resources are absent after cleanup")
    parser.add_argument("--protected-instance-id", default=os.environ.get("VULHARNESS_PROTECTED_INSTANCE_ID"), help="account-specific protected instance ID; prefer VULHARNESS_PROTECTED_INSTANCE_ID and never commit it")
    parser.add_argument("--ssm-attempts", type=int, default=40)
    parser.add_argument("--ssm-seconds", type=float, default=5)
    args = parser.parse_args()
    evidence_dir = args.evidence_dir or Path("docs/evidence/aws") / args.method / args.deployment_id
    evidence_dir.mkdir(parents=True, exist_ok=True)
    results: list[Result] = []
    metadata = {"schema_version": "1.0", "evaluation_version": "1.0", "scenario": "php2shell", "deployment_method": args.method, "deployment_id": args.deployment_id, "region": args.region, "profile": args.profile, "observed_at": now(), "mode": "cleanup-absence" if args.expect_absent else "lifecycle"}
    aws = Aws(args.profile, args.region)
    try:
        inventory = collect_inventory(aws, args.deployment_id, args.method)
        (evidence_dir / "inventory.json").write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n")
        lifecycle = load_lifecycle_evidence(args.lifecycle_evidence)
        lifecycle_location = str(args.lifecycle_evidence) if args.lifecycle_evidence else "inventory.json"
        if args.expect_absent:
            evaluate_cleanup_absence(aws, inventory, args.deployment_id, args.method, results, "inventory.json", args.protected_instance_id)
            evaluate_guardduty_inventory(results, inventory, "inventory.json")
        else:
            evaluate_infrastructure(aws, inventory, args.deployment_id, args.method, results, lifecycle, lifecycle_location, args.protected_instance_id)
        if args.include_ssm and not args.expect_absent:
            evaluate_ssm_runtime(aws, inventory, results, args.ssm_attempts, args.ssm_seconds, evidence_dir, args.phase)
        elif not args.expect_absent:
            for lab_id in ("lab-c", "lab-d"):
                add_result(results, "RUN-001", "SKIP", "runtime evaluation requested explicitly", "not requested", "inventory.json", failure="NOT_COLLECTED", skip_classification="coverage_gap", lab_id=lab_id, phase=args.phase)
    except AwsEvaluationError as exc:
        (evidence_dir / "evaluation-error.txt").write_text(str(exc) + "\n")
        # Do not mix partial observations with the fail-closed API-error
        # result set; that could create duplicate contract identities.
        results.clear()
        for definition in json.loads(DEFINITIONS.read_text())["evaluations"]:
            if definition["id"].startswith(("INF-", "RUN-")):
                if definition.get("scope", "deployment") == "lab":
                    for lab_id in ("lab-c", "lab-d"):
                        add_result(results, definition["id"], "FAIL", definition["title"], str(exc), "evaluation-error.txt", failure="API_ERROR", recovery="Fix the AWS API or permission error, then rerun the evaluator.", lab_id=lab_id, phase=args.phase)
                else:
                    add_result(results, definition["id"], "FAIL", definition["title"], str(exc), "evaluation-error.txt", failure="API_ERROR", recovery="Fix the AWS API or permission error, then rerun the evaluator.")
    try:
        validate_result_identities(results)
    except AwsEvaluationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    blocked_count = sum(item.failure_classification == "BLOCKED_BY_EXTERNAL_DEPENDENCY" for item in results)
    payload = {**metadata, "results": [result.as_dict() for result in results], "summary": {"PASS": sum(item.status == "PASS" for item in results), "FAIL": sum(item.status == "FAIL" for item in results), "SKIP": sum(item.status == "SKIP" for item in results), "BLOCKED_BY_EXTERNAL_DEPENDENCY": blocked_count}}
    (evidence_dir / "evaluation.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"Deployment method: {args.method}")
    print(f"Deployment ID: {args.deployment_id}")
    print(f"Results: PASS={payload['summary']['PASS']} FAIL={payload['summary']['FAIL']} SKIP={payload['summary']['SKIP']} BLOCKED_BY_EXTERNAL_DEPENDENCY={payload['summary']['BLOCKED_BY_EXTERNAL_DEPENDENCY']}")
    for item in results:
        print(f"{item.result_id}: {item.status} — {item.observed}")
    if payload["summary"]["BLOCKED_BY_EXTERNAL_DEPENDENCY"]:
        return 2
    return 1 if payload["summary"]["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
