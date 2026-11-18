# VulHarness architecture synthesis

Claim statuses in this page follow [schema.md](schema.md). The full authoritative component model remains [docs/architecture.md](../docs/architecture.md).

## Purpose and scope

**Verified implementation:** VulHarness is an AI Security Lab community project for authorized vulnerability investigation, response workflows, and independent evaluation. It does not distribute intentionally vulnerable applications. Evidence, authorization, provenance, uncertainty, and cleanup are first-class concerns.

## Component boundaries

**Agreed architectural decision:** scenarios, labs, walkthroughs, workflows, skills, checks, evaluations, integrations, and the future Core Harness have distinct responsibilities.

- A scenario owns vulnerability context, sources, conditions, and expected outcomes.
- A lab owns scenario-specific environment configuration.
- A walkthrough owns participant procedures for an environment and method.
- A check collects or validates concrete evidence.
- An evaluation compares observed evidence with stated expectations.
- An integration adapts an external provider while preserving provenance and errors.
- Reusable workflows and skills remain provider-independent and separate from scenarios.

PHP2Shell is Scenario 1, not a special case in generic interfaces.

## Scenario 1 environments

**Verified implementation:** Labs A and B are independent local Docker environments. They share the demonstration application and Nginx configuration through read-only mounts while retaining separate Compose projects, networks, and loopback ports.

**Proposed design:** Labs C and D are separate EC2 instances. Their static Compose models reuse the same assets and pin the same respective PHP images as Labs A and B. Each EC2 host binds its inspection endpoint to its own `127.0.0.1:8080`.

| Lab | Environment | Runtime ID | Initial PHP intent | Status |
| --- | --- | --- | --- | --- |
| A | Local Docker | `lab-a` | 8.4.27 | Implemented |
| B | Local Docker | `lab-b` | 8.4.26; update to 8.4.27 | Implemented |
| C | AWS EC2 | `lab-c` | 8.4.27 | Scaffold only |
| D | AWS EC2 | `lab-d` | 8.4.26; update to 8.4.27 | Scaffold only |

Neutral identifiers prevent lab names from disclosing the expected security finding.

## Deterministic local design

**Verified implementation:** the local raw endpoint returns schema version, PHP version, SAPI, and observation timestamp. A Python standard-library checker validates bounded loopback endpoints, preserves per-target errors, and classifies both PHP2Shell CVEs using one shared version-assessment implementation.

The CLI supports one target, all configured local targets, and JSON. Hello World 2.0 uses the same checker and renders a data-driven runtime inventory. Its remediation controls are visible but disabled and have no mutation route.

The Lab B lifecycle evaluation defines `before`, `config-only`, and `after`. It separates desired Compose configuration, running container image, and HTTP-observed runtime.

## AWS infrastructure deployment and planned adapter

**Verified implementation:** the AWS CLI deployment method creates two independently tagged EC2 infrastructure stacks for Labs C and D. It creates a dedicated VPC, public subnet, Internet Gateway, route table, zero-ingress security group, dedicated SSM instance profile, and two Amazon Linux 2023 ARM64 `t4g.small` instances with encrypted 20-GiB gp3 roots and required IMDSv2. It waits for SSM `Online` status but does not execute commands or deploy Docker/PHP.

**Agreed architectural decision:** AWS CLI, CloudFormation, and Terraform are independent deployment methods. Participants choose exactly one method; no method adopts resources created by another.

**Proposed design:** a future optional AWS adapter will:

1. Accept an explicitly authorized account or role context and region allowlist.
2. Discover only instances matching exact Scenario 1 and lab-specific tags.
3. Record EC2 discovery separately from SSM connectivity.
4. Use authenticated SSM access for bounded, read-only collection from the instance-local endpoint.
5. Pass normalized runtime facts into provider-independent assessment logic.
6. Feed local and cloud records into one extensible dashboard inventory.

Stopped, unreachable, ambiguously tagged, or uninspectable instances remain unknown or inconclusive. A running EC2 instance is not runtime evidence.

See the [AWS plan](../scenarios/php2shell/labs/aws/README.md) for proposed fields and unresolved design choices.

## Future stages

**Agreed architectural decision:** agent-assisted investigation and reusable skills come after deterministic local and cloud workflows are understood. Provider-specific adapters for Codex, Claude Code, AWS, or other platforms are permitted, while reusable interfaces remain provider-independent.

**Proposed design:** Scenario 2 will be a separate later expansion for a multi-container or load-balanced cloud-like application. Scenario 1 remains focused on single-host local Docker and EC2 exercises.
