# VulHarness architecture

VulHarness is scenario-driven but uses reusable framework components. It separates the vulnerability or security finding being investigated from the walkthroughs, workflows, skills, checks, evaluations, and integrations used to investigate and verify it.

The current repository documents these boundaries. The future Core Harness is intentionally not implemented yet; the AWS lab tooling remains scenario-specific and independent from that future component.

## Implemented today and future direction

Implemented today:

- the PHP2Shell reference scenario and its local Docker Labs A/B;
- AWS Labs C/D with independent AWS CLI, CloudFormation, and Terraform
  deployment methods;
- deterministic checks, the Lab B remediation lifecycle, and independent
  evaluations;
- the PHP2Shell-specific orchestration command at
  `scripts/vulharness-php2shell.py`; and
- evidence, authorization, exact-scope cleanup, and documented validation
  boundaries.

Future direction:

- additional vulnerability scenarios with their own environments, checks, and
  evaluations;
- reusable orchestration, evidence, lifecycle, and authorization components
  proven across multiple scenarios;
- scenario discovery or a registry;
- agent-operated harness workflows; and
- a chief-of-staff agent that coordinates authorized scenarios.

The future items are design direction, not current interfaces. PHP2Shell's
orchestration command must not be described as a generic multi-scenario
runtime.

## Conceptual model

```text
Scenario
  ├── references Walkthroughs
  ├── references reusable Workflows and Skills
  ├── records conditions, references, evidence requirements,
  │   and expected outcomes
  └── is independently assessed by Evaluations
          └── may use Checks to verify evidence
```

These are conceptual relationships, not a rigid execution hierarchy. A scenario can be investigated manually, by deterministic script, through a future Core Harness, with an agent, or through an external integration. Environment and execution method are separate dimensions.

## Components

### Scenarios

A scenario describes a vulnerability or security finding, including affected conditions, technical references, evidence requirements, and expected outcomes. It defines the assessment context: identity, purpose, environment assumptions, available walkthroughs, and status.

Scenarios are independent of a specific cloud provider or agent. They may reference reusable workflows and skills but must not duplicate or own reusable workflow and skill definitions. PHP2Shell is the first reference scenario; it is not a special case and must not be hardcoded into generic interfaces.

### Labs

A lab is a scenario-specific, controlled test environment that makes one or more walkthroughs reproducible. A lab may use Docker, virtual machines, cloud resources, or another authorized environment. It can support manual investigation, deterministic checks, agent-assisted workflows, and independent evaluations, but it remains scenario content rather than a reusable Core Harness component.

Labs are optional; not every scenario needs one. A lab must document provenance, versions, configuration, authorization, isolation, evidence expectations, limitations, and cleanup. VulHarness labs must not distribute intentionally vulnerable applications unless the project scope and authorization model are explicitly changed.

### Walkthroughs

A walkthrough is a goal-oriented, guided investigation or response for a particular environment and execution method. It may be manual, scripted, agent-assisted, or integrated into another system.

Walkthroughs should explain authorization, scope, preconditions, evidence collection, provenance, configured versus expected versus observed behavior, uncertainty, expected outcomes, and cleanup. Manual investigations are first-class contributions.

The current repository provides one canonical PHP2Shell participant guide that combines the implemented local manual and deterministic journey with the implemented AWS infrastructure/runtime workflow and clearly marked future agent-assisted stages. The detailed manual-investigation evidence reference remains separate. Future stages should extend the canonical scenario journey without presenting unimplemented functionality as operational.

### Workflows

A workflow is a reusable security process, such as:

```text
Discover → Assess → Remediate → Verify
```

Workflows should be reusable across scenarios where appropriate and expose provider-independent inputs and outputs. A scenario may reference a workflow without embedding scenario-specific branches in it.

No executable workflows are implemented in this milestone.

### Checks

A check is a concrete mechanism for collecting or verifying evidence. Checks may be generic or scenario-specific. Generic checks should eventually live in shared framework components; scenario-specific checks may remain inside their scenario.

Checks should be deterministic where possible, explain their assumptions, preserve provenance and timestamps, and report uncertainty rather than hiding it. The PHP2Shell Stage 2 local HTTP version check is the first scenario-specific executable check. It remains separate from reusable workflows, evaluations, agent skills, and the future Core Harness.

