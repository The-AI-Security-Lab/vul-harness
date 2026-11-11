# Contributing to VulHarness

VulHarness welcomes workshop participants, security practitioners, researchers, and tool builders who want to contribute reproducible vulnerability investigation and response content.

Contributions are submitted through GitHub pull requests. A scenario does not need an executable workflow, agent integration, cloud deployment, or automation layer to be useful or accepted.

The [scenario development guide](docs/scenario-development-guide.md) describes
the recommended progression from manual investigation to deterministic checks,
independent evaluation, and optional scenario-specific orchestration. Read it
alongside this contribution guide and the [PHP2Shell reference scenario](scenarios/php2shell/README.md).

## What you can contribute

- A new vulnerability assessment scenario
- A manual or automated walkthrough
- A reusable workflow that can be referenced by multiple scenarios
- A reusable skill or practitioner capability
- Generic or scenario-specific checks
- Evaluation definitions and golden expectations
- Optional integrations or adapters for clouds, Kubernetes, security products, APIs, MCP servers, or CI/CD systems
- A scenario-specific lab with reproducible setup and cleanup documentation
- Lab setup instructions, configuration examples, and documentation

Manual-only scenario contributions are explicitly welcome. Contributors do not need to implement an agent integration.

## Scenario contributions

A scenario describes a vulnerability or security finding, including affected conditions, technical references, evidence requirements, and expected outcomes. It must not distribute an intentionally vulnerable application. Participants may use Docker, existing images, virtual machines, EC2, ECS, EKS, other Kubernetes environments, on-premises infrastructure, CI/CD systems, or other authorized environments when the contribution explains the assumptions and provenance.

Labs are optional scenario-specific environments, not reusable Core Harness components. A lab contribution must document its image or infrastructure provenance, target versions, configuration, authorization and isolation boundary, evidence expectations, limitations, and cleanup. A scenario does not need a Docker lab to be accepted.

At minimum, a scenario contribution should provide:

- A stable scenario ID and title
- A concise description of the intended security outcome
- A short practitioner-facing `What You Need to Know` quick advisory in the scenario README
- Authoritative technical references where relevant
- Preconditions, target version, configuration, provenance, and environment assumptions
- One or more walkthroughs, including a manual walkthrough when appropriate
- Expected outcomes and clear evaluation criteria
- The evidence a participant should collect
- Limitations, uncertainty, failure modes, and cleanup guidance
- A statement of the authorization and isolation boundary

The quick advisory should be readable in approximately two minutes and summarize what happened, confirmed vulnerability identifiers, affected technologies, relevant conditions, evidence requirements, verified remediation, uncertainty, and authoritative references. It is required once per scenario, not once per walkthrough.

Do not invent affected versions, fixed versions, CVEs, or exposure conditions. If a claim requires verification, mark it as unresolved and identify the authoritative source that must be checked.

The current PHP2Shell command at `scripts/vulharness-php2shell.py` is
scenario-specific. Do not imply that an arbitrary new scenario can run through
it, and do not introduce a generic registry or plug-in contract without a
separate architectural decision. A future scenario may use different
environments, checks, evaluators, and execution methods.

Use the methodology in the [scenario development guide](docs/scenario-development-guide.md)
to decide which parts are appropriate. Manual-only, local-only, and
documentation-led contributions remain first-class.

## Reusable content and integrations

Keep reusable content separate from scenario-specific content:

- **Walkthroughs** are goal-oriented investigations for an environment and execution method.
- **Workflows** are reusable security processes such as Discover → Assess → Remediate → Verify.
- **Skills** are reusable agent-readable instructions or practitioner procedures.
- **Checks** are concrete mechanisms for collecting or verifying evidence.
- **Evaluations** independently compare observed evidence with expected conditions and outcomes.
- **Integrations** are optional adapters for external clouds, systems, products, APIs, MCP servers, and CI/CD platforms.

Scenarios may reference reusable workflows and skills, but should not copy or own them. Generic checks should eventually live in shared framework components; scenario-specific checks may remain with their scenario. Provider-specific adapters are permitted, but reusable interfaces must remain provider-independent.

Integrations should preserve source, timestamp, scope, freshness, and coverage information. Findings from an external security product must not automatically be treated as verified runtime exposure.

## Technical references

For public vulnerability claims, prioritize:

- Vendor security advisories
- Official CVE records
- Official cloud-provider documentation
- Official API and protocol documentation

Third-party research and proof-of-concept material may supplement those sources but must not independently establish golden expectations. For authorized private findings without public advisories, contributors may provide sanitized, reproducible evidence with documented provenance and limitations.

## Pull-request process

1. Create a branch and make the smallest focused change that explains the contribution.
2. Add or update documentation and metadata before adding implementation.
3. Run the validation checks described below.
4. Open a GitHub pull request using the repository template.
5. Respond to review questions about authorization, reproducibility, evidence, sources, and evaluation criteria.

Do not commit vulnerable applications, credentials, real target data, or unnecessary exploit tooling. Do not test third-party systems without explicit authorization.

## Reproducibility, evidence, and evaluation requirements

Document enough information for another authorized practitioner to understand and repeat the investigation:

- Intended security outcome and scope
- Preconditions and authorization boundary
- Environment type, target version, and configuration
- Image, package, source, or VM provenance
- Host and runtime assumptions
- Safe reproduction steps, where appropriate
- Artifacts collected and how they were protected or redacted
- Expected, unsupported, inconclusive, and missing-evidence outcomes
- Limitations, uncertainty, and cleanup steps
- Secret-hygiene expectations

Golden expectations must not be changed simply to match an agent's output. Evaluation should distinguish configured, expected, and observed behavior, and should remain independent of the agent or provider that produced the evidence.

## Validation checklist

Before opening a pull request, confirm that:

- The contribution stays within an authorized lab or testing boundary.
- It does not build or distribute an intentionally vulnerable application.
- All public version and vulnerability claims are sourced or clearly marked for verification.
- The documentation identifies provenance, versions, configuration, scope, and assumptions.
- Evidence and expected outcomes are clearly separated.
- Manual-only contributions remain usable without an agent integration.
- Internal links and referenced paths work.
- No credentials, private data, or unrelated generated files are included.
- The contribution is compatible with Apache License 2.0 and adds no noncommercial restriction.

## Licensing

VulHarness is licensed under Apache License 2.0. Original project material developed by The AI Security Lab is identified in [NOTICE](NOTICE); independent contributors retain rights in their original contributions. By submitting a contribution for inclusion, contributors make it available under Apache 2.0 unless a separate written arrangement applies.

Paid workshop materials, recordings, and separately developed proprietary services are outside this repository unless explicitly included.

## Project decisions still required

- TODO: select and publish the official security-reporting contact and response process.
