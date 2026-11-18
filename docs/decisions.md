# AWS Lab C/D implementation decisions

This record captures the implementation decisions for the three independent AWS deployment methods and the shared runtime/evaluation workflow. Operational commands remain in the method READMEs and the canonical participant guide.

## AWS-001 — Independent deployment methods

- **Decision:** AWS CLI, CloudFormation, and Terraform each create and own a complete Lab C/D stack.
- **Reason:** participants can select one method without hidden dependencies, shared state, or resource adoption across methods.
- **Ownership:** every resource carries exact project, scenario, environment, deployment, management, owner, expiration, resource, and method tags.
- **Verification:** the evaluator filters by the exact deployment and method tags and fails closed on duplicates or missing resources.

## AWS-002 — Disposable network boundary

- **Decision:** each deployment creates a dedicated VPC and public subnet with an Internet Gateway and default route.
- **Reason:** outbound bootstrap is simple and repeatable while the dedicated VPC avoids modifying the reference instance or an unrelated VPC.
- **Controls:** the lab security group has zero inbound rules; application traffic remains loopback-only; no SSH key pair is configured.
- **Trade-off:** public IPv4 and EBS/EC2 resources can incur cost until cleanup completes.

## AWS-003 — SSM-only administration

- **Decision:** each stack uses a dedicated IAM role/profile with only `AmazonSSMManagedInstanceCore` and requires IMDSv2.
- **Reason:** it removes SSH exposure and keeps administration auditable through an AWS-managed channel.
- **Boundary:** SSM Online proves management-plane registration only. Docker, Compose, PHP, and serving-runtime readiness require separate SSM evidence.

## AWS-004 — Shared runtime workflow, independent evaluator

- **Decision:** deployment methods stop at infrastructure; one shared SSM workflow transfers approved assets and runs Docker/Compose, while a separate evaluator collects and assesses evidence.
- **Reason:** provisioning and verification must remain independently testable and no method should own PHP assessment semantics.
- **Evidence:** runtime JSON, SAPI, timestamp, compose status, image identity, SSM command identity, and collection limitations are retained per method/deployment.

## AWS-005 — Lifecycle phases

- **Decision:** Lab C uses PHP 8.4.27; Lab D starts at 8.4.26, is remediated to 8.4.27, and can be reset to 8.4.26.
- **Reason:** the same infrastructure supports before/remediation/after evidence without changing the infrastructure method.
- **Limitation:** version comparison remains an upstream-version signal and does not prove application exploitability or non-exploitability.

## AWS-006 — Cleanup and evidence retention

- **Decision:** cleanup is exact-ID and ownership-tag scoped, confirmation-gated, dependency-aware, and followed by an independent absence check. Terraform state is retained until that check succeeds.
- **Reason:** teardown output alone is not proof that all deployment resources are gone, and broad account deletion is unsafe.
- **Observed historical result:** the prior CLI full deployment was user-confirmed deleted. Cleanup command output and independent post-cleanup inventory were not supplied for review, so automated cleanup verification is not claimed.

## AWS-007 — GuardDuty-managed VPC endpoint cleanup boundary

