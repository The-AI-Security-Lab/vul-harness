# PHP2Shell AWS EC2 deployment plan

> **AWS Lab C/D — three independent infrastructure methods and shared SSM runtime workflow**

This directory contains deployment scaffolds and independent infrastructure deployment methods for two AWS EC2 environments:

- [Lab C](lab-c/README.md) — one EC2 instance using the PHP 8.4.27 image reference.
- [Lab D](lab-d/README.md) — a second EC2 instance using the PHP 8.4.26 image reference and a separate update override for PHP 8.4.27.
- [AWS CLI deployment](deployment/cli/README.md) — shell-based infrastructure deployment.
- [CloudFormation deployment](deployment/cloudformation/README.md) — independent stack-based infrastructure deployment.
- [Terraform deployment](deployment/terraform/README.md) — independent state-based infrastructure deployment.
- [Shared SSM workflow](deployment/shared/README.md) — Docker/Compose bootstrap, reset, and remediation used by all methods.
- [AWS lifecycle evaluator](../../evals/aws-lifecycle/README.md) — exact-tag, fail-closed infrastructure/runtime/PHP evidence.
- [Participant orchestration command](../../../../scripts/README.md) — scope-aware local/AWS command center.

The repository does not create AWS resources during tests or documentation validation. Running one of the deployment commands is an explicit participant action. Infrastructure methods do not install Docker or start Compose; the shared workflow performs those actions only through authenticated SSM after infrastructure validation.

Participants must choose exactly one independent infrastructure method:

1. AWS CLI — available in this stage.
2. CloudFormation — available.
3. Terraform — available.

Each method is independent. Do not combine methods or reuse resources, stacks, state, VPCs, subnets, IAM roles, security groups, or instances created by another method.

## Deployment layout

The Compose files reuse application and Nginx assets from `labs/local/lab-a/` through relative, read-only bind mounts. A future EC2 deployment must therefore preserve this repository layout, or copy the complete `scenarios/php2shell/labs/` subtree to the same relative paths. Copying only an individual `lab-c` or `lab-d` directory will not work.

Each lab is intended for a separate EC2 instance. Both may bind Nginx to `127.0.0.1:8080` on their own host because they do not share a host. The inspection endpoint must not be published on an instance's public or private network interface.

## Approved Stage 2B architecture

- AWS region: `us-east-1`
- AWS CLI profile: supplied explicitly by the participant; never commit local
  profile names or credentials
- Two separate `t4g.small` ARM64 EC2 instances
- Amazon Linux 2023 ARM64, selected from the AWS-published AMIs in the region
- Dedicated VPC and public subnet with an Internet Gateway and public IPv4 for outbound access
- Encrypted 20-GiB gp3 root volume
- Dedicated security group with zero inbound rules
- No SSH key pair
- Dedicated IAM role with `AmazonSSMManagedInstanceCore` only
- IMDSv2 required
- Unique deployment and expiration tags
- No modification or adoption of the existing `php2shell-container` instance

The public subnet is an infrastructure-stage choice for simple outbound bootstrap access. Zero inbound security-group rules and loopback-only application binding remain required. Docker and PHP deployment are performed later through the shared SSM workflow and evaluated independently.

## CLI prerequisites and commands

Run from the repository root. The default profile and region can be overridden with `--profile`, `--region`, `AWS_PROFILE`, and `AWS_REGION`.

The operator needs permission to create and delete the deployment-owned VPC, subnet, Internet Gateway, route table, security group, IAM role/profile, EC2 instances, and tagged EBS volumes. The script does not run `aws configure`, perform SSO login, assume a role, or print credentials.

```bash
./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh deploy
```

The command generates a deployment ID, defaults expiration to 24 hours, creates Lab C and Lab D infrastructure, waits for EC2 running and status-ok checks, polls network/IAM dependencies, waits for both instances to report SSM `Online`, and prints the deployment ID for later commands.

```bash
VULHARNESS_DEPLOYMENT_ID=vh-<deployment-id> \
  ./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh status

VULHARNESS_DEPLOYMENT_ID=vh-<deployment-id> \
  ./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh cleanup --dry-run

VULHARNESS_DEPLOYMENT_ID=vh-<deployment-id> \
  ./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh cleanup
```

Confirmed cleanup requires typing `DELETE <deployment-id>` after the exact tagged target list is displayed. Cleanup is safe to retry, uses bounded dependency waits/retries, and never uses account-wide deletion filters. A partial deployment remains inspectable through `status` and `cleanup --dry-run`.

