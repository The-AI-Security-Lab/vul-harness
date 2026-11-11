# AI Security Engineering Lab

**Investigate. Automate. Verify.**

## Scale Vulnerability Investigations with AI

VulHarness is an open-source community project for authorized vulnerability
investigation and response workflows. It turns a documented investigation into
repeatable walkthroughs, deterministic checks, independent evaluations, and
carefully bounded orchestration.

The project does not distribute intentionally vulnerable applications. Use only
isolated environments and targets that you are authorized to test.

## Start here

The first reference scenario is [PHP2Shell](scenarios/php2shell/README.md).
The [participant lab guide](scenarios/php2shell/walkthroughs/participant-lab-guide.md)
is the canonical self-service path from manual investigation through
deterministic automation, independent evaluation, and the PHP2Shell-specific
orchestration command. It explains which AWS steps are optional and which
future agent capabilities are not implemented.

```bash
git clone https://github.com/The-AI-Security-Lab/vul-harness.git
cd vul-harness
```

Before running a lab, read [SECURITY.md](SECURITY.md), the
[scenario overview](scenarios/php2shell/README.md), and the
[participant guide](scenarios/php2shell/walkthroughs/participant-lab-guide.md).

## Available today

- Local Docker Labs A and B with manual investigation and a remediation/reset
  lifecycle.
- AWS EC2 Labs C and D with AWS CLI, CloudFormation, and Terraform provisioning
  alternatives, plus a shared authenticated SSM runtime workflow.
- Deterministic runtime checks, independent local and AWS evaluations, and the
  PHP2Shell-specific Python orchestration command.
- Scenario-development, contribution, architecture, and evidence-handling
  documentation.

The local lifecycle and offline AWS orchestration/evaluator coverage are
testable without live infrastructure. Historical live AWS validation is
documented as historical validation; raw account and resource evidence is
private and excluded from this repository. A fixed-version result does not
prove exploitability or complete remediation.

## Project boundaries

Scenarios own their environment-specific labs and walkthroughs. Checks collect
concrete evidence, evaluations compare evidence with expected outcomes, and
orchestration coordinates existing components without replacing human review.
Environment and execution method remain separate dimensions, and provider
adapters must not make reusable interfaces provider-specific.

Read [docs/architecture.md](docs/architecture.md),
[docs/scenario-development-guide.md](docs/scenario-development-guide.md), and
[CONTRIBUTING.md](CONTRIBUTING.md) before proposing a new scenario. The
[evaluation guidance](evals/README.md) explains evidence provenance,
limitations, and independent golden expectations.

## Future direction

Reusable skills, a Chief-of-Staff Agent, generalized multi-scenario execution,
automatic remediation, and AI-assisted scenario planning are future work. They
are not implemented by the current PHP2Shell reference scenario.

## License

Original VulHarness material developed by The AI Security Lab is licensed under
the [Apache License, Version 2.0](LICENSE). See [NOTICE](NOTICE) for attribution
and [SECURITY.md](SECURITY.md) for reporting and authorized-testing boundaries.
