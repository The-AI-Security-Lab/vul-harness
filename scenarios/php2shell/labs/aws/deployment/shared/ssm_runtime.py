#!/usr/bin/env python3
"""Transfer the approved PHP2Shell Compose assets and run them through SSM."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[6]
DEFAULT_PROFILE = "vul-harness-lab-nov26"
DEFAULT_REGION = "us-east-1"
METHOD_TAG = {
    "aws-cli": "aws-cli",
    "cloudformation": "cloudformation",
    "terraform": "terraform",
}
COMPOSE_VERSION = "v2.39.2"


class RuntimeErrorWithEvidence(RuntimeError):
    pass


def aws_call(profile: str, region: str, service: str, *args: str) -> Any:
    command = ["aws", "--profile", profile, "--region", region, "--no-cli-pager", service, *args, "--output", "json"]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        message = result.stderr.strip().splitlines()
        raise RuntimeErrorWithEvidence(message[-1] if message else f"aws {service} failed")
    return json.loads(result.stdout or "null")


def find_instance(profile: str, region: str, method: str, deployment_id: str, lab_id: str) -> str:
    filters = [
        "Name=tag:VulHarnessProject,Values=VulHarness",
        "Name=tag:VulHarnessScenario,Values=php2shell",
        "Name=tag:VulHarnessEnvironment,Values=aws-ec2",
        f"Name=tag:VulHarnessDeployment,Values={deployment_id}",
        f"Name=tag:VulHarnessDeploymentMethod,Values={METHOD_TAG[method]}",
        f"Name=tag:VulHarnessLab,Values={lab_id}",
    ]
    response = aws_call(profile, region, "ec2", "describe-instances", "--filters", *filters)
    instances = [instance for reservation in response.get("Reservations", []) for instance in reservation.get("Instances", []) if instance.get("State", {}).get("Name") != "terminated"]
    if len(instances) != 1:
        raise RuntimeErrorWithEvidence(f"expected exactly one active {lab_id} instance, found {len(instances)}")
    return instances[0]["InstanceId"]


def asset_paths(lab_id: str) -> list[Path]:
    lab = "lab-c" if lab_id == "lab-c" else "lab-d"
    return [
        REPOSITORY_ROOT / "scenarios/php2shell/labs/local/lab-a/app/index.php",
        REPOSITORY_ROOT / "scenarios/php2shell/labs/local/lab-a/nginx/default.conf",
        REPOSITORY_ROOT / f"scenarios/php2shell/labs/aws/{lab}/compose.{lab}.yaml",
    ]


def remote_path(path: Path) -> str:
    relative = path.relative_to(REPOSITORY_ROOT)
    return f"/opt/vulharness/{relative.as_posix()}"


def build_commands(lab_id: str, action: str) -> list[str]:
    paths = asset_paths(lab_id)
    commands = [
        "set -Eeuo pipefail",
        "sudo install -d -m 0755 /opt/vulharness/scenarios/php2shell/labs/local/lab-a/app",
        "sudo install -d -m 0755 /opt/vulharness/scenarios/php2shell/labs/local/lab-a/nginx",
        f"sudo install -d -m 0755 /opt/vulharness/scenarios/php2shell/labs/aws/{'lab-c' if lab_id == 'lab-c' else 'lab-d'}",
    ]
    for path in paths:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        destination = remote_path(path)
        expected_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        commands.extend([
            f"printf '%s' '{encoded}' | base64 --decode | sudo tee '{destination}' >/dev/null",
            f"test \"$(sudo sha256sum '{destination}' | awk '{{print $1}}')\" = '{expected_sha256}'",
            f"sudo chmod 0644 '{destination}'",
        ])
    commands.extend([
        "sudo dnf install -y docker",
        "sudo systemctl enable --now docker",
        "sudo install -d -m 0755 /usr/local/lib/docker/cli-plugins",
        "if ! sudo docker compose version >/dev/null 2>&1; then "
        "command -v curl >/dev/null 2>&1 && tmp_compose=$(mktemp) && "
        f"curl --fail --silent --show-error --location 'https://github.com/docker/compose/releases/download/{COMPOSE_VERSION}/docker-compose-linux-aarch64' -o \"$tmp_compose\" && "
        f"expected_compose_sha=$(curl --fail --silent --show-error --location 'https://github.com/docker/compose/releases/download/{COMPOSE_VERSION}/checksums.txt' | "
        "awk '{name=$2; sub(/^\\*/, \"\", name); if (name == \"docker-compose-linux-aarch64\") print $1}') && "
        "actual_compose_sha=$(sha256sum \"$tmp_compose\" | awk '{print $1}') && "
        "test -n \"$expected_compose_sha\" && test \"$expected_compose_sha\" = \"$actual_compose_sha\" && "
        "sudo install -m 0755 \"$tmp_compose\" /usr/local/lib/docker/cli-plugins/docker-compose && rm -f \"$tmp_compose\"; fi",
        "sudo docker compose version",
    ])
    compose = f"/opt/vulharness/scenarios/php2shell/labs/aws/{'lab-c' if lab_id == 'lab-c' else 'lab-d'}/compose.{lab_id}.yaml"
    if action == "remediate":
        update = "/opt/vulharness/scenarios/php2shell/labs/aws/lab-d/compose.lab-d.update.yaml"
        encoded = base64.b64encode((REPOSITORY_ROOT / "scenarios/php2shell/labs/aws/lab-d/compose.lab-d.update.yaml").read_bytes()).decode("ascii")
        expected_sha256 = hashlib.sha256((REPOSITORY_ROOT / "scenarios/php2shell/labs/aws/lab-d/compose.lab-d.update.yaml").read_bytes()).hexdigest()
        commands.extend([
            "sudo install -d -m 0755 /opt/vulharness/scenarios/php2shell/labs/aws/lab-d",
            f"printf '%s' '{encoded}' | base64 --decode | sudo tee '{update}' >/dev/null",
            f"test \"$(sudo sha256sum '{update}' | awk '{{print $1}}')\" = '{expected_sha256}'",
            f"sudo chmod 0644 '{update}'",
            f"sudo docker compose -f '{compose}' -f '{update}' config --quiet",
            f"sudo docker compose -f '{compose}' -f '{update}' pull",
            f"sudo docker compose -f '{compose}' -f '{update}' up -d --remove-orphans",
        ])
    else:
        commands.extend([
            f"sudo docker compose -f '{compose}' config --quiet",
            f"sudo docker compose -f '{compose}' pull",
            f"sudo docker compose -f '{compose}' up -d --remove-orphans",
        ])
    return commands


def run(profile: str, region: str, method: str, deployment_id: str, lab_id: str, action: str, attempts: int, seconds: float) -> None:
    instance_id = find_instance(profile, region, method, deployment_id, lab_id)
    commands = build_commands(lab_id, action)
    parameters = json.dumps({"commands": commands}, separators=(",", ":"))
    response = aws_call(profile, region, "ssm", "send-command", "--document-name", "AWS-RunShellScript", "--instance-ids", instance_id, "--parameters", parameters, "--timeout-seconds", "900")
    command_id = response["Command"]["CommandId"]
    terminal = {"Success", "Failed", "TimedOut", "Cancelled", "Cancelling"}
    last: dict[str, Any] = {}
    for _ in range(attempts):
        last = aws_call(profile, region, "ssm", "get-command-invocation", "--command-id", command_id, "--instance-id", instance_id)
        if last.get("Status") in terminal:
            break
        time.sleep(seconds)
    if last.get("Status") != "Success":
        raise RuntimeErrorWithEvidence(
            "SSM bootstrap timed out or failed: "
            f"deployment={deployment_id} lab={lab_id} instance={instance_id} "
            f"command={command_id} status={last.get('Status', 'unknown')} "
            f"recovery='python3 scenarios/php2shell/labs/aws/deployment/shared/ssm_runtime.py "
            f"{'remediate' if action == 'remediate' else 'bootstrap'} --method {method} "
            f"--deployment-id {deployment_id} --lab-id {lab_id}'"
        )
    print(f"SSM bootstrap succeeded: deployment={deployment_id} lab={lab_id} instance={instance_id} command={command_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("bootstrap", "reset", "remediate"))
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--region", default=DEFAULT_REGION)
    parser.add_argument("--method", choices=tuple(METHOD_TAG), required=True)
    parser.add_argument("--deployment-id", required=True)
    parser.add_argument("--lab-id", choices=("lab-c", "lab-d"), required=True)
    parser.add_argument("--attempts", type=int, default=120)
    parser.add_argument("--seconds", type=float, default=5)
    args = parser.parse_args()
    action = "remediate" if args.action == "remediate" else "base"
    try:
        run(args.profile, args.region, args.method, args.deployment_id, args.lab_id, action, args.attempts, args.seconds)
    except (OSError, RuntimeErrorWithEvidence) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
