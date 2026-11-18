# PHP2Shell Stage 1 evidence report template

Use this template for the 90-minute workshop exercise:

**Discover → Compare → Remediation Decision → Verify → Record Evidence**

This report is for an authorized local lab. It records what was observed, what was compared with authoritative guidance, what remediation decision was made, and what remains unestablished. It does not require exploit testing and must not claim that an update occurred unless an update was actually observed and documented.

## Report metadata

- Participant:
- Workshop date:
- Report identifier:
- Lab location or project directory:
- Report status: `draft` / `complete`

## 1. Lab scope and authorization

- Authorization basis:
- In-scope systems, containers, images, and endpoints:
- Out-of-scope systems and endpoints:
- Isolation boundary:
- Network exposure:
- Evidence retention and redaction plan:

The supplied local application lab is a controlled system under test. It is not the VulHarness assessment engine and does not establish application exposure by itself.

## 2. Discover

### Discovery timestamp

- UTC discovery timestamp:
- Local timezone, if useful:
- Person or process collecting the evidence:

### HTTP-observed runtime

Record the values shown by the **Inspect Runtime** page.

- URL inspected: `http://127.0.0.1:8080/?inspect=1`
- PHP version observed through HTTP:
- HTTP-serving SAPI:
- Loaded PHP configuration file:
- Memory limit:
- File uploads:
- Session upload progress:
- UTC timestamp shown by the application:

### PHP-FPM container identity

- Compose service:
- Container name or ID:
- Container state:
- Container start time:
- Configured PHP image reference:
- Resolved PHP image ID or digest:
- PHP-FPM host port exposure: expected `none`

### Terminal-observed PHP runtime

Record terminal output separately from the HTTP-served observation. The commands below run from the repository root. Commands run through `docker compose exec ... php` invoke the PHP CLI SAPI inside the PHP-FPM image; they do not replace the HTTP SAPI observation.

- Terminal PHP version:
- Terminal SAPI:
- Loaded configuration output:
- Relevant effective settings:
- Commands used:

```sh
docker compose -f scenarios/php2shell/labs/local/lab-a/compose.lab-a.yaml ps
docker compose -f scenarios/php2shell/labs/local/lab-a/compose.lab-a.yaml exec -T php-fpm php --version
docker compose -f scenarios/php2shell/labs/local/lab-a/compose.lab-a.yaml exec -T php-fpm php -r 'echo php_sapi_name(), PHP_EOL;'
docker compose -f scenarios/php2shell/labs/local/lab-a/compose.lab-a.yaml exec -T php-fpm php --ini
docker compose -f scenarios/php2shell/labs/local/lab-a/compose.lab-a.yaml exec -T php-fpm php -r 'foreach (array("memory_limit", "file_uploads", "session.upload_progress.enabled") as $name) { echo $name, "=", ini_get($name), PHP_EOL; }'
PHP_CONTAINER="$(docker compose -f scenarios/php2shell/labs/local/lab-a/compose.lab-a.yaml ps -q php-fpm)"
docker inspect "$PHP_CONTAINER" --format '{{.Config.Image}}'
docker inspect "$PHP_CONTAINER" --format '{{.Image}}'
```

## 3. Compare

### Authoritative fixed-version reference

- Reference used: [PHP2Shell reference register](../references.md)
- CVE-2026-109618 advisory: [GHSA-w8hw-w9fx-j79w](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w)
- CVE-2026-109619 advisory: [GHSA-6wmf-4rv5-p3rp](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp)
- Branch being compared:
- Authoritative fixed upstream release:
- Source access date:
- Distribution package or vendor backport source, if applicable:

For the supplied lab target, compare the HTTP-observed runtime—not only the CLI output—with the authoritative branch-specific fixed release. A fixed upstream version supports a fixed-version assessment for that runtime comparison; it does not prove non-exploitability or actual application exposure.

### CVE assessments

Use one state for each CVE and explain the evidence:

- `Fixed upstream version`
- `Potentially affected upstream version`
- `Not applicable`
- `Inconclusive`

#### CVE-2026-109618

- Assessment:
- Evidence supporting the assessment:
- Applicable SAPI, configuration, worker, and deployment conditions established:
- Vendor backport status:
- What remains unestablished:

#### CVE-2026-109619

