# PHP2Shell reference register

This register documents the two upstream PHP vulnerabilities that the requested PHP2Shell scenario groups together. “PHP2Shell” is VulHarness scenario terminology; the upstream sources identify the issues by their CVE and GHSA identifiers.

The claims below were checked against the PHP Foundation security-release post, the official PHP.net release announcement, and the corresponding `php-src` security advisories. The OpenAI disclosure and checker repository are treated as supplemental defensive-assessment sources, not as substitutes for the upstream advisories.

## Confirmed upstream vulnerabilities

| CVE | Upstream advisory | Title | Upstream patched releases |
| --- | --- | --- | --- |
| [CVE-2026-109618](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w) | [GHSA-w8hw-w9fx-j79w](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w) | RCE via OOM corruption | PHP 8.2.35, 8.3.36, 8.4.27, 8.5.12 |
| [CVE-2026-109619](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp) | [GHSA-6wmf-4rv5-p3rp](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp) | RCE via stale global state | PHP 8.2.35, 8.3.36, 8.4.27, 8.5.12 |

The GHSA advisories explicitly list the affected upstream ranges as `< 8.2.35`, `< 8.3.36`, `< 8.4.27`, and `< 8.5.12` for both vulnerabilities. These ranges describe upstream `php-src` releases; they are not sufficient to classify a distribution package that may contain backported security fixes.

## CVE-2026-109618 — RCE via OOM corruption

### Technical definition

The advisory describes an out-of-memory path in which PHP exits a context before request memory is fully initialized and later request shutdown processes invalid state. The advisory identifies several ways a request may reach OOM within apparent PHP limits, including multipart parsing and application-specific allocations.

### Affected versions and fixed releases

- Affected upstream ranges: `< 8.2.35`, `< 8.3.36`, `< 8.4.27`, and `< 8.5.12`.
- Fixed upstream releases: `8.2.35`, `8.3.36`, `8.4.27`, and `8.5.12`.
- The official PHP.net release announcement states that those releases fix the vulnerability and advises updating. It also states that PHP 8.1 and older no longer receive updates from the PHP project; distributions and LTS vendors may provide backported fixes, and minimal source backports were provided for PHP 7.4, 8.0, and 8.1.

### Preconditions and exposure conditions

The advisory establishes different evidence levels by SAPI and deployment:

- Apache `mod_php` invokes request shutdown even when request startup fails. The advisory reports confirmed unauthenticated RCE over HTTP against `mod_php` with default PHP input and memory limits and normal prefork configurations.
- PHP-FPM is supported by source analysis as susceptible, but the advisory says no complete FPM exploit was demonstrated for the startup-failure path described there. Other application-level OOM paths may still be relevant.
- FrankenPHP is described as likely susceptible to application-independent attacks because it is analogous to `mod_php`; LSAPI is described as likely susceptible to application-specific attacks but unvalidated.
- Exploit reliability depends on the PHP build, extensions, frontend behavior, allocator layout, worker configuration, and request path.

These conditions mean that an affected upstream version is a triage signal, not proof of runtime exposure.

### Patch and mitigation guidance

Updating to a release containing the patch is the only complete mitigation. The advisory describes `memory_limit=-1` as a primary administrative configuration mitigation for the confirmed controllable-OOM path, but explicitly says it is not complete. It also describes conservative request-size and multipart limits, frontend enforcement, input bounds, and carefully scoped container or cgroup limits as risk-reduction measures. The advisory warns against using `RLIMIT_AS` or `RLIMIT_DATA` as a substitute because they can trigger the vulnerable allocation-failure path.

### Non-destructive assessment methods

Without sending exploit probes, a participant can collect:

