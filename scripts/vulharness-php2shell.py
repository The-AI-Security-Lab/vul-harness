#!/usr/bin/env python3
"""Participant-facing orchestration for the PHP2Shell scenario.

This command is deliberately a coordinator.  It validates scope and approval,
then invokes the existing lab, deployment, runtime, and evaluator commands.
It does not contain vulnerability, PHP-version, or AWS ownership logic.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import selectors
import secrets
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
AWS_PROFILE_DEFAULT = "vul-harness-lab-nov26"
AWS_REGION_DEFAULT = "us-east-1"
OWNER_DEFAULT = "workshop"
ORCHESTRATION_DIR = ROOT / ".vulharness-orchestration"
DEPLOYMENT_METADATA_DIR = ORCHESTRATION_DIR / "deployments"

COMMANDS = (
    "help",
    "preflight",
    "setup",
    "status",
    "inspect",
    "assess",
    "dashboard",
    "remediate",
    "verify",
    "reset",
    "cleanup",
)
AWS_METHODS = ("aws-cli", "cloudformation", "terraform")
LOCAL_LABS = ("lab-a", "lab-b")
AWS_LABS = ("lab-c", "lab-d")

EXIT_OK = 0
EXIT_OPERATION_FAILED = 1
EXIT_USAGE = 2
EXIT_PREREQUISITE = 3
EXIT_BLOCKED = 4

REDACTIONS = (
    (re.compile(r"(?i)(aws_secret_access_key\s*[=:]\s*)[^\s,;]+"), r"\1<redacted>"),
    (re.compile(r"(?i)(aws_session_token\s*[=:]\s*)[^\s,;]+"), r"\1<redacted>"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "<redacted-access-key>"),
)


class HarnessError(Exception):
    """A user-facing validation or orchestration error."""

    def __init__(self, message: str, code: int = EXIT_USAGE):
        super().__init__(message)
        self.code = code


def redact(value: str) -> str:
    for pattern, replacement in REDACTIONS:
        value = pattern.sub(replacement, value)
    return value


def progress(message: str, status: str) -> None:
    """Emit participant-facing progress without contaminating JSON stdout."""

    print(f"[VulHarness] {message} {status}", file=sys.stderr, flush=True)


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def timestamp_id(method: str) -> str:
    prefix = {"aws-cli": "cli", "cloudformation": "cfn", "terraform": "tf"}[method]
    now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"vh-{prefix}-{now}-{secrets.token_hex(4)}"


def default_expiry() -> str:
    return (
        (datetime.now(timezone.utc) + timedelta(hours=24))
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def compose_file(lab: str) -> Path:
    return ROOT / "scenarios" / "php2shell" / "labs" / "local" / lab / f"compose.{lab}.yaml"


def wrapper_path(method: str) -> Path:
    if method == "aws-cli":
        return ROOT / "scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh"
    if method == "cloudformation":
        return ROOT / "scenarios/php2shell/labs/aws/deployment/cloudformation/cf-lab.sh"
    return ROOT / "scenarios/php2shell/labs/aws/deployment/terraform/tf-lab.sh"


def script_path(relative: str) -> Path:
    return ROOT / relative


def aws_common(args: argparse.Namespace) -> list[str]:
    return ["--profile", args.profile, "--region", args.region]


def aws_env(args: argparse.Namespace, method: str | None = None) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "AWS_PROFILE": args.profile,
            "AWS_REGION": args.region,
            "AWS_PAGER": "",
        }
    )
    if method == "terraform":
        environment["AWS_SDK_LOAD_CONFIG"] = "1"
    if method == "aws-cli":
        environment["VULHARNESS_OWNER"] = resolve_owner(args)
    return environment


def execute(
    args: argparse.Namespace,
    label: str,
    command: list[str],
    *,
    environment: dict[str, str] | None = None,
    inherit_stdio: bool = False,
) -> dict[str, Any]:
    """Run one existing component without invoking a shell."""

    result: dict[str, Any] = {
        "label": label,
        "command": command,
        "returncode": None,
        "ok": False,
    }
    try:
        if args.output == "text" and not inherit_stdio:
            process = subprocess.Popen(
                command,
                cwd=ROOT,
                env=environment or os.environ.copy(),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,
            )
            selector = selectors.DefaultSelector()
            assert process.stdout is not None
            assert process.stderr is not None
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")
            captured = {"stdout": [], "stderr": []}
            while selector.get_map():
                for key, _ in selector.select(timeout=0.25):
                    line = key.fileobj.readline()
                    if line == "":
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                        continue
                    stream = key.data
                    safe_line = redact(line)
                    captured[stream].append(safe_line)
                    print(safe_line, end="", file=sys.stdout if stream == "stdout" else sys.stderr, flush=True)
            returncode = process.wait()
            result.update(
                {
                    "returncode": returncode,
                    "ok": returncode == 0,
                    "stdout": "".join(captured["stdout"]),
                    "stderr": "".join(captured["stderr"]),
                }
            )
            return result

        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=environment or os.environ.copy(),
            check=False,
            text=True,
            capture_output=not inherit_stdio,
        )
    except FileNotFoundError as exc:
        result.update({"returncode": 127, "error": str(exc)})
        if args.output == "text":
            print(f"ERROR: prerequisite command is unavailable: {command[0]}", file=sys.stderr)
        return result
    except OSError as exc:
        result.update({"returncode": 126, "error": str(exc)})
        if args.output == "text":
            print(f"ERROR: could not execute {command[0]}: {exc}", file=sys.stderr)
        return result

    result.update({"returncode": completed.returncode, "ok": completed.returncode == 0})
    if not inherit_stdio:
        result["stdout"] = redact(completed.stdout or "")
        result["stderr"] = redact(completed.stderr or "")
        if args.output == "text":
            if completed.stdout:
                print(redact(completed.stdout), end="")
            if completed.stderr:
                print(redact(completed.stderr), end="", file=sys.stderr)
    return result


def mapped_exit(result: dict[str, Any], *, blocked_codes: Iterable[int] = (2,)) -> int:
    code = result.get("returncode")
    if code in (None, 127, 126):
        return EXIT_PREREQUISITE
    if code == 0:
        return EXIT_OK
    if code in blocked_codes:
        return EXIT_BLOCKED
    return EXIT_OPERATION_FAILED


def run_plan(
    args: argparse.Namespace,
    operation: str,
    plan: list[tuple[str, list[str], dict[str, str] | None]],
    *,
    inherit_stdio: bool = False,
    blocked_codes: Iterable[int] = (2,),
) -> int:
    steps: list[dict[str, Any]] = []
    exit_code = EXIT_OK
    progress(operation, "STARTED")
    for index, (label, command, environment) in enumerate(plan, start=1):
        progress(f"{operation} step {index}/{len(plan)}: {label}", "STARTED")
        step = execute(
            args,
            label,
            command,
            environment=environment,
            inherit_stdio=inherit_stdio,
        )
        steps.append(step)
        if not step["ok"]:
            exit_code = mapped_exit(step, blocked_codes=blocked_codes)
            progress(
                f"{operation} step {index}/{len(plan)}: {label} (exit {step['returncode']})",
                "FAILED",
            )
            for skipped_index, (skipped_label, _, _) in enumerate(plan[index:], start=index + 1):
                progress(
                    f"{operation} step {skipped_index}/{len(plan)}: {skipped_label}",
                    "SKIPPED",
                )
            break
        progress(f"{operation} step {index}/{len(plan)}: {label}", "OK")
    progress(operation, "OK" if exit_code == EXIT_OK else "FAILED")
    payload = {
        "operation": operation,
        "ok": exit_code == EXIT_OK,
        "exit_code": exit_code,
        "steps": steps,
    }
    if args.deployment_id:
        payload["deployment_id"] = args.deployment_id
    if args.method:
        payload["method"] = args.method
    if args.env:
        payload["env"] = args.env
    if args.env == "aws" and args.method and args.deployment_id:
        evidence = ROOT / "docs" / "evidence" / "aws" / args.method / args.deployment_id
        payload["evidence_dir"] = str(evidence.relative_to(ROOT))
        if exit_code != EXIT_OK:
            recovery = [
                "python3 scripts/vulharness-php2shell.py",
                "--env aws",
                "--method",
                args.method,
                "--deployment-id",
                args.deployment_id,
            ]
            payload["recovery_commands"] = [
                " ".join(recovery + ["status"]),
                " ".join(recovery + ["cleanup", "--dry-run"]),
            ]
    if args.output == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    return exit_code


def emit_message(args: argparse.Namespace, message: str, *, code: int = EXIT_USAGE) -> int:
    if args.output == "json":
        print(json.dumps({"ok": False, "exit_code": code, "error": message}, indent=2))
    else:
        print(f"ERROR: {message}", file=sys.stderr)
    return code


def validate(args: argparse.Namespace) -> None:
    if args.command in (None, "help"):
        return
    if not args.env:
        raise HarnessError("--env is required for every command except help")
    if args.method and args.env != "aws":
        raise HarnessError("--method is valid only with --env aws")
    if args.env == "aws" and args.command != "help" and not args.method:
        raise HarnessError("--method is required with --env aws")
    if args.lab and args.env == "local" and args.lab not in LOCAL_LABS:
        raise HarnessError("local environments support only --lab lab-a or --lab lab-b")
    if args.lab and args.env == "aws" and args.lab not in AWS_LABS:
        raise HarnessError("AWS environments support only --lab lab-c or --lab lab-d")
    if args.phase and args.state:
        raise HarnessError("--phase and --state cannot be used together")
    if args.phase and args.env != "aws":
        raise HarnessError("--phase is valid only with --env aws")
    if args.phase and args.command not in {"assess", "verify"}:
        raise HarnessError("--phase is valid only for assess or verify")
    if args.state and args.env != "local":
        raise HarnessError("--state is valid only with --env local")
    if args.state and args.command != "assess":
        raise HarnessError("--state is valid only for local assess")
    if args.env == "local" and args.deployment_id:
        raise HarnessError("--deployment-id is valid only with --env aws")
    if args.dry_run and args.command != "cleanup":
        raise HarnessError("--dry-run is valid only with cleanup")
    if args.expect_absent and not (args.env == "aws" and args.command == "verify"):
        raise HarnessError("--expect-absent is valid only for AWS verify")
    if args.allow_guardduty_cleanup and not (args.env == "aws" and args.command == "cleanup"):
        raise HarnessError("--allow-guardduty-cleanup is valid only for AWS cleanup")
    if args.output == "json" and args.command == "dashboard":
        raise HarnessError("dashboard is interactive and does not support --output json")
    if args.output == "json" and args.command == "cleanup" and not args.dry_run:
        raise HarnessError("confirmed cleanup is interactive; use text output")

    if args.env == "aws":
        if not args.profile.strip():
            raise HarnessError("AWS profile must not be empty")
        if not args.region.strip():
            raise HarnessError("AWS Region must not be empty")
        if args.command == "dashboard":
            raise HarnessError("dashboard is currently supported only with --env local")
        if args.command in {"setup", "status", "cleanup"} and args.lab:
            raise HarnessError(f"AWS {args.command} is deployment-scoped; omit --lab")
        if args.command in {"inspect", "assess", "verify"} and args.lab:
            raise HarnessError(
                f"AWS {args.command} evaluates both Lab C and Lab D; omit --lab"
            )
        if args.command in {"remediate", "reset"} and args.lab != "lab-d":
            raise HarnessError(f"AWS {args.command} is supported only for --lab lab-d")
        if args.command in {"status", "inspect", "assess", "remediate", "verify", "reset", "cleanup"} and not args.deployment_id:
            raise HarnessError(f"AWS {args.command} requires --deployment-id")
        if args.command == "verify" and args.expect_absent and args.phase:
            raise HarnessError("--expect-absent cannot be combined with --phase")
        if args.command in {"assess", "verify"} and not args.expect_absent and not args.phase:
            args.phase = "initial"
    else:
        if args.command == "assess":
            if args.lab != "lab-b":
                raise HarnessError("local assess requires --lab lab-b")
            if not args.state:
                raise HarnessError("local assess requires --state before|config-only|after")
        if args.command == "dashboard" and args.lab:
            raise HarnessError("dashboard checks the configured local targets; omit --lab")
        if args.command in {"remediate", "reset"}:
            if args.lab != "lab-b":
                raise HarnessError(f"local {args.command} requires --lab lab-b")
        if args.command == "cleanup" and args.lab not in LOCAL_LABS:
            raise HarnessError("local cleanup requires exactly one named lab")
        if args.command in {"status", "inspect", "verify"} and args.state:
            raise HarnessError(f"local {args.command} does not use --state; use assess")

    protected_approval = {
        "setup": "setup",
        "remediate": "remediate",
        "reset": "reset",
    }
    if args.command in protected_approval and args.approve != protected_approval[args.command]:
        raise HarnessError(
            f"{args.command} requires explicit --approve {protected_approval[args.command]}"
        )
    if args.command == "cleanup" and not args.dry_run and args.approve != "cleanup":
        raise HarnessError("confirmed cleanup requires explicit --approve cleanup")
    if args.approve and args.approve not in {"setup", "remediate", "reset", "cleanup"}:
        raise HarnessError("unsupported approval token")


def local_compose_plan(args: argparse.Namespace, lab: str, operation: str) -> list[tuple[str, list[str], dict[str, str] | None]]:
    compose = ["docker", "compose", "-f", str(compose_file(lab))]
    if operation == "setup":
        if lab == "lab-a":
            return [("start lab-a", compose + ["up", "-d", "--build"], None)]
        update = compose_file("lab-b").with_name("compose.lab-b.update.yaml")
        base = ["docker", "compose", "-f", str(compose_file("lab-b"))]
        combined = base + ["-f", str(update)]
        return [
            ("reset lab-b project before setup", combined + ["down"], None),
            ("pull lab-b images", base + ["pull"], None),
            ("start lab-b", base + ["up", "-d"], None),
        ]
    if operation == "status":
        return [(f"status {lab}", compose + ["ps"], None)]
    if operation == "cleanup":
        if args.dry_run:
            return [(f"preview cleanup named {lab} project", compose + ["ps"], None)]
        return [(f"cleanup named {lab} project", compose + ["down"], None)]
    raise HarnessError(f"unsupported local Compose operation: {operation}")


def local_remediation_plan() -> list[tuple[str, list[str], dict[str, str] | None]]:
    base = ["docker", "compose", "-f", str(compose_file("lab-b"))]
    update = compose_file("lab-b").with_name("compose.lab-b.update.yaml")
    combined = base + ["-f", str(update)]
    return [
        ("pull remediated Lab B php-fpm image", combined + ["pull", "php-fpm"], None),
        (
            "recreate remediated Lab B services",
            combined + ["up", "-d", "--force-recreate", "php-fpm", "web"],
            None,
        ),
    ]


def local_plan(args: argparse.Namespace, operation: str) -> list[tuple[str, list[str], dict[str, str] | None]]:
    labs = [args.lab] if args.lab else list(LOCAL_LABS)
    if operation == "setup":
        plan: list[tuple[str, list[str], dict[str, str] | None]] = []
        for lab in labs:
            plan.extend(local_compose_plan(args, lab, "setup"))
        return plan
    if operation == "status":
        return [step for lab in labs for step in local_compose_plan(args, lab, "status")]
    if operation == "cleanup":
        return local_compose_plan(args, args.lab, "cleanup")
    raise HarnessError(f"unsupported local plan operation: {operation}")


def local_checker_plan(args: argparse.Namespace) -> list[tuple[str, list[str], dict[str, str] | None]]:
    command = [
        sys.executable,
        str(script_path("scenarios/php2shell/checks/local-http-version/cli.py")),
    ]
    if args.lab:
        command += ["--target", args.lab]
        label = f"inspect {args.lab} HTTP runtime"
    else:
        command += ["--all"]
        label = "inspect local HTTP runtimes"
    if args.output == "json":
        command += ["--json"]
    return [(label, command, None)]


def local_assess_plan(args: argparse.Namespace) -> list[tuple[str, list[str], dict[str, str] | None]]:
    return [
        (
            f"evaluate Lab B {args.state} state",
            [
                sys.executable,
                str(script_path("scenarios/php2shell/evals/remediation-lifecycle/evaluate.py")),
                "--state",
                args.state,
            ],
            None,
        )
    ]


def aws_preflight_plan(args: argparse.Namespace) -> list[tuple[str, list[str], dict[str, str] | None]]:
    if not command_exists("aws"):
        raise HarnessError("AWS CLI is not available on PATH", EXIT_PREREQUISITE)
    if not wrapper_path(args.method).exists():
        raise HarnessError(f"deployment wrapper is missing: {wrapper_path(args.method)}", EXIT_PREREQUISITE)
    plan = [
        (
            "resolve AWS caller identity",
            ["aws", *aws_common(args), "--no-cli-pager", "sts", "get-caller-identity", "--output", "json"],
            aws_env(args, args.method),
        )
    ]
    if args.method == "terraform":
        if not command_exists("terraform"):
            raise HarnessError("Terraform is not available on PATH", EXIT_PREREQUISITE)
        tf_dir = ROOT / "scenarios/php2shell/labs/aws/deployment/terraform"
        plan.extend(
            [
                ("inspect Terraform version", ["terraform", "version"], aws_env(args, "terraform")),
                (
                    "check Terraform formatting",
                    ["terraform", f"-chdir={tf_dir}", "fmt", "-check"],
                    aws_env(args, "terraform"),
                ),
                (
                    "initialize Terraform provider schema",
                    ["terraform", f"-chdir={tf_dir}", "validate"],
                    aws_env(args, "terraform"),
                ),
            ]
        )
    return plan


def aws_wrapper_plan(args: argparse.Namespace, action: str) -> list[tuple[str, list[str], dict[str, str] | None]]:
    wrapper = wrapper_path(args.method)
    command = [str(wrapper), *aws_common(args)]
    if args.deployment_id:
        command += ["--deployment-id", args.deployment_id]
    if args.expires_at:
        command += ["--expires-at", args.expires_at]
    if args.method != "aws-cli":
        command += ["--owner", resolve_owner(args)]
    if args.method == "terraform" and args.state_dir:
        command += ["--state-dir", args.state_dir]
    if args.allow_guardduty_cleanup:
        command += ["--allow-guardduty-cleanup"]
    if action == "cleanup" and args.dry_run:
        command += ["--dry-run"]
    command += [action]
    return [(f"AWS {args.method} {action}", command, aws_env(args, args.method))]


def aws_runtime_plan(
    args: argparse.Namespace,
    action: str,
    lab: str | None = None,
) -> list[tuple[str, list[str], dict[str, str] | None]]:
    lab_id = lab or args.lab
    if not lab_id:
        raise HarnessError(f"SSM {action} requires a lab identifier")
    command = [
        sys.executable,
        str(script_path("scenarios/php2shell/labs/aws/deployment/shared/ssm_runtime.py")),
        action,
        "--profile",
        args.profile,
        "--region",
        args.region,
        "--method",
        args.method,
        "--deployment-id",
        args.deployment_id,
        "--lab-id",
        lab_id,
    ]
    return [(f"SSM {action} {lab_id}", command, aws_env(args, args.method))]


def aws_evaluator_plan(args: argparse.Namespace, *, include_ssm: bool) -> list[tuple[str, list[str], dict[str, str] | None]]:
    command = [
        sys.executable,
        str(script_path("scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py")),
        "--profile",
        args.profile,
        "--region",
        args.region,
        "--method",
        args.method,
        "--deployment-id",
        args.deployment_id,
    ]
    if args.expect_absent:
        command += ["--expect-absent"]
    else:
        command += ["--phase", args.phase or "initial"]
        if include_ssm:
            command += ["--include-ssm"]
    return [("AWS lifecycle evaluator", command, aws_env(args, args.method))]


def metadata_path(deployment_id: str, method: str) -> Path:
    safe_method = method.replace("/", "-")
    safe_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", deployment_id)
    return DEPLOYMENT_METADATA_DIR / f"{safe_method}-{safe_id}.json"


def metadata_owner(args: argparse.Namespace) -> str:
    deployment_id = args.deployment_id or os.environ.get("VULHARNESS_DEPLOYMENT_ID", "")
    if not deployment_id or not args.method:
        return ""
    path = metadata_path(deployment_id, args.method)
    if not path.exists():
        return ""
    try:
        value = json.loads(path.read_text(encoding="utf-8")).get("owner", "")
    except (OSError, json.JSONDecodeError):
        return ""
    return value if isinstance(value, str) else ""


def resolve_owner(args: argparse.Namespace) -> str:
    if args.owner:
        return args.owner
    configured_owner = os.environ.get("VULHARNESS_OWNER", "")
    return configured_owner or metadata_owner(args) or OWNER_DEFAULT


def write_metadata(args: argparse.Namespace, status: str) -> None:
    DEPLOYMENT_METADATA_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "deployment_id": args.deployment_id,
        "method": args.method,
        "profile": args.profile,
        "region": args.region,
        "owner": args.owner,
        "expires_at": args.expires_at,
        "status": status,
        "metadata_path": str(metadata_path(args.deployment_id, args.method).relative_to(ROOT)),
    }
    metadata_path(args.deployment_id, args.method).write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def metadata_expiry(args: argparse.Namespace) -> str:
    path = metadata_path(args.deployment_id, args.method)
    if not path.exists():
        return ""
    try:
        value = json.loads(path.read_text(encoding="utf-8")).get("expires_at", "")
    except (OSError, json.JSONDecodeError):
        return ""
    return value if isinstance(value, str) else ""


def run_local(args: argparse.Namespace) -> int:
    if args.command == "preflight":
        missing = [name for name in ("docker",) if not command_exists(name)]
        if missing:
            return emit_message(args, f"missing local prerequisite(s): {', '.join(missing)}", code=EXIT_PREREQUISITE)
        return run_plan(
            args,
            "local preflight",
            [
                ("inspect Docker daemon", ["docker", "info"], None),
                ("inspect Docker Compose", ["docker", "compose", "version"], None),
            ],
        )
    if args.command in {"setup", "status", "cleanup"}:
        return run_plan(args, f"local {args.command}", local_plan(args, args.command))
    if args.command in {"inspect", "verify"}:
        return run_plan(args, f"local {args.command}", local_checker_plan(args))
    if args.command == "assess":
        return run_plan(args, "local assess", local_assess_plan(args))
    if args.command == "remediate":
        return run_plan(args, "local remediate", local_remediation_plan())
    if args.command == "reset":
        update = compose_file("lab-b").with_name("compose.lab-b.update.yaml")
        combined = ["docker", "compose", "-f", str(compose_file("lab-b")), "-f", str(update)]
        base = ["docker", "compose", "-f", str(compose_file("lab-b"))]
        return run_plan(
            args,
            "local reset",
            [
                ("stop Lab B update project", combined + ["down"], None),
                ("start Lab B baseline project", base + ["up", "-d"], None),
            ],
        )
    if args.command == "dashboard":
        dashboard = script_path("scenarios/php2shell/checks/local-http-version/dashboard.py")
        print("Dashboard: http://127.0.0.1:8081 (Ctrl-C to stop)")
        return run_plan(
            args,
            "local dashboard",
            [("start local dashboard", [sys.executable, str(dashboard)], None)],
            inherit_stdio=True,
        )
    raise HarnessError(f"unsupported local command: {args.command}")


def run_aws(args: argparse.Namespace) -> int:
    if args.command == "preflight":
        return run_plan(args, "AWS preflight", aws_preflight_plan(args))
    if args.command == "setup":
        requested_id = args.deployment_id or os.environ.get("VULHARNESS_DEPLOYMENT_ID", "")
        if requested_id:
            args.deployment_id = requested_id
        else:
            args.deployment_id = timestamp_id(args.method)
        args.owner = resolve_owner(args)
        if not args.expires_at:
            args.expires_at = os.environ.get("VULHARNESS_EXPIRES_AT", "") or metadata_expiry(args)
        if not args.expires_at and not requested_id:
            args.expires_at = default_expiry()
        write_metadata(args, "starting")
        plan = aws_preflight_plan(args) + aws_wrapper_plan(args, "deploy")
        for lab in AWS_LABS:
            plan.extend(aws_runtime_plan(args, "bootstrap", lab))
        code = run_plan(args, "AWS setup", plan)
        write_metadata(args, "deployed" if code == EXIT_OK else "partial-or-failed")
        if args.output == "text":
            print(f"Deployment ID: {args.deployment_id}")
            print(f"Metadata: {metadata_path(args.deployment_id, args.method).relative_to(ROOT)}")
        return code
    args.owner = resolve_owner(args)
    if args.command == "status":
        return run_plan(args, "AWS status", aws_wrapper_plan(args, "status"))
    if args.command == "inspect":
        return run_plan(args, "AWS inspect", aws_evaluator_plan(args, include_ssm=False))
    if args.command == "assess":
        return run_plan(args, "AWS assess", aws_evaluator_plan(args, include_ssm=True))
    if args.command == "verify":
        return run_plan(args, "AWS verify", aws_evaluator_plan(args, include_ssm=not args.expect_absent))
    if args.command == "remediate":
        return run_plan(args, "AWS remediate", aws_runtime_plan(args, "remediate"))
    if args.command == "reset":
        return run_plan(args, "AWS reset", aws_runtime_plan(args, "reset"))
    if args.command == "cleanup":
        return run_plan(
            args,
            "AWS cleanup",
            aws_wrapper_plan(args, "cleanup"),
            inherit_stdio=not args.dry_run,
        )
    raise HarnessError(f"unsupported AWS command: {args.command}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vulharness-php2shell.py",
        description="Scope-aware orchestration for the VulHarness PHP2Shell labs.",
    )
    parser.add_argument("command", nargs="?", choices=COMMANDS, help="operation to run")
    parser.add_argument("--env", choices=("local", "aws"), help="execution environment")
    parser.add_argument("--lab", choices=(*LOCAL_LABS, *AWS_LABS), help="one lab when the operation is lab-scoped")
    parser.add_argument("--method", choices=AWS_METHODS, help="AWS deployment method")
    parser.add_argument(
        "--deployment-id",
        default=os.environ.get("VULHARNESS_DEPLOYMENT_ID"),
        help="exact AWS deployment identity (or VULHARNESS_DEPLOYMENT_ID)",
    )
    parser.add_argument("--phase", choices=("initial", "remediated", "reset"), help="AWS evidence phase")
    parser.add_argument("--state", choices=("before", "config-only", "after"), help="local Lab B evaluation state")
    parser.add_argument("--output", choices=("text", "json"), default="text")
    parser.add_argument("--approve", choices=("setup", "remediate", "reset", "cleanup"), help="explicit operation approval")
    parser.add_argument("--profile", default=os.environ.get("AWS_PROFILE", AWS_PROFILE_DEFAULT))
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", AWS_REGION_DEFAULT))
    parser.add_argument("--owner", help="deployment owner (or VULHARNESS_OWNER)")
    parser.add_argument("--expires-at")
    parser.add_argument("--state-dir")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-guardduty-cleanup", action="store_true")
    parser.add_argument("--expect-absent", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in (None, "help"):
        parser.print_help()
        return EXIT_OK if args.command == "help" else EXIT_USAGE
    try:
        validate(args)
        if args.env == "local":
            return run_local(args)
        return run_aws(args)
    except HarnessError as exc:
        return emit_message(args, str(exc), code=exc.code)
    except KeyboardInterrupt:
        return emit_message(args, "operation interrupted; inspect the named scope before retrying", code=EXIT_OPERATION_FAILED)


if __name__ == "__main__":
    raise SystemExit(main())
