# VulHarness

> This is the `stage1-nov-26-workshop` workshop branch. The complete PHP2Shell
> implementation is undergoing final participant validation. Start with the
> [participant lab guide](scenarios/php2shell/walkthroughs/participant-lab-guide.md).

VulHarness is an open-source AI Security Lab community project for building, running, and independently evaluating vulnerability investigation and response workflows.

It is intended for security practitioners, workshop participants, researchers, workflow authors, and evaluators who need reproducible ways to investigate authorized vulnerability scenarios and compare the quality of evidence and decisions. VulHarness is not a repository for distributing intentionally vulnerable applications.

## Project principles

- **Authorized testing only.** Every exercise must use a lab or target for which the participant has clear permission.
- **Reproducible investigations.** Contributions document environment assumptions, target provenance, relevant versions, configuration, evidence, and cleanup.
- **Independent evaluation.** Results are evaluated using observable evidence and expected outcomes, not an agent's self-reported success.
- **Composable content.** Scenarios, walkthroughs, workflows, skills, checks, and evaluations have distinct responsibilities.
- **Provider-independent interfaces.** Optional adapters for Claude Code, Codex, AWS, other clouds, security products, or other systems may be added without making reusable framework interfaces provider-specific.
- **No vulnerable application distribution.** Participants may use Docker, existing images, virtual machines, EC2, ECS, EKS, other authorized cloud infrastructure, or their own environments, but VulHarness does not provide an intentionally vulnerable application.

## Repository layout

```text
README.md                         Project overview and starting point
AGENTS.md                         Guidance for coding agents and contributors
CONTRIBUTING.md                   Contribution and pull-request guidance
SECURITY.md                       Responsible disclosure and testing boundaries
LICENSE                           Apache License 2.0
NOTICE                            Project copyright and attribution notice
docs/architecture.md              Conceptual architecture and extension model
docs/scenario-development-guide.md Methodology for future scenario contributions
scenarios/                        Vulnerability assessment scenario content
scenarios/php2shell/              First reference scenario
scenarios/php2shell/checks/       Scenario-specific deterministic checks
scenarios/php2shell/evals/        Scenario-specific evaluations
wiki/                             Maintained project knowledge and decisions
evals/                            Evaluation principles and documentation
.github/PULL_REQUEST_TEMPLATE.md  Pull-request checklist
```

Future framework components such as shared workflows, generic checks, skills, integrations, and the Core Harness are documented as extension points but do not receive empty placeholder directories until they contain useful implementation or contributor-facing documentation.

## Scenario-specific labs

Labs are scenario-specific, controlled environments that make a walkthrough reproducible. They can support manual investigation, deterministic security checks, agent-assisted workflows, and independent verification and evaluations. Labs remain separate from the reusable Core Harness, and not every scenario needs a lab.

Scenario 1 is [PHP2Shell](scenarios/php2shell/README.md). Its canonical lab registry defines local Docker Labs [A](scenarios/php2shell/labs/local/lab-a/README.md) and [B](scenarios/php2shell/labs/local/lab-b/README.md), plus AWS EC2 Labs [C](scenarios/php2shell/labs/aws/lab-c/README.md) and [D](scenarios/php2shell/labs/aws/lab-d/README.md). Lab identifiers are neutral; findings come from observed evidence rather than names.

## Architecture at a glance

VulHarness is scenario-driven and uses reusable framework components:

```text
Scenario
  ├── references Walkthroughs for a goal, environment, and method
  ├── references reusable Workflows and Skills
  ├── records conditions, technical references, evidence requirements,
  │   and expected outcomes
  └── is independently assessed by Evaluations
          └── may use Checks to verify evidence
```

Environments and execution methods are separate dimensions. For example, a local container, an EC2 instance, or a CI/CD pipeline may eventually be investigated manually, deterministically by script, through the Core Harness, with an agent, through an MCP/API, or through inventory and security-product integrations. The [architecture document](docs/architecture.md) defines these boundaries without implementing them prematurely.

## Getting started

The first reference scenario is [PHP2Shell](scenarios/php2shell/README.md). To explore it:

1. Read the [security boundaries](SECURITY.md).
2. Read the [scenario overview](scenarios/php2shell/README.md) and [reference register](scenarios/php2shell/references.md).
3. Browse the [walkthrough index](scenarios/php2shell/walkthroughs/README.md).
4. Follow the [local manual investigation](scenarios/php2shell/walkthroughs/local/manual-investigation/README.md) using an isolated, authorized environment that you provide or provision.
5. Use the [evaluation guidance](evals/README.md) to record evidence and compare it with the scenario's expected outcomes.

