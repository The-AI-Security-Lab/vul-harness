# PHP2Shell Lab B — Local Docker

> **Technical environment reference.** Follow the canonical [participant lab guide](../../../walkthroughs/participant-lab-guide.md) for the progressive journey, exact lifecycle commands, expected results, reset, cleanup, and troubleshooting.

Lab B is a controlled companion to [Lab A](../lab-a/README.md). It provides an independent Nginx and PHP-FPM environment for comparing desired Compose configuration, running container identity, and the PHP runtime actually serving HTTP requests.

The base configuration references the official upstream `php:8.4.26-fpm-bookworm` image by digest. That upstream version is below the documented PHP 8.4 fixed threshold of `8.4.27`, so the deterministic checker reports `potentially_affected_upstream_version`. This classification does **not** establish that the application is vulnerable or exploitable. No exploit testing is part of this lab.

## Technical configuration

| Property | Value |
| --- | --- |
| Compose project | `vulharness-php2shell-lab-b` |
| Base model | `compose.lab-b.yaml` |
| Update override | `compose.lab-b.update.yaml` |
| Base PHP | Pinned PHP 8.4.26 FPM Bookworm image |
| Update PHP | Pinned PHP 8.4.27 FPM Bookworm image |
| HTTP binding | `127.0.0.1:8082` |
| PHP-FPM port | Internal network only, port 9000 |
| Runtime target ID | `lab-b` |
| Raw evidence endpoint | `http://127.0.0.1:8082/?inspect=1&format=json` |
| Application source | Lab A assets mounted read-only |

The base and update files can be merged to express desired PHP 8.4.27 configuration. Inspecting that merged model does not update a running container and does not establish the serving PHP version.

## Independence from Lab A

Lab B has its own Compose project, containers, and project-scoped networks. Lab A retains the `local-php-app` Compose project identity and publishes `127.0.0.1:8080`; Lab B publishes `127.0.0.1:8082`.

Both labs use service names `web` and `php-fpm`, but their Compose project boundaries keep those services independent. Lab B reuses Lab A's application and Nginx configuration through read-only mounts, avoiding source duplication without allowing container-side modification.

## Safety and isolation

- Use this lab only on a local system you are authorized to operate.
- Do not change the web binding to a public interface.
- Do not add credentials, personal data, production data, or sensitive files.
- The services use read-only root filesystems, dropped capabilities, and `no-new-privileges`.
- Historical software can contain defects beyond this scenario. Keep it isolated and remove it after the workshop.
- Do not use broad Docker cleanup commands; unrelated projects are outside this lab's scope.

VulHarness does not publish the PHP image or an intentionally vulnerable application. Docker retrieves the identified official upstream image only when an operator explicitly runs the participant-guide commands. The registry manifest advertised Linux `amd64` and `arm64/v8` variants among others. Each participant should confirm successful image resolution on their own Docker host.

## State and evidence model

Keep these claims separate:

1. **Desired configuration:** image reference produced by the Compose model.
2. **Running container identity:** image reference and digest reported for the current PHP-FPM container.
3. **Observed serving runtime:** version and SAPI returned through Nginx over HTTP.
4. **Version classification:** deterministic comparison with the documented upstream fixed threshold.
5. **Exploitability:** not assessed by this lab or checker.

The canonical guide owns the before, configuration-only, and after exercise; dashboard use; independent evaluation; reset; and scoped cleanup. Do not infer runtime state from either Compose file alone.

See the [technical reference register](../../../references.md) for authoritative version claims and the [checker documentation](../../../checks/local-http-version/README.md) for target configuration and result interpretation.
