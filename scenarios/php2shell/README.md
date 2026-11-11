# PHP2Shell scenario

This workshop implementation is maintained on the
[`stage1-nov-26-workshop`](https://github.com/The-AI-Security-Lab/vul-harness/tree/stage1-nov-26-workshop)
branch and is undergoing final participant validation. Start with the
[canonical participant lab guide](walkthroughs/participant-lab-guide.md).

PHP2Shell is the first reference scenario for VulHarness. It demonstrates how the framework can develop from a manual investigation toward reusable, verifiable workflows without making PHP2Shell a special case.

## What You Need to Know

PHP2Shell refers to two confirmed critical upstream PHP vulnerabilities: [CVE-2026-109618](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w), RCE via OOM corruption, and [CVE-2026-109619](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp), RCE via stale global state. The PHP advisories list affected upstream branches below `8.2.35`, `8.3.36`, `8.4.27`, and `8.5.12`; the corresponding fixed upstream releases are `8.2.35`, `8.3.36`, `8.4.27`, and `8.5.12`.

Those ranges are upstream `php-src` ranges, not a universal statement about every installed package. Exposure depends on the runtime actually serving requests, the SAPI and worker model (`mod_php`, PHP-FPM, FrankenPHP, LSAPI, or another path), request routing, configuration, extensions, frontend behavior, and—in some cases—application behavior and reuse of the same worker. Installed PHP, a potentially affected upstream version, applicable vulnerability conditions, and demonstrated exposure are separate claims.

Practitioners should collect evidence for PHP presence, the serving runtime and SAPI, upstream or distribution package identity, build provenance, effective configuration, worker/deployment conditions, and vendor backport status. A version banner alone is not proof. The verified remediation is to update to a fixed release or an authoritative vendor package containing the fix; configuration mitigations described in the advisories are limited and do not replace patching. See the [PHP Foundation security release](https://thephp.foundation/blog/2026/10/21/todays-php-security-release-and-how-were-strengthening-php-security/) and [OpenAI coordinated disclosure](https://openai.com/index/coordinated-disclosure-of-critical-vulnerabilities/) for response context. Detailed technical conditions remain in the [reference register](references.md).

This repository does not build or distribute an intentionally vulnerable application. Participants must provide or provision an isolated environment that they are authorized to test, using Docker, an existing image, a virtual machine, an authorized cloud environment, or another suitable lab setup.

## Scope

The currently available walkthrough is the canonical progressive participant journey. It begins with a local manual investigation and extends through deterministic checks, independent evaluation, the PHP2Shell-specific orchestration harness, and an optional AWS workflow:

1. Understand the security problem and its evidence limits.
2. Investigate isolated local Labs A and B manually.
3. Optionally investigate AWS Labs C and D through an authorized deployment.
4. Convert the manual workflow into deterministic checks.
5. Define and execute independent evaluations.
6. Coordinate the existing components through the PHP2Shell-specific harness.

Within those stages, the participant should document authorization and scope, collect evidence with provenance and relevant timestamps, distinguish configured, expected, and observed behavior, record uncertainty, and clean up the environment.

The scenario is about disciplined investigation and verification. It does not authorize testing third-party systems and does not prescribe a single provider, agent, workflow, or command sequence.

## Scenario 1 lab registry

Neutral identifiers keep the lab name separate from the finding a participant should discover.

| Lab | Environment | Intended initial PHP | Status | Documentation |
| --- | --- | --- | --- | --- |
| Lab A (`lab-a`) | Local Docker | 8.4.27 | Implemented; live use completed before migration | [Lab A](labs/local/lab-a/README.md) |
| Lab B (`lab-b`) | Local Docker | 8.4.26, with an 8.4.27 update override | Implemented; three lifecycle states validated before migration | [Lab B](labs/local/lab-b/README.md) |
| Lab C (`lab-c`) | AWS EC2 | 8.4.27 | Independent infrastructure methods and shared SSM runtime workflow | [Lab C](labs/aws/lab-c/README.md) |
| Lab D (`lab-d`) | AWS EC2 | 8.4.26, with an 8.4.27 update override | Independent infrastructure methods and shared SSM runtime workflow | [Lab D](labs/aws/lab-d/README.md) |

Labs A and B are independent local Compose projects on `127.0.0.1:8080` and `127.0.0.1:8082`. They demonstrate why the PHP runtime serving an HTTP request matters and preserve configured, deployed, and observed state as separate evidence.

Labs C and D run on two separate EC2 instances. Their inspection endpoints remain bound to each instance's loopback interface. The [AWS lab plan](labs/aws/README.md) includes independent AWS CLI, CloudFormation, and Terraform infrastructure methods, shared SSM runtime inspection, and a scoped cloud evaluator. Dashboard integration remains a later stage.

Use the [canonical Scenario 1 participant guide](walkthroughs/participant-lab-guide.md) and its [orchestration command](../../scripts/README.md) for the progressive workshop journey. The [manual investigation reference](walkthroughs/local/manual-investigation/README.md) provides deeper evidence requirements, while the guide itself contains the tested local path, implemented AWS workflow, and clearly marked future agent-assisted stages.

## References and version claims

See the [reference register](references.md). The upstream PHP advisories currently confirmed for this scenario are [CVE-2026-109618](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w), RCE via OOM corruption, and [CVE-2026-109619](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp), RCE via stale global state.

Their upstream affected ranges and fixed releases are documented in the register. Distribution-package status, backported fixes, SAPI applicability, configuration conditions, and actual exposure require separate evidence. Do not treat a version banner as definitive proof.

The [`scenario.yaml`](scenario.yaml) file contains a minimal descriptive metadata contract. It is not validated by an implemented schema validator.

## Walkthroughs

The [walkthrough index](walkthroughs/README.md) distinguishes currently available content from possible future extensions.

The [canonical participant guide](walkthroughs/participant-lab-guide.md) is the single self-service journey for Scenario 1. It demonstrates the implemented before, configuration-only, and after states using the local labs, shared checker, runtime inventory dashboard, and lifecycle evaluation. The same guide includes the three AWS infrastructure methods, shared SSM runtime workflow, independent cloud evaluator, and future agent-assisted workflows as planned.

The [local manual investigation](walkthroughs/local/manual-investigation/README.md) remains a supporting evidence reference and is intentionally usable without an agent integration.

## Evaluation expectations

The investigation should make it possible to review:

- Whether the lab, authorization boundary, and scope were clearly established
- Whether PHP installation and runtime information were identified with evidence
- Whether any selected runtime was provisioned reproducibly and with provenance
- Whether configured, expected, and observed behavior were distinguished
- Whether the participant defined and executed golden evaluations independently of any agent output
- Which conclusions were supported, unsupported, inconclusive, or missing sufficient evidence
- Whether uncertainty, limitations, timestamps, and cleanup were documented

See the [evaluation guidance](../../evals/README.md) for the distinction between expected outcomes, evidence, checks, and verification.

## Current status

Implemented locally:

- Labs A and B, the raw runtime endpoint, and neutral runtime IDs `lab-a` and `lab-b`
- The [deterministic checker and CLI](checks/local-http-version/README.md), including `--target`, `--all`, and `--json`
- The localhost Hello World 2.0 runtime inventory with disabled remediation controls
- The [Lab B lifecycle evaluation](evals/remediation-lifecycle/evaluate.py) for `before`, `config-only`, and `after`
- The [canonical participant guide](walkthroughs/participant-lab-guide.md) and the [PHP2Shell orchestration command](../../scripts/README.md), including safe local reset, AWS method selection, SSM runtime workflow, cleanup, troubleshooting, and planned future agent-assisted stages

On November 9, 2026, post-migration reconciliation completed successfully. Lab A and Lab B both served PHP 8.4.27, both CVEs were classified `fixed_upstream_version` for both labs, and the Lab B `after` evaluation passed all six checks. This remains version-based verification; application exploitability and complete remediation were not established.

Labs C and D include Compose models, three independent EC2 deployment methods, shared SSM runtime actions, and a scoped cumulative evaluator. AWS CLI, CloudFormation, and Terraform live lifecycles have been independently validated, including runtime remediation/reset and cleanup absence checks. Dashboard AWS integration, agent-assisted investigation, reusable skills, automatic remediation, a generalized evaluation framework, and the Core Harness remain future work.

Use the [canonical guide](walkthroughs/participant-lab-guide.md) for operational local commands and scoped cleanup. Lab A/B/C/D READMEs remain technical environment references.
