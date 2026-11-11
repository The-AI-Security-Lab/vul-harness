# PHP2Shell local HTTP version check

This Stage 2 check automates version verification for configured PHP2Shell local labs. One standard-library Python engine powers both interfaces:

- `cli.py` — one-runtime or all-runtime terminal output, with optional JSON
- `dashboard.py` — localhost-only **Hello World 2.0** runtime inventory on port 8081

The checker reads raw PHP version, SAPI, and observation-time facts from each authorized local lab. It does not reuse the PHP application’s CVE conclusions, send exploit probes, modify targets, perform remediation, or assess application exploitability.

## Requirements

- Python 3.9 or later
- At least one configured local PHP lab
- No third-party Python packages

All commands below start from the repository root.

## Configured targets

[`targets.json`](targets.json) is the explicit allowlist used by both the CLI and dashboard:

| Target ID | Purpose | Evidence endpoint |
| --- | --- | --- |
| `lab-a` | First local Docker runtime | `http://127.0.0.1:8080/?inspect=1&format=json` |
| `lab-b` | Second local Docker runtime | `http://127.0.0.1:8082/?inspect=1&format=json` |

The registry is configuration, not network discovery. Each entry must have a unique lowercase ID and a unique endpoint using:

- Plain HTTP and a literal loopback IP address
- An explicit port
- The exact `/` path and `inspect=1&format=json` query
- No credentials, fragment, alternate path, or remote host

To add another authorized local lab, add one `id` and `endpoint` object to `targets.json`. No checker or dashboard source change is required. Invalid, duplicate, hostname-based, or non-loopback targets are rejected before collection.

The endpoint returns only schema version, PHP version, SAPI, and observation timestamp. Collection does not follow redirects and uses strict time and response-size limits.

## Start a lab

For Lab A:

```sh
docker compose -f scenarios/php2shell/labs/local/lab-a/compose.lab-a.yaml up -d --build
```

For Lab B, follow the [Lab B instructions](../../labs/local/lab-b/README.md). The two projects have separate ports, containers, and networks.

## Run the CLI

Check Lab A, which is the default:

```sh
python3 scenarios/php2shell/checks/local-http-version/cli.py
```

Select Lab B explicitly:

```sh
python3 scenarios/php2shell/checks/local-http-version/cli.py --target lab-b
```

Check every configured target independently:

```sh
python3 scenarios/php2shell/checks/local-http-version/cli.py --all
```

Add `--json` to a single-target or all-target command:

```sh
python3 scenarios/php2shell/checks/local-http-version/cli.py --all --json
```

Expected Lab A output includes:

```text
VulHarness PHP2Shell version check
Runtime ID: lab-a
Evidence source: http://127.0.0.1:8080/?inspect=1&format=json
Observed PHP version: 8.4.27
Observed SAPI: fpm-fcgi
CVE-2026-109618: fixed_upstream_version; fixed release 8.4.27
CVE-2026-109619: fixed_upstream_version; fixed release 8.4.27
Application exploitability assessed: no
```

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | All selected comparisons are `fixed_upstream_version` |
| `1` | At least one selected comparison is `potentially_affected_upstream_version` |
| `2` | At least one result is `inconclusive`, with no operational failure |
| `3` | At least one endpoint is unavailable, times out, or returns an HTTP failure |
| `4` | The target registry cannot be loaded or validated |

For `--all`, the highest applicable code is returned. Reports for reachable targets are still produced when another configured target is unavailable.

## Start Hello World 2.0

```sh
python3 scenarios/php2shell/checks/local-http-version/dashboard.py
```

Open [http://127.0.0.1:8081](http://127.0.0.1:8081), then select **Check Runtimes**. The dashboard displays one table row per configured target with the target ID, endpoint, observed PHP version, assessment status, observation timestamp, and evidence details.

The **Remediate** control is intentionally disabled. It communicates the future workflow boundary but has no route or mutation behavior. Updates remain an explicit practitioner action, followed by an independent recheck.

The dashboard:

- Binds only to `127.0.0.1:8081`
- Checks only the validated entries in `targets.json`
- Accepts no target URL or command input
- Escapes collected content before rendering it
- Uses fixed request timeouts and bounded responses
- Has no database, external API, telemetry, analytics, client scripts, or frontend dependencies

Stop the dashboard with `Ctrl+C`.

## Result meaning

- `fixed_upstream_version` — the observed serving version is at or above the [documented fixed release](../../references.md) for its recognized branch.
- `potentially_affected_upstream_version` — the observed serving version is below the documented fixed release; vendor backports are not assessed.
- `inconclusive` — evidence is unavailable, malformed, unsupported, or reports an unexpected SAPI.

These are version-based results. They do not prove vulnerability, non-exploitability, package provenance, vendor backport status, applicable deployment conditions, or successful remediation. The Lab B exercise deliberately distinguishes desired Compose configuration, running container identity, and the runtime observed through HTTP.

## Tests

```sh
cd scenarios/php2shell/checks/local-http-version
python3 -m unittest -v test_checker.py
```

The tests use deterministic in-process evidence and require neither Docker nor network access.

## Cleanup

Stop the dashboard with `Ctrl+C`. Follow the cleanup command in the README for each lab you started. Do not use broad Docker cleanup commands; unrelated local projects are outside this workshop’s scope.
