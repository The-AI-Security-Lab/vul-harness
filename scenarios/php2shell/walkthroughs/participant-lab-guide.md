# PHP2Shell Participant Lab Guide

This is the canonical self-service journey for VulHarness Scenario 1. Run all commands from the repository root unless a step says otherwise. The guide grows progressively: the orchestration command provides one safe entry point for the implemented local and AWS paths, while the detailed sections retain the evidence and learning context. Agent-assisted work stays clearly marked as planned.

The workshop journey is:

```text
Authorize → Inspect → Compare → Automate → Remediate → Verify → Evaluate → Clean up
```

## What is implemented

The local Lab A and Lab B journey is implemented and tested. It runs two independent PHP environments, inspects the PHP runtime actually serving HTTP requests, automates the version comparison, updates Lab B, and independently verifies the deployed result.

The AWS Lab C and Lab D journey includes live-validated infrastructure, three independent deployment methods, shared SSM-only Docker/Compose bootstrap, scoped EC2 discovery, Systems Manager runtime collection, and an independent cloud evaluator. The local dashboard is implemented; an AWS-hosted dashboard and agent-assisted investigation remain future work.

## Part A — Understand the security problem

PHP2Shell is the name used in this scenario for two upstream PHP vulnerabilities: CVE-2026-109618, remote code execution through out-of-memory corruption, and CVE-2026-109619, remote code execution through stale global state. Both have upstream PHP 8.4 fixes in PHP 8.4.27. Their technical conditions differ, so a version comparison is not proof that an application is exploitable or non-exploitable. See the [PHP2Shell reference register](../references.md) for authoritative advisories, affected branches, prerequisites, and limitations.

This is a version-based investigation and remediation exercise. It does not execute exploits, prove exposure, or test remote code execution.

The completed local path takes approximately 15–25 minutes after the required images are available. Independent participants may take longer, especially during the first image download.

## 1. Prerequisites and safety

You need:

- Docker with Docker Compose v2
- Python 3.9 or later
- A terminal and web browser
- A local copy of the VulHarness repository
- Authorization to run local containers on the workstation

Open a terminal in the repository root. The following should list `README.md` and `scenarios`:

```sh
pwd
ls README.md scenarios
```

Confirm that Docker and Compose are available:

```sh
docker info
docker compose version
```

If `docker info` reports that it cannot connect to the daemon, start Docker Desktop, Colima, or your authorized Docker service before continuing.

All commands below run from the **VulHarness repository root** unless explicitly stated otherwise.

Use only these authorized local labs. Do not add credentials, personal data, production data, or unrelated Docker projects. The PHP inspection endpoints are training diagnostics and must remain on loopback. Do not use exploit probes or broad Docker cleanup commands.

Technical environment details are maintained separately in the [Lab A README](../labs/local/lab-a/README.md) and [Lab B README](../labs/local/lab-b/README.md).

## Part B — Manual local investigation with Labs A and B

### Start the labs

Why this matters: Lab A and Lab B are separate Compose projects. Starting and inspecting them independently prevents one environment’s desired state from being mistaken for the other’s runtime evidence.

Start Lab A:

```sh
docker compose -f scenarios/php2shell/labs/local/lab-a/compose.lab-a.yaml up -d --build
```

Reset Lab B to its initial configuration, then start it:

```sh
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml down
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml pull
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml up -d
```

The reset command affects only the explicitly named Lab B project. Do not use broad cleanup commands such as `docker system prune`.

Confirm both projects are running:

```sh
docker compose -f scenarios/php2shell/labs/local/lab-a/compose.lab-a.yaml ps
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml ps
```

Expected initial state:

| Lab | Browser address | Expected serving PHP | Purpose |
| --- | --- | --- | --- |
| Lab A | `http://127.0.0.1:8080` | 8.4.27 | First local runtime |
| Lab B | `http://127.0.0.1:8082` | 8.4.26 | Before-remediation runtime |

Both ports bind only to `127.0.0.1`. They are not intended for public or remote exposure. Lab B’s version is below the upstream fixed threshold; that does not establish that the application is exploitable.

### Inspect the serving runtimes

Why this matters: a version declared in a Compose file is desired configuration. The response produced through Nginx and PHP-FPM is evidence of the runtime currently serving the application.

Open these addresses in a browser:

