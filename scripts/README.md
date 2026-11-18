# PHP2Shell orchestration command

[`vulharness-php2shell.py`](vulharness-php2shell.py) is the participant-facing
command center for the PHP2Shell scenario. It coordinates the existing Compose projects,
AWS deployment wrappers, SSM runtime workflow, checker, and evaluators. It does
not duplicate PHP advisory logic, AWS ownership filters, or runtime collection.

Run it from the repository root:

```text
python3 scripts/vulharness-php2shell.py <command> --env <local|aws> [scope options]
```

## Command contract

| Command | Local | AWS | Mutating or approval |
| --- | --- | --- | --- |
| `preflight` | Docker daemon and Compose | AWS identity; Terraform toolchain when selected | Read-only |
| `setup` | Start named Lab A/B Compose projects | Deploy both C/D with one selected method, then bootstrap both through shared SSM | Requires `--approve setup` |
| `status` | Named Compose status | Exact deployment status | Read-only |
| `inspect` | HTTP runtime checker | Infrastructure evaluator without SSM runtime collection | Read-only |
| `assess` | Lab B `before`, `config-only`, or `after` evaluator | AWS evaluator with SSM evidence | Read-only collection |
| `dashboard` | Local runtime inventory on `127.0.0.1:8081` | Unsupported | Interactive |
| `remediate` | Lab B update Compose override | Lab D SSM remediation | Requires `--approve remediate` |
| `verify` | HTTP runtime checker | Runtime evaluator or independent absence evaluator | Read-only |
| `reset` | Lab B baseline Compose | Lab D SSM reset | Requires `--approve reset` |
| `cleanup` | One named Compose project | Exact deployment wrapper cleanup | Dry-run or `--approve cleanup` |

AWS infrastructure commands require `--method aws-cli`, `cloudformation`, or
`terraform`. They also require the explicit `--profile` and `--region` values
when those differ from the defaults. AWS setup creates or resumes only the
deployment ID passed with `--deployment-id`; a generated ID is retained in the
ignored `.vulharness-orchestration/deployments/` metadata directory.

AWS `setup` stops after infrastructure validation and then invokes the shared
SSM bootstrap independently for Lab C and Lab D. A bootstrap failure is
reported as a partial operation; rerun with the same deployment ID after
checking `status`.

The AWS wrappers remain the authority for exact ownership tags, resumability,
dependency-aware cleanup, interactive `DELETE <deployment-id>` confirmation,
GuardDuty external-dependency blocking, and bounded AWS waiters/polling. The
orchestrator never supplies a generic `--yes`, broad deletion filter, SSH key,
or credential value.

## Exit codes

- `0`: requested operation completed successfully.
- `1`: an invoked component failed or reported an ordinary failed evaluation.
- `2`: invalid, incompatible, or insufficiently scoped command.
- `3`: a required local executable or prerequisite is unavailable.
- `4`: a partial/unhealthy or externally blocked AWS state was reported.

The command prints JSON only when `--output json` is requested. Confirmed AWS
cleanup remains text-only so the underlying confirmation prompt is visible and
interactive. Interrupted or failed operations retain the deployment ID in the
error path; inspect with `status`, then use the exact wrapper cleanup dry-run.
