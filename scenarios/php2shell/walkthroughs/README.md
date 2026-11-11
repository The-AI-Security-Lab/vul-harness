# PHP2Shell walkthroughs

Walkthroughs are organized by environment and investigation method. The directory structure is not a mandatory learning-level hierarchy, and a scenario may eventually support multiple combinations of environment and method.

## Canonical participant journey

- [Participant Lab Guide](participant-lab-guide.md)

This is the single self-service lab journey. It progresses through prerequisites, the scope-aware orchestration command, local manual investigation, deterministic automation, remediation and independent verification, implemented AWS Labs C/D, cleanup, and troubleshooting. Each stage states whether it is implemented or planned.

## Supporting evidence reference

- [Local manual investigation](local/manual-investigation/README.md)

The manual investigation document and evidence-report template provide deeper evidence requirements and report structure. They support the canonical guide; they are not separate participant journeys.

## Possible future extensions

The framework may eventually support walkthroughs for combinations such as:

- ECS, EKS, or other Kubernetes investigation using cloud inventory and runtime evidence
- Agent-assisted investigation using Claude Code, Codex, or another coding agent
- MCP/API-assisted investigation
- CSPM/CNAPP enrichment followed by independent runtime verification
- CI/CD evaluation of affected artifacts
- Continuous or scheduled assessment

These are extension points, not implemented walkthroughs. Future stages should extend the canonical guide and must document authorization, scope, preconditions, target version, provenance, configuration, evidence, freshness, uncertainty, and cleanup.