- Assessment:
- Evidence supporting the assessment:
- Applicable SAPI, configuration, worker, and deployment conditions established:
- Vendor backport status:
- What remains unestablished:

## 4. Remediation decision

- Decision: `update required` / `update not required for this target` / `defer pending evidence` / `inconclusive`
- Reasoning:
- Remediation guidance or vendor source:
- Scope of the decision:

### Was an update actually performed?

- Update performed in this lab session: `yes` / `no` / `not observed`
- If yes, target, action, timestamp, and before/after evidence:
- If no or not observed, explain:

The current fixed-version lab may be used as a verification target without claiming that it was updated during the workshop. Do not infer an update event from the fact that the current runtime is fixed.

## 5. Verify

### Current fixed-runtime verification

- HTTP-observed PHP version after the remediation decision:
- HTTP-serving SAPI:
- PHP-FPM container identity:
- PHP image reference:
- PHP image digest or resolved image ID:
- Terminal-observed PHP version:
- Version comparison result:
- PHP-FPM host port exposure:

This section verifies the current serving runtime and its image identity. It does not establish that a remediation transition occurred and does not prove non-exploitability.

## 6. Record evidence

### Evidence sources and commands

List each source with its purpose, timestamp, and whether it is self-reported or independently collected.

| Source or command | Purpose | Timestamp | Evidence type | Notes |
| --- | --- | --- | --- | --- |
| Browser `/?inspect=1` | HTTP-serving runtime evidence | | Self-observed by diagnostic app | |
| `docker compose -f .../compose.lab-a.yaml ps` | Service state and published ports | | Terminal-collected | |
| `docker compose -f .../compose.lab-a.yaml exec ... php --version` | PHP binary version in image | | Terminal-collected | CLI SAPI |
| `docker compose -f .../compose.lab-a.yaml exec ... php --ini` | CLI configuration sources | | Terminal-collected | |
| `docker inspect` | Container/image identity | | Terminal-collected | |
| Official PHP advisory | Fixed release and conditions | | Authoritative reference | |

### Limitations and unresolved questions

- Does the inspected HTTP request definitively represent the intended deployment path?
- Is the package upstream-built or distribution-maintained?
- Are vendor backports present?
- Which SAPI, worker, configuration, extension, and request-path conditions remain unverified?
- What evidence would be needed to make a stronger exposure claim?
- Other limitations or unresolved questions:

Do not convert missing evidence into a negative finding. Do not equate a fixed-version result with proof that the application is not exploitable.

### Cleanup status

- Containers stopped or reset:
- Temporary files and credentials removed:
- Evidence redacted and retained:
- Any cleanup not completed:

## Illustrative before-remediation evidence fixture

> **SUPPLIED TEACHING EVIDENCE — NOT COLLECTED FROM THE RUNNING LAB**

This fixture is an illustrative report input for the workshop. It is not a historical observation, does not describe the current PHP-FPM container, and does not claim that the application was exploitable. No historical version, timestamp, image digest, or provenance is invented here; a facilitator must replace the placeholders with supplied, source-backed evidence or leave them explicitly unavailable.

```text
fixture_status: supplied_before_remediation_teaching_evidence
collected_from_running_lab: false
historical_observation_timestamp: not provided
historical_provenance: not provided
php_version: facilitator-supplied value required
http_serving_sapi: facilitator-supplied value required
image_reference_or_digest: facilitator-supplied value required
assessment: compare only after authoritative source verification
application_exposure: not established
exploit_execution: not performed
update_event: not observed in the running lab
```

When a facilitator supplies a source-verified older PHP version, label it **synthetic teaching evidence** or **supplied evidence**, retain its provenance, and keep it separate from the current fixed-runtime observation. A version comparison alone does not establish exploitability.

## 90-minute workshop sequence

| Time | Activity |
| --- | --- |
| 0–10 min | Introduction, advisory context, authorization, and lab setup |
| 10–25 min | Discover browser, HTTP-serving SAPI, terminal runtime, and container identity |
| 25–40 min | Compare observed evidence with authoritative fixed-version guidance |
| 40–50 min | Review supplied before-remediation evidence and determine the remediation decision |
| 50–70 min | Verify the fixed runtime, HTTP SAPI, PHP-FPM image identity, and host-port boundary |
| 70–85 min | Complete the evidence report, limitations, and unresolved questions |
| 85–90 min | Share findings, state what was not established, and clean up |
