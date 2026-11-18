# Current project status

Last maintained: 2026-11-10. Status terms follow [schema.md](schema.md).

## Verified implementation

- PHP2Shell Scenario 1 documentation, metadata, technical reference register, and manual investigation guidance.
- Neutral local lab structure under `labs/local/lab-a/` and `labs/local/lab-b/`.
- Nginx plus PHP-FPM application, raw runtime JSON endpoint, loopback bindings, pinned images, and container hardening.
- Deterministic Python checker with `lab-a` and `lab-b`, `--target`, `--all`, and `--json`.
- Hello World 2.0 local runtime inventory with evidence details and disabled remediation controls.
- Lab B lifecycle evaluation for `before`, `config-only`, and `after`.
- One canonical Scenario 1 participant guide containing the tested local journey, all AWS deployment/runtime methods, reset, cleanup, troubleshooting, and planned agent-assisted stages.
- Independent AWS CLI, CloudFormation, and Terraform infrastructure deployment methods for Labs C/D with exact deployment ownership/method tags.
- Shared SSM-only Docker/Compose bootstrap and phase-aware independent AWS lifecycle evaluator.
- Scope-aware PHP2Shell orchestration command at [`scripts/vulharness-php2shell.py`](../scripts/vulharness-php2shell.py), with local/AWS command routing, operation-specific approvals, stable exits, JSON output, and exact deployment-ID forwarding.
- Public [scenario development methodology](../docs/scenario-development-guide.md) covering research, manual baselines, deterministic automation, independent evaluation, optional orchestration, and contribution review.

## Observed test evidence

- After the path migration, 19 checker tests and 11 lifecycle-evaluation tests passed without changes to assessment semantics.
- Static Compose validation passed for Labs A, B, B with update override, C, D, and D with update override.
- Python, JSON, scenario YAML, internal Markdown link, stale-path, and trailing-whitespace checks passed.
- On November 9, 2026, the Lab A and Lab B containers were successfully recreated using their migrated Compose paths.
- At 04:50:03 UTC, HTTP runtime evidence reported PHP 8.4.27 for both Lab A and Lab B.
- Both CVE-2026-109618 and CVE-2026-109619 were classified `fixed_upstream_version` for both local labs.
- At 04:50:17 UTC, the Lab B `after` lifecycle evaluation returned PASS. All six evaluation checks passed, including corroboration of the running PHP-FPM image against the pinned PHP 8.4.27 image digest.
- On November 10, 2026, the new orchestration command completed a local lifecycle: both labs started, Lab B before/config-only evaluations passed, remediation and after verification passed, reset returned Lab B to 8.4.26, cleanup dry-runs listed only named projects, confirmed cleanup removed both projects, and final named-project status showed no containers.
- Application exploitability was not assessed. The successful version-based verification does not establish complete vulnerability remediation or non-exploitability.
- Before this consolidation, live Lab B evaluations were reported PASS for `before`, `config-only`, and `after`.
- The exact dates and retained output artifacts for those live lifecycle observations were not recorded in the repository.

Local post-migration reconciliation and runtime validation are complete. The latest verified local state is PHP 8.4.27 serving HTTP for both Lab A and Lab B.

## Implemented deployment tooling and evidence boundaries

