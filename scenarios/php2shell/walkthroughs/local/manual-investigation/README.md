# PHP2Shell — local manual investigation

This walkthrough is a four-stage, participant-facing manual investigation for an authorized local PHP2Shell lab. It does not require an agent, workflow engine, cloud service, or provider integration.

Do not use this walkthrough against a system without explicit authorization. VulHarness does not distribute an intentionally vulnerable application; the participant is responsible for obtaining or provisioning an isolated environment from an appropriate source.

The current baseline is evidence-first. It does not require exploit execution, remote code execution, OOM triggering, crafted uploads, fatal errors, or other exploit probes. Actual terminal commands and expected outputs will be developed and validated interactively in a later project-owner task.

## Using the local application lab

[Local Lab A](../../../labs/local/lab-a/README.md) is an available environment for this walkthrough. It runs Nginx and PHP-FPM as separate services and provides a minimal HTTP application with an **Inspect Runtime** view.

Use the lab to compare three observations:

- **PHP CLI inspection:** the PHP binary and configuration visible to a terminal process.
- **PHP-FPM inspection:** the SAPI, configuration, worker, and image identity of the runtime serving the application.
- **HTTP-served application inspection:** the evidence returned by the actual PHP-FPM request path behind Nginx.

These can differ because a host may have multiple PHP installations, a web server may use a different SAPI or configuration source, and a container or distribution package may have different provenance or backported fixes. The lab's version assessment is an upstream-version signal only. Vulnerability applicability, vendor patch status, and independent exposure verification remain manual evaluation tasks.

## Stage 1 workshop exercise

The initial 90-minute workshop focuses on **Discover → Compare → Remediation Decision → Verify → Record Evidence**. Use the [Stage 1 evidence-report template](stage-1-evidence-report.md) to record the lab scope, HTTP-serving runtime, PHP-FPM image identity, authoritative fixed-version comparison, remediation decision, verification result, limitations, and cleanup.

The workshop uses the existing PHP 8.4.27 local lab as a fixed-version verification target. A supplied before-remediation fixture may be used for the comparison exercise, but it must be clearly labeled as teaching evidence and must not be presented as an observation from the running lab. The workshop does not claim that an update occurred unless a before/after transition was actually observed and recorded.

| Time | Activity |
| --- | --- |
| 0–10 min | Introduction, advisory context, authorization, and lab setup |
| 10–25 min | Discover browser, HTTP-serving SAPI, terminal runtime, and container identity |
| 25–40 min | Compare observed evidence with authoritative fixed-version guidance |
| 40–50 min | Review before-remediation evidence and determine the remediation decision |
| 50–70 min | Verify the fixed runtime and image identity |
| 70–85 min | Complete the evidence report |
| 85–90 min | Findings, limitations, and cleanup |

## Stage 1 — Set up an isolated local lab

Establish the authorization, scope, and safety boundary before interacting with the target.

Document:

- The system or image being used and why its use is authorized
- Whether the lab uses Docker, an existing image, a virtual machine, or another local environment
- Target version, configuration, image/package/source/VM provenance, and host assumptions
- Network exposure, least-privilege settings, and isolation controls
- The evidence retention, reset, and cleanup plan

Collect evidence that identifies the environment without including secrets or private data. If the target cannot be isolated, its provenance cannot be established, or the scope is unclear, record that uncertainty and stop or narrow the investigation.

Expected outcome: the participant can explain what is in scope, why it is authorized, how it is isolated, what is configured, and how it will be cleaned up.

## Stage 2 — Discover whether PHP is installed and identify runtime information

Determine whether PHP is installed and which PHP runtime is actually relevant to the target. Treat CLI PHP, a web-server module, PHP-FPM, and other SAPIs as potentially different runtimes.

Collect read-only evidence, where available, for:

- Whether PHP is present as a binary, package, process, service, module, or serving runtime
- The runtime version and build information
- The executable, package, module, or installation location
- The SAPI and the request path that uses it
- The configured and loaded configuration sources
- Extensions, worker model, process reuse, and deployment details relevant to request handling
- The command, observation, timestamp, or artifact supporting each fact