Start with the canonical [Scenario 1 Participant Lab Guide](scenarios/php2shell/walkthroughs/participant-lab-guide.md). It contains the complete tested local journey, the available AWS infrastructure/runtime workflow, and clearly marked future agent-assisted work. The [deterministic checker](scenarios/php2shell/checks/local-http-version/README.md), [AWS lifecycle evaluator](scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py), and [Lab B lifecycle evaluation](scenarios/php2shell/evals/remediation-lifecycle/evaluate.py) remain implementation references.

Evaluation principles are documented in [evals/README.md](evals/README.md). Persistent project context, design decisions, status, and open questions are maintained in the [LLM Wiki](wiki/index.md); operational commands remain authoritative in the repository and participant guides.

## Available today

The first reference implementation is PHP2Shell. It currently includes:

- Local Docker Labs A and B, including the Lab B remediation lifecycle.
- AWS EC2 Labs C and D.
- Independent AWS CLI, CloudFormation, and Terraform deployment methods.
- The Python orchestration harness at
  [`scripts/vulharness-php2shell.py`](scripts/vulharness-php2shell.py).
- Deterministic runtime checks, remediation and reset operations, and
  independent evaluations with evidence and authorization boundaries.

Validation status is intentionally separated by environment. The local
orchestration lifecycle and its tests have been run successfully. Historical
AWS CLI, CloudFormation, and Terraform validation is summarized in the project
wiki, but raw AWS evidence is intentionally excluded from this public
repository because it can contain live account and infrastructure metadata.
The AWS evaluator and orchestration harness have offline/mock coverage; any
live output is written locally under the ignored `docs/evidence/aws/` directory
and must be handled as private evidence. Infrastructure health, SSM
connectivity, PHP runtime readiness, and vulnerability exposure remain
separate claims.

## Build or contribute a vulnerability scenario

VulHarness welcomes reproducible vulnerability investigation scenarios. Read
the [scenario development guide](docs/scenario-development-guide.md),
[CONTRIBUTING.md](CONTRIBUTING.md), and the existing
[PHP2Shell reference scenario](scenarios/php2shell/README.md). PHP2Shell is a
reference implementation, not a requirement that every future scenario use
AWS, Terraform, CloudFormation, four labs, or the same checks and evaluators.
Future scenarios may define different environments, evidence, deterministic
checks, and independent evaluations. Generic multi-scenario execution is not
implemented today.

## Coming soon — Chief-of-Staff Agent

Planned future work may explore a chief-of-staff agent that accepts a question
such as “Are we impacted by PHP2Shell?”, discovers the relevant scenario,
invokes only authorized VulHarness operations, and reports evidence-backed
results and unknowns. This is not implemented. We intend to explore or
demonstrate the concept in a follow-up livestream; no date or registration
link has been announced.

## Future — AI-assisted scenario planning

A future assistant could interview contributors about a new vulnerability,
ask clarifying questions about target environment, scope, evidence, and
expected outcomes, and help produce a scenario implementation plan. Any plan
would still require human review, deterministic implementation, independent
evaluations, and explicit authorization. No scenario generator, registry, or
agent framework is implemented.

## License

Original VulHarness material developed by The AI Security Lab is copyright © 2026 The AI Security Lab. Independent contributors retain rights in their original contributions; contributions included in this repository are licensed under the [Apache License, Version 2.0](LICENSE). Apache 2.0 permits commercial use and this repository adds no noncommercial restriction.

Paid AI Security Lab workshop materials, recordings, and separately developed proprietary services are outside the scope of this repository unless explicitly included.

## Project status

Local Scenario 1 functionality is implemented and its three Lab B lifecycle states were reported successfully validated before the lab-directory migration. AWS Labs C/D now include independent CLI, CloudFormation, and Terraform infrastructure methods, a shared SSM-only Docker/Compose workflow, and a scoped independent evaluator. Historical AWS validation summaries are recorded per deployment method; raw live evidence is retained privately outside the public tree. Infrastructure health remains distinct from PHP runtime readiness.

Reusable workflows, agent skills, generic multi-scenario execution, automatic remediation, a generalized evaluation framework, chief-of-staff agent orchestration, and the Core Harness remain future work. The current orchestration command is PHP2Shell-specific. See the [current project status](wiki/current-status.md) for the concise implementation boundary.

The official security-reporting contact remains a TODO in [SECURITY.md](SECURITY.md). No future commercial platform roadmap is part of this repository's architecture.
