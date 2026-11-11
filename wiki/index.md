# VulHarness LLM Wiki

This lightweight Markdown wiki preserves project knowledge across development sessions. It follows the persistent-wiki pattern described in [Karpathy's LLM Wiki note](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): source material remains authoritative, maintained wiki pages synthesize it, and a schema defines how claims are recorded.

This is not `llms.txt`, a database, a search service, or an operational runbook. Repository documentation and participant guides remain authoritative for commands and safety instructions.

## Knowledge layers

1. **Sources:** repository code, Compose files, documentation, tests, observed validation reports, and cited primary advisories.
2. **Maintained wiki:** the pages below summarize architecture, decisions, progress, and unresolved questions without replacing sources.
3. **Schema:** [schema.md](schema.md) defines claim categories, citations, update rules, and the chronological log convention.

## Pages

- [Architecture](architecture.md) — Scenario 1 boundaries, labs, checks, evaluations, and planned cloud adapter.
- [Decisions](decisions.md) — agreed design choices and rationale.
- [Current status](current-status.md) — implemented, observed, scaffolded, planned, and blocked work.
- [Log](log.md) — chronological wiki-maintenance and project-progress entries.
- [Schema](schema.md) — maintenance rules and claim-status vocabulary.

## Primary repository sources

- [Root project overview](../README.md)
- [Framework architecture](../docs/architecture.md)
- [Scenario 1 registry](../scenarios/php2shell/README.md)
- [PHP2Shell technical references](../scenarios/php2shell/references.md)
- [Canonical Scenario 1 participant guide](../scenarios/php2shell/walkthroughs/participant-lab-guide.md)
- [AWS EC2 plan](../scenarios/php2shell/labs/aws/README.md)
- [Evaluation principles](../evals/README.md)

Read [current-status.md](current-status.md) first when resuming work, then consult [decisions.md](decisions.md) before changing architecture.
