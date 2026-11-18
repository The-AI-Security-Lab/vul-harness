# AWS Lab C/D cumulative evaluations

`evaluations.json` is the versioned evaluation contract for all three independent infrastructure methods. `aws_evaluate.py` is an independent, read-only evaluator: it discovers resources by exact deployment and method tags, queries AWS configuration, records machine-readable JSON evidence, and prints a human-readable summary.

Run infrastructure evaluation:

```bash
export AWS_PROFILE="REPLACE_WITH_YOUR_PROFILE"
export AWS_REGION="us-east-1"
export VULHARNESS_DEPLOYMENT_ID="REPLACE_WITH_DEPLOYMENT_ID"
python3 scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method aws-cli --deployment-id "$VULHARNESS_DEPLOYMENT_ID"
```

If the account contains a protected reference instance, set its account-specific
ID in the local environment variable `VULHARNESS_PROTECTED_INSTANCE_ID`. Do not
write that value into the repository. If it is unset, the resource-independence
check is reported as `SKIP` with `skip_classification=configuration_missing`.

Include SSM, Docker, Compose, and loopback runtime evidence:

```bash
python3 scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method aws-cli --deployment-id "$VULHARNESS_DEPLOYMENT_ID" \
  --include-ssm --phase initial
```

Use `--phase remediated` after the Lab D update and `--phase reset` after restoring the Lab D baseline. The runtime pass includes actual loopback HTTP JSON, SAPI, Compose status, and image evidence; SSM Online alone is never treated as PHP readiness.

Evidence is written locally under the ignored `docs/evidence/aws/<method>/<deployment-id>/` path. These artifacts can contain live account and resource identifiers and must not be committed or uploaded. A missing or unavailable API result is recorded as `FAIL` or `SKIP` with a failure classification; the evaluator does not convert missing evidence into `PASS`.

The public repository contains no live AWS evidence fixtures. Historical live-validation results are summarized in the wiki and decision records; the current regression suite uses offline/mock inputs.

Each result retains the contract `evaluation_id` for compatibility and adds a
unique `result_id`. Deployment-scoped checks use the contract ID directly;
Lab C/D checks use `<evaluation_id>:<lab-id>:<phase>`. The `lab_id` and `phase`
fields are also present explicitly. Summary totals count result records after
this scoping, so a result for Lab C cannot be mistaken for Lab D. GuardDuty
conditional checks use `skip_classification=conditional_guardduty_evidence`;
missing lifecycle artifacts use `skip_classification=coverage_gap`.

Pass a controlled lifecycle manifest to grade recovery and idempotency evidence:

```bash
python3 scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method aws-cli --deployment-id "$VULHARNESS_DEPLOYMENT_ID" \
  --lifecycle-evidence "docs/evidence/aws/aws-cli/$VULHARNESS_DEPLOYMENT_ID/lifecycle.json"
```

Run independent post-cleanup absence verification separately from the healthy-state evaluator:

```bash
python3 scenarios/php2shell/evals/aws-lifecycle/aws_evaluate.py \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --method aws-cli --deployment-id "$VULHARNESS_DEPLOYMENT_ID" --expect-absent
```

`--expect-absent` passes only when exact deployment-tagged EC2, VPC, networking, volume, network-interface, role, and instance-profile inventories are empty. If an unowned VPC endpoint or other external dependency is present in the deployment VPC, the result remains `FAIL` with `failure_classification=BLOCKED_BY_EXTERNAL_DEPENDENCY`, and the command exits 2. It does not delete residual or unrelated resources. Genuine residual resources remain classified as `RESIDUAL_RESOURCES`.

PHP version and remediation results use independently collected loopback HTTP evidence plus the existing deterministic checker. The evaluator still does not assess application exploitability or prove that an upstream version claim covers distribution backports.