- The PHP runtime actually serving requests and its SAPI.
- Upstream runtime version, build provenance, package provenance, and vendor patch/backport information.
- Effective `memory_limit`, `post_max_size`, upload and input limits, relevant multipart/request limits, and where each setting is applied.
- Web-server or frontend request-size controls, PHP worker model, process recycling, extensions, and deployment topology.
- Whether the observed deployment is CLI-only, application-serving, or a persistent worker service.
- Relevant vendor or distribution security notices and package changelog evidence.

Do not infer vulnerability status from an `X-Powered-By` or other version banner alone. Do not send OOM, multipart, or other exploit-triggering requests in this manual baseline.

## CVE-2026-109619 — RCE via stale global state

### Technical definition

The advisory describes request-owned global state that survives after request memory is freed. A producer stores request-owned state, a persistent worker retains the reference, the same worker handles another request, and a consumer reads or acts on the stale state before normal request initialization resets it. The advisory identifies use-after-free, memory disclosure, and RCE impact for confirmed cases.

### Affected versions and fixed releases

- Affected upstream ranges: `< 8.2.35`, `< 8.3.36`, `< 8.4.27`, and `< 8.5.12`.
- Fixed upstream releases: `8.2.35`, `8.3.36`, `8.4.27`, and `8.5.12`.
- The same PHP.net release and support caveats apply: PHP 8.1 and older require distribution/LTS-vendor verification or an upgrade path, and a version number does not reveal whether a package contains a backported fix.

### Preconditions and exposure conditions

The advisory requires a producer and consumer across a request boundary, with both requests reaching the same worker. Confirmed or specifically demonstrated cases include:

- PHP 8.5 fatal-error backtrace state when `fatal_error_backtraces` is enabled, forming the basis of the confirmed `mod_php` exploitation.
- Session upload-progress lifecycle state, including a later request handled by the same worker. The advisory says session upload progress is enabled by default; the validated FPM path depends on a suitable application operation.
- Initialization-time diagnostics or other request, extension, or application state, whose applicability depends on the exact producer, consumer, configuration, extensions, and reachable application flow.

The advisory describes `mod_php` as conditionally exposed through early directory configuration and describes conditional FPM reachability when a frontend supplies `PHP_VALUE` or `PHP_ADMIN_VALUE` parameters that produce an early diagnostic. `.user.ini` and FPM pool timing differ. LSAPI is a conditional candidate, while an equivalent early configuration consumer was not established in default FrankenPHP configuration; that does not make an environment immune.

### Patch and mitigation guidance

Updating to a release containing the complete state-reset patch is the only reliable mitigation. The advisory says there is no complete generic configuration mitigation. For PHP 8.5, `fatal_error_backtraces=0` administratively removes the confirmed fatal-backtrace producer but does not cover other state. Disabling `session.upload_progress.enabled` and restarting workers blocks the demonstrated session path but does not cover other lifecycle paths.

### Non-destructive assessment methods

Without triggering fatal errors, upload-progress paths, or exploit probes, a participant can collect:

- The actual SAPI, worker model, worker reuse/recycling behavior, frontend, and request routing.
- Upstream runtime version, build provenance, package provenance, and vendor patch/backport information.
- `fatal_error_backtraces`, `session.upload_progress.enabled`, startup configuration sources, early directory/FPM/frontend overrides, and relevant extensions.
- Whether the application has reachable upload, import, callback, error, serialization, plugin, or extension paths that may create request-owned state.
- Startup logging configuration and historical logs, while treating absence of a log entry as non-proof of safety.
- Vendor or distribution guidance confirming whether the fixed patch is present.

## Upstream releases versus distribution packages

