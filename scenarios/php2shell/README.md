# PHP2Shell scenario

PHP2Shell is the first reference scenario for VulHarness. It demonstrates how a
manual vulnerability investigation can become a repeatable workflow with
deterministic checks and independent evaluation, without making PHP2Shell a
special case in the framework.

Start with the [canonical participant lab guide](walkthroughs/participant-lab-guide.md).
It is the single progressive journey; the technical READMEs linked below hold
environment-specific commands and implementation detail.

## Security context

PHP2Shell refers to two confirmed critical upstream PHP vulnerabilities:
[CVE-2026-109618](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w),
RCE via OOM corruption, and
[CVE-2026-109619](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp),
RCE via stale global state. The advisories list affected upstream branches
below `8.2.35`, `8.3.36`, `8.4.27`, and `8.5.12`; the corresponding fixed
upstream releases are `8.2.35`, `8.3.36`, `8.4.27`, and `8.5.12`.

Those ranges are upstream `php-src` ranges, not a universal statement about
every installed package. Exposure depends on the serving runtime, SAPI, worker
model, request routing, configuration, extensions, frontend behavior, and
vendor backports. A version banner is not proof. Collect provenance, effective
configuration, runtime evidence, timestamps, and limitations; patch to a fixed
release or authoritative vendor package rather than relying on a configuration
mitigation. See the [reference register](references.md) for authoritative
sources and detailed conditions.

This repository does not build or distribute an intentionally vulnerable
application. Participants provide or provision an isolated environment they
are authorized to test.

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
endpoint remains loopback-only. The [AWS lab plan](labs/aws/README.md) defines
AWS CLI, CloudFormation, and Terraform provisioning, shared SSM runtime
actions, and a scoped evaluator.

## Implementation map

- [Manual walkthroughs](walkthroughs/README.md) explain the investigation and
  evidence requirements.
- [Deterministic local checks](checks/local-http-version/README.md) inspect
  explicitly configured loopback targets.
- [Independent local evaluation](evals/remediation-lifecycle/evaluate.py)
  compares Lab B before, configuration-only, and after states.
- [Independent AWS evaluation](evals/aws-lifecycle/README.md) separates
  infrastructure, SSM, runtime, version classification, cleanup, and absence.
- [PHP2Shell orchestration](../../scripts/README.md) coordinates the existing
  components with explicit scope and operation-specific approvals.

CloudFormation and Terraform provision infrastructure; they are not runtime
inspection tools. Runtime evidence comes from the shared authenticated SSM
workflow and independent evaluator. AWS live output is local private evidence
under the ignored `docs/evidence/aws/` path and must not be committed or
uploaded. Offline tests and mock coverage do not claim live AWS execution.

## Contribution boundary

PHP2Shell is a reference scenario, not a requirement that every future scenario
use AWS, four labs, or the same evaluator. Read the
[scenario development guide](../../docs/scenario-development-guide.md),
[CONTRIBUTING.md](../../CONTRIBUTING.md), and
[SECURITY.md](../../SECURITY.md) before contributing. Keep scenario-specific
content under `scenarios/`; keep reusable workflows, checks, skills, and
integrations separate. Do not add credentials, real target data, exploit
tooling, or intentionally vulnerable applications.

Future dashboard cloud integration, agent-assisted investigation, reusable
skills, automatic remediation, generalized evaluation, and a Core Harness are
not implemented.