### Evaluations

An evaluation independently compares observed evidence with defined expected conditions and outcomes. Golden expectations must not be changed simply to match an agent's output.

Evaluations should distinguish:

- Supported conclusions
- Unsupported conclusions
- Inconclusive observations
- Missing or insufficient evidence

They should remain independent of the tool, workflow, agent, provider, or integration that produced the evidence.

### Skills

A skill is reusable agent-readable instruction or a reusable practitioner procedure. Future examples might include inspecting a local runtime, querying cloud inventory, collecting runtime configuration, validating evidence, or preparing an assessment report.

Skills should not unnecessarily depend on a particular vulnerability. Provider-specific adapters may translate skills to platforms such as Claude Code or Codex, but the reusable skill contract should remain provider-independent.

### Integrations

Integrations are optional adapters for external systems, including:

- AWS, Azure, and Google Cloud
- Kubernetes and on-premises systems
- CSPM/CNAPP products
- Cloud and application security APIs
- MCP servers and tools
- CI/CD systems

Integrations should preserve source, timestamp, scope, freshness, and coverage information. An inventory finding, a version associated with a vulnerable package, and actual runtime exposure are different claims. An external security-product finding must not automatically be treated as verified runtime exposure.

The PHP2Shell AWS deployment methods and independent evaluator use AWS CLI subprocesses and exact deployment/method tags. They are scenario-specific infrastructure and evidence tooling, not a generalized cloud integration or Core Harness. No credentials or raw live AWS evidence are stored in the repository. The evaluator writes account- and resource-scoped output locally under the ignored `docs/evidence/aws/` directory, and live resources are created only by an explicit participant command.

### Future Core Harness

The Core Harness is a future deterministic foundation for execution, authorization, policy, evidence collection, verification, and reporting. It should demonstrate meaningful value beyond ordinary scripting before it is implemented.

The Core Harness should own generic lifecycle and execution concerns, not scenario-specific vulnerability claims or duplicated scenario content. No Core Harness interface or runtime has been implemented or finalized.

### Future chief-of-staff agent

A conceptual future workflow is:

1. A security engineer asks, “Are we impacted by PHP2Shell?”
2. The agent interprets the request and discovers an available scenario.
3. It identifies the authorized environment and permitted scope.
4. It invokes deterministic operations that the human has authorized.
5. It reads evidence and independent evaluations.
6. It reports assessed assets, potential impact, limitations, and unknowns.
7. It requests explicit authorization before remediation or destructive action.

This is an architecture explanation only. No agent framework, MCP server,
scenario registry, autonomous operation, or scenario generator is implemented.

## Environments and execution methods

VulHarness intentionally keeps these dimensions independent.

### Potential environments

- Local Docker containers
- Local virtual machines
- AWS EC2
- AWS ECS
- AWS EKS
- Other Kubernetes environments
- Azure and Google Cloud
- On-premises infrastructure
- CI/CD pipelines

### Potential investigation and execution methods

- Manual investigation
- Deterministic scripted investigation
- Core Harness-driven execution
- Agent-assisted investigation using coding agents such as Claude Code or Codex
- Reusable skills
- MCP/API-assisted investigation
- Cloud inventory discovery
- CSPM/CNAPP security-product enrichment
- Continuous or scheduled assessment

This allows combinations such as manual investigation of a local container, scripted investigation of an EC2 instance, agent-assisted investigation of an EC2 instance, cloud inventory assessment across workloads, or CI/CD evaluation of affected artifacts. Future documentation and implementations should not impose a hierarchy that prevents these combinations.

The local Scenario 1 exercise and the AWS Lab C/D infrastructure/runtime workflow are operational as explicit, participant-run paths. The cloud workflow is intentionally scoped to exact deployment/method tags and is not a general account inventory adapter.

## Scenario 1 deployment model

PHP2Shell Scenario 1 uses neutral lab identifiers across environments:

- Labs A and B are independent local Docker environments.
- Labs C and D are two independent AWS EC2 instances, not two applications on one instance.

Labs own environment configuration; the deterministic checker owns raw runtime validation and version assessment; evaluations own expected-state comparison. Lab names do not encode a finding.

The AWS implementation keeps provider concerns outside the checker:

