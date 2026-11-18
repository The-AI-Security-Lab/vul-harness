# PHP2Shell scenario

PHP2Shell is the first reference scenario for VulHarness. It demonstrates how a
manual vulnerability investigation can become repeatable deterministic checks
and independent evaluation without making PHP2Shell a special case in the
framework.

## What You Need to Know

PHP2Shell covers two upstream PHP security advisories:
[CVE-2026-109618](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w),
RCE via OOM corruption, and
[CVE-2026-109619](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp),
RCE via stale global state. The advisories list affected upstream branches
below `8.2.35`, `8.3.36`, `8.4.27`, and `8.5.12`; the corresponding fixed
upstream releases are `8.2.35`, `8.3.36`, `8.4.27`, and `8.5.12`.

Those are upstream `php-src` ranges, not a universal statement about every
installed package. Exposure depends on the serving runtime, SAPI, worker model,
request routing, configuration, extensions, frontend behavior, and vendor
backports. A version banner alone does not prove exploitability, and a fixed
version result does not prove complete remediation. Collect runtime provenance,
effective configuration, timestamps, evidence, and limitations. See the
[reference register](references.md) for authoritative sources and detailed
conditions.

This repository does not build or distribute an intentionally vulnerable
application. Participants provide or provision an isolated environment they
are authorized to test.

## Start the participant lab

Begin with the [canonical participant lab guide](walkthroughs/participant-lab-guide.md).
It is the single authoritative execution sequence for prerequisites, manual
investigation, deterministic checks, independent evaluation, optional AWS
operations, orchestration, and cleanup. Do not use this overview as a
replacement for the guide's step-by-step commands.

Local Labs A and B are the recommended starting point. They support the manual
investigation and local automation journey without AWS charges. AWS Labs C and
D are optional, independent environments; they may incur charges and require
an authorized AWS account, permissions, and explicit cleanup.

Manual investigation can be completed without the checker, evaluator, or
VulHarness orchestration command. Automation adds repeatable evidence
collection and comparison; it does not replace participant observation or
independent review.

## Choose Local or AWS

Choose one environment path for the investigation:

- **Local:** use the Docker Compose Labs A and B documented in the participant
  guide. This is the recommended first path for learning the evidence model.
- **AWS:** select one deployment method for Labs C and D: AWS CLI,
  CloudFormation, or Terraform. The wrappers provision infrastructure; the
  shared authenticated SSM workflow bootstraps or changes the runtime; the
  evaluator independently compares collected evidence with expected state.

AWS deployment methods are alternatives, not three steps in one deployment.
Keep the profile, Region, deployment ID, method, and owner consistent for
status, runtime actions, evaluation, and cleanup. AWS evidence may contain
account and resource identifiers and remains local under the ignored
`docs/evidence/aws/` path; it must not be committed or uploaded.

## Lab registry

Neutral identifiers keep the lab name separate from the finding a participant
must discover.

| Lab | Environment | Intended initial PHP | Documentation |
| --- | --- | --- | --- |
| Lab A (`lab-a`) | Local Docker | 8.4.27 | [Lab A](labs/local/lab-a/README.md) |
| Lab B (`lab-b`) | Local Docker | 8.4.26, with an 8.4.27 update override | [Lab B](labs/local/lab-b/README.md) |
| Lab C (`lab-c`) | AWS EC2 | 8.4.27 | [Lab C](labs/aws/lab-c/README.md) |
| Lab D (`lab-d`) | AWS EC2 | 8.4.26, with an 8.4.27 update override | [Lab D](labs/aws/lab-d/README.md) |

Labs A and B are independent local Compose projects on `127.0.0.1:8080` and
`127.0.0.1:8082`. Labs C and D are separate EC2 instances whose inspection
endpoint remains loopback-only.

## Current implementation and limitations

Implemented today:

- Manual local investigation and AWS Console/Session Manager inspection.
- Deterministic local runtime checks using explicitly configured endpoints.
- Independent local remediation-lifecycle and AWS lifecycle evaluations.
- AWS CLI, CloudFormation, and Terraform deployment alternatives.
- Shared authenticated SSM bootstrap, remediation, and reset operations.
- PHP2Shell-specific orchestration with scoped operations and approvals.

The checker classifies observed upstream PHP versions; it does not prove
exploitability. Evaluators compare evidence with expected conditions and do not
accept an agent, wrapper, or orchestrator self-report as proof. Offline tests
and mock coverage do not claim live AWS execution. Historical live AWS
validation is documented as historical validation, while raw account and
resource evidence remains private.

Planned or not implemented: reusable coding-agent skills, a Chief of Staff
Agent, generalized multi-scenario orchestration, automatic remediation,
external security integrations, and a provider-independent Core Harness.

## Folder structure and technical references

| Folder or reference | Responsibility |
| --- | --- |
| [`walkthroughs/`](walkthroughs/README.md) | Canonical participant journey, manual evidence methodology, and expected outcomes. |
| [`labs/`](labs/README.md) | Scenario-specific local and AWS environments, provider operations, and manual AWS inspection reference. |
| [`checks/`](checks/README.md) | Deterministic evidence collection and the shared PHP runtime checker. |
| [`evals/`](evals/README.md) | Independent comparisons of observed evidence with expected conditions. |
| [`scripts/`](../../scripts/README.md) | PHP2Shell-specific orchestration command contract and approval boundaries. |
| [`references.md`](references.md) | Authoritative advisory and technical reference register. |