- **Observed:** A GuardDuty-managed endpoint in the CLI deployment VPC was created with the `GuardDutyManaged=true` tag. Its CloudTrail `CreateVpcEndpoint` event identified the GuardDuty service-linked role and `guardduty.amazonaws.com` as the caller.
- **Configuration:** GuardDuty Runtime Monitoring and EC2 automated agent management are enabled. Coverage currently reports one unrelated/reference EC2 resource in another VPC, unhealthy with `No Agent Reporting`; no active VulHarness instance remains in the deployment VPC.
- **Decision:** VulHarness cleanup and absence evaluation must treat an unapproved or recreated service dependency as `BLOCKED_BY_EXTERNAL_DEPENDENCY`, never as a successful or resource-free cleanup. Explicit cleanup authorization may release only a verified GuardDuty endpoint/SG in a uniquely identified lab VPC after endpoint, ENI, SG, VPC-scope, and unrelated-consumer checks pass. VulHarness never changes Runtime Monitoring or any account-level security service.
- **Participant boundary:** participants must not assume permission to delete or release GuardDuty-managed resources. If the account owner cannot authorize the supported, exact-VPC release, cleanup stops without modifying the endpoint and reports the blocker; the evaluator remains `FAIL` with `failure_classification=BLOCKED_BY_EXTERNAL_DEPENDENCY` until an independent absence check passes.
- **Recurrence:** GuardDuty automated agent configuration establishes connectivity across VPCs, so future dedicated lab VPCs can receive the same endpoint. Fresh CloudFormation and Terraform VPCs reproduced the endpoint; their exact endpoints were released by the supported, explicitly authorized provider cleanup path. The historical CLI VPC was later verified as VulHarness-owned, released with the same scoped GuardDuty procedure, and deleted.
- **Supported release boundary:** the account owner reviews monitored resources and uses GuardDuty's supported Runtime Monitoring cleanup controls; only after service/agent dependencies are released may the owner remove the endpoint. Disabling automated agent configuration alone does not necessarily remove the endpoint.
- **Evidence:** Historical live inspection confirmed the service-managed dependency and its ownership metadata. Raw account and resource artifacts are intentionally omitted from this public repository; see the [AWS Runtime Monitoring cleanup guidance](https://docs.aws.amazon.com/guardduty/latest/ug/runtime-monitoring-agent-resource-clean-up.html), [AWS Runtime Monitoring connectivity](https://docs.aws.amazon.com/guardduty/latest/ug/runtime-monitoring-agent-connectivity.html), and [AWS IaC guidance](https://docs.aws.amazon.com/guardduty/latest/ug/using-iac-with-gdu-automated-agents-runtime-monitoring.html).

## AWS-008 — CloudFormation and Terraform live validation

- **Observed:** Two CloudFormation deployments completed infrastructure, initial, remediation, reset, and independent absence evaluations. One recovered after the account VPC quota was freed. GuardDuty endpoints and tagged security groups were released only inside the exact lab VPCs with explicit opt-in.
- **Observed:** Terraform 1.17.1 and AWS provider 6.72.0 initially stalled during provider credential validation even though AWS CLI STS succeeded. Explicit provider profile selection plus `AWS_SDK_LOAD_CONFIG=1` made the bounded provider plan and apply succeed. The root cause was execution-environment/profile loading sensitivity, not an AWS account or credential failure.
- **Observed:** Two fresh Terraform lifecycles completed infrastructure, SSM/Docker/PHP, remediation/reset, repeated-deploy/bootstrap/remediation, GuardDuty-aware destroy, and independent absence verification. Both post-cleanup evaluations passed 2/2.
- **Decision:** Keep the explicit Terraform profile input and `AWS_SDK_LOAD_CONFIG=1` wrapper default. Retain each state directory until the independent absence evaluator passes. Treat provider initialization timeouts and endpoint deletion as bounded, observable recovery states rather than healthy completion.
- **Evidence:** Historical live validation summaries are retained in this decision record; raw AWS artifacts are intentionally omitted from the public repository. See the [Terraform README](../scenarios/php2shell/labs/aws/deployment/terraform/README.md) for the reproducible workflow.

## AWS-009 — Historical CLI VPC ownership and GuardDuty-aware cleanup

- **Observed:** A historical lab VPC had exact VulHarness project/scenario/environment/managed-by/deployment/owner tags, no EC2 instances, and a recreated GuardDuty endpoint. The endpoint's ENI was requester-managed by `amazon-aws`; CloudTrail identified the GuardDuty service-linked role and `GuardDutyRuntimeMonitoring` as creator.
- **Decision:** The ownership and dependency checks were sufficient for the explicitly authorized scoped cleanup. The supported endpoint release was initiated without changing GuardDuty or Runtime Monitoring, the endpoint/ENI disappeared, the verified unreferenced GuardDuty SG was deleted, and then the exact subnet and VPC were removed.
- **Verification:** Independent post-cleanup evaluation passed 2/2; no deployment-owned VPC, subnet, ENI, route table, security group, IGW, instance, volume, IAM role, or profile remained. The protected instance was absent from the deployment scope. AWS resource-tagging output may retain stale terminated-instance/volume records; authoritative EC2 describe calls and the evaluator reported absence.
- **Evidence:** Historical live cleanup artifacts are retained privately and are intentionally omitted from this public repository. See the [GuardDuty cleanup guidance](https://docs.aws.amazon.com/guardduty/latest/ug/runtime-monitoring-agent-resource-clean-up.html).

## AWS-010 — Lab- and phase-scoped evaluation results

- **Decision:** retain the contract `evaluation_id` for compatibility, and add `result_id`, `lab_id`, and `phase` to each result. Deployment-scoped checks use the contract ID; per-lab checks use `<evaluation_id>:<lab-id>:<phase>`.
- **Reason:** Lab C and Lab D share the same evaluation contract, but Lab D remediation/reset checks must not be emitted for Lab C. Result identity and summary totals must remain unambiguous within one evidence artifact.
- **Skip semantics:** GuardDuty conditional checks use `skip_classification=conditional_guardduty_evidence`; missing lifecycle artifacts use `coverage_gap`; a phase not requested uses `phase_not_requested`. Historical evidence is preserved and is not rewritten.

## AWS-011 — Validated Terraform toolchain

- **Decision:** document Terraform `1.17.1` with AWS provider `6.72.0` as the validated live toolchain. Preserve the existing provider constraint and lockfile.
- **Observed limitation:** Terraform `1.5.7` in a later audit environment failed provider schema initialization with `Unrecognized remote plugin message`; that environment was not treated as validated.
- **Recovery:** run `terraform init -reconfigure`, `fmt -check`, and `validate` with the validated toolchain before planning or applying. Repair only the local `.terraform/` cache when authorized; never remove the lockfile, state, or evidence.

## AWS-012 — Scenario orchestration command

- **Decision:** provide one participant-facing `scripts/vulharness-php2shell.py` command that delegates to the existing local and AWS components.
- **Reason:** participants and automation need one stable, scope-aware interface without duplicating checker, evaluator, AWS ownership, or GuardDuty logic.
- **Controls:** local cleanup requires one named lab; AWS infrastructure commands are deployment-scoped; AWS methods require an explicit method and exact deployment ID; setup/remediation/reset/confirmed cleanup require operation-specific approval; confirmed AWS cleanup keeps the underlying interactive confirmation.
- **Exit contract:** `0` success, `1` invoked failure, `2` invalid/incompatible request, `3` missing prerequisite, and `4` partial/unhealthy or externally blocked AWS state. JSON output includes invoked commands and redacted child output; credentials are never passed as command arguments or written to metadata.
- **Resumability:** AWS setup retains the chosen deployment ID in ignored local metadata and forwards it unchanged on retries. The existing method wrapper remains authoritative for exact-tag discovery, validation, reuse, and safe recovery.
- **Validation:** mocked orchestration tests cover command combinations, approval boundaries, lab/method scope, phase/absence evaluator invocation, named cleanup, and repeated deployment identity.

## DOC-001 — Manual-to-harness contribution progression

- **Decision:** teach and document the progression `Manual investigation → coding-agent-assisted deterministic automation → independent evaluation → harness engineering → reusable scenario patterns → future AI-agent orchestration`.
- **Reason:** contributors should understand the security questions, evidence, and expected outcomes before using a coordinator or proposing shared abstractions.
- **Current boundary:** PHP2Shell is the first reference implementation. Its local/AWS labs, checks, evaluations, and `scripts/vulharness-php2shell.py` are available today, but the orchestration command is scenario-specific.
- **Future boundary:** additional scenarios may use different environments, checks, and evaluators. A shared registry, generic multi-scenario execution, chief-of-staff agent, and AI-assisted scenario planner remain future concepts and require human review, deterministic implementation, and independent evaluation.
- **Contribution guidance:** the public [scenario development guide](scenario-development-guide.md) is the methodology reference; [CONTRIBUTING.md](../CONTRIBUTING.md) remains the pull-request and safety contract.
