# Scenario development guide

This guide explains how to contribute a reproducible vulnerability
investigation scenario to VulHarness. PHP2Shell is the current reference
implementation, but it is not a template that every scenario must copy
literally. A useful contribution may be manual-only, local-only, or smaller
than PHP2Shell. AWS, Terraform, CloudFormation, four labs, and agent
integration are optional.

The engineering progression is:

```text
Manual investigation
  → coding-agent-assisted deterministic automation
  → independent evaluation
  → harness engineering
  → reusable scenario patterns
  → future AI-agent orchestration
```

Manual investigation and deterministic evidence remain useful even when no
agent or orchestration layer is present.

## Step 1 — Research the vulnerability

Start with authoritative sources and record their scope and freshness.

- Prefer vendor advisories, official CVE records, official cloud
  documentation, and official API or protocol documentation.
- Record CVE or finding identifiers, affected versions or conditions, fixed
  versions, applicability criteria, and remediation guidance only when the
  sources support those claims.
- Separate an installed package version, an upstream vulnerable version, an
  applicable vulnerability condition, and demonstrated exposure.
- Identify runtime, deployment, worker, configuration, request-routing, and
  vendor-backport conditions that affect applicability.
- Record explicit uncertainties. Do not turn missing evidence into an
  affected or fixed conclusion.

The scenario README should provide a short practitioner-facing advisory and
link to a fuller reference register where needed. Do not commit an
intentionally vulnerable application or exploit infrastructure.

## Step 2 — Define the investigation

Write the questions before writing commands. For example:

- What asset, package, service, or runtime is in scope?
- What is the authorized environment and who owns it?
- What evidence distinguishes desired configuration from running state?
- What permissions, network paths, or external services are required?
- What are the expected known-good, potentially affected, failed, and
  insufficient-evidence outcomes?
- What constitutes done, including independent verification and cleanup?

Define the scope boundary, assumptions, permissions, evidence schema, expected
outcomes, limitations, and definition of done. Keep security decisions visible
in documentation and evaluations rather than hiding them in opaque scripts.

## Step 3 — Build a reproducible environment

Start locally when a local environment answers the investigation questions.
Add cloud or other remote environments only when they change the evidence or
operational decision.

- Use only environments that the contributor and participant are authorized to
  create and inspect.
- Isolate lab resources from production and unrelated user resources.
- Document image, package, source, VM, or infrastructure provenance.
- Record versions, configuration, ports, network boundaries, identities,
  permissions, and assumptions.
- Provide setup, reset, and cleanup procedures with exact ownership scope.
- Prefer safe fixtures and observable state over distributing unnecessary
  vulnerable services or exploit tooling.

Every environment should have a clear failure and recovery path. A cloud
deployment should be disposable, least-privilege, independently owned, and
cost-aware.

## Step 4 — Establish the manual baseline

The manual walkthrough is the reference for what the automation must preserve.
Document the commands a security engineer would run, the expected
observations, and the evidence to retain.

Explain how to distinguish:

- configured or desired state;
- deployed state;
- the process or image currently running; and
- the runtime actually serving or handling the request.

Capture source, target identity, timestamp, transport, raw response, and
collection limitations. State what a participant can conclude and what remains
unknown. A manual-only contribution is complete when another authorized
practitioner can follow it without relying on an agent or undocumented
conversation context.

## Step 5 — Develop deterministic automation

Automate predictable collection, comparison, and repeatable lifecycle steps.
The automation should have explicit inputs and scope, bounded retries where
eventual consistency exists, useful failure states, and safe cleanup.

Coding agents such as Codex or Claude Code may assist with implementation,
test generation, and documentation. The security engineer remains responsible
for defining expected outcomes, reviewing the code, authorizing mutations, and
verifying the result.

Keep these properties visible:

- no credentials or private data in source, output, or evidence;
- no broad account, host, container, or filesystem cleanup;
- no hidden destructive action or generic approval bypass;
- stable command and output contracts;
- explicit timeout, retry, partial-state, and recovery behavior;
- evidence provenance and redaction;
- safe rerun and idempotency expectations.

An LLM is not required to execute deterministic checks. Participants should be
able to run the approved commands directly.

## Step 6 — Create independent evaluations

Define expected state separately from the collection code. Evaluations should
compare observed evidence with golden expectations without accepting an agent's
self-report as proof.

Include, where relevant:

- known-good and known-affected examples;
- configuration-only state;
- failed remediation or stale-running-state evidence;
- reset and recovery states;
- missing, malformed, inaccessible, and stale evidence;
- independent absence verification after cleanup.

Preserve evidence source, timestamp, target scope, freshness, and limitations.
Use result identities that remain unambiguous across scenario, lab, phase, and
deployment. Distinguish:

- `PASS`: the expected condition is supported by sufficient evidence;
- `FAIL`: evidence contradicts the expected condition or a required check
  failed;
- `SKIP`: the check was intentionally conditional or not requested, with a
  classification explaining why; and
- insufficient or unknown evidence: a conclusion cannot be supported.

A conditional external-service skip must not be mistaken for a coverage gap or
a successful cleanup.

## Step 7 — Integrate with orchestration

Once the manual commands, deterministic checks, and independent evaluations
are stable, a scenario may coordinate them through a harness. The current
PHP2Shell reference is [`scripts/vulharness-php2shell.py`](../scripts/vulharness-php2shell.py).

It demonstrates a scenario-specific coordinator that:

- validates environment, lab, method, and deployment scope;
- requires operation-specific authorization for mutations;
- invokes existing checks, evaluators, deployment wrappers, and runtime
  actions;
- preserves independent evaluator semantics;
- returns stable exits, structured output, evidence paths, and recovery hints;
- keeps cleanup exact, repeatable, and dependency-aware.

Do not invent a generic plug-in API merely to make a new scenario appear
automatically supported. Today, a new scenario should provide its own clear
commands and documentation. Future reusable opportunities may include common
scope validation, evidence envelopes, lifecycle state handling, authorization
prompts, and report formatting, but those abstractions need demonstrated use
across multiple scenarios first.

## Step 8 — Document and contribute

A complete scenario contribution normally includes:

- scenario README and short advisory summary;
- scenario metadata;
- authoritative references or sanitized private-finding provenance;
- one or more lab READMEs when environments are provided;
- a manual investigation walkthrough;
- deterministic checks and independent evaluations when automation is useful;
- regression tests and representative evidence examples or schemas;
- setup, reset, cleanup, cost, permissions, and authorization guidance;
- explicit limitations, uncertainty, and unsupported conclusions.

Not every scenario needs AWS, Terraform, CloudFormation, four labs, a
dashboard, or an agent. Keep scenario-specific content under `scenarios/` and
reusable workflows, checks, skills, and integrations separate. Do not claim
that an implementation exists because it is only a future design.

Before opening a pull request:

1. Read [CONTRIBUTING.md](../CONTRIBUTING.md), the [security policy](../SECURITY.md),
   and the relevant architecture guidance.
2. Check internal links, metadata syntax, stale paths, command examples, and
   the complete file tree.
3. Run the scenario's tests and read-only validation.
4. Confirm that no credentials, personal data, private keys, vulnerable
   applications, unnecessary exploit tooling, or generated artifacts are
   included.
5. Use the [pull-request template](../.github/PULL_REQUEST_TEMPLATE.md) to
   explain authorization, provenance, expected outcomes, evidence, cleanup,
   and remaining decisions.

Submit a focused pull request. Reviewers should be able to determine what is
implemented, what is optional, what is future work, how evidence was obtained,
and how the scenario can be safely reset and removed.
