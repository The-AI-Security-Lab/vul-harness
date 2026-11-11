# PHP2Shell Lab A — Local Docker

> **Technical environment reference.** Follow the canonical [participant lab guide](../../../walkthroughs/participant-lab-guide.md) for the progressive journey, expected results, reset, cleanup, and troubleshooting.

## Purpose

Lab A provides a small, reproducible local web environment for the [PHP2Shell scenario](../../../README.md). It helps practitioners distinguish the PHP runtime installed in a container from the PHP-FPM runtime actually serving an HTTP request, collect relevant configuration evidence, compare an observed upstream version with the two documented advisories, and record an independent assessment.

The Compose model explicitly retains the legacy project identity `local-php-app` so containers created before the directory migration can be reconciled without silently changing project ownership. The directory and participant-facing identifier are Lab A.

The lab does not contain an intentionally vulnerable PHP release, send exploit probes, demonstrate remote code execution, or prove actual vulnerability exposure. It is a controlled evidence-collection environment, not the reusable Core Harness and not a substitute for vendor patch-provenance review.

## Project attribution

**VulHarness — An open-source project by AI Security Lab**

- [AI Security Lab](https://www.aisecuritylab.com)
- [VulHarness GitHub](https://github.com/The-AI-Security-Lab/vul-harness) — project repository.

## Prerequisites

- Docker CLI
- Docker Compose v2 (`docker compose`)
- A running Docker engine

On macOS, [Colima](https://github.com/abiosoft/colima) is supported. Start Colima with the resources appropriate for your machine before using Docker Compose.

The lab uses the official `php:8.4.27-fpm-bookworm` image. PHP 8.4.27 is an upstream fixed release for both PHP2Shell advisories. The Compose file pins the current multi-platform image index digest (`sha256:b75642e8c89c321039f351466134df951576fb0f7017117b3931e9a19b908d6c`) in addition to the explicit patch-version tag. If the image is refreshed or the digest must be changed, record the new digest and provenance in the investigation evidence.

The Nginx service uses the official `nginx:1.30.6` image with the current manifest digest (`sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703`). Neither service requires cloud credentials, a Docker socket mount, privileged mode, or host filesystem access beyond the read-only application and Nginx configuration mounts.

Compose creates a dedicated `php2shell` internal network for web-to-FPM traffic. Nginx also joins a separate `loopback-access` bridge because the current Colima engine does not forward published ports from containers attached only to an internal network; the only published endpoint remains `127.0.0.1:8080`, and PHP-FPM remains on the internal network without a host port.

## Start

From this directory, run the explicitly named Compose file:

```sh
docker compose -f compose.lab-a.yaml up -d --build
```

The `--build` flag is harmless for this image-only Compose project and keeps the command consistent with future lab extensions.

## Inspect in a browser

Open [http://127.0.0.1:8080](http://127.0.0.1:8080). The page displays a minimal PHP Hello World application. Select **Inspect Runtime** to display evidence collected from the PHP runtime serving that HTTP request:

- PHP version
- Server API / SAPI
- Loaded PHP configuration file
- Memory limit
- File uploads status
- Session upload progress status
- UTC observation timestamp

The page separately shows an upstream-version assessment for CVE-2026-109618 and CVE-2026-109619. It intentionally labels application exposure as **Not independently verified**.

### Inspect and reset controls

**Inspect Runtime** is a read-only diagnostic request. Inspection results appear only when the URL contains the exact query parameter `inspect=1`; other values such as `inspect=3`, `inspect=anything`, or an empty value leave the page in its initial Hello World state.

When results are visible, **Reset Test** is a keyboard-accessible link back to `/`. It clears the inspection view and removes `inspect=1` from the URL, but does not restart containers, change PHP configuration, modify application files, delete evidence, or clear Docker volumes. A new inspection can be started immediately afterward.

The page reports self-observed runtime information from the PHP process serving the request. That diagnostic output is evidence to collect and review, not an independent security verdict; authoritative package provenance, deployment conditions, and exposure still require separate investigation.

This diagnostic endpoint is intentionally exposed inside a controlled local training lab. Do not copy it into a production application without appropriate authentication, authorization, data-minimization, and operational security controls.

### Raw runtime facts for Stage 2

The deterministic [Stage 2 local HTTP version check](../../../checks/local-http-version/README.md) reads raw runtime facts from:

```text
http://127.0.0.1:8080/?inspect=1&format=json
```

The JSON body contains only `schema_version`, `php_version`, `sapi`, and `observed_at`. It intentionally excludes configuration details, CVE classifications, and vulnerability conclusions. The existing HTML **Inspect Runtime** and **Reset Test** behavior is unchanged.

For the 90-minute workshop, use the [Stage 1 evidence-report template](../../../walkthroughs/local/manual-investigation/stage-1-evidence-report.md). It records discovery, comparison with authoritative fixed-version guidance, the remediation decision, verification of the current PHP-FPM runtime and image identity, limitations, and cleanup. The current PHP 8.4.27 lab is a fixed-version verification target; it must not be described as having been updated during the workshop unless an actual before/after transition was observed.

## Independent terminal verification

The following commands inspect the actual `php-fpm` Compose service without running application commands or exploit probes:

```sh
docker compose -f compose.lab-a.yaml ps
docker compose -f compose.lab-a.yaml exec -T php-fpm php --version
docker compose -f compose.lab-a.yaml exec -T php-fpm php -r 'echo php_sapi_name(), PHP_EOL;'
docker compose -f compose.lab-a.yaml exec -T php-fpm php --ini
docker compose -f compose.lab-a.yaml exec -T php-fpm php -r 'foreach (array("memory_limit", "file_uploads", "session.upload_progress.enabled") as $name) { echo $name, "=", ini_get($name), PHP_EOL; }'
```

Inspect container identity and state:

```sh
PHP_CONTAINER="$(docker compose -f compose.lab-a.yaml ps -q php-fpm)"
docker inspect "$PHP_CONTAINER" --format '{{.Config.Image}}'
docker inspect "$PHP_CONTAINER" --format '{{.Image}}'
docker inspect "$PHP_CONTAINER" --format '{{.State.Status}} started={{.State.StartedAt}}'
```

The first inspect value should include the explicit PHP tag and pinned digest. The second value is the content-addressed image ID used by the running container. Record both values where available.

## Evidence collection

Record:

- UTC observation timestamp
- Browser-observed PHP version and SAPI from the HTTP request
- Terminal-observed PHP version and CLI SAPI from the PHP-FPM image
- Loaded configuration and relevant effective settings
- Container image reference, image ID/digest, and container state
- Application and network scope
- The [PHP2Shell advisory references](../../../references.md)
- The assessment state for each CVE and the uncertainty that remains

Keep software presence, runtime actually in use, potentially affected upstream version, applicable advisory conditions, and demonstrated exposure as separate claims. A version string does not establish distribution backports, runtime linkage, or exploitability.

## Limitations

- The initial lab uses a fixed upstream PHP release and does not demonstrate exploitation.
- Runtime inspection alone does not prove vulnerability, applicability, or exploitability.
- Version-based findings require advisory interpretation and package patch-provenance review.
- The lab uses PHP-FPM behind Nginx; its observations do not represent every PHP SAPI, worker model, frontend, or deployment.
- A locally reachable application is not equivalent to an internet-exposed deployment.
- The `loopback-access` bridge is present for Docker-engine port-forwarding compatibility and should not be treated as an egress-control boundary; the published HTTP endpoint is still restricted to `127.0.0.1`.
- The application does not inspect distribution package metadata or vendor backport records.

## Cleanup

Stop and remove the lab containers and dedicated network with:

```sh
docker compose -f compose.lab-a.yaml down
```

The Compose file does not create named volumes or persistent application data. The downloaded images remain in the local Docker cache; remove them separately only if you intentionally want to reclaim that cache space.
