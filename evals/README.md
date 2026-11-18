# Evaluations

Evaluations independently compare observed evidence with a scenario's defined conditions and expected outcomes. They are independent of the tool, workflow, agent, provider, cloud, security product, or integration that produced the evidence.

A participant may complete a scenario manually and still produce a valid evaluation result. Golden expectations must not be changed simply to match an agent's output.

## Configured, expected, and observed behavior

Keep these concepts separate:

- **Configured behavior** is what the environment, runtime, policy, or deployment declares or is intended to do.
- **Expected behavior** is what the scenario says should be established under stated conditions.
- **Observed behavior** is what the collected evidence shows happened in the tested environment.

An evaluation explains how these categories relate. A configured setting is not automatically proof of runtime exposure, and an observed symptom is not automatically proof of a particular vulnerability claim.

## Expected outcomes

An expected outcome is a statement about what the investigation should establish. It should be observable and scoped to the scenario. Examples include:

- A required runtime fact was identified and supported by evidence.
- A configuration or environment assumption was confirmed or rejected.
- A relevant uncertainty was recorded instead of being presented as fact.
- Cleanup was completed and documented.

Do not turn an unverified hypothesis into an expected fact. Public version and vulnerability claims require authoritative advisory, vendor, official CVE, official cloud, or official API/protocol verification.

## Evidence

Evidence is the artifact or observation supporting an outcome. It may include redacted command output, configuration excerpts, runtime metadata, timestamps, screenshots, inventory records, or a participant's structured report, depending on the scenario.

Each evaluation should make clear:

- What evidence is expected
- How the evidence is collected
- The source, provenance, scope, freshness, and relevant timestamps
- What sensitive information must be redacted
- How conflicting, stale, incomplete, or unavailable evidence is handled

Evidence should be independently inspectable where practical. A tool or agent's assertion that it succeeded is not, by itself, sufficient evidence.

## Verification principles

- Prefer observable facts over narrative claims.
- Use more than one signal when a single signal is fragile or ambiguous.
- Record uncertainty and environmental limitations.
- Distinguish absent evidence from evidence of absence.
- Keep checks focused on verification; keep interpretation and scoring in the evaluation.
- Preserve enough provenance for another authorized practitioner to understand the result.
- Avoid requiring a particular provider, agent, automation platform, or cloud.
- Do not conflate inventory findings, vulnerable versions, and actual runtime exposure.
- Treat CSPM/CNAPP or other security-product findings as enrichment unless independently verified by appropriate runtime evidence.

## Evaluation outcomes

Evaluations should distinguish at least these evidence conclusions:

- **Supported:** the observed evidence supports the stated conclusion under the documented conditions.
- **Unsupported:** the evidence does not support the stated conclusion or contradicts it.
- **Inconclusive:** the available environment or evidence cannot support a reliable conclusion.
- **Missing or insufficient evidence:** a required artifact or observation was not collected or is not adequate for the claim.

A scenario may also use summary classifications such as pass, partial, fail, or inconclusive, provided the underlying evidence conclusion remains visible.

## Golden evaluations

A golden evaluation is a documented reference for the evidence and reasoning expected from a scenario under stated conditions. It should describe:

- The authorization, scope, and environment assumptions
- Configured behavior relevant to the investigation
- The facts that should be discoverable
- The evidence that supports each expected outcome
- Acceptable variations in commands or presentation
- Expected uncertainty and known limitations
- Supported, unsupported, inconclusive, and missing-evidence conditions
- Cleanup expectations

Golden evaluations should judge outcomes and evidence rather than require one exact command sequence. They should not depend on a vulnerable application distributed by VulHarness.

## Evaluation lifecycle

The current repository includes a scenario-specific PHP2Shell version check, a narrowly scoped [PHP2Shell Lab B remediation lifecycle evaluation](../scenarios/php2shell/evals/remediation-lifecycle/evaluate.py), and an independent [AWS Lab C/D lifecycle evaluator](../scenarios/php2shell/evals/aws-lifecycle/README.md). The AWS evaluator compares exact-tag infrastructure, SSM, Docker/Compose, PHP, cleanup, and GuardDuty evidence for one selected deployment method. These remain scenario-specific evaluations, not a generalized evaluation framework or Core Harness implementation.

Contributors should continue to define scenario expectations explicitly and explain how a reviewer can inspect the underlying evidence manually.
