# VulHarness

VulHarness is an open-source AI Security Lab community project for building,
running, and independently evaluating authorized vulnerability investigation
and response workflows. It does not distribute intentionally vulnerable
applications.

## Current public branches

The public project foundation is maintained on `main`. The complete PHP2Shell
workshop implementation is being validated separately on the
[`stage1-nov-26-workshop` branch](https://github.com/The-AI-Security-Lab/vul-harness/tree/stage1-nov-26-workshop)
and will remain separate until human participant acceptance is complete.

The workshop branch contains the participant guide, local and optional AWS
labs, deterministic checks, independent evaluations, orchestration code, tests,
architecture documentation, and scenario-development methodology.

## Project principles

- Authorized testing only, with explicit scope and least privilege.
- Reproducible investigations with evidence provenance and cleanup guidance.
- Independent evaluation of observable evidence and expected outcomes.
- No credentials, private data, or raw live infrastructure evidence in public
  contributions.
- No distribution of intentionally vulnerable applications.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution boundaries and the
pull-request process. Security concerns should follow [SECURITY.md](SECURITY.md).

## License

VulHarness is licensed under the [Apache License, Version 2.0](LICENSE).