1. An optional AWS adapter discovers only instances matching approved account, region, scenario, and lab-tag scope.
2. Discovery records instance identity and state but does not infer a PHP runtime.
3. Authenticated Systems Manager transport collects bounded, read-only runtime facts from an instance-local endpoint.
4. Provider-independent assessment logic classifies normalized runtime evidence.
5. The evaluator writes normalized machine-readable evidence; dashboard integration remains a later interface.

Stopped, unreachable, ambiguously tagged, or uninspectable instances remain unknown or inconclusive. The implementation is documented in the [PHP2Shell AWS lab plan](../scenarios/php2shell/labs/aws/README.md), [shared SSM workflow](../scenarios/php2shell/labs/aws/deployment/shared/README.md), and [AWS lifecycle evaluator](../scenarios/php2shell/evals/aws-lifecycle/README.md).

Scenario 2 is reserved for a later multi-container or load-balanced cloud-like application. It must remain a separate scenario expansion rather than being folded into Scenario 1's single-host local and EC2 labs.

## Participant orchestration boundary

The PHP2Shell participant command at `scripts/vulharness-php2shell.py` is a
scenario-facing coordinator, not the future generic Core Harness. It owns
command-line scope validation, operation-specific approval, stable exit codes,
structured output, deployment-identity retention, and delegation to existing
Compose, deployment-wrapper, SSM, checker, and evaluator interfaces.

It does not own PHP advisory semantics, AWS tag filters, GuardDuty release
policy, or evidence comparison. Local and AWS operations remain separate, AWS
methods remain independent, and `--deployment-id` is always forwarded
unchanged to the selected method. Confirmed cleanup preserves the underlying
interactive confirmation and external-dependency boundary. This keeps the
participant journey simple without making PHP2Shell assumptions part of a
provider-independent framework interface.

## Architectural boundaries

- Scenarios own scenario context and references; reusable workflows and skills remain separate and reusable.
- Labs own scenario-specific controlled environments and are separate from the reusable Core Harness.
- Walkthroughs own goal-oriented participant procedures for an environment and method.
- Workflows own reusable security processes.
- Skills own reusable instructions and procedures.
- Checks own concrete evidence collection or verification.
- Evaluations own independent comparison of observed evidence with expected outcomes.
- Integrations own translation to external systems while preserving provenance.
- The future Core Harness owns generic deterministic lifecycle and execution concerns.
- PHP2Shell must not be hardcoded into generic framework interfaces.
- Agent-assisted execution is optional; manual investigations are first-class.
- Configured, expected, and observed behavior must be distinguished.
- Inventory findings, vulnerable versions, and actual runtime exposure must not be conflated.
- Authorization, scope, least privilege, and cleanup are fundamental requirements.
- Evidence must preserve provenance and relevant timestamps.
- Planned capabilities must not be described as implemented functionality.

## Environment and provenance

VulHarness does not distribute intentionally vulnerable applications. Participants may use authorized local or cloud environments, including Docker, virtual machines, EC2, ECS, EKS, and other supported infrastructure. Reproducible setup guidance should identify:

- Target version and configuration
- Image, package, source, or VM provenance
- Host and runtime assumptions
- Authorization, isolation, least-privilege, and network scope
- Evidence provenance and relevant timestamps
- Cleanup and reset procedure

Public vulnerability claims must be checked against vendor advisories, official CVE records, official cloud documentation, or official API/protocol documentation before being presented as facts. Third-party research can supplement those sources but must not independently establish golden expectations.

## Initial metadata contract

The initial `scenario.yaml` contract is intentionally small and descriptive. It includes an ID, title, description, references, available walkthroughs, and status. PHP2Shell additionally records a minimal list of confirmed vulnerability identifiers and advisory links; it does not introduce a version-range or package schema. The contract is documented in the [PHP2Shell scenario README](../scenarios/php2shell/README.md).

This is not yet a formal schema, and no validator should be inferred from the file. Do not over-engineer metadata or interfaces before real walkthrough implementations reveal their requirements.

## Open architectural questions

- Which metadata fields need formal validation after additional scenarios exist?
- What portable evidence format and redaction model are actually needed?
- What check inputs, outputs, and uncertainty states emerge from real walkthroughs?
- What Core Harness behavior demonstrates value beyond ordinary scripting?
- How should optional provider adapters be packaged and tested?
