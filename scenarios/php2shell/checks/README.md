# PHP2Shell checks

The `checks/` folder contains concrete, deterministic evidence collectors and
the shared PHP runtime classification engine. It is separate from `evals/`:
checks observe and normalize evidence; evaluators independently compare that
evidence with expected outcomes.

The current implementation is scenario-specific. It is not a generic VulHarness
plugin or an automatic interface for future scenarios.

## Current check tools

| File | Responsibility | Changes state? |
| --- | --- | --- |
| [`local-http-version/checker.py`](local-http-version/checker.py) | Shared parser and PHP upstream-version classifier used by the CLI and evaluators. | No. |
| [`local-http-version/cli.py`](local-http-version/cli.py) | Reads the configured local HTTP targets and prints runtime evidence and classifications. | No. |
| [`local-http-version/dashboard.py`](local-http-version/dashboard.py) | Serves a localhost-only view over the same configured checks. | No. |
| [`local-http-version/targets.json`](local-http-version/targets.json) | Declares the explicitly allowed local endpoints. | No. |

The checker does not discover arbitrary hosts, modify containers, prove
exploitability, or replace the independent evaluators. The AWS evaluator reuses
the checker engine only after collecting deployment-scoped runtime evidence.

Run the participant-facing CLI from the repository root with Python and the
named local labs available:

```bash
python3 scenarios/php2shell/checks/local-http-version/cli.py --all
```

See the [participant guide](../walkthroughs/participant-lab-guide.md) for the
learning sequence and the [evaluation index](../evals/README.md) for the
independent comparison layer.