Record both the upstream PHP version and the distribution package identity. A distribution package may contain a security backport while retaining an upstream-looking version number. The [PHP downloads guidance](https://www.php.net/downloads.php) notes that distribution binaries can contain provider patches over which the PHP project has no control.

Do not treat an `X-Powered-By`, `Server`, package, or CLI version banner as definitive proof of the version serving the relevant request path, patch status, or vulnerability exposure. The [supplemental checker reference](https://github.com/openai/php2shell-checker) explicitly treats missing or advertised versions as limited assessment evidence.

Expected outcome: the participant has an evidence-backed inventory of PHP presence, the runtime actually in use, its SAPI, upstream or package version, provenance, and relevant configuration—or a clearly documented reason the inventory is incomplete.

## Stage 3 — Provision the selected PHP runtime if required

Only provision another runtime when the investigation requires a controlled comparison or the current environment does not provide the needed information.

Document:

- Why the additional runtime is needed
- The selected upstream version and configuration
- The image, package, source, or VM provenance
- Whether the runtime is upstream-built or distribution-maintained
- How the runtime is isolated from the host and other systems
- Any configuration changes made for the controlled comparison
- Relevant timestamps and how the runtime will be reset and removed

Use a selected runtime as an experimental control, not as evidence that the target uses that runtime or that a target is exposed. Do not treat a selected upstream version as equivalent to a distribution package with possible backports.

The [PHP2Shell reference register](../../../references.md) documents the two confirmed upstream advisories, their fixed upstream releases, and the configuration and SAPI conditions that still require evidence. This walkthrough intentionally makes no claim that a provisioned runtime is exploitable.

Expected outcome: the selected runtime is reproducible, isolated, and described well enough for another authorized practitioner to understand the comparison.

## Stage 4 — Define and execute golden evaluations

Evaluate evidence independently of any agent or tool conclusion. The baseline should produce one assessment for each vulnerability:

- **Affected:** only when the evidence supports an affected upstream range or an authoritative vendor-package finding and the relevant vulnerability conditions are applicable.
- **Fixed:** when the actual serving runtime is at or above the upstream fixed release, or an authoritative distribution/vendor source confirms a backported fix.
- **Not applicable:** when evidence rules out the relevant PHP execution path or required conditions. PHP absence alone can support this only for the PHP-specific claim; an unknown or unlinked runtime is inconclusive.
- **Inconclusive:** when version, package provenance, serving runtime, SAPI, configuration, worker behavior, request path, or vendor backport status is insufficient to support a conclusion.

Do not use “affected” as a synonym for “version is below the upstream fix.” Keep these claims separate:

1. PHP is present.
2. This PHP runtime is actually serving the relevant requests.
3. The upstream or distribution package version is known.
4. The advisory's conditions are applicable to this deployment.
5. The evidence demonstrates actual exposure.

### Evidence required for CVE-2026-109618

The evaluation should review:

- Actual serving SAPI and worker/deployment path, especially whether Apache `mod_php`, PHP-FPM, FrankenPHP, LSAPI, or another path is involved.
- Upstream or distribution version and patch provenance.
- Effective memory, request-body, multipart, input, upload, frontend, and worker controls relevant to OOM handling.
- Relevant extensions and application/request paths that can allocate significant memory.
- Vendor guidance or package evidence for backported fixes.

The evaluation must not claim actual exposure from version inspection alone. The advisory reports confirmed HTTP RCE against `mod_php`, while describing FPM as source-analysis susceptible without a complete demonstrated FPM exploit for the startup-failure path, and describing FrankenPHP/LSAPI as conditional or unvalidated in the stated ways.

### Evidence required for CVE-2026-109619

The evaluation should review:

- Actual serving SAPI, persistent worker behavior, worker recycling, frontend, and request routing.
- Upstream or distribution version and patch provenance.
- `fatal_error_backtraces`, `session.upload_progress.enabled`, startup configuration sources, early directory or frontend overrides, and relevant extensions.
- Whether relevant application or extension paths can produce request-owned state, diagnostics, fatal interruptions, or later consumers.
- Logs and configuration-audit evidence, while treating absence of a log entry as non-proof of safety.
- Vendor guidance or package evidence for backported fixes.

The evaluation must not claim actual exposure without evidence of the applicable producer/consumer conditions. The advisory requires requests to reach the same worker and distinguishes confirmed cases from conditional candidate cases.

### Evidence required for demonstrated exposure

Demonstrated exposure is a separate claim from software presence, potential affected version, or applicable conditions. Establishing it would require additional authorized evidence tied to the actual deployment, request path, worker, and relevant application/configuration behavior. This baseline does not require or prescribe that evidence, and it does not require exploit execution or remote code execution.

Golden expectations must not be changed simply to match an agent's output. Equivalent safe collection procedures are acceptable, but the reviewer must be able to inspect the evidence and understand its provenance, timestamp, limitations, and uncertainty.

Expected outcome: the participant produces a reviewable result for each CVE with supporting evidence, provenance, relevant timestamps, an assessment state, and an explicit statement of what remains unestablished.

## Evidence and uncertainty

Keep evidence minimal, relevant, and redacted. Record source, provenance, timestamps, versions, package identity, configuration assumptions, SAPI, scope, and environmental limitations. Treat missing evidence as missing evidence; do not silently convert it into a negative finding or a positive claim.

The documented golden evaluations remain expectations that a reviewer can
inspect manually. The deterministic [HTTP version check](../../../checks/local-http-version/README.md)
and narrowly scoped [Lab B remediation lifecycle evaluation](../../../evals/remediation-lifecycle/evaluate.py)
are combined with these components by the canonical [participant lab guide](../../participant-lab-guide.md).
No generalized evaluation runner exists.

## Cleanup

At the end of the walkthrough:

- Remove or reset temporary containers, VMs, runtimes, files, and credentials created for the lab.
- Confirm that test services are no longer exposed.
- Preserve only the redacted evidence required for evaluation.
- Record any cleanup that could not be completed.
