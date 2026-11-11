# Security and responsible disclosure

VulHarness is intended for authorized vulnerability assessment, controlled training, and independent evaluation. Its documentation is not permission to test a system, network, application, package, or service.

## Authorized testing boundary

Use VulHarness content only against:

- A local lab that you created or are explicitly authorized to use
- A Docker image, virtual machine, or other environment whose use is permitted
- A system owned by you or covered by clear written authorization
- An authorized EC2, ECS, EKS, Kubernetes, Azure, Google Cloud, on-premises, or CI/CD environment
- A workshop or evaluation environment with defined rules of engagement

Do not probe, exploit, or otherwise test third-party systems without explicit authorization. Do not include real credentials, private customer data, or sensitive production artifacts in a contribution.

Participants are responsible for least privilege, isolation, scope control, provenance and version recording, evidence protection, and cleanup.

## What VulHarness does and does not provide

VulHarness does not distribute intentionally vulnerable applications. Contributors may provide reproducible setup instructions and configuration examples, but those instructions must identify the source and provenance of the environment and remain within an authorized testing context.

The initial repository does not implement executable checks, workflows, skills, integrations, agent orchestration, cloud infrastructure, or the future Core Harness.

## Reporting a security issue in VulHarness

If you identify a security issue in the repository, documentation, metadata, checks, workflows, integrations, or future framework implementation, please report it privately rather than opening a public issue with sensitive details.

The preferred reporting channel is GitHub Private Vulnerability Reporting:
[Report a vulnerability](https://github.com/The-AI-Security-Lab/vul-harness/security/advisories/new).
Repository owners must enable **Private vulnerability reporting** in the
repository's Security and analysis settings before this form is available.

If the private-reporting form is unavailable, do not disclose secrets,
personal data, live target details, or operational exploit material in public
issues, pull requests, or discussions. The repository currently publishes no
email fallback or other unverified reporting address; maintainers must enable
GitHub Private Vulnerability Reporting before accepting confidential reports.
A report should include the affected path or component, a concise impact
description, safe reproduction details, and any suggested mitigation.

## Upstream vulnerability disclosures

If an investigation identifies a previously undisclosed vulnerability in a third-party product, follow that vendor's responsible-disclosure process. Do not use a VulHarness pull request as a substitute for notifying the affected vendor, and do not publish sensitive details before coordinated disclosure is appropriate.

## Out of scope

The following are not appropriate for public VulHarness contributions:

- Testing systems without authorization
- Credentials, tokens, private keys, or personal data
- Unredacted production logs or customer artifacts
- Instructions whose primary purpose is unauthorized access or persistence
- Claims about affected versions, fixed versions, CVEs, or exposure conditions that have not been checked against authoritative sources