The CLI's `status` and post-deployment validation establish infrastructure and SSM connectivity only. They do not establish Docker readiness, PHP presence, PHP SAPI, serving-runtime identity, or vulnerability exposure.

## Scoped discovery and verification

The existing local target registry is intentionally unchanged. AWS targets cannot be represented safely as ordinary localhost URLs on the participant workstation.

The independent evaluator accepts an explicitly authorized profile, region, method, deployment ID, and exact ownership tags. A selected lab is identified with:

```text
VulHarnessScenario=php2shell
VulHarnessLab=lab-c
```

or the corresponding `lab-d` value. Discovery queries only the selected deployment and method; it does not enumerate every EC2 instance in an account.

Discovery and verification are distinct:

1. EC2 discovery identifies the expected instance, instance state, region, and instance ID.
2. Connectivity assessment establishes whether the instance is an authorized, reachable SSM managed node.
3. Runtime verification uses authenticated SSM access to run a bounded, read-only request to `http://127.0.0.1:8080/?inspect=1&format=json` on that instance.
4. The shared deterministic assessment logic compares the returned raw facts with the documented upstream thresholds.

A running instance is not proof that PHP is installed or serving requests. A stopped, unreachable, ambiguously tagged, or uninspectable instance must produce unknown or `inconclusive` evidence, never `fixed_upstream_version`.

## Evaluation evidence

The evaluator writes one machine-readable result set and evidence directory per method/deployment under the ignored local `docs/evidence/aws/` path. These artifacts may contain live account and resource identifiers; do not commit or upload them. A future dashboard should continue to render a single data-driven inventory rather than four hardcoded lab cards. Records should carry:

- Lab identifier and environment (`local` or `aws-ec2`)
- Discovery status and connectivity status
- AWS instance ID and region when applicable
- Evidence source and collection transport
- Observed serving PHP version and SAPI
- Observation timestamp
- Per-CVE classifications
- Collection errors and verification limitations

The provider-independent checker continues to assess normalized runtime evidence. AWS discovery and SSM transport remain method-specific adapters, while PHP2Shell version-comparison semantics stay in the shared checker.

## Shared deployment tags

Every CLI-owned resource receives the following tags:

```text
VulHarnessProject=VulHarness
VulHarnessScenario=php2shell
VulHarnessEnvironment=aws-ec2
VulHarnessDeployment=<unique-deployment-id>
VulHarnessManagedBy=aws-cli
VulHarnessDeploymentMethod=aws-cli
VulHarnessOwner=<owner>
VulHarnessExpires=<UTC-ISO-8601-timestamp>
VulHarnessResource=<resource-kind>
VulHarnessLab=lab-c|lab-d       # instances and their root volumes
```

CloudFormation and Terraform use the same contract with their own management and deployment-method values. The shared SSM workflow and evaluator require the method value so one deployment method cannot adopt another method's resources.

Discovery and cleanup require the exact project, scenario, environment, deployment, and management tags. A duplicate match is an error. The existing `php2shell-container` instance is not a valid match because it has no deployment tags.

## Resolved workshop decisions and future questions

The workshop architecture, tag contract, AMI family, ARM64 sizing, encrypted storage, SSM-only administration, shared bootstrap, exact-tag discovery, cleanup boundary, and independent evidence workflow are implemented and live-validated. See [implementation decisions](../../../../docs/decisions.md) and the [current status](../../../../wiki/current-status.md) for evidence.

Remaining questions concern future generalization rather than the current participant path:

- Role assumption and credential/session UX for additional accounts
- Whether remote checks should later be initiated by a dashboard or adapter process
- Generalized evidence persistence and redaction formats
- Dashboard cloud integration and orphan-resource reporting beyond exact deployments

GuardDuty Runtime Monitoring can create a service-managed endpoint inside a lab VPC. That endpoint is not deployment-owned and may block VPC deletion. Cleanup must first confirm the exact VPC, endpoint service, ENI, security group, and absence of unrelated consumers. Only an authorized account owner may approve the supported GuardDuty-aware release; participants without that permission must stop, report the blocker, and leave the endpoint untouched. The evaluator reports this state as `FAIL` with `BLOCKED_BY_EXTERNAL_DEPENDENCY`, and an independent absence evaluation must pass before the deployment is considered removed.
