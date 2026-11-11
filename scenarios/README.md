# Scenarios

A scenario describes a vulnerability or security finding in a bounded, authorized environment. It includes affected conditions, technical references, evidence requirements, and expected outcomes, while remaining independent of any particular cloud provider or agent.

## Scenario responsibilities

A scenario may define or reference:

- Identity, title, description, and status
- Affected conditions and environment assumptions
- Optional scenario-specific labs and their provenance
- References to authoritative advisories or primary technical sources
- Participant-facing walkthroughs
- Reusable workflows and skills that can be applied to the scenario
- Evidence requirements and expected outcomes
- Evaluation definitions and checks, when they exist
- A concise practitioner-facing `What You Need to Know` quick advisory in the scenario README

Scenarios do not distribute intentionally vulnerable applications and should not embed provider-specific behavior into reusable interfaces.

## Separation from reusable content

Walkthroughs, workflows, skills, checks, evaluations, and integrations have distinct responsibilities:

- A **walkthrough** is a goal-oriented investigation or response for an environment and execution method.
- A **workflow** provides reusable security-process orchestration.
- A **skill** provides reusable agent-readable instructions or a practitioner procedure.
- A **check** verifies or collects a concrete evidence item.
- An **evaluation** independently compares observed evidence with expected conditions and outcomes.
- An **integration** adapts an external system while preserving provenance, scope, timestamps, freshness, and coverage.

A **lab** is a scenario-specific controlled environment for reproducible investigation. Labs are optional and are not components of the reusable Core Harness.

Scenarios may reference reusable workflows and skills, but they must not copy or own definitions intended to be shared. Manual-only scenarios are valid and do not require agent integration.

Every new vulnerability scenario should include one scenario-level quick advisory near the beginning of its README. The advisory should summarize what happened, confirmed identifiers, affected technologies and relevant conditions, evidence requirements, verified remediation, authoritative references, and uncertainty. Walkthroughs do not each need a separate advisory.

## Environments and methods

Environment and execution method are independent dimensions. Potential environments include local Docker, virtual machines, EC2, ECS, EKS, other Kubernetes environments, Azure, Google Cloud, on-premises infrastructure, and CI/CD pipelines. Potential methods include manual, deterministic scripted, Core Harness-driven, agent-assisted, skill-based, MCP/API-assisted, cloud-inventory, security-product-enriched, continuous, and scheduled assessment.

PHP2Shell provides one canonical participant guide that progresses from the implemented local manual and deterministic journey into the implemented AWS Labs C/D workflow and clearly marked planned agent-assisted stages. The separate manual-investigation evidence reference remains available for deeper collection. Future combinations should extend the scenario guide without describing scaffolds as deployed functionality.

## Scenario lifecycle

1. Define the intended security outcome, affected conditions, and authorization boundary.
2. Record target version, configuration, provenance, scope, and environment assumptions.
3. Add one or more reproducible walkthroughs.
4. Define evidence requirements and expected outcomes.
5. Review uncertainty, configured versus expected versus observed behavior, failure modes, and cleanup.
6. Submit the scenario through a pull request for review.

## Reference scenario

[PHP2Shell](php2shell/README.md) is the first reference scenario. It demonstrates the documentation and metadata model without receiving special treatment in framework interfaces.
