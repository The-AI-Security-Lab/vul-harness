# Wiki maintenance schema

This file defines how future sessions maintain the VulHarness wiki. It is a Markdown convention, not a formal validator or agent instruction file.

## Claim categories

Every material claim should be identifiable as one of these categories:

### Verified implementation

Code, configuration, or documentation exists in the repository and has been directly inspected. Link to the relevant source file. Do not infer that a scaffold has been deployed.

### Observed test evidence

A test, command, or live observation was reported or directly observed. Record what ran, its result, scope, and date when known. If output artifacts or dates are unavailable, say so explicitly. Test evidence does not automatically establish production or cloud behavior.

### Agreed architectural decision

A project owner explicitly selected a boundary, naming rule, interface direction, or sequencing decision. Record the rationale and source task or repository document. Do not rewrite an agreed decision as implemented functionality.

### Proposed design

A concrete approach is documented for review but not yet implemented or approved in all details. List assumptions and link open questions.

### Open question

A material choice or missing fact blocks or shapes future implementation. State the decision owner or required evidence when known. Do not silently resolve it in synthesis.

## Source and link rules

- Prefer relative links to repository sources.
- Link public technical claims to authoritative advisories through the scenario reference register.
- Keep operational commands in repository READMEs and participant guides; summarize and link from the wiki.
- When sources conflict, record the conflict instead of selecting a convenient claim.
- Preserve uncertainty, source, scope, freshness, and relevant timestamps.
- Do not copy entire source documents into the wiki.

## Page responsibilities

- `index.md`: catalog and navigation; update whenever a page is added or renamed.
- `architecture.md`: maintained synthesis of component and environment relationships.
- `decisions.md`: agreed decisions and rationale; revise when a decision is superseded, preserving the old decision in the log.
- `current-status.md`: concise implemented, observed, scaffolded, planned, and open state.
- `log.md`: append-only chronological maintenance and progress record.
- `schema.md`: maintenance convention; change only when the project adopts a new knowledge-management rule.

## Log format

Use:

```text
## [YYYY-MM-DD] type | concise title
```

Allowed types include `consolidation`, `implementation`, `validation`, `decision`, `source`, and `lint`. Do not invent a date; use `date not recorded` in prose when importing older observations.

## Update workflow

1. Read `index.md`, `current-status.md`, and relevant source documentation.
2. Inspect the repository or evidence directly.
3. Update existing pages before creating overlapping pages.
4. Classify new claims using the categories above.
5. Add or repair cross-links.
6. Append a log entry for material changes.
7. Check for contradictions, stale paths, unsupported claims, and orphan pages.

The wiki requires no database, embeddings, vector search, Obsidian dependency, or external service.
