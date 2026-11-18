# Architectural decisions

This page records agreed decisions, not operational instructions. Claim categories follow [schema.md](schema.md).

## Scenario and component separation

**Decision:** keep scenarios, labs, walkthroughs, reusable workflows, skills, checks, evaluations, integrations, and the future Core Harness conceptually separate.

**Rationale:** environment configuration, evidence collection, security interpretation, and expected-outcome evaluation evolve independently. Separation prevents PHP2Shell or a provider from becoming hardcoded into reusable interfaces.

Source: [framework architecture](../docs/architecture.md).

## Neutral lab identifiers

**Decision:** Scenario 1 uses Lab A through Lab D and runtime IDs `lab-a` through `lab-d`. Names and participant-facing titles do not encode patched, vulnerable, fixed, or remediation status.

**Rationale:** participants should establish findings from evidence rather than infer them from environment names.

Source: [Scenario 1 registry](../scenarios/php2shell/README.md).

## Scenario 1 environment allocation

**Decision:** Labs A and B are local Docker environments. Labs C and D are two separate AWS EC2 instances. Scenario 2 is reserved for a later multi-container or load-balanced cloud-like application.

**Rationale:** Scenario 1 compares the same single-host workflow across local and EC2 environments without introducing distributed-application behavior prematurely.

## Runtime evidence over deployment intent

**Decision:** serving-runtime evidence is authoritative for the deterministic version observation. Desired Compose configuration and running image identity are corroborating but distinct evidence.

**Rationale:** selecting an update file does not prove that a container was recreated or that a new runtime serves HTTP requests.

Sources: [canonical participant guide](../scenarios/php2shell/walkthroughs/participant-lab-guide.md), [lifecycle evaluation](../scenarios/php2shell/evals/remediation-lifecycle/evaluate.py).

## AWS discovery and inspection boundary

**Decision:** AWS discovery uses approved account/region scope and exact project, scenario, deployment, method, and lab tags. It does not scan every EC2 instance. PHP verification uses authenticated SSM transport to a loopback-only endpoint.

**Rationale:** EC2 inventory is not PHP runtime evidence, and the diagnostic endpoint should not be exposed publicly.

Status: implemented for the AWS lifecycle evaluator and shared SSM workflow; dashboard integration remains a later interface.

Source: [AWS EC2 lab plan](../scenarios/php2shell/labs/aws/README.md).

## AWS infrastructure deployment methods

**Decision:** AWS CLI, CloudFormation, and Terraform are independent infrastructure deployment methods. Participants choose exactly one method and no method reuses resources created by another.

**Decision:** the approved first deployment creates a dedicated VPC and public subnet, two separate Amazon Linux 2023 ARM64 `t4g.small` instances, encrypted 20-GiB gp3 roots, a zero-ingress security group, a dedicated `AmazonSSMManagedInstanceCore` role, required IMDSv2, and exact deployment/expiration tags.

**Rationale:** a dedicated, disposable stack makes ownership and cleanup auditable while avoiding adoption of the existing `php2shell-container` instance or unrelated account resources. Public-subnet egress keeps the first infrastructure method simple; zero inbound rules and loopback-only application binding preserve the lab endpoint boundary.

**Limitation:** infrastructure HEALTHY and SSM Online do not establish Docker, Compose, PHP, serving-runtime identity, or vulnerability exposure. Those claims require the shared SSM workflow and independent evaluator.

Source: [AWS CLI deployment README](../scenarios/php2shell/labs/aws/deployment/cli/README.md).

## Dashboard shape

**Decision:** Hello World 2.0 remains one data-driven inventory, not a set of hardcoded lab cards.

**Rationale:** local and future cloud targets should share normalized evidence presentation while preserving environment-specific metadata and errors.

## One canonical participant guide per scenario

**Decision:** each scenario maintains one progressively extended participant guide. Scenario 1 uses `scenarios/php2shell/walkthroughs/participant-lab-guide.md` as its single self-service journey.

**Rationale:** participants should have one clear starting point that preserves completed exercises, introduces later stages in sequence, and marks planned functionality without fragmenting the journey across environment-specific guides. Lab READMEs remain technical environment references, and the manual-investigation documents remain supporting evidence references rather than separate participant journeys.

The Scenario 1 guide progresses from prerequisites and manual investigation through deterministic automation, remediation and independent verification, the AWS infrastructure/runtime stages, planned agent-assisted workflows, cleanup, and troubleshooting.

Source: [canonical Scenario 1 participant guide](../scenarios/php2shell/walkthroughs/participant-lab-guide.md).

## Wiki role

**Decision:** maintain a small Markdown wiki as derived project knowledge. Repository documentation and participant guides remain authoritative for operational instructions.

**Rationale:** persistent synthesis prevents architectural decisions and unresolved questions from being repeatedly reconstructed from chat history, without adding a database, embeddings, or external service.

Source: [wiki index](index.md) and [Karpathy's LLM Wiki note](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).
