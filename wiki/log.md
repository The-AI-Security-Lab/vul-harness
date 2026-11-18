# Wiki and project log

Entries are chronological and use the format defined in [schema.md](schema.md). This log records verified maintenance work; it does not manufacture dates for earlier milestones.

## [2026-11-09] validation | AWS CLI Part 1 live deployment

- Completed the AWS CLI Part 1 live validation for both Lab C and Lab D.
- Observed both EC2 instances running with the approved Amazon Linux 2023 ARM64 and `t4g.small` configuration.
- Confirmed encrypted root storage, required IMDSv2, zero inbound security-group rules, and SSM `Online` for both instances.
- Recorded the result as infrastructure health and SSM connectivity only. Docker, Compose, PHP, serving-runtime identity, and vulnerability exposure were not established.
- The validation used the corrected default-route handling and JSON EC2 `TagSpecifications` payloads.
- The user confirmed that the full deployment resources were deleted.
- Cleanup command output and independent post-cleanup inventory were not supplied for review, so automated cleanup verification is not claimed.

Sources: [canonical participant guide](../scenarios/php2shell/walkthroughs/participant-lab-guide.md), [AWS CLI deployment README](../scenarios/php2shell/labs/aws/deployment/cli/README.md), [AWS CLI deployment script](../scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh).

## [2026-11-09] validation | AWS CLI full runtime lifecycle and cleanup boundary

- Created an isolated CLI deployment after read-only preflight found the default lab CIDR already in use; a different disposable lab CIDR was selected.
- The first attempt stopped before EC2 creation because the newly created IAM instance profile was not yet visible to `run-instances`. Bounded retry was added and the same deployment ID resumed without duplicate network or IAM resources.
- Infrastructure validation and the independent evaluator passed for exactly two tagged ARM64 `t4g.small` instances, the current Amazon Linux 2023 ARM64 AMI, encrypted 20-GiB gp3 roots, required IMDSv2, zero ingress rules, the minimal SSM policy, and exclusion of the protected instance.
- The shared SSM bootstrap initially exposed that AL2023 did not provide `docker-compose-plugin` in the Amazon Linux repository. The workflow was corrected to install the pinned official ARM64 Compose plugin with checksum verification; both Lab C and Lab D then bootstrapped successfully.
- Initial runtime evidence passed for Lab C PHP 8.4.27 and Lab D PHP 8.4.26. Lab D remediation, repeated remediation, and reset to PHP 8.4.26 each produced successful SSM/runtime evidence. Application exploitability was not assessed.
- Confirmed cleanup terminated both deployment instances and removed the route table, Internet Gateway, security group, IAM profile, and IAM role. Subnet/VPC deletion was blocked by an unrelated untagged GuardDuty-managed endpoint in the deployment subnet.
- The endpoint was not deleted or modified. The exact-tag post-cleanup inventory recorded only the residual deployment VPC/subnet and terminated tagged instances; the protected instance was absent. A full cleanup pass was therefore not claimed.

Sources: [AWS CLI deployment README](../scenarios/php2shell/labs/aws/deployment/cli/README.md), [shared SSM workflow](../scenarios/php2shell/labs/aws/deployment/shared/README.md), and [AWS lifecycle evaluator](../scenarios/php2shell/evals/aws-lifecycle/README.md). Raw live evidence is intentionally omitted from this public repository.

## [2026-11-09] implementation | Cross-method managed-dependency cleanup guard

- Added read-only VPC endpoint checks to the CloudFormation and Terraform cleanup wrappers.
- Confirmed cleanup now refuses to delete or destroy a deployment when an unowned VPC dependency remains, while dry-run reports the dependency without modifying it.
- Added offline mocked-AWS regression coverage for both wrappers.
- Reconfirmed that the CLI lifecycle deployment remains blocked by an untagged GuardDuty endpoint; no endpoint or unrelated resource was modified.

Source: [deployment cleanup guard tests](../scenarios/php2shell/labs/aws/deployment/test_cleanup_guards.sh).

## [2026-11-10] investigation | GuardDuty VPC endpoint cleanup blocker

- Read-only EC2 inspection confirmed an available GuardDuty service-managed interface endpoint in the lab VPC, tagged only `GuardDutyManaged=true`, with no VulHarness ownership tags.
- Its endpoint network interface was requester-managed by `amazon-aws`, and CloudTrail identified `GuardDutyRuntimeMonitoring` under the GuardDuty service-linked role as the creator.
- GuardDuty Runtime Monitoring and automated agent management were enabled. Coverage included an unrelated reference resource; no active VulHarness resource remained in the deployment VPC. This did not authorize endpoint deletion while account-level Runtime Monitoring remained enabled.
- The pattern is likely to recur: GuardDuty automated agent configuration establishes connectivity across VPCs. AWS documents that service-managed endpoint cleanup is controlled through Runtime Monitoring/agent cleanup, and that disabling automated agent configuration alone does not necessarily remove the endpoint.
- Updated the independent evaluator to include VPC endpoints in inventory and classify the cleanup result as `FAIL` with `failure_classification=BLOCKED_BY_EXTERNAL_DEPENDENCY`, exit code 2. Genuine residual-only cleanup failures remain `RESIDUAL_RESOURCES`.
- CloudFormation and Terraform remain offline-validated only; live testing cannot safely resume until the account owner resolves the GuardDuty dependency.

