# AI Security Engineering Lab

**Investigate. Automate. Verify.**

## What is VulHarness?

VulHarness is an open-source community project for authorized vulnerability
investigation and response workflows. It helps turn a documented investigation
into a repeatable sequence:

1. **Investigate** manually and record what is configured, running, and
   observable.
2. **Automate** bounded evidence collection and repeatable lifecycle steps.
3. **Verify** the result with independent evaluations rather than trusting an
   agent, wrapper, or participant self-report.

Scenario-specific orchestration may coordinate those components, but it does
not replace human authorization, review, or evidence limitations. The project
does not distribute intentionally vulnerable applications. Use only isolated
environments and targets that you are authorized to test.

## Choose your path

### Run a scenario

Start with the [PHP2Shell scenario overview](scenarios/php2shell/README.md),
then follow its [canonical participant lab guide](scenarios/php2shell/walkthroughs/participant-lab-guide.md).
The guide is the authoritative execution sequence for the implemented local
and optional AWS journeys.

```bash
git clone https://github.com/The-AI-Security-Lab/vul-harness.git
cd vul-harness
```

The current PHP2Shell implementation is on the
[`stage1-nov-26-workshop` branch](https://github.com/The-AI-Security-Lab/vul-harness/tree/stage1-nov-26-workshop).
Read [SECURITY.md](SECURITY.md) before running any lab.

### Create a scenario

Read the [scenario model and lifecycle](scenarios/README.md), then the
[scenario-development guide](docs/scenario-development-guide.md) and
[CONTRIBUTING.md](CONTRIBUTING.md). A scenario can be manual-only and does not
need AWS, an agent, a skill, orchestration, or advanced evaluations.

## What's available today

The following capabilities are implemented in the PHP2Shell workshop branch:

- Local Docker Labs A and B with manual investigation and a remediation/reset
  lifecycle.
- AWS EC2 Labs C and D with AWS CLI, CloudFormation, and Terraform provisioning
  alternatives, plus the shared authenticated SSM runtime workflow.
- Deterministic runtime checks, independent local and AWS evaluations, and the
  PHP2Shell-specific Python orchestration command.
- Scenario-development, contribution, architecture, and evidence-handling
  documentation.

The local lifecycle and offline AWS orchestration/evaluator coverage are
testable without live infrastructure. Historical live AWS validation is
documented as historical validation; raw account and resource evidence is
private and excluded from this repository. A fixed-version result does not
prove exploitability or complete remediation.

## Repository structure

```text
.
├── scenarios/       Scenario context, labs, walkthroughs, checks, and evals
├── docs/            Architecture and scenario-development guidance
├── evals/           Repository-level evaluation principles
├── scripts/         Scenario-specific orchestration commands
├── wiki/            Project decision and status references
├── .github/         Contribution and issue templates
├── CONTRIBUTING.md  Contribution process and boundaries
├── SECURITY.md      Security reporting and authorized-testing policy
├── LICENSE          Apache License 2.0
└── NOTICE           Attribution
```

The [PHP2Shell README](scenarios/php2shell/README.md) is the scenario-specific
discovery page. Its `walkthroughs/`, `labs/`, `checks/`, and `evals/` indexes
explain the technical responsibilities of those folders.

## How VulHarness works

- **Scenarios** define the security question, affected conditions, references,
  evidence requirements, and expected outcomes.
- **Walkthroughs** describe the investigation sequence and what participants
  can and cannot conclude.
- **Labs** provide bounded, scenario-specific environments and provider/runtime
  operations.
- **Checks** collect concrete evidence from explicitly authorized targets.
- **Evaluations** compare observed evidence with independent expected outcomes.
- **Orchestration** coordinates existing components with explicit scope and
  approvals without replacing human review.

Environment and execution method remain separate dimensions. A manual
investigation, direct provider command, deployment wrapper, runtime automation,
deterministic check, evaluator, and scenario-specific orchestrator must not be
presented as interchangeable operations.

Read the [architecture](docs/architecture.md) and
[evaluation guidance](evals/README.md) for evidence provenance, limitations,
and independent golden expectations.

## Branch and implementation status

The default `main` branch currently contains the public project foundation.
The complete PHP2Shell implementation and workshop documentation remain on
[`stage1-nov-26-workshop`](https://github.com/The-AI-Security-Lab/vul-harness/tree/stage1-nov-26-workshop)
while participant validation continues. The workshop branch has not been
merged into `main` by this documentation update.

### Roadmap

Future capabilities are not current functionality. Dates below are indicative
planning targets, not commitments.

| Capability | Status / target |
| --- | --- |
| PHP2Shell local labs and deterministic checks | Available on the workshop branch |
| AWS CLI, CloudFormation, and Terraform labs | Available on the workshop branch |
| PHP2Shell VulHarness orchestration | Available on the workshop branch |
| Reusable coding-agent skills | Indicative December 2026 workshop target |
| Chief of Staff Agent | Indicative Q1 2027 workshop target |
| Generalized multi-scenario Harness | Indicative Q1 2027 target |
| Automated remediation | Indicative Q1 2027 target |
| External security integrations | Indicative Q1 2027 target |
| Additional vulnerability scenarios | Indicative Q2 2027 target |
| Azure and GCP environments | Indicative Q2 2027 target |

## Contributing, safety, and license

To propose a new vulnerability scenario, start with the
[scenario model](scenarios/README.md), [scenario-development guide](docs/scenario-development-guide.md),
and [CONTRIBUTING.md](CONTRIBUTING.md). Proposals should define authorization
and scope, evidence requirements, independent evaluation expectations, safety
boundaries, and cleanup before implementation.

Keep credentials, private evidence, personal data, production artifacts,
intentionally vulnerable applications, and unnecessary exploit tooling out of
the repository. See [SECURITY.md](SECURITY.md) for reporting and
authorized-testing boundaries.

Original VulHarness material developed by The AI Security Lab is licensed under
the [Apache License, Version 2.0](LICENSE). See [NOTICE](NOTICE) for
attribution.
