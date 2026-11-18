# Scale Vulnerability Investigations with AI

*PHP2Shell — An AI Security Engineering Lab*

This lab is for cybersecurity practitioners who want to use AI to investigate
vulnerabilities, automate repeatable tasks, and scale their security workflows.
Prior VulHarness or workshop experience is not required. This participant lab
guide is the canonical self-service path for the PHP2Shell scenario.

A new PHP security advisory has been published. Your security team needs to
determine which applications may be affected, what PHP versions are actually
running, whether remediation reached deployed environments, and how to repeat
that investigation efficiently.

The learning progression is:

~~~text
Investigate → Automate → Verify
~~~

You will investigate the problem manually, examine how coding-agent assistance
can help turn a documented investigation into deterministic automation, run
existing checks and evaluations, and use the implemented VulHarness command to
coordinate the workflow. Future skills, agents, and integrations are discussed
as design ideas; no autonomous vulnerability-investigation agent is required
or implemented by this guide.

The [PHP2Shell custom tools reference](../README.md#custom-tools-and-scripts) lists every participant-facing script, its workflow role, prerequisites, and whether it observes, evaluates, changes, or removes anything.

## Understand PHP2Shell

PHP is a server-side runtime commonly used to generate web responses. The
runtime that actually serves a request may be behind Nginx, Apache, PHP-FPM,
FrankenPHP, LSAPI, or another worker model. That is why a package version or a
container declaration is not the same thing as evidence about the runtime
serving an application.

In this scenario, PHP2Shell refers to two upstream PHP vulnerabilities:

- [CVE-2026-109618](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w),
  remote code execution through out-of-memory corruption.
- [CVE-2026-109619](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp),
  remote code execution through stale global state.

For PHP 8.4, the corresponding upstream fixed release in this exercise is
8.4.27. See the [PHP2Shell reference register](../references.md) for the
authoritative advisories, affected branches, prerequisites, and limitations.
The [PHP Foundation security release](https://thephp.foundation/blog/2026/10/21/todays-php-security-release-and-how-were-strengthening-php-security/)
and [OpenAI coordinated disclosure](https://openai.com/index/coordinated-disclosure-of-critical-vulnerabilities/)
provide additional response context.

During this lab, collect evidence for:

- Authorization and investigation scope.
- The runtime actually serving HTTP requests, including PHP version and SAPI.
- Configuration intent versus deployed and observed runtime state.
- Image, package, or build provenance where available.
- Remediation and reset actions.
- Evidence source, timestamp, freshness, and collection limitations.

Version-based checks can classify an upstream-version state for this exercise.
They cannot establish application exploitability, distribution backport status,
all advisory applicability conditions, or non-exploitability.

## What this lab contains

| Lab | Environment | Initial PHP | Purpose |
|---|---|---|---|
| Lab A | Local Docker | 8.4.27 | Upstream fixed-version reference |
| Lab B | Local Docker | 8.4.26 | Investigation and remediation target |
| Lab C | AWS EC2 | 8.4.27 | Cloud fixed-version reference |
| Lab D | AWS EC2 | 8.4.26 | Cloud investigation and remediation target |

Labs A and B are independent local Docker Compose environments. Labs C and D
demonstrate the same security investigation principles on two separate EC2
instances using authenticated AWS Systems Manager access. The AWS examples are
AWS-specific; Azure, GCP, other servers, and other endpoints are possible
future adaptations, not implemented equivalents in this repository.

Available today:

- Manual local investigation and remediation with Labs A and B.
- Deterministic local runtime checks and the Hello World 2.0 dashboard.
- Independent local lifecycle evaluations.
- AWS CLI, CloudFormation, and Terraform deployment methods, shared SSM
  runtime collection, and scoped AWS evaluation for authorized participants.
- The PHP2Shell-specific Python orchestration command.

Future work is tracked in the root README [roadmap](../../../README.md#roadmap).
This workshop does not implement reusable coding-agent skills, a Chief of Staff
Agent, generalized multi-scenario execution, automated remediation, external
security integrations, or Azure and GCP environments. Azure and GCP are future
environment targets, not supported participant workflows today.

A version below an upstream fixed threshold does not automatically prove that
an application is exploitable. This exercise does not execute exploits, prove
external exposure, or test remote code execution.

## Contents

- [Understand PHP2Shell](#understand-php2shell)
- [What this lab contains](#what-this-lab-contains)
- [Part A — Getting Started](#part-a--getting-started)
  - [Prerequisites and safety](#prerequisites-and-safety)
  - [Choose Your Lab Path](#choose-your-lab-path)
- [Part B — Local Environment: Labs A and B](#part-b--local-environment-labs-a-and-b)
  - [Prepare and start the local labs](#prepare-and-start-the-local-labs)
  - [Manual investigation](#manual-investigation)
  - [Apply the Lab B remediation](#apply-the-lab-b-remediation)
  - [Manually verify the observed runtime](#manually-verify-the-observed-runtime)
  - [Automated vulnerability checks](#automated-vulnerability-checks)
  - [Independent remediation lifecycle evaluation](#independent-remediation-lifecycle-evaluation)
  - [Reset and cleanup](#reset-and-cleanup)
- [Part C — AWS Environment: Labs C and D](#part-c--aws-environment-labs-c-and-d)
  - [AWS account readiness and safety](#aws-account-readiness-and-safety)
  - [Deployment methods and wrapper reference](#deployment-methods-and-wrapper-reference)
  - [Deploy Labs C and D](#deploy-labs-c-and-d)
  - [Capture and verify the deployment ID](#capture-and-verify-the-deployment-id)
  - [Inspect AWS infrastructure and runtime manually](#inspect-aws-infrastructure-and-runtime-manually)
  - [Automated AWS runtime workflow](#automated-aws-runtime-workflow)
  - [Independent AWS lifecycle evaluation](#independent-aws-lifecycle-evaluation)
  - [Remediation, reset, and scoped cleanup](#remediation-reset-and-scoped-cleanup)
- [Part D — VulHarness Orchestration](#part-d--vulharness-orchestration)
  - [Why introduce a harness?](#why-introduce-a-harness)
  - [Run VulHarness](#run-vulharness)
  - [Repository architecture and contributions](#repository-architecture-and-contributions)
  - [Future skills and agent concepts](#future-skills-and-agent-concepts)
  - [Contributing](#contributing)
- [Appendix](#appendix)
  - [Troubleshooting and recovery](#troubleshooting-and-recovery)
  - [Technical references](#technical-references)
  - [Reset and cleanup reference](#reset-and-cleanup-reference)
- [What this lab establishes](#what-this-lab-establishes)

# Part A — Getting Started

Part A explains the workshop purpose, prerequisites, safety boundaries, and the available paths. The local and AWS environments are independent choices; neither is a prerequisite for the other.

> **Execution mode — Orientation and safety:** these instructions establish scope and prerequisites. They do not deploy infrastructure or change a runtime.

## Prerequisites and safety

### Start from a fresh clone

The primary examples use a Unix-style shell. Use one of these supported
workstation layouts:

#### Supported workstation layouts

- **macOS:** Docker Desktop or Colima with a running Docker engine.
- **Linux:** a running Docker Engine with Docker Compose v2.
- **Windows:** WSL2 with Docker Desktop integration enabled.

Native Windows PowerShell and native Windows Docker workflows are not validated
by this repository. Windows participants should run the Linux commands below
inside WSL2.

#### Clone the public repository

Clone the public repository and enter its root:

~~~bash
# Clone the public repository.
git clone https://github.com/The-AI-Security-Lab/vul-harness.git

# Enter the repository root.
cd vul-harness
~~~

Verify the repository root:

~~~bash
# Print the current directory.
pwd

# Confirm the expected repository files are present.
ls README.md scenarios/php2shell
~~~

Verify Git:

~~~bash
git --version
~~~

### Required for local labs

- Git
- Docker with Docker Compose v2
- Python 3.9 or later
- A command-line terminal appropriate for your operating system (for example,
  Terminal on macOS, a Linux terminal, or a WSL2 terminal on Windows), and a
  web browser.
- An authorized workstation on which you may run the local containers

Check the local tools:

~~~bash
# Confirm the Docker daemon is responding.
docker info

# Confirm Docker Compose v2 is available.
docker compose version

# Confirm Python is available.
python3 --version
~~~

Some systems invoke Python as python rather than python3. If python3 does not
exist, verify python --version and substitute python consistently in the
commands below. If Docker cannot connect to its daemon, use the concise
[Docker daemon troubleshooting](#docker-daemon-unavailable-or-not-responding)
subsection before starting Lab A or Lab B.

### Shared safety instructions

- Work only in environments you own or are explicitly authorized to use.
- Do not use production systems, unrelated Docker projects, or unrelated cloud
  resources.
- Do not use exploit probes, production scans, broad inventory, broad cleanup,
  `docker system prune`, or account-wide security-setting changes.
- Keep credentials, tokens, personal data, private infrastructure identifiers,
  and live evidence out of Git. Keep AWS evidence under the ignored local
  `docs/evidence/aws/` path.
- The PHP inspection endpoints are training diagnostics bound to loopback; do
  not expose them publicly.
- Mutating and destructive actions require the documented operation-specific
  approval, reviewed scope, and independent verification.
- Coding-agent assistance does not replace authorization, human review,
  deterministic checks, or independent evaluation.

All commands below run from the VulHarness repository root unless stated
otherwise. Local technical details are in the [Lab A README](../labs/local/lab-a/README.md)
and [Lab B README](../labs/local/lab-b/README.md).

## Choose Your Lab Path

Choose one environment and one workflow, or use both if useful. You can complete only one path; AWS is optional and does not require completing the local labs first.

| Environment | Manual investigation | Automation and evaluation | VulHarness |
| --- | --- | --- | --- |
| Local — Labs A/B | [Local manual investigation](#manual-investigation) | [Local automation and evaluation](#automated-vulnerability-checks) | [Local Harness workflow](#local-harness-workflow) |
| AWS — Labs C/D | [AWS manual investigation](#aws-manual-investigation) | [AWS automation and evaluation](#automated-aws-runtime-workflow) | [AWS Harness workflow](#aws-harness-workflow) |

Use the [evidence report template](evidence-report-template.md) to record observations, version classifications, timestamps, remediation evidence, and verification results. Keep live AWS evidence private under the ignored `docs/evidence/aws/` path.

### Optional coding-agent workflow

Codex, Claude Code, or another suitable coding agent is optional. The manual
investigation and deterministic commands remain usable without an agent. An
agent may help explain commands, generate tests, or organize evidence; the
[shared safety instructions](#shared-safety-instructions) still apply.

# Part B — Local Environment: Labs A and B

Local Docker is a complete, optional PHP2Shell path. It can be followed without deploying AWS resources. The local journey uses manual investigation first, then deterministic checks and an independent lifecycle evaluator; VulHarness orchestration is documented in Part D.

## Prepare and start the local labs

> **Execution mode — Direct runtime commands:** the Compose commands below change only the named local projects. They do not use VulHarness orchestration or the independent evaluator.

### Check Docker and Compose readiness

~~~bash
# Confirm the Docker daemon is responding.
docker info

# Confirm Docker Compose v2 is available.
docker compose version
~~~

Before starting either lab, confirm that `docker info` shows a responding Server section. If Docker cannot connect to its daemon, use [Docker daemon unavailable or not responding](#docker-daemon-unavailable-or-not-responding).

### Start Lab A

`compose.lab-a.yaml` defines the fixed-version reference lab. It uses a pinned image reference rather than a local `build:` context and starts with PHP 8.4.27.

~~~bash
docker compose -f scenarios/php2shell/labs/local/lab-a/compose.lab-a.yaml up -d
~~~

### Start Lab B

`compose.lab-b.yaml` defines the initial investigation and remediation lab. It starts with PHP 8.4.26. `compose.lab-b.update.yaml` is an override for the later fixed-image remediation and is not used during initial startup.

~~~bash
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml up -d
~~~

If Lab B was previously remediated, use the optional [reset](#reset-and-cleanup) before relying on the initial-state expectations. This extra reset is needed only when an existing named Lab B project may still be serving the fixed image.

### Confirm Lab A is running

~~~bash
docker compose -f scenarios/php2shell/labs/local/lab-a/compose.lab-a.yaml ps
~~~

### Confirm Lab B is running

~~~bash
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml ps
~~~

Both projects should report their expected services as running. Their ports bind only to 127.0.0.1.

## Manual investigation

Sometimes called **Hard Mode**, this path asks you to inspect runtime evidence manually, compare it with the advisory, apply a scoped update, and verify the result. It does not use VulHarness orchestration or the independent evaluator, and you may stop after completing it.

> **Execution mode — Manual investigation:** browser actions and the commands in this section observe or deliberately change only the named local lab.

### Inspect the actual HTTP-serving runtimes

Expected initial state:

| Lab | Browser | Expected PHP | Purpose |
| --- | --- | --- | --- |
| Lab A | [http://127.0.0.1:8080](http://127.0.0.1:8080) | 8.4.27 | Fixed-version reference |
| Lab B | [http://127.0.0.1:8082](http://127.0.0.1:8082) | 8.4.26 | Before-remediation target |

For each lab in the table:

1. Select **Inspect Runtime**.
2. Record the PHP version, SAPI, and observation timestamp.
3. Select **Reset Test**; this resets only browser request state and does not
   stop or recreate containers.

For PHP 8.4, the upstream fixed release used in this exercise is 8.4.27. The
initial browser observations therefore establish Lab A as the fixed-version
reference and Lab B as below that threshold. This comparison does not prove
exploitability or non-exploitability.

### Inspect the existing Lab B update configuration

The base Lab B Compose file defines the initial PHP 8.4.26 service.

The following command combines the base configuration with an update override
that selects the fixed PHP 8.4.27 image:

~~~bash
# Inspect the merged Lab B image configuration without changing containers.
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml config --images
~~~

The output should include the pinned PHP 8.4.27 image:

~~~text
php:8.4.27-fpm-bookworm@sha256:b75642e8c89c321039f351466134df951576fb0f7017117b3931e9a19b908d6c
~~~

The `config --images` command displays the resulting image configuration
without applying the update or changing the running lab.

## Apply the Lab B remediation

### Pull the fixed PHP image

This downloads the approved PHP 8.4.27 image:

~~~bash
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml pull php-fpm
~~~

### Recreate Lab B using the fixed image

This recreates Lab B's PHP-FPM and Nginx containers:

~~~bash
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml up -d --force-recreate php-fpm web
~~~

This changes only the named Lab B project in your local Docker environment. Lab
A is not modified.

## Manually verify the observed runtime

Manual runtime inspection is the first verification after remediation.

| Lab | Browser | Before remediation | After remediation |
| --- | --- | --- | --- |
| Lab A | [http://127.0.0.1:8080](http://127.0.0.1:8080) | 8.4.27 | 8.4.27 |
| Lab B | [http://127.0.0.1:8082](http://127.0.0.1:8082) | 8.4.26 | 8.4.27 |

For each lab in the table:

1. Select **Inspect Runtime**.
2. Record the PHP version, SAPI, and observation timestamp.
3. Select **Reset Test**; this resets only browser request state and does not
   stop or recreate containers.

Lab A should remain unchanged because the labs have separate Compose projects,
containers, networks, and loopback ports.

The override selecting PHP 8.4.27 is configuration intent. The HTTP response
from the recreated PHP-FPM service is runtime evidence; a successful Compose
command alone does not prove that the intended image is serving requests.

## Automated vulnerability checks

The custom `cli.py` command checks the PHP runtime currently serving each local
application and compares the observed version with the documented upstream
fixed version for the two PHP2Shell CVEs. It reads runtime information and does
not modify the containers.

Its output includes:

- Observed PHP version and SAPI.
- Evidence source and observation timestamp.
- Per-CVE version classification.
- Limitations, including that exploitability is not established.

Supported options are:

| Option | Purpose |
| --- | --- |
| `--target lab-a` or `--target lab-b` | Check one configured runtime; Lab A is the default when no selection is supplied. |
| `--all` | Check every configured runtime. |
| `--json` | Emit structured evidence without changing the observation. |
| `--help` | Show the command-line help. |

The checker exit codes are:

| Exit code | Meaning |
| --- | --- |
| `0` | The observed version is classified as `fixed_upstream_version`. |
| `1` | The observed version is classified as `potentially_affected_upstream_version`. This is a meaningful result, not automatically an evidence-collection failure. |
| `2` | The observation is inconclusive because the available evidence is insufficient to classify the runtime. |
| `3` | Operational evidence collection failed. |
| `4` | Target configuration or target selection is invalid or unavailable. |

Run it for both labs:

~~~bash
# Check the fixed-version reference runtime.
python3 scenarios/php2shell/checks/local-http-version/cli.py --target lab-a

# Check the Lab B runtime under investigation.
python3 scenarios/php2shell/checks/local-http-version/cli.py --target lab-b
~~~

Expected versions depend on whether Lab B was reset:

| Case | Lab A | Lab B |
| --- | --- | --- |
| Lab B was remediated and not reset | 8.4.27 | 8.4.27 |
| Lab B was reset to its base configuration | 8.4.27 | 8.4.26 |

Expected checker results:

- PHP 8.4.27 should be classified as `fixed_upstream_version` and return exit
  code `0`.
- PHP 8.4.26 should be classified as
  `potentially_affected_upstream_version` and return exit code `1`
  (`FAILED`). This is an expected, meaningful classification when Lab B is in
  its initial state; it means evidence was collected and the observed version
  is potentially affected. It does not mean the checker failed to collect
  evidence.
- Exit code `2` means the observation is inconclusive; the available evidence
  was insufficient to classify the runtime.
- Exit code `3` means operational evidence collection failed.
- Exit code `4` means the target configuration is invalid or unavailable.
- A version classification alone does not establish exploitability.

Use the browser observation as the first manual verification; this automated
check follows it. The independent lifecycle evaluator below performs a separate
comparison of expected outcomes with collected evidence.

### Optional local dashboard

The custom `dashboard.py` program is a localhost-only view over the explicit
targets in `checks/local-http-version/targets.json`: Lab A and Lab B by
default. It does not discover Docker containers, scan arbitrary PHP services,
edit Compose files, run Docker mutations, or provide a remediation action.

1. **Start the dashboard.** Run:

   ~~~bash
   python3 scenarios/php2shell/checks/local-http-version/dashboard.py
   ~~~

2. **Open the dashboard.** Visit
   [http://127.0.0.1:8081](http://127.0.0.1:8081).
3. **Check the runtimes.** Select **Check Runtimes** to collect fresh,
   read-only evidence from the configured targets.
4. **Inspect the evidence.** Review each target's endpoint, observed PHP
   version, assessment status, and observation timestamp.
5. **Expand the results.** Open the evidence details for SAPI, evidence source,
   per-CVE classifications, and limitations.
6. **Understand Remediate.** The grey **Remediate** controls are deliberately
   disabled. They are not an executable action; use the approved remediation
   workflow in this guide instead. After an approved update, select **Recheck**.
7. **Stop the dashboard.** Return to its terminal and press `Ctrl+C` when
   finished.

## Independent remediation lifecycle evaluation

> **Execution mode — Independent evaluation:** the evaluator compares observed
> evidence with expected states separately from the checker and any agent or
> orchestration command.

The custom
[`evals/remediation-lifecycle/evaluate.py`](../evals/remediation-lifecycle/evaluate.py)
program is the independent remediation-lifecycle evaluator. It performs a
repeatable comparison between expected outcomes and observed evidence,
separately from the checker, harness, coding agent, or provider that collected
the evidence. It does not remediate or reset containers.

If you have already completed the manual remediation and only want the participant result, you may stop after the manual verification above. To run the complete independent before/config-only/after lifecycle, [reset](#reset-and-cleanup) Lab B once to its base configuration; you do not need to repeat the manual investigation.

The `before` and `config-only` evaluations both require Lab B to be running
PHP 8.4.26. If Lab B was previously remediated and is serving PHP 8.4.27, use
the canonical [reset](#reset-and-cleanup) instructions, confirm the baseline,
and then run the evaluator; do not weaken the expected state or repeat the
manual investigation.

The evaluator accepts one required parameter:

| Parameter | Meaning |
| --- | --- |
| `--state before` | Expect Lab B to be running PHP 8.4.26 with the potentially affected upstream-version classification. |
| `--state config-only` | Expect the runtime still to be PHP 8.4.26 while the merged Compose configuration selects the fixed PHP-FPM image. |
| `--state after` | Expect the running runtime and PHP-FPM container image to match the fixed PHP 8.4.27 expectation. |
| `--help` | Show the evaluator's command-line help. |

There are no profile, target, remediation, or reset arguments. The evaluator is
read-only: `config-only` inspects desired Compose configuration, while `after`
inspects the running PHP-FPM container. Neither mode changes containers.

### Before-remediation evaluation

For this state, the evaluator compares the observed Lab B state with the
documented expectation and returns a nonzero result when the evidence does not
match. Its config-only and after modes add bounded, read-only Docker inspection;
it never changes containers.

~~~bash
python3 scenarios/php2shell/evals/remediation-lifecycle/evaluate.py --state before
~~~

Expected summary:

~~~text
State: before
Result: PASS
Observed PHP version: 8.4.26
Expected PHP version: 8.4.26
Summary: PASS — state=before; Lab B serves PHP 8.4.26 with the expected potentially_affected_upstream_version classification.
Next action: Record the baseline evidence, then inspect the merged configuration or apply the approved remediation.
~~~

Both CVEs must be potentially_affected_upstream_version. PASS establishes
that Lab B's HTTP-serving runtime matches the documented before-state; it does
not prove vulnerability or exploitability.

### Configuration-only evaluation

Inspect the merged desired configuration without redeploying. This command
checks configuration intent only; it does not change the running Lab B project:

~~~bash
# Inspect the merged Compose model without changing the running project.
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml config --images
~~~

The output should show the approved PHP 8.4.27 image. Configuration intent and
deployed runtime are separate facts.

Now run the independent configuration-only evaluation. It confirms that the
desired Compose model selects PHP 8.4.27 while the runtime still serving HTTP
remains PHP 8.4.26:

~~~bash
# Compare the expected config-only state with collected runtime evidence.
python3 scenarios/php2shell/evals/remediation-lifecycle/evaluate.py --state config-only
~~~

Expected result: `PASS` when both the PHP 8.4.26 runtime and the fixed desired
image are observed. If the runtime is already PHP 8.4.27, this state should
return `FAIL`; that is an expected state mismatch for an already-remediated
Lab B, not a reason to weaken the evaluator.

### Apply and evaluate the after-state

Apply the same scoped update used in Hard Mode:

~~~bash
# Pull the approved fixed PHP image.
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml pull php-fpm

# Recreate Lab B with the fixed PHP-FPM image.
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml up -d --force-recreate php-fpm web

# Collect deterministic observations from both local labs.
python3 scenarios/php2shell/checks/local-http-version/cli.py --all

# Evaluate the remediated Lab B state independently.
python3 scenarios/php2shell/evals/remediation-lifecycle/evaluate.py --state after
~~~

PASS requires HTTP-observed PHP 8.4.27, fixed classifications for both CVEs,
and a read-only running-container inspection identifying the approved fixed
PHP-FPM image. It does not prove non-exploitability or complete remediation.

The evaluator prints `Result`, observed and expected PHP versions, the expected
classification, each individual check, and final `Summary:` and `Next action:`
lines. The summary identifies the evaluated state and observed-versus-expected
evidence. The next action is state-aware: for example, an already-remediated
`before` state directs the participant to reset Lab B, confirm PHP 8.4.26, and
rerun `--state before`. These lines still do not establish exploitability or
complete remediation.

### Evaluation reset checkpoint

If another participant or exercise needs the expected baseline, use the
canonical [Reset and cleanup](#reset-and-cleanup) section to reset only Lab B
to PHP 8.4.26. Then rerun:

~~~bash
# Recheck the expected baseline after the reset checkpoint.
python3 scenarios/php2shell/evals/remediation-lifecycle/evaluate.py --state before
~~~

If you are continuing into Harness Mode, keep Labs A and B running. If you are
ending the local exercise, use the same canonical section to clean up only the
named Lab B and Lab A Compose projects.

## Reset and cleanup

Resetting Lab B is optional during the local manual path, but it is required
before the independent before-state evaluation. Use this canonical checkpoint
to return only Lab B to PHP 8.4.26:

~~~bash
# Stop Lab B before starting it again from the base Compose file.
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml down

# Start Lab B from its PHP 8.4.26 base configuration.
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml up -d
~~~

If you are continuing to another local exercise or Harness Mode, keep Labs A
and B running. When the local exercise is finished, stop only the named
Compose projects:

~~~bash
# Stop only the named Lab B project.
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml down

# Stop only the named Lab A project.
docker compose -f scenarios/php2shell/labs/local/lab-a/compose.lab-a.yaml down
~~~

Do not remove unrelated containers or images.

# Part C — AWS Environment: Labs C and D

AWS is an optional extension of the local PHP2Shell investigation. The security question remains the same: what is running, what evidence proves it, what permissions are in scope, and what remains unknown? You can start here without completing the local path.

> **Execution mode — Mixed AWS workflow:** AWS Console and Session Manager provide manual inspection; deployment wrappers automate infrastructure provisioning; SSM automates runtime bootstrap; deterministic checks collect evidence; and independent evaluation compares the expected state.

## AWS account readiness and safety

Choose the AWS Region for this disposable lab and use the official guidance
for [named AWS CLI profiles](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html),
[AWS CLI authentication](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-authentication.html),
and [AWS Regions](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones-setup.html).

Set the variables once and reuse them:

~~~bash
# Select the authorized AWS CLI profile.
export AWS_PROFILE="REPLACE_WITH_YOUR_PROFILE"

# Select the AWS Region for this deployment.
export AWS_REGION="us-east-1"

# Select exactly one deployment method.
export VULHARNESS_METHOD="aws-cli"
~~~

`VULHARNESS_METHOD` must remain the selected value (`aws-cli`, `cloudformation`, or `terraform`) for subsequent wrapper, SSM, evaluator, and Harness commands. Verify identity before deployment:

~~~bash
# Show the selected AWS CLI configuration.
aws configure list --profile "$AWS_PROFILE"

# Verify the authenticated AWS identity in the selected Region.
aws sts get-caller-identity --profile "$AWS_PROFILE" --region "$AWS_REGION"
~~~

### AWS-specific prerequisites and safeguards

- Use an authorized, non-production AWS account and profile. The selected
  identity must have only the permissions needed to inspect and, when
  explicitly approved, create and remove the deployment-owned EC2, VPC, IAM,
  and SSM resources.
- AWS CLI is required for all methods. Terraform participants use the
  live-validated Terraform 1.17.1 and AWS provider 6.72.0 toolchain documented
  for this path; the configuration retains broader compatibility constraints.
- EC2 `t4g.small`, EBS, public IPv4, and related networking resources may
  incur charges until scoped cleanup completes.
- If the account contains a protected reference instance, set its
  account-specific ID only in the local environment as
  `VULHARNESS_PROTECTED_INSTANCE_ID=your-protected-instance-id`. Never commit
  it. If unset, the evaluator reports the resource-independence check as SKIP
  with `skip_classification=configuration_missing`.
- GuardDuty-managed endpoints are external cleanup dependencies. Default
  cleanup blocks on a verified dependency; the separate
  `--allow-guardduty-cleanup` authorization is limited to the verified
  deployment endpoint and its dependent resources and does not change
  account-level GuardDuty settings.

## Deployment methods and wrapper reference

Wrappers automate provisioning; they are not manual resource-by-resource procedures. They create tagged Lab C/D infrastructure and perform method-specific ownership and configuration checks, but do not install Docker, start Compose, or inspect PHP.

| Method | Script | Purpose |
| --- | --- | --- |
| AWS CLI | [`aws-lab.sh`](../labs/aws/deployment/cli/aws-lab.sh) | Tagged infrastructure provisioning using AWS CLI operations |
| CloudFormation | [`cf-lab.sh`](../labs/aws/deployment/cloudformation/cf-lab.sh) | Stack-based provisioning |
| Terraform | [`tf-lab.sh`](../labs/aws/deployment/terraform/tf-lab.sh) | Terraform configuration and state-based provisioning |

| Operation or parameter | AWS CLI | CloudFormation | Terraform |
| --- | --- | --- | --- |
| `deploy`, `status`, `cleanup --dry-run`, approved `cleanup` | Supported | Supported | Supported |
| `--profile`, `--region`, `--deployment-id`, `--expires-at` | Supported | Supported | Supported |
| `--allow-guardduty-cleanup` | Supported | Supported | Supported |
| `--owner` | Not a CLI flag; use `VULHARNESS_OWNER` | Supported flag | Supported flag |
| `--state-dir` | Not supported | Not supported | Supported |

All three wrappers default the owner to `workshop` when no override is supplied.
`VULHARNESS_OWNER` is part of the deployment scope: it is written to the
`VulHarnessOwner` tags and is used when matching resources for status and
cleanup. For a custom owner, set it before using any method:

~~~bash
export VULHARNESS_OWNER="vulharness-workshop"
~~~

The AWS CLI wrapper has no `--owner` flag: its effective owner is the
`VULHARNESS_OWNER` environment value. CloudFormation and Terraform also read
that environment value, but their supported `--owner` flag overrides it when
provided. When reusing an existing deployment, restore the original owner
value; for CloudFormation or Terraform either omit `--owner` or pass the same
original value explicitly. Never change ownership casually during status,
remediation, evaluation, reset, or cleanup; mismatches must remain failures.

The wrappers apply the common `VulHarnessProject`, `VulHarnessScenario`,
`VulHarnessEnvironment`, `VulHarnessDeployment`, `VulHarnessManagedBy`,
`VulHarnessDeploymentMethod`, `VulHarnessOwner`, and `VulHarnessExpires` tags,
plus `VulHarnessResource`, to the deployment VPC, subnet, Internet Gateway,
route table, security group, IAM role, instance profile, EC2 instances, and root
volumes. Lab-specific `VulHarnessLab` tags identify `lab-c` and `lab-d`
instances and volumes. Use the full tag set—not a VPC match alone—to confirm
ownership before an operation.

Detailed provider-specific permissions, Terraform state, SSM recovery, IAM ownership, and GuardDuty cleanup guidance are in the [central AWS labs reference](../labs/README.md) and the linked method READMEs.

## Deploy Labs C and D

Choose exactly one method. Do not combine wrappers, state, or deployment IDs.

### Option A — AWS CLI

[`aws-lab.sh`](../labs/aws/deployment/cli/aws-lab.sh) creates the tagged infrastructure directly through AWS CLI operations. The observed workshop duration is approximately 5–10 minutes, depending on AWS API and SSM readiness; it is an estimate, not a guarantee.

~~~bash
# Create the AWS CLI deployment when this is the selected method.
./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" deploy
~~~

### Option B — CloudFormation

[`cf-lab.sh`](../labs/aws/deployment/cloudformation/cf-lab.sh) manages a dedicated CloudFormation stack. The observed duration is approximately 5–15 minutes, depending on stack and instance readiness; it is an estimate, not a guarantee.

~~~bash
# Create the CloudFormation deployment when this is the selected method.
./scenarios/php2shell/labs/aws/deployment/cloudformation/cf-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" deploy
~~~

### Option C — Terraform

[`tf-lab.sh`](../labs/aws/deployment/terraform/tf-lab.sh) manages the resources with Terraform and local state. The observed duration is approximately 5–15 minutes, including provider initialization and instance readiness; it is an estimate, not a guarantee.

~~~bash
# Create the Terraform deployment when this is the selected method.
./scenarios/php2shell/labs/aws/deployment/terraform/tf-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" deploy
~~~

Run only the command matching `VULHARNESS_METHOD`. Successful output includes a method-specific success message and the generated deployment summary.

The wrappers provision two separate EC2 instances and their supporting
infrastructure: a dedicated VPC, public subnet, Internet Gateway, route table,
zero-ingress security group, IAM role and instance profile for SSM, encrypted
EBS root volumes, and public IPv4 addresses. Lab C is the PHP 8.4.27 reference
environment; Lab D starts with PHP 8.4.26 and is the remediation target.
Infrastructure creation or SSM Online status alone does not establish PHP
runtime readiness.

## Capture and verify the deployment ID

After deploy, locate the generated deployment ID in the wrapper output and set it exactly:

~~~bash
export VULHARNESS_DEPLOYMENT_ID="REPLACE_WITH_DEPLOYMENT_ID_FROM_OUTPUT"
~~~

The deployment ID is the ownership boundary for later status, runtime, evaluation, remediation, reset, cleanup, and absence verification. If an authorized deployment already exists, reuse its exact ID and original owner instead of deploying a second copy. Run the selected method's read-only status command first; it must confirm the deployment ID, method, owner, and Lab C/D tags. Do not combine methods or adopt unrelated resources.

### Confirm the deployment scope

Use only the status command for the method that created the deployment. These
operations are read-only and do not bootstrap, remediate, or delete resources.

~~~bash
# AWS CLI
./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" status

# CloudFormation
./scenarios/php2shell/labs/aws/deployment/cloudformation/cf-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" status

# Terraform
./scenarios/php2shell/labs/aws/deployment/terraform/tf-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" status
~~~

Run only the block matching `VULHARNESS_METHOD`. Confirm the deployment ID,
method tag, owner tag, Lab C/Lab D scope, and expected resource ownership.
`HEALTHY` or a complete CloudFormation/Terraform state is infrastructure
evidence only; it does not prove Docker, PHP, or application readiness.

## Automated AWS runtime workflow

The shared [`ssm_runtime.py`](../labs/aws/deployment/shared/ssm_runtime.py)
workflow performs bounded, approved bootstrap, remediation, and reset operations
on exactly tagged instances. It uses AWS Systems Manager Run Command through the
`SendCommand` API, not SSH, and does not open inbound SSH access. Bootstrap
completion, container readiness, PHP version verification, and vulnerability
classification are separate evidence claims.

~~~bash
# Bootstrap Lab C through SSM Run Command.
python3 scenarios/php2shell/labs/aws/deployment/shared/ssm_runtime.py bootstrap \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --lab-id lab-c

# Bootstrap Lab D through SSM Run Command.
python3 scenarios/php2shell/labs/aws/deployment/shared/ssm_runtime.py bootstrap \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --lab-id lab-d
~~~

SSM success means the approved remote command completed and the bootstrap
assets/configuration were applied. A typical success message distinguishes
these states:

~~~text
SSM command execution: Success
Bootstrap result: approved lab assets transferred and checked; Docker enabled; Compose validated; base lab services started.
Runtime verification and vulnerability classification were not performed by this SSM operation; run the evaluator next.
~~~

The actual output contains the deployment, instance, and command IDs. It does
not by itself prove containers are ready, PHP is serving the expected version,
or the application is healthy.

If you enter this workflow directly and the Part C deployment still exists,
reuse its exact method, owner, and deployment ID; do not run a second
deployment. If it was cleaned up, return to [Deploy Labs C and D](#deploy-labs-c-and-d)
and create one fresh deployment before bootstrapping.

## Inspect AWS infrastructure and runtime manually

Use the manual AWS reference in [`labs/README.md`](../labs/README.md) for the resource model and recovery guidance. The supported workshop path uses the wrappers; this guide does not ask participants to reproduce destructive infrastructure operations resource by resource.

### AWS manual investigation

Use the AWS Console and Session Manager after both bootstrap commands and before
the independent evaluation. The [central AWS labs reference](../labs/README.md) explains
the resource model and recovery guidance; the steps below are the participant
verification path.

1. Sign in to the AWS Management Console, select the deployment Region, and
   open **EC2 → Instances**.
2. Use relevant tags individually or together to locate your deployment. Before
   inspecting or acting on a resource, verify the exact deployment ID, owner,
   deployment method, and Lab C/Lab D identity; do not copy an instance ID from
   another deployment.

   | Tag key | Value | Purpose |
   | --- | --- | --- |
   | `VulHarnessProject` | `VulHarness` | Project boundary |
   | `VulHarnessScenario` | `php2shell` | Scenario boundary |
   | `VulHarnessEnvironment` | `aws-ec2` | Environment boundary |
   | `VulHarnessDeployment` | `<your deployment ID>` | Deployment ownership |
   | `VulHarnessManagedBy` | `<selected method>` | Wrapper ownership |
   | `VulHarnessDeploymentMethod` | `<selected method>` | Method boundary |
   | `VulHarnessOwner` | `<your owner>` | Ownership boundary |
   | `VulHarnessExpires` | `<deployment expiry>` | Lifecycle metadata |
   | `VulHarnessResource` | `instance` | Resource type |
   | `VulHarnessLab` | `lab-c` or `lab-d` | Lab selection |

3. Confirm that the two matching rows are separately tagged `lab-c` and
   `lab-d`.
4. Select an instance, choose **Connect**, select **Session Manager**, and
   choose **Connect**. Session Manager is used instead of SSH; do not open
   inbound SSH ports. If the tab is unavailable, recheck that the instance is
   running and SSM Online, then confirm IAM permissions and the instance
   profile/agent path with the workshop owner.

### Inspect Lab C manually

Run these commands in the Lab C Session Manager shell:

~~~bash
# Move to the deployed repository.
cd /opt/vulharness

# List Docker Compose projects on the instance.
sudo docker compose ls

# Show the Lab C Compose service state.
sudo docker compose -f scenarios/php2shell/labs/aws/lab-c/compose.lab-c.yaml ps

# Show Lab C container names, images, and statuses.
sudo docker ps --filter 'label=com.docker.compose.project=vulharness-php2shell-lab-c' --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'

# Show the configured PHP-FPM image for Lab C.
sudo docker compose -f scenarios/php2shell/labs/aws/lab-c/compose.lab-c.yaml images php-fpm

# Verify the PHP binary serving from the Lab C PHP-FPM container.
sudo docker compose -f scenarios/php2shell/labs/aws/lab-c/compose.lab-c.yaml exec -T php-fpm php -v
~~~

The `web` and `php-fpm` services should be running, and `php -v` should report
PHP 8.4.27. Lab C is the fixed-version comparison environment.

### Inspect Lab D manually

Run the corresponding commands in the Lab D Session Manager shell:

~~~bash
# Move to the deployed repository.
cd /opt/vulharness

# List Docker Compose projects on the instance.
sudo docker compose ls

# Show the Lab D Compose service state.
sudo docker compose -f scenarios/php2shell/labs/aws/lab-d/compose.lab-d.yaml ps

# Show Lab D container names, images, and statuses.
sudo docker ps --filter 'label=com.docker.compose.project=vulharness-php2shell-lab-d' --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'

# Show the configured PHP-FPM image for Lab D.
sudo docker compose -f scenarios/php2shell/labs/aws/lab-d/compose.lab-d.yaml images php-fpm

# Verify the PHP binary serving from the Lab D PHP-FPM container.
sudo docker compose -f scenarios/php2shell/labs/aws/lab-d/compose.lab-d.yaml exec -T php-fpm php -v
~~~

Lab D should report PHP 8.4.26 and represents the potentially affected
upstream-version state. That observation alone does not confirm exploitability.
Record the discovered instance IDs, Compose projects, observed images, PHP
versions, classifications, and verification status in the
[evidence report template](evidence-report-template.md). A tag or image
reference is configuration evidence, not independent proof of the running
binary; `php -v` is direct runtime evidence.

## Independent AWS lifecycle evaluation

The custom [`aws_evaluate.py`](../evals/aws-lifecycle/aws_evaluate.py) program
is an independent evaluator. Run it after bootstrap to collect deployment-scoped
inventory and, with `--include-ssm`, runtime evidence. It is independent of the
Harness success response and does not send exploit probes.

Its relevant parameters are:

| Parameter | Purpose |
| --- | --- |
| `--profile` | AWS CLI profile for the deployment account. |
| `--region` | AWS Region containing the deployment. |
| `--method` | The original deployment method: `aws-cli`, `cloudformation`, or `terraform`. |
| `--deployment-id` | The exact deployment scope to evaluate. |
| `--include-ssm` | Collect SSM command results and runtime evidence in addition to inventory. Omit it for inventory-only evaluation. |
| `--phase` | Expected lifecycle phase: `initial`, `remediated`, or `reset`. |
| `--expect-absent` | Evaluate post-cleanup absence instead of a running deployment. |

The evaluator's inventory and runtime evidence remain separate from the
deployment wrapper's status response. Omitting `--include-ssm` does not verify
containers, PHP versions, or runtime classifications.

~~~bash
# Collect deployment-scoped inventory and initial SSM/runtime evidence.
python3 scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" \
  --include-ssm --phase initial
~~~

The exact current Compose readiness wording is `RUNNING; HEALTH UNVERIFIED`. The evaluator has confirmed the required `web` and `php-fpm` Compose services are running. The current Compose files do not define health checks, so running containers are not equivalent to verified application health. PHP runtime observations and version classifications are separate evidence.

| Lab | EC2 instance | Observed PHP | Expected PHP | Runtime status | Classification | Evidence | Next step |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Lab C | discovered ID | 8.4.27 | 8.4.27 | `RUNNING; HEALTH UNVERIFIED` | `fixed_upstream_version` | runtime evidence collected; PHP verified | fixed reference |
| Lab D | discovered ID | 8.4.26 | 8.4.26 | `RUNNING; HEALTH UNVERIFIED` | `potentially_affected_upstream_version` | runtime evidence collected; PHP verified | investigate/remediate |

The evaluator obtains the version from the loopback inspection document served by the application and cross-checks container/Compose evidence, SAPI, timestamp, SSM result, and ownership. It validates a timezone-aware observation timestamp as part of deterministic evidence parsing; it does not emit a separate timestamp result row. A potentially affected version is an investigation signal, not confirmed exploitability.

Association status is distinct from the `SendCommand` result: an unrelated `AssociationStatus=Failed` does not by itself mean bootstrap failed. SSM Online, command success, service state, runtime health, PHP verification, and classification must remain separate claims.

## Remediation, reset, and scoped cleanup

Only Lab D is changed by the AWS remediation and reset operations. Lab C remains
the fixed-version reference environment.

### Remediate Lab D

~~~bash
# Apply the approved fixed-image update to Lab D through SSM Run Command.
python3 scenarios/php2shell/labs/aws/deployment/shared/ssm_runtime.py remediate \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --lab-id lab-d
~~~

### Evaluate the remediated Lab D state

~~~bash
# Independently evaluate both AWS labs after the Lab D remediation.

python3 scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --include-ssm --phase remediated
~~~

### Reset Lab D

~~~bash
# Restore Lab D's baseline runtime through SSM Run Command.

python3 scenarios/php2shell/labs/aws/deployment/shared/ssm_runtime.py reset \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --lab-id lab-d
~~~

### Evaluate the reset Lab D state

~~~bash
# Independently evaluate both AWS labs after the Lab D reset.

python3 scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --include-ssm --phase reset
~~~

Cleanup is destructive and requires a reviewed dry run, explicit authorization,
the wrapper's safeguards, and independent absence verification.
GuardDuty-managed networking remains an external dependency: default cleanup
blocks, and the explicit `--allow-guardduty-cleanup` opt-in requires the
normal approval plus its separate authorization. It is limited to the verified
deployment endpoint and dependencies and does not change account-level
GuardDuty settings.

### AWS CLI cleanup

The AWS CLI wrapper reads the original owner from `VULHARNESS_OWNER`; it does
not accept `--owner`:

~~~bash
# Preview AWS CLI cleanup for the scoped deployment.
./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" cleanup --dry-run

# Perform AWS CLI cleanup only after reviewing the dry run.
./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" cleanup

# Independently verify that AWS CLI resources are absent.
python3 scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method aws-cli \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --expect-absent
~~~

### CloudFormation cleanup

For CloudFormation, keep the original owner in `VULHARNESS_OWNER` or pass it
explicitly with the supported `--owner` flag. The default below is
`workshop` when no custom owner was used:

~~~bash
# Preview CloudFormation cleanup while preserving the original owner.
./scenarios/php2shell/labs/aws/deployment/cloudformation/cf-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" \
  --owner "${VULHARNESS_OWNER:-workshop}" cleanup --dry-run

# Perform CloudFormation cleanup only after reviewing the dry run.
./scenarios/php2shell/labs/aws/deployment/cloudformation/cf-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" \
  --owner "${VULHARNESS_OWNER:-workshop}" cleanup

# Independently verify that CloudFormation resources are absent.
python3 scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method cloudformation \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --expect-absent
~~~

### Terraform cleanup

For Terraform, keep the original owner and the same state directory used for
deployment. The default state directory is `.vulharness-terraform-state`;
append the same `--state-dir` value to both wrapper commands if a non-default
directory was used:

~~~bash
# Preview Terraform cleanup with the original owner and state directory.
./scenarios/php2shell/labs/aws/deployment/terraform/tf-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" \
  --owner "${VULHARNESS_OWNER:-workshop}" cleanup --dry-run

# Perform Terraform cleanup only after reviewing the dry run.
./scenarios/php2shell/labs/aws/deployment/terraform/tf-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" \
  --owner "${VULHARNESS_OWNER:-workshop}" cleanup

# Independently verify that Terraform resources are absent.
python3 scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method terraform \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --expect-absent
~~~

The wrapper cleanup commands above are destructive only on the approved
cleanup command, after its interactive deployment-specific confirmation.
If the dry run identifies a verified GuardDuty-managed endpoint, add
`--allow-guardduty-cleanup` only to the approved wrapper cleanup command after
the separate GuardDuty authorization and the normal cleanup approval. Do not
add it casually. Each method's dry run, cleanup, and independent
`--expect-absent` evaluation must use the same deployment ID and ownership
scope. Do not broaden scope if cleanup is blocked or partial; retain the exact
deployment ID and rerun the supported recovery/status and absence checks. Keep
local evidence private and never commit or upload it.

# Part D — VulHarness Orchestration

VulHarness is the scenario-specific orchestration entry point for authorized
vulnerability investigation, remediation workflows, and independent
verification.

## Before running VulHarness: confirm your labs are ready

Local Labs A/B and AWS Labs C/D are independent paths. You may enter Harness
Mode directly; completing the local path is not required before using AWS.
Reuse an existing lab only after confirming its project or deployment scope,
owner, method, Region, and current runtime state. If a lab is absent, create or
start it using the relevant [local setup instructions](#prepare-and-start-the-local-labs)
or [AWS deployment and bootstrap instructions](#deploy-labs-c-and-d). Existing
labs may already be remediated or reset, so inspect their state before
assessing. Harness `setup` is mutating and is not a read-only readiness check.
Never create a duplicate AWS deployment merely to resolve an evaluation error;
follow the scoped recovery guidance instead.

## Why introduce a harness?

> **Execution mode — VulHarness orchestration:** the scenario-specific command
> coordinates existing labs, wrappers, runtime actions, checks, evaluators, and
> approvals. It does not replace their implementation or make an independent
> security judgment.

Disconnected commands can be useful for learning, but they become difficult to
repeat across environments. A harness provides one scope-aware entry point
while preserving the underlying checks, evaluators, deployment wrappers, and
approval boundaries.

VulHarness coordinates existing operations; it does not replace security
judgment or turn a version comparison into proof of exposure.

| Component | Responsibility |
| --- | --- |
| Labs | Provide scenario-specific, authorized environments |
| Checks | Collect or verify concrete evidence |
| Evaluations | Compare observed evidence with expected outcomes independently |
| Orchestration | Validate scope, approvals, command routing, and recovery hints |
| Evidence | Preserve source, timestamp, scope, freshness, and limitations |
| Approvals | Keep remediation and destructive operations explicit |

## Run VulHarness

The implemented entry point is:

~~~text
scripts/vulharness-php2shell.py
~~~

This custom Python program is the Harness orchestration tool. It validates
the environment, deployment method, deployment scope, and operation-specific
approvals, then routes requests to the existing Compose commands, AWS wrappers,
SSM runtime workflow, deterministic checker, or independent evaluator. It does
not replace those tools or make an independent security judgment. Local setup,
remediation, reset, and cleanup, plus AWS setup, remediation, reset, and
cleanup, can change explicitly named targets; inspect, assess, verify, status,
and preflight are observational. Read the command's scope and approval error
before retrying a failed operation.

### Command reference

| Operation | Purpose |
| --- | --- |
| `preflight` | Validate prerequisites and selected scope |
| `setup` | Provision/start the selected environment with approvals where required |
| `status` | Inspect deployment or local project state |
| `inspect` | Collect deployment-scoped inventory evidence |
| `assess` | Run a phase-specific evaluation |
| `dashboard` | Start the local observation dashboard |
| `remediate` | Apply the named remediation with approval |
| `verify` | Collect and compare verification evidence |
| `reset` | Restore the named lab baseline with approval |
| `cleanup` | Preview or perform scoped cleanup with approval |

### Parameter reference

| Parameter | Use |
| --- | --- |
| `--env` | Required environment selector such as `local` or `aws` |
| `--lab` | Optional or operation-specific lab selector, such as `lab-b` or `lab-d` |
| `--profile` | AWS CLI profile; used for AWS operations and defaults from `AWS_PROFILE` or the implementation default |
| `--region` | AWS Region; used for AWS operations and defaults from `AWS_REGION` or the implementation default |
| `--method` | AWS method selector; required for AWS operations and must remain the deployment's original method |
| `--deployment-id` | Required for AWS status, inspection, assessment, verification, remediation, reset, and cleanup; setup may generate one when creating |
| `--phase` / `--state` | Select AWS evaluation phase or local expected state |
| `--approve` | Required operation-specific approval for mutating operations |
| `--dry-run` | Preview cleanup without deleting |
| `--output` | Select output format where supported |
| `--owner` | AWS ownership value; the orchestrator uses the supported environment or wrapper argument for the selected method |
| `--expires-at` | Deployment expiry metadata where supported |
| `--state-dir` | Terraform state directory; used for Terraform operations only |
| `--allow-guardduty-cleanup` / `--expect-absent` | Explicit GuardDuty cleanup opt-in or post-cleanup absence verification |

### Architecture

~~~text
Participant or future coding agent
              | reviewed, authorized request
              v
VulHarness PHP2Shell orchestrator
       |                         |
       v                         v
Local Docker commands       AWS deployment wrappers -> SSM runtime
       |                         |
       v                         v
Deterministic checker       Runtime evidence and inventory
              \              /
               v            v
          Independent evaluators
                     |
                     v
          Evidence outputs with provenance
~~~

Independent evaluators compare collected evidence with expected outcomes; they do not simply trust an orchestrator success response or an agent conclusion.

### Local Harness workflow

#### 1. Check local prerequisites

Run the read-only local preflight:

~~~bash
# Check local prerequisites without changing the labs.
python3 scripts/vulharness-php2shell.py preflight --env local
~~~

#### 2. Start Labs A/B if absent

If either local project is absent, start the named projects with the approved
setup operation:

~~~bash

# Start the named local projects with the approved setup operation.
python3 scripts/vulharness-php2shell.py setup --env local --approve setup
~~~

If the projects are already running from an earlier workflow, you may begin
with the read-only `status` and `inspect` commands below instead of invoking
`setup` again. Harness `setup` can recreate Lab B and return it to its base
configuration, so do not use `setup` merely to observe an existing state.

#### 3. Confirm Lab B's current runtime state

Before the `before` assessment, verify Lab B's current state. `status` is a
read-only Compose-state check; `inspect` reads the configured HTTP runtime.
Do not reset Lab A:

~~~bash
# Read local Compose project state.
python3 scripts/vulharness-php2shell.py status --env local --lab lab-b

# Collect read-only HTTP runtime evidence from Lab B.
python3 scripts/vulharness-php2shell.py inspect --env local --lab lab-b
~~~

If the inspection reports PHP 8.4.27 or `fixed_upstream_version`, Lab B is
already remediated. Reset only Lab B through the approved Harness operation,
then verify the expected PHP 8.4.26 baseline with the same status and inspection
commands before running the assessment:

~~~bash
# Reset only Lab B to its documented baseline.
python3 scripts/vulharness-php2shell.py reset \
  --env local --lab lab-b --approve reset

# Confirm the reset Compose state.
python3 scripts/vulharness-php2shell.py status --env local --lab lab-b

# Confirm the reset HTTP runtime evidence.
python3 scripts/vulharness-php2shell.py inspect --env local --lab lab-b
~~~

Inspection of PHP 8.4.26 may return checker exit code 1; that is the expected
potentially affected classification when evidence was collected successfully.
Only proceed to the `before` assessment after the observed baseline is 8.4.26.
If Lab B already reports 8.4.26, do not reset it again.

#### 4. Assess the initial Lab B state

~~~bash
# Independently evaluate Lab B's expected baseline.
python3 scripts/vulharness-php2shell.py assess \
  --env local --lab lab-b --state before
~~~

The optional dashboard is read-only. Start it in a second terminal if you want
the local page available while continuing:

~~~bash

# Start the optional read-only local dashboard.
python3 scripts/vulharness-php2shell.py dashboard --env local
~~~

Use its local page, press Ctrl+C in that terminal when finished, and return to
the original terminal.

#### 5. Remediate only Lab B

~~~bash

# Apply the approved Lab B remediation.
python3 scripts/vulharness-php2shell.py remediate \
  --env local --lab lab-b --approve remediate
~~~

#### 6. Verify the remediated state

~~~bash

# Collect post-remediation evidence through the harness.
python3 scripts/vulharness-php2shell.py verify --env local
~~~

The remediation command is the approved Harness action; it changes only Lab B.
A local verification after remediation should observe the fixed Lab B runtime.

#### 7. Reset only Lab B

~~~bash
# Restore Lab B to its baseline for another lifecycle evaluation.
python3 scripts/vulharness-php2shell.py reset \
  --env local --lab lab-b --approve reset
~~~

#### 8. Verify the reset baseline

~~~bash

# Evaluate the restored baseline independently.
python3 scripts/vulharness-php2shell.py assess \
  --env local --lab lab-b --state before
~~~

Do not clean up Labs A or B until all local harness steps are complete. Review
the cleanup target list first, then perform only the named cleanup:

~~~bash
# Preview the named Lab B Compose project.
python3 scripts/vulharness-php2shell.py cleanup \
  --env local --lab lab-b --dry-run

# Clean up Lab B only after reviewing the preview and approving it.
python3 scripts/vulharness-php2shell.py cleanup \
  --env local --lab lab-b --approve cleanup

# Preview the named Lab A Compose project.
python3 scripts/vulharness-php2shell.py cleanup \
  --env local --lab lab-a --dry-run

# Clean up Lab A only after reviewing the preview and approving it.
python3 scripts/vulharness-php2shell.py cleanup \
  --env local --lab lab-a --approve cleanup
~~~

### AWS Harness workflow

The AWS harness uses the exact `VULHARNESS_METHOD` and
`VULHARNESS_DEPLOYMENT_ID` established in Part C. Do not replace them with
`aws-cli` or a new placeholder when continuing with CloudFormation or
Terraform. The harness requires a deployment ID for `status`, `inspect`,
`assess`, `remediate`, `verify`, `reset`, and `cleanup`.

#### AWS prerequisites and variable validation

Confirm that `AWS_PROFILE`, `AWS_REGION`, `VULHARNESS_METHOD`,
`VULHARNESS_DEPLOYMENT_ID`, and `VULHARNESS_OWNER` still identify the intended
deployment. Use the same profile, Region, method, deployment ID, and owner as
Part C. A deployment ID identifies the whole deployment, not an individual lab.

#### New deployment versus existing deployment

`setup` is the exception: if you pass the existing deployment ID, it resumes
that exact deployment after validating ownership; if you omit the ID, the
implementation generates a new method-specific ID, writes local orchestration
metadata, deploys infrastructure, bootstraps both labs, and prints the new ID.
To avoid an unintended duplicate deployment, reuse the Part C deployment ID whenever
that deployment still exists. If it was cleaned up, return to
[AWS account readiness and safety](#aws-account-readiness-and-safety)
and create one fresh deployment before continuing here.

If the deployment does not exist, return to Part C to deploy and bootstrap Labs
C/D, or use the supported Harness setup path only after verifying its method,
profile, Region, owner, approval, and deployment-ID behavior. If the deployment
exists but is unhealthy or partially bootstrapped, stop and follow the scoped
[AWS deployment recovery](#aws-deployment-recovery) path; do not blindly
recreate or adopt resources.

The Harness treats the two AWS labs differently:

| Lab | Harness scope |
| --- | --- |
| Lab C | Fixed-version reference. AWS `assess` and normal `verify` evaluate it together with Lab D; there is no Lab C remediation or reset command. |
| Lab D | Investigation/remediation target. Use `--lab lab-d` for AWS `remediate` and `reset`, then evaluate the deployment-wide result. |

Do not add `--lab` to AWS `assess` or normal `verify`; those evaluator
operations are deployment-wide and cover both labs. Use `--lab lab-d` only for
the AWS runtime operations that change or restore Lab D.

The expected lifecycle states are:

| Phase | Lab C expected | Lab D expected |
| --- | --- | --- |
| `initial` | 8.4.27 | 8.4.26 |
| `remediated` | 8.4.27 | 8.4.27 |
| `reset` | 8.4.27 | 8.4.26 |

`--phase` selects the expected evaluation state; it does not change
infrastructure. `--approve remediate` and `--approve reset` authorize distinct
mutating operations. Lab C remains unchanged throughout Lab D remediation and
reset.

The AWS Harness operation boundaries are:

| Operation | What it does | Prerequisite or safety boundary |
| --- | --- | --- |
| `preflight` | Checks AWS identity and, for Terraform, the Terraform toolchain | Read-only; no deployment required |
| `setup` | Creates or resumes infrastructure, then bootstraps Labs C and D through SSM | Requires `--approve setup`; deployment ID may be generated when creating |
| `status` | Runs the selected deployment wrapper's status check | Requires the existing deployment ID, method, owner, profile, and Region |
| `inspect` | Runs deployment-scoped infrastructure evaluation without SSM collection | Requires an existing deployment |
| `assess` / normal `verify` | Runs the independent AWS evaluator, including runtime evidence when requested | Requires an existing deployment and available SSM/runtime evidence |
| `remediate` / `reset` | Changes only Lab D through the shared SSM runtime workflow | Requires an active Lab D and the matching approval token |
| `cleanup` | Runs the selected wrapper's scoped infrastructure cleanup | Review `--dry-run` first; confirmed cleanup requires explicit approval and ownership checks |

#### Confirm Lab C and Lab D readiness

Preflight is read-only. For an existing deployment, run it and then run the
method-matching status command from Part C to confirm identity, ownership,
Region, and infrastructure scope. Neither preflight nor infrastructure status
proves SSM connectivity, container readiness, PHP runtime health, or version
classification.

~~~bash
# Check AWS identity and selected-method prerequisites.
python3 scripts/vulharness-php2shell.py preflight \
  --env aws --method "$VULHARNESS_METHOD" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION"
~~~

If the deployment already exists, confirm its wrapper status using the
method-specific command in [Confirm the deployment scope](#confirm-the-deployment-scope)
before assessing. Do not adopt a deployment that fails ownership or scope
validation.

If you have confirmed the intended deployment ID and need Harness to resume it,
run setup with explicit setup approval. Setup can create or resume resources and
bootstraps both labs; it is mutating and is not a readiness check:

~~~bash

# Resume the exact deployment and bootstrap both AWS labs.
python3 scripts/vulharness-php2shell.py setup \
  --env aws --method "$VULHARNESS_METHOD" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --approve setup
~~~

After setup or an independently completed Part C bootstrap, confirm status
again before collecting runtime evidence:

~~~bash

# Check infrastructure status without bootstrapping or changing runtime state.
python3 scripts/vulharness-php2shell.py status \
  --env aws --method "$VULHARNESS_METHOD" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID"
~~~

#### Assess the initial state of both labs

Run this only after the deployment-wide status is in scope and both Labs C and
D have completed the Part C SSM bootstrap. Assessment requires deployment
inventory plus available runtime evidence; infrastructure status alone is not
enough.

~~~bash
# Evaluate Lab C and Lab D initial evidence together.
python3 scripts/vulharness-php2shell.py assess \
  --env aws --method "$VULHARNESS_METHOD" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --phase initial
~~~

#### Remediate Lab D only

~~~bash

# Remediate only Lab D through the shared SSM workflow.
python3 scripts/vulharness-php2shell.py remediate \
  --env aws --method "$VULHARNESS_METHOD" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --lab lab-d \
  --approve remediate
~~~

#### Verify the remediated state of both labs

Run this after the approved Lab D remediation completes. Lab C must remain the
fixed reference; the verification still evaluates both labs.

~~~bash

# Evaluate the deployment after the Lab D remediation; this includes Lab C.
python3 scripts/vulharness-php2shell.py verify \
  --env aws --method "$VULHARNESS_METHOD" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --phase remediated
~~~

#### Reset Lab D only

~~~bash

# Reset only Lab D through the shared SSM workflow.
python3 scripts/vulharness-php2shell.py reset \
  --env aws --method "$VULHARNESS_METHOD" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --lab lab-d \
  --approve reset
~~~

#### Verify the reset state of both labs

Run this after the approved Lab D reset completes. The expected reset result is
Lab C at PHP 8.4.27 and Lab D at PHP 8.4.26; the verification still evaluates
both labs.

~~~bash

# Evaluate the deployment after the Lab D reset; this includes Lab C.
python3 scripts/vulharness-php2shell.py verify \
  --env aws --method "$VULHARNESS_METHOD" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --phase reset
~~~

The harness's AWS implementation has offline/mock regression coverage; this
sequence is not a claim of live AWS validation. Do not call cleanup until the
AWS lifecycle is complete. Review the exact deployment targets with a dry run,
then approve confirmed cleanup using the same deployment ID:

~~~bash
# Preview the exact AWS deployment cleanup and external dependencies.
python3 scripts/vulharness-php2shell.py cleanup \
  --env aws --method "$VULHARNESS_METHOD" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --dry-run

# Perform cleanup only after reviewing the dry run and receiving approval.
python3 scripts/vulharness-php2shell.py cleanup \
  --env aws --method "$VULHARNESS_METHOD" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --approve cleanup

# Independently verify that the deployment-owned resources are absent.
python3 scripts/vulharness-php2shell.py verify \
  --env aws --method "$VULHARNESS_METHOD" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --expect-absent
~~~

Confirmed AWS cleanup remains interactive and requires the exact
deployment-specific confirmation. Setup stops on partial failure and retains
the deployment identity for recovery; resume with the same method and ID only
after reviewing exact ownership tags. The harness does not adopt unrelated
resources.

### Harness result semantics

The JSON output contains invoked scope, child commands, redacted output, and
the local evidence directory. Exit codes are:

- 0: requested operation completed successfully.
- 1: invoked component failed or reported an ordinary failed evaluation.
- 2: invalid, incompatible, or insufficiently scoped command.
- 3: required local executable or prerequisite is unavailable.
- 4: partial, unhealthy, or externally blocked AWS state.

Do not interpret a successful setup as proof of PHP runtime readiness or a
successful version comparison as proof of exploitability. Infrastructure,
SSM, runtime, version classification, remediation, reset, and cleanup absence
remain separate evidence claims.

## Repository architecture and contributions

The PHP2Shell implementation is a reference scenario, not a generic registry
or automatic agent platform:

~~~text
scripts/vulharness-php2shell.py       scenario-specific orchestration
scenarios/php2shell/scenario.yaml     scenario identity and metadata
scenarios/php2shell/references.md     advisory and technical references
scenarios/php2shell/labs/             controlled local/AWS environments
scenarios/php2shell/checks/           deterministic evidence collection
scenarios/php2shell/evals/            independent expected-state evaluations
scenarios/php2shell/walkthroughs/     participant learning journeys
docs/architecture.md                  framework boundaries and future direction
~~~

Labs own environment configuration. Checks collect concrete evidence.
Evaluations compare observed evidence with expected outcomes independently of
the harness or a coding agent. Walkthroughs explain the learning journey;
technical READMEs hold implementation commands.

Read the [architecture document](../../../docs/architecture.md),
[CONTRIBUTING.md](../../../CONTRIBUTING.md), and
[scenario development guide](../../../docs/scenario-development-guide.md) to
understand the boundaries between reusable components and scenario-specific
implementation.

## Future skills and agent concepts

### Reusable coding-agent skills

A coding-agent skill is a reusable set of instructions or a practitioner
procedure that tells an agent how to perform a bounded capability: for example,
inspect a runtime, collect evidence, validate a result, or prepare a report.

A future PHP investigation skill could reuse documented commands, evidence
fields, authorization boundaries, and validation methods. It must still perform
fresh advisory analysis for a new PHP CVE. A new advisory cannot inherit old
affected-version rules merely because the runtime or product name is similar.

Reusable skills are future work unless implemented evidence exists. Manual
walkthroughs and deterministic checks remain first-class.

### Future agent orchestration

An eventual agent could:

1. Interpret a security advisory.
2. Identify an authorized investigation scope.
3. Select suitable deterministic tools.
4. Execute only permitted checks.
5. Review evidence and report unknowns.
6. Propose next steps.
7. Request authorization before remediation or destructive action.
8. Use independent evaluation rather than trusting its own conclusion.

This is future architecture, not an implemented autonomous workflow. Any agent
must distinguish inventory, desired configuration, running image, serving
runtime, and demonstrated exposure.

### Future security integrations

Future adapters could enrich an investigation with:

- CNAPP or CSPM findings
- SIEM and logging platforms
- Cloud-provider inventory APIs
- Notifications such as Slack

These are integration possibilities, not currently implemented features. An
external finding must not automatically be treated as verified runtime
exposure, and an adapter must preserve source, timestamp, scope, freshness, and
coverage.

## Contributing

VulHarness welcomes additional vulnerability investigation scenarios. A useful
contribution may be manual-only, local-only, or smaller than PHP2Shell. Start
with the [scenario development guide](../../../docs/scenario-development-guide.md)
and [CONTRIBUTING.md](../../../CONTRIBUTING.md).

A scenario should document its authorization boundary, provenance,
preconditions, evidence requirements, expected outcomes, limitations,
failure/recovery paths, and cleanup. Keep scenario-specific content under
scenarios/; keep reusable workflows, checks, skills, and integrations separate.
Do not distribute intentionally vulnerable applications, credentials, real
target data, or unnecessary exploit tooling.

# Appendix

## Troubleshooting and recovery

### Wrong working directory

Every command expects the repository root:

~~~bash
ls README.md scenarios/php2shell
~~~

### Docker daemon unavailable or not responding

A Docker runtime can appear to be running while its Docker daemon is not
responding. During participant testing, the failure appeared as:

~~~text
Cannot connect to the Docker daemon at unix:///Users/.../.colima/default/docker.sock
~~~

#### 1. Diagnose first (all platforms)

Run these read-only checks before starting Lab A or Lab B:

~~~bash
# List available Docker contexts without changing the selected context.
docker context ls

# Confirm the Docker daemon's Server section responds.
docker info

# Confirm Docker Compose is available.
docker compose version
~~~

`docker info` must show a responding **Server** section. A client version or a
running Docker Desktop/Colima process alone is not enough.

#### 2. macOS — Colima

If Colima reports running but Docker cannot connect, this sequence successfully
resolved the issue during live participant testing:

~~~bash
# Check Colima's reported state.
colima status

# Stop the Colima runtime before restarting it.
colima stop

# Start the Colima runtime again.
colima start

# Confirm the Docker daemon responds after the restart.
docker info
~~~

#### 3. macOS — Docker Desktop

Check that Docker Desktop is running and that its engine has started. Restart
Docker Desktop if necessary, then run `docker info` again.

#### 4. Linux — Docker Engine

Check the Docker service using the system's service manager. For systems using
systemd:

~~~bash
sudo systemctl status docker
~~~

If the service is stopped, start it using your system's approved administrative
procedure, then rerun `docker info`.

#### 5. Windows — Docker Desktop with WSL2

Confirm Docker Desktop is running and WSL2 integration is enabled for the
selected distribution. Restart Docker Desktop if necessary, reopen the WSL2
terminal, and rerun `docker info`. Native Windows PowerShell workflows are not
validated by this repository.

Restarting Docker Desktop or Colima may interrupt other running containers.
Do not use `docker system prune`, delete Docker data, reset Docker Desktop to
factory defaults, or remove unrelated containers. Do not automatically change
Docker contexts; first confirm which intended runtime should serve this lab.

### Port already in use

Inspect current bindings without modifying them:

~~~bash
docker ps --format 'table {{.Names}}\t{{.Ports}}'
~~~

Lab A requires 8080, the dashboard requires 8081, and Lab B requires 8082.
Stop only the process or project you own.

### Dashboard already running

Use the existing [http://127.0.0.1:8081](http://127.0.0.1:8081) window. If you
own its terminal, press Ctrl+C before starting another process.

### PHP runtime does not match the expected state

Collect fresh evidence:

~~~bash
# Collect deterministic Lab B evidence.
python3 scenarios/php2shell/checks/local-http-version/cli.py --target lab-b

# Inspect the merged desired Lab B image configuration.
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml config --images
~~~

If the desired image is fixed but HTTP still reports 8.4.26, the runtime has
not been recreated. Return to [Apply the Lab B remediation](#apply-the-lab-b-remediation). If you intended the before-state, use [Reset and cleanup](#reset-and-cleanup).

### Container starts but HTTP is unavailable

Inspect only Lab B:

~~~bash
# Show the selected Lab B Compose service state.
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml ps

# Show recent Lab B service logs.
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml logs --tail=50 web php-fpm

# Request fresh Lab B runtime evidence.
curl --fail --show-error --max-time 3 'http://127.0.0.1:8082/?inspect=1&format=json'
~~~

An unavailable or malformed response remains FAIL or inconclusive. Do not
convert missing evidence into a successful evaluation.

### AWS deployment recovery

For a partial deployment, run status, then cleanup --dry-run and review
only the exact deployment-owned targets. Resume with the same deployment ID
only after ownership tags and the recovery state are understood. For VPC CIDR
conflicts, select an unused CIDR for a new deployment ID rather than reusing
another project's VPC. See the [AWS CLI README](../labs/aws/deployment/cli/README.md)
and [AWS lab guide](../labs/aws/README.md) for bounded retries, provider
constraints, and GuardDuty dependency handling.

## Technical references

- [PHP2Shell reference register](../references.md)
- [Scenario overview](../README.md)
- [Architecture](../../../docs/architecture.md)
- [Scenario development guide](../../../docs/scenario-development-guide.md)
- [AWS lab plan](../labs/aws/README.md)
- [AWS lifecycle evaluator](../evals/aws-lifecycle/README.md)
- [Local manual investigation reference](local/manual-investigation/README.md)

The technical READMEs contain implementation-specific deployment and recovery
detail. Historical live AWS validation, when documented there, is distinct
from offline tests and mock coverage that can run without AWS.

## Reset and cleanup reference

For local work, return Lab B to its before-state with the reset sequence in
[Reset and cleanup](#reset-and-cleanup) or the
[evaluation reset checkpoint](#evaluation-reset-checkpoint). Keep Labs A and B running if
another section still needs them. When finished, use the named project cleanup
commands in [Reset and cleanup](#reset-and-cleanup) or the local Harness cleanup
sequence in [Local Harness workflow](#local-harness-workflow).

For AWS work, reset only Lab D with the shared SSM command, evaluate the
`reset` phase, run the selected method's `cleanup --dry-run`, review exact
ownership, perform interactive cleanup only when authorized, and run
`--expect-absent`. Keep the deployment ID and Terraform state until absence is
verified. Never use broad account cleanup or infer absence from a failed API
call.

## What this lab establishes

- Investigation starts with authorization, scope, and observable evidence.
- Configuration is intent; runtime observation is evidence.
- Deterministic automation makes a documented investigation repeatable.
- Independent evaluation separates expected outcomes from tool or agent claims.
- Deployment is not complete until the relevant runtime is independently
  verified and cleanup is scoped.
- A fixed-version result is not proof of non-exploitability or complete
  remediation.

For deeper local evidence requirements, see the [manual investigation
reference](local/manual-investigation/README.md). For checker details and
target configuration, see the [local HTTP version-check documentation](../checks/local-http-version/README.md). Environment-specific implementation details remain in the Lab A/B/C/D READMEs.