The [official PHP downloads page](https://www.php.net/downloads.php) notes that binaries provided by Linux distributions contain patches added by the build provider, over which the PHP project has no control. The [PHP.net security-release announcement](https://www.php.net/archive/2026.php) says Linux distributions and LTS vendors received the patches in advance and directs users to their vendors; it also documents that PHP 8.1 and older may have vendor backports.

Therefore:

- A runtime version below an upstream fixed release supports a **potentially affected upstream-version** conclusion.
- A vendor package at that version may still contain a backported fix; package provenance and vendor security guidance are required.
- A runtime at or above an upstream fixed release supports a **fixed upstream-version** conclusion for that branch, subject to confirming that the inspected runtime is the one serving requests.
- Neither conclusion establishes actual exposure without SAPI, configuration, worker, request-path, and deployment evidence.

## Evidence state model

The manual evaluation should keep these claims separate:

| Claim | Minimum evidence | What it does not establish |
| --- | --- | --- |
| Software presence | PHP binary, package, process, or serving-runtime evidence | That the target request path uses it |
| Runtime actually in use | SAPI, process/worker, route, or service evidence | That the runtime is the only PHP installation present |
| Potentially affected upstream version | Runtime version and branch compared with the advisory | Vendor backport status or runtime exposure |
| Fixed upstream or vendor package | Fixed upstream release or authoritative vendor backport evidence | That the inspected version is the serving runtime unless deployment linkage is shown |
| Applicable vulnerability conditions | SAPI, configuration, worker, request-path, extension, and application evidence relevant to that advisory | Successful exploitation or code execution |
| Demonstrated exposure | Separate authorized, non-destructive evidence sufficient for the claim | A general guarantee about other deployments |

## Supplemental defensive assessment source

The [OpenAI `php2shell-checker` repository](https://github.com/openai/php2shell-checker) is a useful reference for a version-based defensive assessment approach. Its README describes checking a local installation or advertised website headers, returning `OK`, `POTENTIALLY VULNERABLE`, or `UNKNOWN`, and explicitly warns that headers cannot reveal backported fixes and that even `OK` describes only the advertised version rather than verifying the installation. It also states that the checker does not send exploit probes.

VulHarness does not copy or execute that repository's code. Its limitations reinforce the manual baseline: version inspection is useful triage evidence, not proof of package patch status, actual runtime linkage, applicable conditions, or exposure.

## Source evidence register

- [PHP Foundation security-release post](https://thephp.foundation/blog/2026/10/21/todays-php-security-release-and-how-were-strengthening-php-security/): identifies both CVEs, their high-level technical categories, affected release updates, and the importance of SAPI/deployment context.
- [GHSA-w8hw-w9fx-j79w](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w): `Affected versions`, `Patched versions`, `Summary`, `OOM strategies`, `Susceptibility`, `Mitigation`, `Impact and reliability`, and `CVE ID` sections.
- [GHSA-6wmf-4rv5-p3rp](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp): `Affected versions`, `Patched versions`, `Summary`, `Concrete and candidate cases`, `Mitigation`, `Logging and configuration audit`, `Impact and reliability`, and `CVE ID` sections.
- [PHP.net 2026 release archive](https://www.php.net/archive/2026.php): 21 October security release, fixed releases, distribution/LTS backport guidance, older-branch support caveats, and mitigation notices.
- [PHP downloads](https://www.php.net/downloads.php): installation guidance stating that distribution binaries may contain provider patches beyond upstream PHP source.
- [OpenAI coordinated disclosure](https://openai.com/index/coordinated-disclosure-of-critical-vulnerabilities/): maintainer-led coordinated response context and link to the defensive version checker; not used as the authority for affected ranges or patch status.
- [OpenAI `php2shell-checker`](https://github.com/openai/php2shell-checker): supplemental description of non-exploitative version/header checks and their limitations; not used as the authority for vulnerability definitions.

## Unresolved questions

- Which distribution and LTS vendors provide backported fixes for the specific target package under investigation?
- Which exact deployment/SAPI/configuration combinations should the first manual lab baseline cover?
- What evidence is sufficient to classify an application-specific producer/consumer path for CVE-2026-109619 without exploit execution?
- How should PHP 7.4, 8.0, and 8.1 source backports be represented once their provenance and patch contents are verified for a target environment?
