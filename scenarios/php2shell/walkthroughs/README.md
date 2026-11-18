# PHP2Shell walkthroughs

Walkthroughs contain participant journeys, manual evidence methodology, and
expected outcomes. They are organized by environment and investigation method;
the directory structure is not a mandatory learning-level hierarchy, and a
scenario may eventually support multiple combinations of environment and method.

## Canonical participant journey

- [Participant Lab Guide](participant-lab-guide.md)

This is the single self-service lab journey. It progresses through prerequisites,
manual investigation, deterministic checks, independent evaluation, AWS
deployment/runtime operations, orchestration, cleanup, and troubleshooting.
Each stage states whether it is implemented or planned.

Execution modes used by the guide are:

- **Manual investigation:** participant observation through the browser, AWS
  Console, Session Manager, Docker, or PHP commands.
- **Direct provider/runtime command:** a raw `aws`, `docker compose`, Terraform,
  CloudFormation, or runtime command executed within the stated scope.
- **Wrapper automation:** a repository deployment wrapper provisions or cleans
  up infrastructure through one selected provider method.
- **Runtime automation:** the shared SSM workflow changes or inspects an
  already-deployed runtime.
- **Check or evaluation:** deterministic evidence collection or an independent
  comparison with expected outcomes.
- **Harness orchestration:** the scenario-specific Python command coordinates
  existing components and approvals.

## Supporting evidence reference

- [Local manual investigation](local/manual-investigation/README.md)
- [Stage 1 evidence-report template](evidence-report-template.md)

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
