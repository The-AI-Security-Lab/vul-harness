# Scenarios

## What is a scenario?

A scenario describes a vulnerability or security finding in a bounded,
authorized environment. It defines the security question, affected conditions,
technical references, evidence requirements, and expected outcomes without
depending on a particular cloud provider or agent.

Keep three concepts separate:

- A **scenario** defines what is being investigated and what evidence supports
  each conclusion.
- A **lab** is an optional, scenario-specific environment in which the
  investigation can be performed.
- An **execution method** describes how the work is performed, such as manual
  observation, a direct provider command, deterministic automation, or a
  scenario-specific orchestrator.

Scenarios do not distribute intentionally vulnerable applications or embed
provider-specific behavior into reusable interfaces.

## PHP2Shell as the reference example

[PHP2Shell](php2shell/README.md) is the first reference scenario. It demonstrates
how a manual investigation can become repeatable deterministic evidence
collection and independent evaluation. It is a reference example, not a
mandatory template for every scenario.

## Minimum scenario structure

Repository conventions do not enforce one universal runtime schema. The
following is a small, reviewable starting point rather than a requirement that
every scenario implement every folder:

```text
scenarios/<scenario-id>/
├── README.md          scenario advisory, scope, evidence, and outcomes
├── scenario.yaml      scenario metadata when machine-readable metadata is used
├── references.md      authoritative technical references when needed
└── walkthroughs/      at least one participant or practitioner journey
```

The README and a clear investigation walkthrough are the important starting
points. Add `scenario.yaml` when the scenario uses repository metadata
conventions, and add `references.md` when public technical claims need a
reference register. `labs/`, `checks/`, and `evals/` are optional extensions.
PHP2Shell uses all of these layers because its workshop requires them; a
manual-only or documentation-led scenario can be smaller.

## How to create a scenario

1. Define the intended security outcome, affected conditions, authorization
   boundary, and what is explicitly out of scope.
2. Research authoritative sources and record scope, freshness, affected
   conditions, fixed versions, provenance, and uncertainty.
3. Write a manual walkthrough with commands, expected observations, evidence
   sources, timestamps, limitations, and safe cleanup.
4. Add only the lab environments needed to answer the investigation question.
5. Add deterministic checks or independent evaluations when repeatability adds
   value. Keep configured, expected, and observed state distinct.
6. If orchestration is useful, coordinate existing operations only after the
   manual and evaluation contracts are stable.
7. Validate links, paths, command examples, tests, evidence handling, and the
   complete file tree before submitting a focused pull request.

The scenario-level **What You Need to Know** advisory belongs near the top of
the scenario README. It should summarize the finding, affected technology and
conditions, evidence requirements, verified remediation, authoritative
references, and uncertainty. It must not turn a version classification into a
claim of exploitability.

## Optional advanced components

- **Labs** provide reproducible local, cloud, or other authorized environments
  when the environment changes the evidence or operational decision.
- **Checks** collect bounded, concrete evidence with stable inputs and outputs.
- **Evaluations** independently compare evidence with golden expectations,
  including missing, stale, failed, and cleanup states where relevant.
- **Workflows, skills, and integrations** may be referenced when they are
  genuinely reusable and provider-independent.
- **Orchestration** may coordinate a scenario's existing commands, but it is
  not a generic agent interface and must preserve human approval boundaries.

Manual-only scenarios are valid. Do not add AWS, coding agents, skills, MCP,
orchestration, advanced evaluations, or hypothetical environments merely to
match PHP2Shell.

## Contribution and review requirements

Read the [scenario-development guide](../docs/scenario-development-guide.md) and
[CONTRIBUTING.md](../CONTRIBUTING.md) before opening a pull request. A complete
proposal should make its authorization boundary, environment provenance,
expected outcomes, evidence sources, uncertainty, permissions, cost, reset,
cleanup, and unsupported conclusions clear.

Evaluations must remain independent: an agent, wrapper, or orchestrator may
collect or report evidence, but its self-reported success is not proof. Preserve
source, scope, timestamp, freshness, and limitations for evidence, and do not
include credentials, private data, vulnerable applications, or unnecessary
exploit tooling.