- Lab A: [http://127.0.0.1:8080](http://127.0.0.1:8080)
- Lab B: [http://127.0.0.1:8082](http://127.0.0.1:8082)

In each application, select **Inspect Runtime**. Record the PHP version, SAPI, and observation timestamp. Select **Reset Test** afterward to return the page to its initial state; this only clears the browser request state and does not stop or recreate containers.

Expected observations:

```text
Lab A: PHP 8.4.27, SAPI fpm-fcgi
Lab B: PHP 8.4.26, SAPI fpm-fcgi
```

Compare the observations with the [documented upstream fixed releases](../references.md). For PHP 8.4, both scenario advisories are fixed upstream in 8.4.27. Lab A is at that threshold. Lab B is below it and therefore warrants a remediation decision, while exploitability and vendor backports remain unassessed.

## Part C — Manual AWS investigation with Labs C and D

AWS is an optional extension of the core local workshop, not a prerequisite
for completing it. Labs C and D use two separate EC2 instances and authenticated
AWS Systems Manager access. The manual questions are the same: what is running,
what evidence proves it, what permissions are in scope, and what remains
unknown?

For an already authorized deployment, establish identity and inspect only the
exact deployment scope:

```bash
export AWS_PROFILE=vul-harness-lab-nov26
export AWS_REGION=us-east-1
aws sts get-caller-identity --profile "$AWS_PROFILE" --region "$AWS_REGION"
./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id <deployment-id> status
```

The manual AWS workflow then separates EC2 inventory, IAM instance-profile
scope, SSM `Online` status, loopback runtime collection, PHP version evidence,
and cleanup evidence. SSM registration proves management-plane connectivity;
it does not prove Docker, Compose, PHP, or runtime readiness. AWS CLI,
CloudFormation, and Terraform are supported provisioning methods, but a
participant chooses at most one for a deployment cycle and does not need to
learn all three. See the [AWS implementation guide](../labs/aws/README.md)
for the detailed, optional cloud workflow. Do not deploy live AWS resources for
the core local workshop.

## Part D — From manual commands to deterministic automation

Why this matters: the checker repeats the version comparison consistently while retaining the raw endpoint, SAPI, timestamp, per-CVE result, and explicit limitations.

Check each lab and then both together:

```sh
python3 scenarios/php2shell/checks/local-http-version/cli.py --target lab-a
python3 scenarios/php2shell/checks/local-http-version/cli.py --target lab-b
python3 scenarios/php2shell/checks/local-http-version/cli.py --all
```

Expected classifications:

```text
lab-a: fixed_upstream_version
lab-b: potentially_affected_upstream_version
```

Start Hello World 2.0 in this terminal:

```sh
python3 scenarios/php2shell/checks/local-http-version/dashboard.py
```

Leave that process running and open [http://127.0.0.1:8081](http://127.0.0.1:8081). Select **Check Runtimes**.

The inventory has one row per explicitly configured endpoint. Expand the evidence details to see each CVE result. The grey **Remediate** buttons are deliberately disabled: the dashboard cannot edit Compose files, run Docker commands, or update containers. Later, **Recheck** collects fresh evidence after you perform an approved update.

Use a second terminal in the repository root for the remaining commands.

## Part E — Independent evaluation

### Establish the before-remediation state

Why this matters: the evaluation turns the documented before-state expectation into a repeatable PASS/FAIL decision without duplicating the checker’s advisory comparison logic.

Run:

```sh
python3 scenarios/php2shell/evals/remediation-lifecycle/evaluate.py --state before
```

Expected summary:

```text
State: before
Result: PASS
Observed PHP version: 8.4.26
Expected PHP version: 8.4.26
```

Both CVEs must be `potentially_affected_upstream_version`. PASS establishes that Lab B’s HTTP-serving runtime matches this exercise’s documented before-state. It does not prove vulnerability or exploitability.

### Inspect the configuration-only state

Why this matters: changing deployment intent is not the same as changing the running service.

Inspect the merged fixed Compose configuration. This command is read-only and does not redeploy the lab:

```sh
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml config --images
```

The output should include:

```text
php:8.4.27-fpm-bookworm@sha256:b75642e8c89c321039f351466134df951576fb0f7017117b3931e9a19b908d6c
```

Do not run `up` yet. Evaluate the configuration-only state:

```sh
python3 scenarios/php2shell/evals/remediation-lifecycle/evaluate.py --state config-only
```

Expected result: PASS. The evaluator confirms two separate facts:

- The merged desired Compose model selects PHP 8.4.27.
- The runtime still serving HTTP is PHP 8.4.26 and remains `potentially_affected_upstream_version`.

The `before` and `config-only` states cannot be distinguished from HTTP evidence alone. The additional read-only Compose inspection supplies the configuration-intent evidence.

### Apply the Lab B update

Why this matters: remediation is not deployed until the relevant service is recreated from the approved fixed configuration.

Pull the fixed PHP image for Lab B:

```sh
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml pull php-fpm
```

Recreate only Lab B’s PHP-FPM and Nginx services:

```sh
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml up -d --force-recreate php-fpm web
```

Verify the serving runtimes independently:

```sh
python3 scenarios/php2shell/checks/local-http-version/cli.py --target lab-b
python3 scenarios/php2shell/checks/local-http-version/cli.py --target lab-a
```

Expected:

```text
lab-b: PHP 8.4.27, fixed_upstream_version
lab-a: PHP 8.4.27, fixed_upstream_version
```

Lab A should remain unchanged because Lab B has its own Compose project, containers, networks, and loopback port.

### Independently verify and evaluate the deployed runtime

Why this matters: independent observation verifies what was deployed rather than trusting the update command’s success message.

Collect a combined CLI report:

```sh
python3 scenarios/php2shell/checks/local-http-version/cli.py --all
```

Return to Hello World 2.0 and select **Recheck**. Lab B should now show PHP 8.4.27 and `fixed_upstream_version`.

Run the after-state evaluation:

```sh
python3 scenarios/php2shell/evals/remediation-lifecycle/evaluate.py --state after
```

PASS requires:

- HTTP-observed PHP 8.4.27 from Lab B
- `fixed_upstream_version` for CVE-2026-109618
- `fixed_upstream_version` for CVE-2026-109619
- A read-only running-container inspection that identifies the approved fixed PHP-FPM image

PASS verifies the version and lifecycle evidence for this exercise. It does not prove non-exploitability, validate every deployment condition, or establish full vulnerability remediation.

## Part F — Introduce VulHarness

Only after the manual investigation, deterministic automation, and independent
evaluation does the unified harness become useful. The entry point is:

```text
scripts/vulharness-php2shell.py
```

It coordinates the existing Compose projects, AWS deployment wrappers, shared
SSM runtime actions, deterministic checks, and independent evaluators. It does
not replace those components or duplicate their PHP advisory, AWS ownership,
GuardDuty, or evidence-comparison logic.

Run it from the repository root. Mutating operations require an
operation-specific approval token; there is no generic `--yes` option.

| Goal | Local command | AWS command shape |
| --- | --- | --- |
| Check prerequisites | `python3 scripts/vulharness-php2shell.py preflight --env local` | `python3 scripts/vulharness-php2shell.py preflight --env aws --method aws-cli --profile vul-harness-lab-nov26 --region us-east-1` |
| Start/deploy | `python3 scripts/vulharness-php2shell.py setup --env local --approve setup` | `python3 scripts/vulharness-php2shell.py setup --env aws --method aws-cli --profile vul-harness-lab-nov26 --region us-east-1 --approve setup` |
| Inspect/status | `python3 scripts/vulharness-php2shell.py inspect --env local` | `python3 scripts/vulharness-php2shell.py status --env aws --method aws-cli --deployment-id <id>` |
| Assess | `python3 scripts/vulharness-php2shell.py assess --env local --lab lab-b --state before` | `python3 scripts/vulharness-php2shell.py assess --env aws --method aws-cli --deployment-id <id> --phase initial` |
| Remediate/reset | `python3 scripts/vulharness-php2shell.py remediate --env local --lab lab-b --approve remediate` | `python3 scripts/vulharness-php2shell.py remediate --env aws --method aws-cli --deployment-id <id> --lab lab-d --approve remediate` |
| Verify | `python3 scripts/vulharness-php2shell.py verify --env local` | `python3 scripts/vulharness-php2shell.py verify --env aws --method aws-cli --deployment-id <id> --phase remediated` |
| Cleanup | `python3 scripts/vulharness-php2shell.py cleanup --env local --lab lab-a --dry-run` | `python3 scripts/vulharness-php2shell.py cleanup --env aws --method aws-cli --deployment-id <id> --dry-run` |

AWS `setup` deploys both EC2 instances with the selected independent method,
then invokes the shared SSM bootstrap for Lab C and Lab D. It stops on a
partial failure and retains the deployment identity for recovery. A new AWS
deployment generates an ID and retains metadata under the ignored
`.vulharness-orchestration/deployments/` directory. Resume with the same
`--deployment-id` or `VULHARNESS_DEPLOYMENT_ID`; do not switch methods or adopt
another deployment.

After confirmed cleanup, run the independent absence evaluation:

```bash
python3 scripts/vulharness-php2shell.py verify \
  --env aws --method aws-cli --deployment-id <id> --expect-absent
```

The harness returns `0` for success, `1` for an invoked failure, `2` for an
invalid or incompatible request, `3` for a missing prerequisite, and `4` for a
partial/unhealthy or externally blocked AWS state. `--output json` includes
the invoked scope, child commands, redacted output, and evidence directory.
Confirmed AWS cleanup remains interactive and requires the underlying exact
`DELETE <deployment-id>` confirmation. GuardDuty-managed endpoints remain an
external dependency; the harness does not change GuardDuty or account-level
security settings.

## Part G — Repository architecture

The PHP2Shell implementation is a reference scenario, not a generic scenario
registry or automatic agent platform:

```text
scripts/vulharness-php2shell.py       scenario-specific orchestration
scenarios/php2shell/scenario.yaml     scenario identity and metadata
scenarios/php2shell/references.md     advisory and technical references
scenarios/php2shell/labs/             controlled local/AWS environments
scenarios/php2shell/checks/           deterministic evidence collection
scenarios/php2shell/evals/            independent expected-state evaluations
scenarios/php2shell/walkthroughs/     participant learning journeys
docs/evidence/                         local evidence; raw AWS output is ignored
docs/architecture.md                  framework boundaries and future direction
```

Labs own environment configuration. Checks collect concrete evidence.
Evaluations compare observed evidence with expected outcomes independently of
the harness or any coding agent. Walkthroughs explain the learning journey;
implementation READMEs hold detailed technical commands. The [architecture
document](../../../docs/architecture.md) defines the separation.

## 8. AWS implementation and lifecycle reference

> **AWS Labs C/D — infrastructure first, then shared SSM runtime evaluation**

This stage describes the Scenario 1 AWS journey for [Lab C and Lab D](../labs/aws/README.md). AWS CLI, CloudFormation, and Terraform infrastructure paths are available. They provision infrastructure only until the shared SSM runtime stage is run; they do not automatically establish PHP runtime readiness.

Participants choose exactly one independent infrastructure deployment method:

1. AWS CLI — [CLI deployment](../labs/aws/deployment/cli/README.md).
2. CloudFormation — [CloudFormation deployment](../labs/aws/deployment/cloudformation/README.md).
3. Terraform — [Terraform deployment](../labs/aws/deployment/terraform/README.md).

Do not combine methods or adopt resources created by another method. The existing `php2shell-container` instance is not part of this exercise and must not be modified.

The intended cloud journey remains:

```text
Discover → Inspect → Compare → Update → Verify → Evaluate
```

It must continue to separate EC2 inventory, SSM connectivity, serving-runtime evidence, version classification, deployment status, and demonstrated exploitability.

### 8.1 AWS prerequisites, method selection and account setup

Before selecting a method, confirm:

- You are authorized to create and remove disposable infrastructure in the approved AWS account.
- The AWS CLI is installed and the `vul-harness-lab-nov26` profile is present.
- Terraform 1.17.1 and AWS provider 6.72.0 are the validated live toolchain if using the Terraform method; the configuration retains its Terraform `>= 1.5.0` and AWS provider `>= 6.43.0, < 7.0.0` constraints, but an older local Terraform/provider cache is not considered validated. Provider initialization must succeed before planning or applying.

If the account contains a protected reference instance, set its account-specific
ID only in the local environment as
`VULHARNESS_PROTECTED_INSTANCE_ID=<instance-id>`. Never commit or paste that
value into public documentation. If it is unset, the evaluator reports the
resource-independence check as `SKIP` with
`skip_classification=configuration_missing`.
- The profile has the least-privilege permissions required for the deployment-owned EC2, VPC, IAM, and SSM resources.
- The intended region is `us-east-1`.
- You have an owner and expiration value for the deployment.
- You understand that this stage creates public-subnet infrastructure with zero inbound security-group rules.

Set the approved profile and region explicitly in the terminal used for the workshop:

```bash
export AWS_PROFILE=vul-harness-lab-nov26
export AWS_REGION=us-east-1
aws configure list --profile "$AWS_PROFILE"
aws sts get-caller-identity --profile "$AWS_PROFILE" --region "$AWS_REGION"
```

Do not place access keys, session tokens, or private credentials in the repository or command output.

Choose exactly one method for a deployment cycle. Do not combine methods or reuse resources, state, stacks, VPCs, subnets, IAM roles, security groups, or instances across methods. `t4g.small` may incur charges; confirm the account's current Free Tier or credit eligibility before deploying.

All three methods select Amazon Linux 2023 ARM64, create two separate `t4g.small` instances with encrypted 20-GiB gp3 roots, require IMDSv2, create a dedicated SSM instance profile, and use zero inbound security-group rules. The method tag keeps their ownership independent.

Run a new AWS CLI deployment from the repository root. It generates a unique deployment ID and a default 24-hour expiration:

```bash
./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh deploy
```

Record the printed deployment ID and export it for later commands:

```bash
export VULHARNESS_DEPLOYMENT_ID=vh-<deployment-id>
./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh status
./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh cleanup --dry-run
```

To resume an interrupted deployment, set the same `VULHARNESS_DEPLOYMENT_ID` and run `deploy` again. The CLI discovers exact deployment-owned resources, preserves the existing expiration timestamp, validates resources before reuse, and creates only missing resources. It does not repair conflicting, ambiguous, orphaned, or incorrectly tagged resources. If Lab C exists but Lab D does not, it validates Lab C and creates only Lab D.

```bash
export VULHARNESS_DEPLOYMENT_ID=vh-<existing-deployment-id>
./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh deploy
```

Confirmed cleanup requires typing `DELETE <deployment-id>` after the exact resource list is shown:

```bash
./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh cleanup
```

Cleanup is manual, scoped to the deployment ID, and safe to retry. EC2 instances, EBS volumes, public IPv4 addresses, and other resources can incur AWS charges while they remain provisioned. Do not leave a workshop deployment running after the exercise.

CloudFormation and Terraform alternatives:

```bash
./scenarios/php2shell/labs/aws/deployment/cloudformation/cf-lab.sh deploy
./scenarios/php2shell/labs/aws/deployment/terraform/tf-lab.sh deploy
```

Use the corresponding `status`, `cleanup --dry-run`, and confirmed `cleanup` commands from the linked technical README. Terraform state must be retained until independent post-cleanup AWS verification succeeds.

### 8.2 Part 1 live-validation result

The AWS CLI Part 1 live validation successfully deployed and validated both Lab C and Lab D. The deployment reached infrastructure `Status: HEALTHY`; the observed infrastructure state included:

- Two separate EC2 instances, correctly identified as Lab C and Lab D.
- EC2 instances running with the approved Amazon Linux 2023 ARM64 configuration.
- `t4g.small` instance sizing.
- Encrypted 20-GiB gp3 root volumes.
- IMDSv2 required.
- Zero inbound security-group rules.
- Both instances registered `Online` in AWS Systems Manager.

This result establishes infrastructure health and SSM connectivity only. It does not establish that Docker, PHP, Compose, the serving endpoint, or the PHP runtime is ready.

CloudFormation has also completed two live, independently evaluated Lab C/D lifecycles, including Docker/Compose bootstrap, PHP baseline/remediation/reset, GuardDuty-aware cleanup, and post-cleanup absence checks. Terraform has completed two independent live lifecycles with the same runtime, remediation, reset, repeatability, GuardDuty-aware cleanup, and post-cleanup absence checks. The Terraform wrapper explicitly selects the AWS profile and enables shared-config loading (`AWS_SDK_LOAD_CONFIG=1`) so provider STS initialization matches AWS CLI profile resolution.

Two live Terraform lifecycles used separate retained state until independent absence verification passed. One recovered from a transient SSM localhost readiness failure, and the other recovered from initial package/plugin readiness races by rerunning the same bounded bootstrap commands.

### 8.3 EC2 provisioning and SSM access

Each method provisions two separate EC2 instances: one for Lab C and one for Lab D. The independent evaluator verifies instance identity, region, tags, IAM instance profile, encrypted root volumes, IMDSv2, zero inbound rules, and SSM registration.

It does not verify Docker readiness, repository-layout provenance, PHP, or the serving runtime. Those checks belong to later stages.

The PHP inspection endpoint must remain bound to `127.0.0.1:8080` on each instance. It must not be exposed through a public IP, load balancer, public security-group ingress rule, or unauthenticated tunnel. Inspection uses authenticated AWS Systems Manager access.

### 8.4 Shared SSM Docker and Compose bootstrap

After infrastructure validation, use the same SSM-only bootstrap for whichever method you selected:

```bash
python3 scenarios/php2shell/labs/aws/deployment/shared/ssm_runtime.py bootstrap \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method <aws-cli|cloudformation|terraform> \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --lab-id lab-c

python3 scenarios/php2shell/labs/aws/deployment/shared/ssm_runtime.py bootstrap \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method <aws-cli|cloudformation|terraform> \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --lab-id lab-d
```

The workflow transfers the approved assets with integrity checks, installs Docker and Compose on Amazon Linux 2023, validates the Compose model, and starts the selected lab. It does not use SSH or open inbound access.

### 8.5 Starting Labs C and D

The deployment artifacts are:

- [Lab C Compose scaffold](../labs/aws/lab-c/compose.lab-c.yaml)
- [Lab D base scaffold](../labs/aws/lab-d/compose.lab-d.yaml)
- [Lab D update override](../labs/aws/lab-d/compose.lab-d.update.yaml)

The future deployment must preserve the repository's `scenarios/php2shell/labs/` layout on each instance because the Compose files reuse shared application and Nginx files through relative, read-only mounts.

The shared bootstrap copies the required files to EC2 and starts the selected workload. Lab C uses PHP 8.4.27. Lab D starts with PHP 8.4.26 and is the remediation target.

### 8.6 Discovering and evaluating the EC2 instances

The independent evaluator requires an explicit method, deployment ID, profile, and region. It queries only exact VulHarness project, scenario, deployment, and method tags; it does not scan every EC2 instance in an account.

Run the initial infrastructure, SSM, Docker, Compose, and PHP evaluation:

```bash
python3 scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method <aws-cli|cloudformation|terraform> \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --include-ssm
```

The evaluator writes machine-readable results and evidence locally under the ignored `docs/evidence/aws/<method>/<deployment-id>/` path. Raw AWS output can contain live account and resource identifiers; do not commit or upload it. Duplicate matches, stopped instances, inaccessible regions, and authorization failures remain failures or insufficient evidence; they are never inferred to be healthy. Use `--phase remediated` after the Lab D update and `--phase reset` after resetting Lab D.

### 8.7 Inspecting running PHP versions

The evaluator separately determines whether each selected instance is an authorized, reachable SSM managed node. A bounded, read-only SSM operation requests raw runtime facts from the loopback-only PHP endpoint on that instance.

A running EC2 instance does not establish that PHP is installed, that the Compose project is running, or that the expected PHP-FPM process serves the application. The response must retain its source, instance identity, region, SAPI, observation timestamp, and collection limitations.

### 8.8 Deterministic cloud assessment

The existing [deterministic checker](../checks/local-http-version/README.md) validates normalized raw runtime evidence and owns the PHP version-comparison semantics. The AWS evaluator collects equivalent evidence through SSM and passes it to shared assessment logic rather than duplicating CVE thresholds.

No `lab-c` or `lab-d` local URL target is required. Do not extend the workstation-local URL registry with URLs that falsely represent remote EC2 evidence.

### 8.9 Cloud inventory in Hello World 2.0

The future dashboard should retain one data-driven inventory table. AWS rows should add environment, instance ID, region, discovery status, connectivity status, evidence source, observed PHP version, per-CVE classifications, timestamp, and limitations.

It must not use four hardcoded summary cards or accept arbitrary URLs, instance IDs, regions, commands, or account-wide scans from browser requests. Current Hello World 2.0 displays local configured targets only.

### 8.10 Applying the Lab D update

Inspect the initial Lab D state before remediation. Then apply only the Lab D update through SSM:

```bash
python3 scenarios/php2shell/labs/aws/deployment/shared/ssm_runtime.py remediate \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method <aws-cli|cloudformation|terraform> \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --lab-id lab-d
```

Selecting or inspecting the update override does not count as deployment. The running container and HTTP-serving runtime must be observed separately. Lab C remains the independent PHP 8.4.27 reference.

### 8.11 Independent cloud verification

Independent verification should repeat SSM connectivity and loopback HTTP collection after deployment, corroborate the running container image where practical, and compare the fresh evidence with the expected upstream threshold.

After remediation, collect the after-state evidence explicitly:

```bash
python3 scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method <aws-cli|cloudformation|terraform> \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --include-ssm --phase remediated
```

Reset Lab D through the same SSM workflow, then collect separate reset evidence:

```bash
python3 scenarios/php2shell/labs/aws/deployment/shared/ssm_runtime.py reset \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method <aws-cli|cloudformation|terraform> \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --lab-id lab-d

python3 scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method <aws-cli|cloudformation|terraform> \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --include-ssm --phase reset
```

Retain the reset evidence separately from the initial and remediated artifacts.

Stopped, unreachable, malformed, or uninspectable instances must produce unknown or `inconclusive` results. They must never be inferred to be fixed.

### 8.12 Cloud evaluation

The cumulative evaluator records infrastructure, runtime, PHP, remediation, recovery, and cleanup evidence as separate results. It uses shared deterministic assessment results while keeping discovery and transport failures visible.

The local Lab B lifecycle evaluation is not evidence that the EC2 exercise works. AWS PHP evidence must come from the selected EC2 instances through SSM.

The evaluator returns a nonzero status when a collected check fails or an AWS inspection error occurs. A skipped lifecycle artifact with `skip_classification=coverage_gap` is not a pass; repeat the required bootstrap/remediation/reset or lifecycle cycle and preserve the evidence directory. GuardDuty checks marked `conditional_guardduty_evidence` remain explicit conditional coverage, not successful cleanup.

### 8.13 AWS reset and cleanup

The CLI deployment includes scoped infrastructure cleanup for its own deployment ID. Later operational stages must extend cleanup to Compose projects, logs, SSM associations, and any additional resources they create.

The CLI records ownership through exact deployment, lab, owner, expiration, and management tags. Its dry-run lists targets, and confirmed cleanup requires an explicit deployment-specific confirmation. Broad account cleanup commands will not be used.

AWS-managed services can create unrelated dependencies inside a new VPC. If cleanup reports an untagged GuardDuty endpoint, do not adopt it as a normal lab resource. The technical wrappers require explicit opt-in and release only a verified endpoint/ENI/SG inside the exact lab VPC after unrelated-consumer checks; otherwise cleanup remains `BLOCKED_BY_EXTERNAL_DEPENDENCY`.

AWS limitations remain explicit:

- Compose scaffolds are not deployed-environment evidence.
- EC2 running state is not PHP runtime evidence.
- Version classification is not proof of exploitability or non-exploitability.
- Distribution backports and applicable advisory conditions require separate evidence.
- AWS inventory is exact-tag scoped; SSM runtime transport is authenticated and bounded. The dashboard remains a future presentation layer.

### 8.14 AWS CLI troubleshooting

- **Missing default route:** A partially created route table may contain only its local route. Re-run `deploy` with the same deployment ID. The CLI uses `create-route` when the `0.0.0.0/0` route is absent and refuses to replace an unrelated route.
- **Malformed EC2 `TagSpecifications`:** `run-instances` requires JSON tag objects with `Key` and `Value` fields. Use the corrected repository script and resume with the same deployment ID; do not manually adopt or retag unrelated instances.
- **VPC CIDR conflict:** The requested CIDR is already in use. Choose an unused `VULHARNESS_VPC_CIDR` for a new deployment ID, or resume the original deployment if its tagged VPC is discoverable. Do not reuse another project’s VPC.
- **Partial deployment:** Run `status` and then `cleanup --dry-run`. A partial or unhealthy deployment is inspectable but not healthy; `status` returns exit code `2`, while an inspectable dry-run returns `0`. Resume with the same deployment ID only after the exact target list and ownership tags are understood.
- **Missing deployment ID:** `deploy` generates one automatically. `status`, `cleanup --dry-run`, confirmed `cleanup`, and resume operations require `--deployment-id` or `VULHARNESS_DEPLOYMENT_ID`.

## Part H — Future scenarios and agent orchestration

> **Planned — No Agent Workflow or Reusable Skill Is Implemented**

A later workshop stage may use Codex, Claude Code, or another coding agent to
assist with an authorized investigation, identify PHP runtimes, collect
evidence, recommend remediation, and recheck after a developer reports that
deployment is complete. This is future work; no generic scenario registry or
LLM integration exists today.

The intended progression is:

1. Give the agent a bounded, authorized investigation scope.
2. Require it to distinguish inventory, desired configuration, running image, serving runtime, and demonstrated exposure.
3. Preserve evidence sources and timestamps instead of accepting the agent's conclusion alone.
4. Keep remediation execution subject to explicit approval and environment ownership.
5. Independently run the deterministic checker and applicable evaluation.
6. Compare agent findings with independently verified outcomes.

Agent integration must remain optional. Manual investigation and deterministic automation stay first-class, reusable skills remain separate from Scenario 1, and provider-specific adapters must not change the shared evidence or assessment semantics.

No agent command, reusable skill, or automatic remediation step is required by
this guide. The current PHP2Shell CLI is scenario-specific orchestration, not
the proposed future chief-of-staff agent.

A future chief-of-staff workflow could look like this:

```text
Security engineer: “Are we impacted by PHP2Shell?”
        ↓
Interpret request → discover an available scenario → identify authorized scope
        ↓
Invoke permitted deterministic operations → read evidence and independent evaluations
        ↓
Report assessed assets, potential impact, and unknowns
        ↓
Request explicit authorization before remediation or destructive action
```

The agent would coordinate approved components, not replace the security
engineer's expected outcomes, authorization decisions, or independent
verification.

Contributors designing another scenario should use the [scenario development
guide](../../../docs/scenario-development-guide.md), not assume that this
PHP2Shell-specific command is a generic platform interface.

## 10. Reset and cleanup

Why this matters: a reproducible lab has an explicit return path to its initial state and a cleanup boundary that does not affect unrelated projects.

Restore Lab B to PHP 8.4.26:

```sh
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml down
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml up -d
```

Confirm the reset:

```sh
python3 scenarios/php2shell/evals/remediation-lifecycle/evaluate.py --state before
```

You can now repeat the remediation and verification steps in Section 5.

To stop and remove Lab B without affecting Lab A:

```sh
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml down
```

When you are finished with Lab A as well:

```sh
docker compose -f scenarios/php2shell/labs/local/lab-a/compose.lab-a.yaml down
```

Stop the dashboard by returning to its terminal and pressing `Ctrl+C`.

## 11. Troubleshooting and recovery

### Wrong working directory

Every command in this guide expects the repository root. Check:

```sh
ls README.md scenarios/php2shell
```

### Docker daemon unavailable

```sh
docker info
```

Start the authorized Docker service if this cannot connect. The evaluator reports a failed read-only inspection rather than changing Docker state.

### Port already in use

Inspect current bindings without modifying them:

```sh
docker ps --format 'table {{.Names}}\t{{.Ports}}'
```

Lab A requires 8080, the dashboard requires 8081, and Lab B requires 8082. Stop only the process or project you own; do not clean up unrelated containers.

### Dashboard already running

Use the existing [http://127.0.0.1:8081](http://127.0.0.1:8081) window. If you own its terminal, press `Ctrl+C` before starting another dashboard process.

### PHP runtime does not match the expected state

First collect fresh HTTP evidence:

```sh
python3 scenarios/php2shell/checks/local-http-version/cli.py --target lab-b
```

Then inspect the desired model:

```sh
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.update.yaml config --images
```

If the desired image is fixed but HTTP still reports 8.4.26, the runtime has not yet been recreated. Return to **Apply the Lab B update** in Part E. If you intended the before-state, perform the reset in Section 10.

### Container starts but the HTTP endpoint is unavailable

Inspect Lab B status and recent logs:

```sh
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml ps
docker compose -f scenarios/php2shell/labs/local/lab-b/compose.lab-b.yaml logs --tail=50 web php-fpm
```

Probe only the authorized local evidence endpoint:

```sh
curl --fail --show-error --max-time 3 'http://127.0.0.1:8082/?inspect=1&format=json'
```

An unavailable or malformed response must remain FAIL/inconclusive. Do not convert missing evidence into a successful evaluation.

## 12. What the workshop establishes

- Configuration is intent.
- Runtime observation is evidence.
- Deployment is not complete until independently verified.
- Deterministic evaluation provides repeatable PASS/FAIL criteria.
- A fixed-version result is not proof of non-exploitability or complete remediation.

For deeper evidence collection, continue with the [manual investigation walkthrough](local/manual-investigation/README.md). For checker details and target configuration, see the [local HTTP version-check documentation](../checks/local-http-version/README.md). Environment-specific implementation details remain in the Lab A/B/C/D READMEs, not separate participant journeys.
