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

## Contents

- [1. Understand PHP2Shell](#1-understand-php2shell)
- [What this lab contains](#what-this-lab-contains)
- [Part A — Hard Mode: Manual Investigation](#part-a-hard-mode-manual-investigation)
  - [2. Prerequisites and safety](#2-prerequisites-and-safety)
  - [3. Manual local investigation — Labs A and B](#3-manual-local-investigation-labs-a-and-b)
  - [4. Manual AWS investigation — Labs C and D](#4-manual-aws-investigation-labs-c-and-d)
    - [4.1 Configure AWS identity and deployment method](#41-configure-aws-identity-and-deployment-method)
    - [4.2 Deploy Labs C and D](#42-deploy-labs-c-and-d)
    - [4.3 Confirm AWS deployment scope](#43-confirm-aws-deployment-scope)
    - [4.4 Inspect and investigate PHP runtimes](#44-inspect-and-investigate-php-runtimes)
    - [4.5 Remediate, verify, and reset Lab D](#45-remediate-verify-and-reset-lab-d)
    - [4.6 AWS cleanup and absence verification](#46-aws-cleanup-and-absence-verification)
- [Part B — Auto Mode: Deterministic Automation](#part-b-auto-mode-deterministic-automation)
  - [5. From manual investigation to automated checks](#5-from-manual-investigation-to-automated-checks)
  - [6. Independent evaluation](#6-independent-evaluation)
  - [7. Automated AWS workflows](#7-automated-aws-workflows)
- [Part C — Harness Mode: VulHarness](#part-c-harness-mode-vulharness)
  - [8. Why introduce a harness?](#8-why-introduce-a-harness)
  - [9. Run VulHarness](#9-run-vulharness)
  - [10. Repository architecture and contributions](#10-repository-architecture-and-contributions)
- [Part D — Beyond the Harness: Skills and Agents](#part-d-beyond-the-harness-skills-and-agents)
  - [11. Reusable coding-agent skills](#11-reusable-coding-agent-skills)
  - [12. Future agent orchestration](#12-future-agent-orchestration)
  - [13. Future security integrations](#13-future-security-integrations)
  - [14. Contribute the next scenario](#14-contribute-the-next-scenario)
- [Appendix](#appendix)
  - [Troubleshooting and recovery](#troubleshooting-and-recovery)
  - [Technical references](#technical-references)
  - [Reset and cleanup reference](#reset-and-cleanup-reference)
- [What this lab establishes](#what-this-lab-establishes)

## 1. Understand PHP2Shell

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

Future work:

- Reusable coding-agent skills, a chief-of-staff agent, generalized
  multi-scenario execution, automatic remediation, and external security
  integrations are not implemented by this workshop.

A version below an upstream fixed threshold does not automatically prove that
an application is exploitable. This exercise does not execute exploits, prove
external exposure, or test remote code execution.

# Part A — Hard Mode: Manual Investigation

## 2. Prerequisites and safety

### Start from a fresh clone

The primary examples use a macOS or Linux terminal and a Unix-style shell.
Windows participants should use WSL2 integrated with Docker Desktop. Native
Windows PowerShell and native Windows Docker workflows are not validated by
this repository. In WSL2, use the Linux commands below after confirming that
Docker Desktop integration is enabled.

Clone the public repository and enter its root:

~~~bash
git clone https://github.com/The-AI-Security-Lab/vul-harness.git
cd vul-harness
~~~

Verify the repository root:

~~~bash
pwd
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
- A terminal and web browser
- An authorized workstation on which you may run the local containers

Check the local tools:

~~~bash
docker info
docker compose version
python3 --version
~~~

Some systems invoke Python as python rather than python3. If python3 does not
exist, verify python --version and substitute python consistently in the
commands below. If Docker cannot connect to its daemon, start Docker Desktop,
Colima, or another Docker service that you are authorized to use.

### Required only for AWS labs

- An authorized AWS account and profile.
- AWS CLI with permission to inspect and, when explicitly approved, create and
  remove the deployment-owned EC2, VPC, IAM, and SSM resources.
- A selected deployment method: AWS CLI, CloudFormation, or Terraform.
- Terraform 1.17.1 with AWS provider 6.72.0 is the live-validated toolchain
  documented for the Terraform path; the configuration retains its broader
  compatibility constraints.
- Awareness that t4g.small, EBS, public IPv4, and related AWS resources may
  incur charges until scoped cleanup completes.

If the account contains a protected reference instance, set its account-specific
ID only in the local environment as
VULHARNESS_PROTECTED_INSTANCE_ID=your-protected-instance-id. Never commit that
value. If it is unset, the evaluator reports the resource-independence check as
SKIP with skip_classification=configuration_missing.

AWS is optional. Do not deploy live AWS resources for the core local workshop.

### Optional coding-agent workflow

Codex, Claude Code, or another suitable coding agent is optional. The manual
investigation and deterministic commands remain usable without an agent. An
agent may help explain commands, generate tests, or organize evidence, but it
does not replace authorization, review, deterministic checks, or independent
evaluation.

### Safety boundary

Run commands only against environments you own or are explicitly authorized
to use. Do not add credentials, personal data, production data, or unrelated
Docker projects. The PHP inspection endpoints are training diagnostics bound
to loopback and must not be exposed publicly. Do not use exploit probes,
production scans, docker system prune, broad AWS inventory, broad AWS cleanup,
or account-wide security-setting changes.

All commands below run from the VulHarness repository root unless stated
otherwise. Local technical details are in the [Lab A README](../labs/local/lab-a/README.md)
and [Lab B README](../labs/local/lab-b/README.md).

## 3. Manual local investigation — Labs A and B

This is the complete Hard Mode investigation. Finish it before moving to
automation. The goal is to observe the runtime, compare it with the advisory,
apply a scoped update, and independently verify the result.

### 3.1 Check Docker and Compose readiness

~~~bash
docker info
docker compose version
~~~

### 3.2 Start Lab A and Lab B

Start Lab A, the fixed-version reference:

~~~bash
docker compose -f scenarios/php2shell/labs/local/lab-a/compose.lab-a.yaml up -d --build
~~~

Reset Lab B to its initial configuration, then start it:

~~~bash
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml down
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml pull
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml up -d
~~~

The reset affects only the explicitly named Lab B project. Do not use broad
cleanup commands.

### 3.3 Confirm both environments are running

~~~bash
docker compose -f scenarios/php2shell/labs/local/lab-a/compose.lab-a.yaml ps
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml ps
~~~

Expected initial state:

| Lab | Browser address | Expected serving PHP | Purpose |
| --- | --- | --- | --- |
| Lab A | http://127.0.0.1:8080 | 8.4.27 | Fixed-version reference |
| Lab B | http://127.0.0.1:8082 | 8.4.26 | Before-remediation target |

Both ports bind only to 127.0.0.1.

### 3.4 Inspect the actual HTTP-serving runtimes

Open:

- [Lab A](http://127.0.0.1:8080)
- [Lab B](http://127.0.0.1:8082)

In each application, select **Inspect Runtime**. Record the PHP version, SAPI,
and observation timestamp. Select **Reset Test** afterward; that resets only
the browser request state and does not stop or recreate containers.

Expected observations:

~~~text
Lab A: PHP 8.4.27, SAPI fpm-fcgi
Lab B: PHP 8.4.26, SAPI fpm-fcgi
~~~

### 3.5 Compare the observed versions with the advisory

For PHP 8.4, upstream fixes for both scenario advisories are present in
8.4.27. Lab A is at that threshold. Lab B is below it and warrants a
remediation decision. This comparison does not prove that Lab B is exploitable
or that Lab A is non-exploitable.

### 3.6 Inspect the existing Lab B update configuration

The merged fixed Compose configuration is read-only inspection of desired
state. It does not redeploy the lab:

~~~bash
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml config --images
~~~

The output should include the pinned PHP 8.4.27 image:

~~~text
php:8.4.27-fpm-bookworm@sha256:b75642e8c89c321039f351466134df951576fb0f7017117b3931e9a19b908d6c
~~~

### 3.7 Apply the approved Lab B update

Pull the fixed image and recreate only Lab B's PHP-FPM and Nginx services:

~~~bash
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml pull php-fpm
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml up -d --force-recreate php-fpm web
~~~

### 3.8 Inspect the remediated runtime in the browser

Manual runtime inspection is the first verification after remediation. Open
[Lab B](http://127.0.0.1:8082), select **Inspect Runtime**, and record the PHP
version, SAPI, and observation timestamp. Repeat the same inspection for
[Lab A](http://127.0.0.1:8080) as the fixed-version reference. Select **Reset
Test** after each observation.

Expected browser observations:

~~~text
lab-b: PHP 8.4.27, fixed_upstream_version
lab-a: PHP 8.4.27, fixed_upstream_version
~~~

Lab A should remain unchanged because the labs have separate Compose projects,
containers, networks, and loopback ports.

The deterministic Python checker is introduced in Auto Mode Section 5.1. Do
not substitute its result for the first manual runtime observation here.

### 3.9 Configuration intent versus runtime evidence

The update override declaring PHP 8.4.27 is configuration intent. The HTTP
response from the recreated PHP-FPM service is runtime evidence. A successful
docker compose command alone does not prove that the intended image is serving
requests.

### 3.10 Reset Lab B when appropriate

Before beginning Part B, reset Lab B to the expected before-state:

~~~bash
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml down
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml up -d
~~~

Confirm the reset with a fresh runtime check:

~~~bash
python3 scenarios/php2shell/checks/local-http-version/cli.py --target lab-b
~~~

The expected result is PHP 8.4.26 and potentially_affected_upstream_version.

### 3.11 Local cleanup checkpoint

If you are continuing to Part B, keep Labs A and B running. If you are ending
the workshop here, stop and remove only the named projects:

~~~bash
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml down
docker compose -f scenarios/php2shell/labs/local/lab-a/compose.lab-a.yaml down
~~~

Do not remove unrelated containers or images.

## 4. Manual AWS investigation — Labs C and D

AWS is an optional extension of the local investigation. The security
questions remain the same: what is running, what evidence proves it, what
permissions are in scope, and what remains unknown?

### 4.1 Configure AWS identity and deployment method

Use an account, profile, region, and disposable deployment that you are
authorized to use. `AWS_PROFILE` selects the local AWS CLI profile,
`AWS_REGION` selects the deployment region, and `VULHARNESS_METHOD` selects one
of the supported infrastructure wrappers. Define these values once and reuse
them throughout Sections 4 and 7:

~~~bash
export AWS_PROFILE="REPLACE_WITH_YOUR_PROFILE"
export AWS_REGION="us-east-1"
export VULHARNESS_METHOD="aws-cli"
aws configure list --profile "$AWS_PROFILE"
aws sts get-caller-identity \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION"
~~~

Use `cloudformation` or `terraform` instead of `aws-cli` when selecting those
methods. Keep `VULHARNESS_METHOD` unchanged for every later SSM, evaluator, and
harness command. Do not commit the profile, credentials, or deployment ID.

The identity commands are read-only. `aws configure list` shows which local
profile settings are available, and `aws sts get-caller-identity` confirms the
authenticated AWS principal in the selected region. Successful identity output
proves authentication only; it does not create infrastructure or prove that a
lab is ready.

`VULHARNESS_DEPLOYMENT_ID` is the unique deployment identifier returned by the
selected wrapper. Do not invent one or set it before the wrapper has returned a
value. The deployment setup in the next subsection captures it.

### 4.2 Deploy Labs C and D

For a new deployment, run exactly one matching wrapper. Each wrapper generates
an ID when no ID is supplied and prints or includes that ID in its deployment
output. Copy the generated value into the shell before running `status`:

- `aws-lab.sh` creates and inspects AWS CLI-managed infrastructure.
- `cf-lab.sh` manages the CloudFormation stack lifecycle.
- `tf-lab.sh` manages Terraform infrastructure and local state.

These `deploy` commands change infrastructure only. They do not install Docker,
bootstrap Compose, inspect PHP, or validate the serving runtime.

AWS CLI:

~~~bash
./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" deploy
~~~

CloudFormation:

~~~bash
./scenarios/php2shell/labs/aws/deployment/cloudformation/cf-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" deploy
~~~

Terraform:

~~~bash
./scenarios/php2shell/labs/aws/deployment/terraform/tf-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" deploy
~~~

Run only the command matching `VULHARNESS_METHOD`. The wrappers identify the
generated value as follows: AWS CLI prints `Deployment ID: vh-cli-...`; Terraform
prints `Terraform deployment applied: vh-tf-...`; CloudFormation prints a stack
name containing `vulharness-php2shell-cloudformation-vh-cfn-...`. Copy the
`vh-cli-...`, `vh-tf-...`, or `vh-cfn-...` value shown by the selected wrapper,
then set the value you observed:

~~~bash
export VULHARNESS_DEPLOYMENT_ID="REPLACE_WITH_DEPLOYMENT_ID_FROM_OUTPUT"
~~~

If an authorized deployment already exists, obtain its ID from the prior
wrapper output, the deployment owner, or the local Terraform state/stack name;
do not guess it. Set that exact ID and use the matching method's read-only
status command:

~~~bash
export VULHARNESS_DEPLOYMENT_ID="REPLACE_WITH_EXISTING_DEPLOYMENT_ID"

./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" status
~~~

For CloudFormation or Terraform, use its corresponding wrapper path and keep
the same method value. A status result must confirm the exact ownership and
method tags before reuse. Do not combine methods, adopt unrelated resources,
or start a second deployment when the existing one is still available.

### 4.3 Confirm AWS deployment scope

Lab C is the cloud fixed-version reference at PHP 8.4.27. Lab D starts at
PHP 8.4.26 and is the remediation target. Each lab runs on its own EC2
instance. SSM Online proves management-plane registration only; it does not
prove Docker, Compose, PHP, or runtime readiness.

Use the selected provisioning method's read-only `status` command. It verifies
the exact deployment identity and ownership boundary without creating or
deleting resources:

#### Deployment status and ownership

~~~bash
./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" status

./scenarios/php2shell/labs/aws/deployment/cloudformation/cf-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" status

./scenarios/php2shell/labs/aws/deployment/terraform/tf-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" status
~~~

Run only the command for the method used to create the deployment. A successful
status check means the wrapper can find the exact tagged deployment and its
expected infrastructure; it is not PHP runtime evidence. Inspect that exactly
the expected Lab C and Lab D resources are in scope, ownership and method tags
match, the IAM instance profile has the documented SSM scope, both instances
are registered with SSM, and any protected reference instance is excluded. See
the [AWS lab plan](../labs/aws/README.md) and the
[method READMEs](../labs/aws/deployment/) for permissions and recovery detail.

### 4.4 Inspect and investigate PHP runtimes

Before changing runtime state, confirm the variables point to the deployment
you just created or safely reused:

~~~bash
printf 'Profile: %s\nRegion: %s\nMethod: %s\nDeployment ID: %s\n' \
  "$AWS_PROFILE" "$AWS_REGION" \
  "$VULHARNESS_METHOD" "$VULHARNESS_DEPLOYMENT_ID"
~~~

The shared `ssm_runtime.py` script performs supported runtime actions through
authenticated AWS Systems Manager. `bootstrap` changes the selected EC2
runtime by transferring approved assets, installing Docker/Compose when
needed, validating the Compose model, and starting the selected lab. It does
not use SSH or open inbound access. Run it for both labs, then use the
read-only `aws_evaluate.py` script for the initial evidence collection:

~~~bash
python3 scenarios/php2shell/labs/aws/deployment/shared/ssm_runtime.py bootstrap \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --lab-id lab-c

python3 scenarios/php2shell/labs/aws/deployment/shared/ssm_runtime.py bootstrap \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --lab-id lab-d

python3 scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" \
  --include-ssm --phase initial
~~~

Run both bootstrap commands before the initial evaluation. The evaluator
separates infrastructure inventory, SSM connectivity, container state, Compose
state, PHP version, SAPI, timestamp, and collection limitations. A running EC2
instance or SSM Online status is not PHP runtime evidence by itself.

Do not use SSH, open inbound security-group rules, public tunnels, or arbitrary
remote commands. CloudFormation and Terraform provision infrastructure; they do
not inspect the runtime. Runtime evidence comes from the shared SSM workflow
and evaluator.

### 4.5 Remediate, verify, and reset Lab D

Compare the initial Lab C and Lab D observations with the upstream fixed
release. Lab C should remain the unchanged PHP 8.4.27 reference. Lab D should
show PHP 8.4.26 before remediation. The `remediate` action changes only Lab D;
the evaluator command that follows is read-only and checks fresh runtime
evidence:

~~~bash
python3 scenarios/php2shell/labs/aws/deployment/shared/ssm_runtime.py remediate \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --lab-id lab-d

python3 scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" \
  --include-ssm --phase remediated
~~~

Reset only Lab D and collect separate reset evidence:

~~~bash
python3 scenarios/php2shell/labs/aws/deployment/shared/ssm_runtime.py reset \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --lab-id lab-d

python3 scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" \
  --include-ssm --phase reset
~~~

Expected transitions are: Lab C remains PHP 8.4.27; Lab D is PHP 8.4.26 in
the initial state, PHP 8.4.27 after remediation, and PHP 8.4.26 after reset.
These observations must come from runtime evidence returned through SSM, not
from a successful command exit alone. Stopped, unreachable, malformed, or
uninspectable instances remain unknown or inconclusive and must never be
inferred to be fixed.

### 4.6 AWS cleanup and absence verification

Keep the deployment running if you are continuing to Section 7 or Harness
Mode. Do not clean it up before those workflows finish. When the AWS journey is
complete, use the selected wrapper's `cleanup --dry-run` first. This is
read-only: inspect the exact deployment-owned resources and any dependency
blockers before approving deletion. Example for AWS CLI:

~~~bash
./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" cleanup --dry-run

./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" cleanup
~~~

Use the corresponding `cf-lab.sh` or `tf-lab.sh` command for the selected
method. The dry-run output is the deletion scope to review. Confirmed cleanup
changes AWS infrastructure and requires explicit authorization plus the exact
`DELETE <deployment-id>` interactive confirmation. For Terraform, retain local
state until absence verification succeeds. After cleanup, run the independent
read-only `--expect-absent` verification:

~~~bash
python3 scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --expect-absent
~~~

`--expect-absent` verifies that exact deployment resources are gone; it does
not delete anything. If cleanup is incomplete or blocked by an external
dependency such as GuardDuty, do not broaden the scope. Keep the deployment ID,
review the wrapper's recovery/status output, resolve the authorized blocker,
and rerun the exact cleanup and absence check. Raw AWS evidence remains local
private evidence under the ignored `docs/evidence/aws/` path; never commit or
upload it.

# Part B — Auto Mode: Deterministic Automation

## 5. From manual investigation to automated checks

Security practitioners already know how to perform the investigation. The
scaling question is how to repeat it consistently across environments without
losing evidence provenance or uncertainty.

There are three complementary modes:

- **Manual investigation:** a practitioner performs bounded commands and
  interprets the evidence.
- **Deterministic automation:** scripts collect defined fields, apply stable
  comparison rules, and return repeatable results.
- **AI-assisted development:** a coding agent can help translate documented
  commands, evidence fields, expected outcomes, and tests into deterministic
  code for human review.

Python is the existing implementation language, not a requirement for the
concept. The deterministic checker owns version-comparison semantics; an agent
must not invent advisory rules or treat its own conclusion as evidence.

### 5.1 Run the local version checker

~~~bash
python3 scenarios/php2shell/checks/local-http-version/cli.py --target lab-a
python3 scenarios/php2shell/checks/local-http-version/cli.py --target lab-b
python3 scenarios/php2shell/checks/local-http-version/cli.py --all
~~~

Expected classifications before remediation are:

~~~text
lab-a: fixed_upstream_version
lab-b: potentially_affected_upstream_version
~~~

The checker retains the raw endpoint, SAPI, observation timestamp, per-CVE
classification, and limitations. It accepts only the explicitly configured
loopback targets.

### 5.2 Use Hello World 2.0

Start the local dashboard:

~~~bash
python3 scenarios/php2shell/checks/local-http-version/dashboard.py
~~~

Open [http://127.0.0.1:8081](http://127.0.0.1:8081) and select **Check
Runtimes**. Expand evidence details to inspect the configured endpoint,
version, SAPI, timestamp, and CVE results. The grey **Remediate** controls are
deliberately disabled: the dashboard cannot edit Compose files, run Docker
commands, or update containers. After an approved update, use **Recheck**.

### 5.3 Automation cleanup checkpoint

When finished with the dashboard, return to its terminal and press Ctrl+C. If
continuing to Section 6, keep Labs A and B running. If ending the exercise,
follow the scoped local cleanup in [Section 3.11](#311-local-cleanup-checkpoint).
Do not remove containers required by subsequent steps.

## 6. Independent evaluation

An evaluation is a repeatable comparison between expected outcomes and observed
evidence. It is independent of the checker, harness, coding agent, or provider
that collected the evidence.

Because Hard Mode remediated Lab B, reset it before running this lifecycle:

~~~bash
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml down
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml up -d
~~~

### 6.1 Before-remediation evaluation

~~~bash
python3 scenarios/php2shell/evals/remediation-lifecycle/evaluate.py --state before
~~~

Expected summary:

~~~text
State: before
Result: PASS
Observed PHP version: 8.4.26
Expected PHP version: 8.4.26
~~~

Both CVEs must be potentially_affected_upstream_version. PASS establishes
that Lab B's HTTP-serving runtime matches the documented before-state; it does
not prove vulnerability or exploitability.

### 6.2 Configuration-only evaluation

Inspect the merged desired configuration without redeploying:

~~~bash
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml config --images
python3 scenarios/php2shell/evals/remediation-lifecycle/evaluate.py --state config-only
~~~

Expected result: PASS. The evaluator confirms that the desired Compose model
selects PHP 8.4.27 while the runtime still serving HTTP remains PHP 8.4.26.
Configuration intent and deployed runtime are separate facts.

### 6.3 Apply and evaluate the after-state

Apply the same scoped update used in Hard Mode:

~~~bash
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml pull php-fpm
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml up -d --force-recreate php-fpm web
python3 scenarios/php2shell/checks/local-http-version/cli.py --all
python3 scenarios/php2shell/evals/remediation-lifecycle/evaluate.py --state after
~~~

PASS requires HTTP-observed PHP 8.4.27, fixed classifications for both CVEs,
and a read-only running-container inspection identifying the approved fixed
PHP-FPM image. It does not prove non-exploitability or complete remediation.

### 6.4 Reset and cleanup checkpoint

Reset Lab B if another participant or exercise needs the expected baseline:

~~~bash
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml down
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml up -d
python3 scenarios/php2shell/evals/remediation-lifecycle/evaluate.py --state before
~~~

If you are continuing into Harness Mode, keep Labs A and B running and do not
run this cleanup checkpoint yet; Section 9.1 needs those projects available.
When ending the local exercise, stop the dashboard if it is running and remove
only the named Lab B and Lab A projects:

~~~bash
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml down
docker compose -f scenarios/php2shell/labs/local/lab-a/compose.lab-a.yaml down
~~~

## 7. Automated AWS workflows

The AWS automation uses the same investigation questions with explicit
deployment scope and machine-readable evidence. It is optional and can incur
cost. Choose exactly one infrastructure method per lifecycle:

1. [AWS CLI deployment](../labs/aws/deployment/cli/README.md)
2. [CloudFormation deployment](../labs/aws/deployment/cloudformation/README.md)
3. [Terraform deployment](../labs/aws/deployment/terraform/README.md)

CloudFormation and Terraform are provisioning alternatives, not substitutes
for SSM runtime inspection. The shared SSM workflow and independent evaluator
remain the runtime and assessment path.

If you start directly in Auto Mode, first review
[Section 4.1](#41-configure-aws-identity-and-deployment-method) and
[Section 4.2](#42-deploy-labs-c-and-d) to define the AWS variables and obtain
one authorized deployment ID. Reuse that deployment if it still exists; do not
run a second `deploy` command just because you entered through Section 7.

### 7.1 Reuse the Section 4 deployment

Continue with the same `AWS_PROFILE`, `AWS_REGION`, `VULHARNESS_METHOD`, and
`VULHARNESS_DEPLOYMENT_ID` values established in Section 4. If that deployment
still exists, do not run another wrapper `deploy` command. Run the selected
method's status command to confirm that the exact deployment remains owned by
the selected method:

~~~bash
./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" status
~~~

For a CloudFormation deployment, use
`scenarios/php2shell/labs/aws/deployment/cloudformation/cf-lab.sh`; for a
Terraform deployment, use
`scenarios/php2shell/labs/aws/deployment/terraform/tf-lab.sh`. Keep
`VULHARNESS_METHOD` aligned with that wrapper. If the Section 4 deployment was
cleaned up, return to [Section 4.1](#41-configure-aws-identity-and-deployment-method),
create one fresh deployment with the selected wrapper, capture its generated
ID, and then return here. This avoids duplicate deployments and unnecessary
AWS cost.

The provisioning wrappers create infrastructure only. They do not install
Docker, start Compose, inspect PHP, or run arbitrary commands through SSM.

### 7.2 Bootstrap through authenticated SSM

Use the `VULHARNESS_METHOD` value defined in Section 4.1. The exact mapping is:

| Provisioning method | `VULHARNESS_METHOD` | Wrapper |
| --- | --- | --- |
| AWS CLI | `aws-cli` | `scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh` |
| CloudFormation | `cloudformation` | `scenarios/php2shell/labs/aws/deployment/cloudformation/cf-lab.sh` |
| Terraform | `terraform` | `scenarios/php2shell/labs/aws/deployment/terraform/tf-lab.sh` |

Then bootstrap both labs through the shared workflow:

~~~bash
python3 scenarios/php2shell/labs/aws/deployment/shared/ssm_runtime.py bootstrap \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --lab-id lab-c

python3 scenarios/php2shell/labs/aws/deployment/shared/ssm_runtime.py bootstrap \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --lab-id lab-d
~~~

The workflow transfers approved assets with integrity checks, installs Docker
and Compose on Amazon Linux 2023, validates the Compose model, and starts the
selected lab. It does not use SSH or open inbound access.

### 7.3 Discover, assess, remediate, and reset

Run the initial infrastructure, SSM, Docker, Compose, and PHP evaluation:

~~~bash
python3 scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" \
  --include-ssm --phase initial
~~~

The evaluator queries only exact project, scenario, deployment, and method
tags. It does not scan an entire account. Evidence is written locally under
the ignored `docs/evidence/aws/` path and must not be committed or uploaded.

Update only Lab D and evaluate the remediated state:

~~~bash
python3 scenarios/php2shell/labs/aws/deployment/shared/ssm_runtime.py remediate \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --lab-id lab-d

python3 scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" \
  --include-ssm --phase remediated
~~~

Reset Lab D and collect separate reset evidence:

~~~bash
python3 scenarios/php2shell/labs/aws/deployment/shared/ssm_runtime.py reset \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --lab-id lab-d

python3 scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method "$VULHARNESS_METHOD" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" \
  --include-ssm --phase reset
~~~

Stopped, unreachable, malformed, or uninspectable instances remain unknown or
inconclusive. They must never be inferred to be fixed.

### 7.4 Scoped cleanup and absence verification

If the AWS deployment is no longer needed after Auto Mode, follow the
independent [Section 4.6 cleanup and absence procedure](#46-aws-cleanup-and-absence-verification).
It contains the method-specific dry-run, exact-scope approval, interactive
confirmation, and `--expect-absent` verification. If continuing into Harness
Mode, keep the deployment and the Section 4 variables available instead.

### 7.5 Method limitations and future CI/CD use

The detailed AWS READMEs document IAM permissions, provider constraints,
partial-deployment recovery, VPC CIDR conflicts, ownership tags, costs,
GuardDuty cleanup constraints, and troubleshooting. The evaluator distinguishes
configured infrastructure, SSM connectivity, serving runtime, version
classification, and demonstrated exploitability.

CI/CD could eventually invoke bounded checks against an authorized build or
deployment, but no production CI/CD integration is validated or implemented by
this workshop.

# Part C — Harness Mode: VulHarness

## 8. Why introduce a harness?

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

## 9. Run VulHarness

The implemented entry point is:

~~~text
scripts/vulharness-php2shell.py
~~~

Run it from the repository root. Mutating operations require an
operation-specific approval token; there is no generic yes option. The local
and AWS lifecycles below are intentionally separate. Complete the local path
without cleaning up if you are continuing to the next local step.

### 9.1 Local lifecycle

Check prerequisites, start the named local projects, and inspect their status:

~~~bash
python3 scripts/vulharness-php2shell.py preflight --env local
python3 scripts/vulharness-php2shell.py setup --env local --approve setup
python3 scripts/vulharness-php2shell.py status --env local
python3 scripts/vulharness-php2shell.py inspect --env local
~~~

Assess Lab B's baseline, then start the dashboard in a second terminal. Use its
local page, press Ctrl+C in that terminal when finished, and return to the
original terminal for remediation and verification:

~~~bash
python3 scripts/vulharness-php2shell.py assess \
  --env local --lab lab-b --state before
python3 scripts/vulharness-php2shell.py dashboard --env local
python3 scripts/vulharness-php2shell.py remediate \
  --env local --lab lab-b --approve remediate
python3 scripts/vulharness-php2shell.py verify --env local
~~~

The dashboard command may remain active while its local page is used. The
remediation command is the approved harness action; it does not turn the
dashboard's disabled remediation controls into an executable action. A local
verification after remediation should observe the fixed Lab B runtime. To
exercise reset and demonstrate the full state transition, reset Lab B and
assess it again:

~~~bash
python3 scripts/vulharness-php2shell.py reset \
  --env local --lab lab-b --approve reset
python3 scripts/vulharness-php2shell.py assess \
  --env local --lab lab-b --state before
~~~

Do not clean up Labs A or B until all local harness steps are complete. Review
the cleanup target list first, then perform only the named cleanup:

~~~bash
python3 scripts/vulharness-php2shell.py cleanup \
  --env local --lab lab-b --dry-run
python3 scripts/vulharness-php2shell.py cleanup \
  --env local --lab lab-b --approve cleanup
python3 scripts/vulharness-php2shell.py cleanup \
  --env local --lab lab-a --dry-run
python3 scripts/vulharness-php2shell.py cleanup \
  --env local --lab lab-a --approve cleanup
~~~

### 9.2 AWS lifecycle

The AWS harness uses the exact `VULHARNESS_METHOD` and
`VULHARNESS_DEPLOYMENT_ID` established in Section 4. Do not replace them with
`aws-cli` or a new placeholder when continuing with CloudFormation or
Terraform. The harness requires a deployment ID for `status`, `inspect`,
`assess`, `remediate`, `verify`, `reset`, and `cleanup`.

`setup` is the exception: if you pass the existing deployment ID, it resumes
that exact deployment after validating ownership; if you omit the ID, the
implementation generates a new method-specific ID, writes local orchestration
metadata, deploys infrastructure, bootstraps both labs, and prints the new ID.
To avoid an unintended duplicate deployment, reuse the Section 4 ID whenever
that deployment still exists. If it was cleaned up, return to
[Section 4.1](#41-configure-aws-identity-and-deployment-method)
and create one fresh deployment before continuing here.

Preflight and status validate the selected scope; setup performs the selected
deployment and shared SSM bootstrap for Labs C and D:

~~~bash
python3 scripts/vulharness-php2shell.py preflight \
  --env aws --method "$VULHARNESS_METHOD" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION"
python3 scripts/vulharness-php2shell.py setup \
  --env aws --method "$VULHARNESS_METHOD" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --approve setup
python3 scripts/vulharness-php2shell.py status \
  --env aws --method "$VULHARNESS_METHOD" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID"
~~~

Assess the initial state, remediate only Lab D, verify the remediated state,
and reset Lab D:

~~~bash
python3 scripts/vulharness-php2shell.py assess \
  --env aws --method "$VULHARNESS_METHOD" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --phase initial
python3 scripts/vulharness-php2shell.py remediate \
  --env aws --method "$VULHARNESS_METHOD" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --lab lab-d \
  --approve remediate
python3 scripts/vulharness-php2shell.py verify \
  --env aws --method "$VULHARNESS_METHOD" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --phase remediated
python3 scripts/vulharness-php2shell.py reset \
  --env aws --method "$VULHARNESS_METHOD" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --lab lab-d \
  --approve reset
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
python3 scripts/vulharness-php2shell.py cleanup \
  --env aws --method "$VULHARNESS_METHOD" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --dry-run
python3 scripts/vulharness-php2shell.py cleanup \
  --env aws --method "$VULHARNESS_METHOD" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --approve cleanup
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

### 9.3 Harness result semantics

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

## 10. Repository architecture and contributions

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

# Part D — Beyond the Harness: Skills and Agents

## 11. Reusable coding-agent skills

A coding-agent skill is a reusable set of instructions or a practitioner
procedure that tells an agent how to perform a bounded capability: for example,
inspect a runtime, collect evidence, validate a result, or prepare a report.

A future PHP investigation skill could reuse documented commands, evidence
fields, authorization boundaries, and validation methods. It must still perform
fresh advisory analysis for a new PHP CVE. A new advisory cannot inherit old
affected-version rules merely because the runtime or product name is similar.

Reusable skills are future work unless implemented evidence exists. Manual
walkthroughs and deterministic checks remain first-class.

## 12. Future agent orchestration

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

## 13. Future security integrations

Future adapters could enrich an investigation with:

- CNAPP or CSPM findings
- SIEM and logging platforms
- Cloud-provider inventory APIs
- Notifications such as Slack

These are integration possibilities, not currently implemented features. An
external finding must not automatically be treated as verified runtime
exposure, and an adapter must preserve source, timestamp, scope, freshness, and
coverage.

## 14. Contribute the next scenario

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

### Docker daemon unavailable

~~~bash
docker info
~~~

Start the authorized Docker service if it cannot connect. The evaluator reports
failed read-only inspection rather than changing Docker state.

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
python3 scenarios/php2shell/checks/local-http-version/cli.py --target lab-b
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml config --images
~~~

If the desired image is fixed but HTTP still reports 8.4.26, the runtime has
not been recreated. Return to [Apply the approved Lab B update](#37-apply-the-approved-lab-b-update). If you intended the before-state, use [Reset Lab B](#310-reset-lab-b-when-appropriate).

### Container starts but HTTP is unavailable

Inspect only Lab B:

~~~bash
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml ps
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml logs --tail=50 web php-fpm
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
[Section 3.10](#310-reset-lab-b-when-appropriate) or
[Section 6.4](#64-reset-and-cleanup-checkpoint). Keep Labs A and B running if
another section still needs them. When finished, use the named project cleanup
commands in [Section 3.11](#311-local-cleanup-checkpoint) or the harness cleanup
sequence in [Section 9.1](#91-local-lifecycle).

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