Raw GuardDuty inspection artifacts are retained privately and intentionally omitted from this public repository. See the [AWS cleanup guidance](https://docs.aws.amazon.com/guardduty/latest/ug/runtime-monitoring-agent-resource-clean-up.html) and [AWS IaC guidance](https://docs.aws.amazon.com/guardduty/latest/ug/using-iac-with-gdu-automated-agents-runtime-monitoring.html).

## [2026-11-09] validation | AWS CLI partial-deployment recovery fix

- Corrected first-run route handling to create a missing default route and replace only an existing route that already targets the deployment-owned Internet Gateway.
- Added refusal to replace unrelated default routes.
- Made partial deployments inspectable: `status` reports incomplete/unhealthy with exit code 2, while `cleanup --dry-run` lists exact targets and returns 0 when inspection succeeds.
- Added EC2 running/status-ok waiters, bounded SSM polling, bounded IAM/network dependency polling, and retry/timeout reporting with recovery commands.
- Added offline mocked-AWS regression tests for route creation, reruns, unrelated-route safety, JSON EC2 tag payloads, partial instance recovery, repeated deploy calls, waiters, SSM polling, partial status, and partial cleanup dry-runs.
- Added resumable discovery that preserves the existing expiration timestamp, validates reusable resource configuration and ownership tags, and refuses orphaned or conflicting resources.
- Did not execute AWS mutation or cleanup operations.

Source: [AWS CLI deployment script](../scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh), [AWS CLI regression tests](../scenarios/php2shell/labs/aws/deployment/cli/test_aws_lab.sh).

## [2026-11-09] implementation | AWS CLI infrastructure deployment method

- Added the first independent AWS infrastructure method for PHP2Shell Labs C and D.
- Added exact deployment, owner, expiration, lab, and management tags.
- Added resumable creation for a dedicated VPC, public subnet, Internet Gateway, route table, security group, IAM role/profile, and two EC2 instances.
- Added infrastructure validation for instance count, tags, ARM64 AMI family, `t4g.small`, encrypted roots, IMDSv2, no SSH key pairs, zero inbound rules, and SSM `Online` status.
- Added ownership-verified dry-run and confirmation-gated cleanup.
- Kept Docker, PHP, SSM command execution, CloudFormation, and Terraform outside this stage.
- Did not provision AWS infrastructure.

Source: [AWS CLI deployment README](../scenarios/php2shell/labs/aws/deployment/cli/README.md), [canonical participant guide](../scenarios/php2shell/walkthroughs/participant-lab-guide.md).

## [2026-11-09] consolidation | Scenario 1 lab migration and AWS scaffolds

- Migrated the two local lab directories to neutral Lab A and Lab B paths and renamed their Compose files.
- Preserved local ports, runtime IDs, image digests, application behavior, Nginx configuration, security controls, and Compose project identity.
- Added static Compose scaffolds for EC2 Labs C and D; no AWS resources were provisioned.
- Added an AWS participant-guide outline and a proposed scoped EC2 discovery plus SSM runtime-inspection design.
- Established `scenarios/php2shell/README.md` as the canonical Scenario 1 lab registry.
- Created this wiki from verified repository contents and decisions supplied for the consolidation task.
- Recorded the previously reported live Lab B lifecycle results without assigning an unrecorded historical date.

Sources: [Scenario 1 registry](../scenarios/php2shell/README.md), [AWS plan](../scenarios/php2shell/labs/aws/README.md), [current status](current-status.md).

## [2026-11-09] validation | Post-migration static and unit checks

- Passed 19 deterministic-checker tests and 11 lifecycle-evaluation tests.
- Passed Python, JSON, and scenario YAML syntax validation.
- Passed static Compose validation for A, B, B with update override, C, D, and D with update override.
- Passed internal Markdown link, removed-path, `llms.txt` absence, and trailing-whitespace checks.
- Did not start, stop, pull, recreate, or inspect live Docker containers and did not execute AWS commands.

Source: [current status](current-status.md).

## [2026-11-09] validation | Local post-migration reconciliation

- Successfully recreated the Lab A and Lab B containers using their migrated Docker Compose paths.
- At 04:50:03 UTC, observed PHP 8.4.27 through the HTTP runtime endpoint for both labs.
- Classified CVE-2026-109618 and CVE-2026-109619 as `fixed_upstream_version` for both Lab A and Lab B.
- At 04:50:17 UTC, the Lab B `after` lifecycle evaluation returned PASS.
- Passed all six lifecycle checks, including verification of the running PHP-FPM image against the pinned PHP 8.4.27 image digest.
- Preserved the verification limitation: application exploitability was not assessed, and version-based verification does not establish complete remediation.
- Confirmed that the earlier `before`, `config-only`, and `after` evaluations had passed before migration; their exact historical timestamps remain unrecorded.
- Local migration reconciliation is complete. AWS Labs C and D remain static scaffolds and have not been deployed.

Remaining work: approve the AWS account, region, AMI, IAM/SSM, tagging, networking, evidence, cost, and cleanup decisions before implementing scoped EC2 discovery or remote runtime inspection.

Sources: [current status](current-status.md), [Scenario 1 registry](../scenarios/php2shell/README.md), [AWS plan](../scenarios/php2shell/labs/aws/README.md).

## [2026-11-09] decision | One canonical participant guide per scenario

- Established `scenarios/php2shell/walkthroughs/participant-lab-guide.md` as the single self-service journey for Scenario 1.
- Preserved the validated local prerequisites, manual investigation, deterministic checker and dashboard, three-state remediation lifecycle, independent verification, reset, cleanup, expected results, safety boundaries, and troubleshooting.
- Integrated the complete planned AWS Labs C/D journey with explicit work-in-progress boundaries.
- Added a planned future agent-assisted stage without introducing agent commands, orchestration, or reusable skills.
- Retained Lab A/B/C/D READMEs as technical environment references and the manual-investigation files as supporting evidence references.
- Removed the superseded local and AWS participant-guide files after their useful content and references were migrated.

Source: [canonical Scenario 1 participant guide](../scenarios/php2shell/walkthroughs/participant-lab-guide.md), [documentation decision](decisions.md).

## [2026-11-10] validation | GuardDuty-aware CloudFormation lifecycles and Terraform boundary

- The previously blocked CLI VPC was released and independently cleaned after the authorized GuardDuty endpoint/ENI/security-group checks. A separate stale CLI VPC recreated its GuardDuty endpoint; deletion was not attempted because the retained destructive authorization named only the previously blocked VPC. It remains `BLOCKED_BY_EXTERNAL_DEPENDENCY`.
- Fixed the CloudFormation template’s unsupported empty `SecurityGroupIngress` property and unsupported `AWS::IAM::InstanceProfile` `Tags` property. The corrected template passed AWS validation.
- A CloudFormation deployment passed infrastructure (11/0), initial runtime (45/0), remediation (47/0), and reset (46/0) evaluations. Its exact stack cleanup released the GuardDuty endpoint and security group; independent absence evaluation passed after terminated-instance records were excluded from residuals.
- A second CloudFormation lifecycle initially rolled back on the account VPC quota, then resumed with the same deployment identity after the first stack was cleaned and passed infrastructure (11/0), initial (45/0), remediation (47/0), reset (46/0), and independent absence evaluation. One endpoint-release waiter timed out even though the endpoint disappeared shortly afterward; rerun cleanup completed after the exact orphan GuardDuty SG was released.
- Added GD-001 through GD-012 to the evaluation contract. Inventory evidence passes only for observed service/scope metadata; unavailable authorization/release/recreation evidence remains SKIP.
- Terraform 1.17.1/AWS provider 6.72.0 passed formatting and validation. Live plan/apply did not create resources and stalled at provider STS credential validation while AWS CLI STS succeeded; Terraform live validation is blocked by the local provider transport environment.

Historical live validation artifacts are retained privately and intentionally omitted from this public repository. See the [GuardDuty decisions](../docs/decisions.md).

## [2026-11-10] validation | Terraform live lifecycles and STS resolution

- Confirmed the approved AWS profile identity through AWS CLI STS. Regional STS DNS and TLS were reachable, and the same profile succeeded with the explicit regional STS endpoint.
- Terraform provider initialization was sensitive to the execution environment's shared-config loading. Passing the profile explicitly through the AWS provider and setting `AWS_SDK_LOAD_CONFIG=1` made bounded Terraform plan/apply succeed; no credentials or tokens were logged.
- Completed two independent Terraform lifecycles with separate retained state directories.
- Both lifecycles passed infrastructure, SSM/Docker/Compose, Lab C PHP 8.4.27, Lab D PHP 8.4.26, Lab D remediation to 8.4.27, reset to 8.4.26, repeated deploy/bootstrap/remediation, GuardDuty-aware destroy, and independent post-cleanup absence verification. The final runtime evaluations were PASS=56, FAIL=0, SKIP=14; each post-cleanup evaluation was PASS=2, FAIL=0.
- The first lifecycle recovered from a transient Lab C localhost readiness failure by repeating the same SSM bootstrap. The second lifecycle recovered from initial package/plugin readiness races and converged to the exact tagged two-instance state without duplicates.
- Terraform provider 6.72.0 released each exact GuardDuty endpoint during destroy. Terraform state was retained until the independent absence evaluator passed.

Historical Terraform validation artifacts are retained privately and intentionally omitted from this public repository. See the [Terraform deployment README](../scenarios/php2shell/labs/aws/deployment/terraform/README.md).

## [2026-11-10] cleanup | Historical CLI VPC and GuardDuty dependency

- Re-inventoried a historical VPC and verified exact ownership tags, no EC2 instances, no unrelated ENIs, and one GuardDuty-managed endpoint.
- Read-only GuardDuty configuration showed Runtime Monitoring and EC2 agent management enabled. CloudTrail identified `GuardDutyRuntimeMonitoring` under the GuardDuty service-linked role as the endpoint creator. GuardDuty and account-level settings were not changed.
- GuardDuty coverage statistics reported one EC2 resource globally, zero healthy and one unhealthy; the historical VPC itself had zero EC2 instances, so no active workload in that VPC was using the endpoint at cleanup time.
- The explicitly authorized, supported GuardDuty-aware release completed: endpoint and service-managed ENI became absent, the verified unreferenced GuardDuty security group was removed, and the exact subnet and VPC were deleted.
- Independent post-cleanup evaluation passed 2/2 with no deployment-owned resources and no protected-instance match. The cleanup command output and independent inventory are captured for this cleanup, unlike the earlier user-confirmed CLI cleanup whose command output was unavailable for review.

Historical cleanup artifacts are retained privately and intentionally omitted from this public repository. See the [GuardDuty decisions](../docs/decisions.md).

## [2026-11-10] verification | Final AWS inventory

- The final authoritative EC2/IAM inventory reported zero active VulHarness VPCs, subnets, security groups, volumes, launch templates, Terraform IAM roles, or Terraform instance profiles. Four tagged Terraform EC2 records remain only as terminated history; no active tagged Terraform instance remains.
- The protected reference instance remained running in its original VPC and was not modified.
- The Resource Groups Tagging API returned stale historical records for deleted/terminated resources; those were not treated as live resources because authoritative EC2/IAM describe/list calls and deployment-scoped absence evaluators reported absence.

The final AWS inventory artifact is retained privately and intentionally omitted from this public repository.

## [2026-11-10] implementation | PHP2Shell orchestration command

- Added `scripts/vulharness-php2shell.py` as a thin participant-facing coordinator for the existing local and AWS components.
- Added operation-specific approvals, local named-project scope, AWS method/deployment scope, stable exit codes, redacted JSON output, retained deployment-ID metadata, and an independent AWS absence-verification command.
- Preserved the existing AWS wrappers as the authority for exact ownership, resumability, waiters/polling, GuardDuty blocking, and interactive cleanup confirmation. No live AWS or SSM command was run for this change.
- Added mocked regression coverage for command compatibility, local remediation/cleanup plans, AWS phase and absence evaluation, GuardDuty authorization, missing approval, and repeated deployment identity.
- Ran the harness through the local lifecycle: preflight, setup, status, HTTP inspection, Lab B before/config-only evaluation, remediation, after verification, reset/baseline evaluation, dry-run cleanup, confirmed cleanup, and final named-project absence. No AWS command or SSM command was executed.
- Updated the canonical participant guide, scenario/AWS READMEs, architecture decisions, current status, and this log. The implementation remains scenario-specific and does not introduce the future generic Core Harness.

Sources: [orchestration README](../scripts/README.md), [orchestration tests](../scripts/test_vulharness_php2shell.py), [architecture decisions](../docs/decisions.md).

## [2026-11-10] documentation | Workshop narrative and scenario contributions

- Reordered the canonical participant guide around the finalized teaching progression: security problem, manual local investigation, optional manual AWS investigation, deterministic automation, independent evaluation, PHP2Shell-specific orchestration, repository architecture, and future agent/scenario direction.
- Added the public [scenario development guide](../docs/scenario-development-guide.md) for research, environment design, manual baselines, deterministic checks, independent evaluations, optional orchestration, and contribution review.
- Clarified root README and contribution guidance: PHP2Shell is the first reference implementation; future scenarios may differ; generic multi-scenario execution, scenario discovery, scenario generation, and agent orchestration are not implemented.
- Documented the conceptual future chief-of-staff workflow and AI-assisted scenario planning without adding agent functionality, registries, dependencies, or AWS operations.

Sources: [participant guide](../scenarios/php2shell/walkthroughs/participant-lab-guide.md), [scenario development guide](../docs/scenario-development-guide.md), [root README](../README.md), [architecture](../docs/architecture.md), and [contribution guide](../CONTRIBUTING.md).