Use the technical READMEs for implementation contracts, configuration details,
provider-specific troubleshooting, SSM recovery, Terraform state, IAM
ownership, GuardDuty cleanup dependencies, and evaluator result contracts.
They support the participant guide; they do not introduce a second execution
sequence.

## Custom Tools and Scripts

These files are PHP2Shell-specific unless a future scenario explicitly reuses
one through a provider-independent interface with its own documentation and
tests. A shared helper inside the PHP2Shell directory is not automatically a
generic VulHarness component. The participant guide introduces participant-facing
tools before their first meaningful use; test files are contributor checks, not
participant tools.

| File | Role and workflow | Effect, evidence, and prerequisites |
| --- | --- | --- |
| [`scripts/vulharness-php2shell.py`](../../scripts/vulharness-php2shell.py) | Harness orchestration for local and AWS lifecycles | Routes existing commands, validates scope and approvals, and preserves exit/JSON contracts. It may start, remediate, reset, or clean up only the explicitly named lab/deployment. Requires Python; AWS workflows also require the selected AWS toolchain. |
| [`checks/local-http-version/cli.py`](checks/local-http-version/cli.py) | Deterministic local runtime checker used in Auto Mode and by the local harness | Reads configured loopback HTTP endpoints and evaluates observed PHP version/SAPI. It does not change Docker or infrastructure. Requires Python and running local labs. |
| [`checks/local-http-version/checker.py`](checks/local-http-version/checker.py) | Shared checker engine imported by the CLI and evaluators | Parses bounded runtime evidence and applies documented version comparisons. It does not perform network discovery or mutations; participants normally invoke it through `cli.py` or an evaluator. Requires Python. |
| [`checks/local-http-version/dashboard.py`](checks/local-http-version/dashboard.py) | Local Hello World 2.0 inventory view | Serves a localhost-only dashboard and performs the same bounded local checks. It observes only; its disabled remediation controls do not edit files or containers. Requires Python and running local labs. |
| [`evals/remediation-lifecycle/evaluate.py`](evals/remediation-lifecycle/evaluate.py) | Independent local Lab B evaluator | Compares before, config-only, and after evidence, including read-only Compose/image inspection. It does not remediate or restart containers. Requires Python; config-only/after modes also require Docker for read-only inspection. |
| [`labs/aws/deployment/cli/aws-lab.sh`](labs/aws/deployment/cli/aws-lab.sh) | AWS CLI deployment and cleanup tool for Labs C/D | Creates/resumes, validates, reports, and deletes only exact tagged deployment resources. `cleanup` is destructive, requires dry-run review plus interactive approval, and requires AWS credentials and CLI permissions. |
| [`labs/aws/deployment/cloudformation/cf-lab.sh`](labs/aws/deployment/cloudformation/cf-lab.sh) | Independent CloudFormation deployment and cleanup tool | Creates or resumes the exact tagged stack and can delete that stack after guarded confirmation. It does not bootstrap Docker or inspect PHP. Requires AWS credentials, CLI, and CloudFormation/EC2/VPC/IAM permissions. |
| [`labs/aws/deployment/terraform/tf-lab.sh`](labs/aws/deployment/terraform/tf-lab.sh) | Independent Terraform deployment and cleanup tool | Creates or resumes method-scoped infrastructure in local Terraform state and can destroy only that state-backed deployment after guarded confirmation. Requires AWS credentials, CLI, Terraform, and a retained state directory. |
| [`labs/aws/deployment/shared/ssm_runtime.py`](labs/aws/deployment/shared/ssm_runtime.py) | Shared authenticated SSM runtime workflow for AWS Labs C/D | Transfers approved lab assets and runs bootstrap, remediation, or reset through SSM on one exact tagged instance. It changes the selected runtime but does not create/delete AWS infrastructure or use SSH. Requires AWS credentials, SSM access, and an existing deployment. |
| [`evals/aws-lifecycle/aws_evaluate.py`](evals/aws-lifecycle/aws_evaluate.py) | Independent AWS inventory, runtime, lifecycle, and absence evaluator | Collects exact deployment-scoped AWS/SSM evidence and compares it with expected infrastructure and PHP states. `--expect-absent` is read-only; the evaluator never deletes resources. Requires AWS credentials and an existing deployment, except that evidence can be reviewed offline afterward. |
| [`labs/aws/deployment/shared/guardduty_cleanup.sh`](labs/aws/deployment/shared/guardduty_cleanup.sh) | Shared cleanup safety helper sourced by AWS deployment wrappers | Detects and, only with the explicit GuardDuty cleanup opt-in and normal cleanup approval, releases verified GuardDuty endpoint dependencies inside the exact deployment VPC. It does not change account-level GuardDuty settings. Requires AWS credentials and wrapper-controlled cleanup. |

Compose files, browser diagnostics, and ordinary `docker compose`/`aws`
commands are manual investigation commands rather than custom executable
tools. Deployment wrappers are infrastructure automation; SSM is runtime
automation; the checker and evaluators are evidence tools; and cleanup remains
an explicit, scoped participant action.

## Contributing and future work

PHP2Shell is a reference scenario, not a requirement that every future scenario
use AWS, four labs, or the same evaluator. Read the
[scenario-development guide](../../docs/scenario-development-guide.md),
[CONTRIBUTING.md](../../CONTRIBUTING.md), and
[SECURITY.md](../../SECURITY.md) before contributing. Keep scenario-specific
content under `scenarios/`; keep reusable workflows, checks, skills, and
integrations separate. Do not add credentials, real target data, exploit
tooling, or intentionally vulnerable applications.
