# PHP2Shell evaluations

The `evals/` folder contains independent comparisons between collected evidence
and defined expected conditions. Evaluators must not accept a participant,
agent, wrapper, or provider self-report as proof.

## Current evaluators

| Evaluator | Responsibility | Collection boundary |
| --- | --- | --- |
| [`remediation-lifecycle/evaluate.py`](remediation-lifecycle/evaluate.py) | Compares Lab B before, configuration-only, and after states, including read-only Compose/image evidence. | Local Docker runtime and HTTP evidence. |
| [`aws-lifecycle/aws_evaluate.py`](aws-lifecycle/aws_evaluate.py) | Evaluates exact deployment inventory, SSM/runtime evidence, PHP classification, cleanup state, and absence. | Explicit AWS profile, Region, method, and deployment ID. |

The deterministic checker in [`checks/`](../checks/README.md) supplies shared
PHP runtime comparison semantics, but the evaluators retain independent
expected-state and lifecycle logic. A version classification does not establish
application exploitability.

AWS evidence is written locally under the ignored
`docs/evidence/aws/<method>/<deployment-id>/` path. It may contain account and
resource identifiers and must not be committed or uploaded. Offline tests use
mocks and fixtures; they do not claim live AWS execution.

Use the [participant guide](../walkthroughs/participant-lab-guide.md) for the
operational sequence and the [AWS evaluator README](aws-lifecycle/README.md) for
result contracts, phases, lifecycle manifests, and independent absence checks.