- Lab C static Compose model with pinned PHP 8.4.27.
- Lab D static base model with pinned PHP 8.4.26 and update override for 8.4.27.
- Relative asset layout for preserving the complete `scenarios/php2shell/labs/` subtree on EC2.
- AWS architecture, prerequisite, discovery, SSM inspection, dashboard-field, and cleanup documentation.
- AWS CLI, CloudFormation, and Terraform deployment methods with independent state/stack boundaries.
- Shared SSM bootstrap, reset/remediation actions, and independent machine-readable AWS lifecycle evaluation.
- Historical AWS CLI Part 1 live validation reported both Lab C and Lab D at infrastructure HEALTHY with running ARM64 `t4g.small` instances, encrypted roots, IMDSv2 required, zero ingress, and SSM Online. The raw account-scoped artifacts are intentionally omitted from this public repository; this result does not establish PHP runtime readiness.
- A later isolated CLI lifecycle validated Docker/Compose bootstrap, Lab C PHP 8.4.27, Lab D PHP 8.4.26, remediation to 8.4.27, repeated remediation, and reset. Cleanup removed the deployment-owned compute/network/IAM resources except for the VPC/subnet retained because AWS GuardDuty created an unrelated managed endpoint inside the subnet.
- CloudFormation and Terraform cleanup wrappers now perform the same read-only unowned-VPC-endpoint preflight and refuse destructive cleanup when a managed dependency remains; the shared helper also handles verified orphan GuardDuty SGs with bounded waits.
- The independent cleanup evaluator now records VPC endpoints and reports an unresolved GuardDuty case as `FAIL` with `failure_classification=BLOCKED_BY_EXTERNAL_DEPENDENCY` and exit code 2, while ordinary residual resources remain `RESIDUAL_RESOURCES`. GD-001 through GD-012 are defined and fail closed when evidence is unavailable.
- Two CloudFormation lifecycles completed independent infrastructure, SSM/Docker/PHP, remediation/reset, and post-cleanup absence validation.
- Two independent Terraform lifecycles completed infrastructure, SSM/Docker/PHP, remediation/reset, repeated-deploy/bootstrap/remediation, GuardDuty-aware destroy, and post-cleanup absence validation. Explicit provider profile selection plus `AWS_SDK_LOAD_CONFIG=1` resolved the Terraform STS initialization issue.
- Orchestration regression tests cover command compatibility, named local cleanup, AWS method/lab scope, evaluator phases, absence verification, approval boundaries, and repeated deployment identity without live AWS calls.
- The canonical participant guide now teaches manual investigation before deterministic automation, independent evaluation, and the PHP2Shell-specific harness; future multi-scenario execution and chief-of-staff agent behavior remain explicitly planned.

Live AWS resources are created only by explicit participant commands. The AWS lifecycle statements above are historical live-validation summaries, not current public fixtures; raw account and resource artifacts are retained privately and are not stored in this repository. The earlier CLI validation deployment was user-confirmed deleted; its cleanup command output and independent post-cleanup inventory were not supplied for review. The later captured CLI lifecycle, both CloudFormation lifecycles, both Terraform lifecycles, and the historical CLI VPC were independently cleaned within exact ownership scope. No active VulHarness VPC remains in the final EC2 inventory; terminated instance records may remain in AWS history.

The current public repository validates AWS behavior through offline/mock regression tests and static checks. An authorized live run may write raw output under the ignored `docs/evidence/aws/` directory, but that output must be treated as private and must not be committed.

## Deployment-method status matrix

| Method | Live lifecycle | Runtime/remediation | Cleanup and absence | Current status |
| --- | --- | --- | --- | --- |
| AWS CLI | Captured CLI runtime lifecycle passed | Lab C 8.4.27; Lab D 8.4.26 → 8.4.27 → 8.4.26 | Captured lifecycle passed after scoped GuardDuty release; historical VPC also passed 2/2 absence | Complete |
| CloudFormation | Two lifecycles passed | Docker/Compose, remediation, reset passed | Both independent absence evaluations passed | Complete |
| Terraform | Two lifecycles passed after explicit profile/SDK config fix | Docker/Compose, remediation, reset passed | Both independent absence evaluations passed 2/2 | Complete |

## Planned work

- Extend normalized inventory records and Hello World 2.0 for AWS metadata and connectivity states.
- Introduce agent-assisted investigation and reusable skills after the deterministic cloud workflow is validated.

## Open questions

The current workshop path has settled the account/profile, region, AMI, Docker bootstrap, SSM, tagging, exact-scope cleanup, cost, and evidence-boundary decisions. Remaining questions are for future generalization:

- Role assumption and credential/session UX for additional accounts
- Dashboard-to-adapter trust boundary
- Generalized evidence retention and redaction formats
- Orphan-resource reporting beyond exact deployment ownership

## Migration caveat

The local lab directories and Compose filenames changed during consolidation. On November 9, 2026, the project owner completed the required reconciliation by recreating Lab A and Lab B from their migrated Compose paths and independently verifying both HTTP runtimes. The earlier caveat about containers retaining the previous bind-mount and Compose metadata is resolved for the validated local environment.
