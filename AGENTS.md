# AGENTS.md

## Purpose

VulHarness is an AI Security Lab community project for authorized vulnerability investigation, response workflows, and independent evaluation. It does not distribute intentionally vulnerable applications.

## Repository navigation

- `scenarios/` contains vulnerability or security-finding context and scenario-specific walkthroughs.
- `evals/` documents independent evaluation principles.
- `docs/` contains framework architecture.
- `.github/` contains contribution templates.
- Future workflows, skills, integrations, checks, and Core Harness components should be added only when they contain useful implementation or contributor-facing documentation.

Read the relevant scenario, walkthrough index, references, architecture, security, and contribution documents before changing content.

## Architectural boundaries

Keep scenario-specific functionality separate from reusable workflows, skills, checks, evaluations, and integrations. Scenarios may reference reusable workflows and skills but must not duplicate or hardcode them. PHP2Shell is a reference scenario, not a generic framework special case.

Environment and execution method are separate dimensions. Manual walkthroughs are first-class. Agent-assisted execution and provider-specific adapters are optional; reusable interfaces must remain provider-independent.

## Evidence and technical claims

Use vendor advisories, official CVE records, official cloud documentation, and official API or protocol documentation for public vulnerability claims. Third-party research may supplement authoritative sources but must not independently establish golden expectations.

Preserve evidence provenance, source, scope, freshness, and relevant timestamps. Distinguish configured, expected, and observed behavior. Do not conflate inventory findings, vulnerable versions, and actual runtime exposure. Keep golden evaluations independent of agent-generated conclusions.

Do not invent affected versions, fixed versions, CVEs, or exposure conditions. Record uncertainty and missing evidence explicitly.

## Safety and validation

Work only within authorized scope and least privilege. Keep credentials, tokens, private keys, personal data, production artifacts, and other secrets out of the repository. Do not build or distribute vulnerable applications.

Before finishing a change, check internal links, metadata syntax, stale paths, documentation claims about implemented versus planned functionality, and the complete file tree. Follow the pull-request checklist in `.github/PULL_REQUEST_TEMPLATE.md`.

During the current repository task, do not commit, push, publish, create a remote repository, or implement executable security functionality without explicit authorization.
