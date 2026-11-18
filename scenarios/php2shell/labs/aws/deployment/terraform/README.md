# Terraform infrastructure deployment

This is the independent Terraform method for PHP2Shell Labs C and D. It creates a separate VPC, subnet, Internet Gateway, route table, zero-ingress security group, SSM IAM role/profile, launch templates, and two `t4g.small` ARM64 EC2 instances. It does not reuse AWS CLI or CloudFormation resources.

Terraform uses local state per deployment. The default state root is `.vulharness-terraform-state/`, which is ignored by Git. Set `VULHARNESS_TERRAFORM_STATE_DIR` or pass `--state-dir` when a different local state location is required. Do not delete state until independent AWS absence verification succeeds.

The wrapper passes `AWS_PROFILE` explicitly to the provider, sets `AWS_SDK_LOAD_CONFIG=1` by default, and supports the standard AWS environment. Set `AWS_PROFILE` and `AWS_REGION` before running commands; credentials are never written to state. This explicit profile/config loading is important in execution environments where AWS CLI can resolve shared credentials but the Terraform provider otherwise stalls at STS initialization.

The method uses the `terraform` deployment-method tag. The shared [SSM runtime workflow](../shared/ssm_runtime.py) and [independent evaluator](../../../../evals/aws-lifecycle/aws_evaluate.py) operate against the method tag and deployment ID.

Terraform requires AWS provider `>= 6.43.0`. That provider natively detects and removes `GuardDutyManaged=true` VPC endpoints and security groups while destroying an `aws_vpc`; the wrapper does not duplicate that deletion. Use `--allow-guardduty-cleanup` as explicit authorization for the provider's scoped cleanup, and ensure the Terraform execution identity has the provider-documented optional `ec2:DescribeVpcEndpoints`, `ec2:DescribeSecurityGroups`, `ec2:DeleteVpcEndpoints`, `ec2:ModifyVpcEndpoint`, and `ec2:DeleteSecurityGroup` permissions.

The validated live toolchain was Terraform `1.17.1` with AWS provider `6.72.0`, as recorded in the lockfile and live evidence. Terraform `1.5.7` was present in one audit environment; its cached provider failed schema initialization with `Unrecognized remote plugin message`, so that environment was not treated as validated. Do not weaken the provider constraint or run `plan`/`apply` until provider initialization succeeds.

Before a participant lifecycle, verify and initialize the provider from this directory without changing the lockfile:

```bash
terraform version
terraform -chdir=scenarios/php2shell/labs/aws/deployment/terraform init -reconfigure
terraform -chdir=scenarios/php2shell/labs/aws/deployment/terraform fmt -check
terraform -chdir=scenarios/php2shell/labs/aws/deployment/terraform validate
```

If initialization still reports a plugin protocol or schema error, use the
validated Terraform toolchain or ask the workshop owner to repair the local
provider cache. Remove only the local `.terraform/` cache when authorized; do
not remove `.terraform.lock.hcl`, deployment state, or evidence. A successful
`validate` is required before `tf-lab.sh deploy`.

## Commands

```bash
export AWS_PROFILE="REPLACE_WITH_YOUR_PROFILE"
export AWS_REGION="us-east-1"
export VULHARNESS_DEPLOYMENT_ID="REPLACE_WITH_DEPLOYMENT_ID"
./scenarios/php2shell/labs/aws/deployment/terraform/tf-lab.sh deploy

./scenarios/php2shell/labs/aws/deployment/terraform/tf-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" status

./scenarios/php2shell/labs/aws/deployment/terraform/tf-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" cleanup --dry-run

./scenarios/php2shell/labs/aws/deployment/terraform/tf-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" cleanup
```

Confirmed cleanup requires typing `DELETE <deployment-id>` and passing `--allow-guardduty-cleanup` when a verified GuardDuty endpoint is present. The wrapper validates the exact VPC and rejects ambiguous or unrelated consumers; the provider then performs its native GuardDuty cleanup during destroy. Terraform destroy output is not independent cleanup verification; run the evaluator after destroy and retain state until resource absence is confirmed.

If `terraform plan` or `apply` stalls at `STS GetCallerIdentity` while AWS CLI STS succeeds, first confirm the profile with `aws sts get-caller-identity`, then run Terraform with the wrapper's explicit profile and `AWS_SDK_LOAD_CONFIG=1`. Use a bounded diagnostic window and inspect both state and an exact AWS inventory before deciding whether a partial apply occurred. Do not claim a live result from `terraform validate` alone. After destroy, retain the state directory until the independent evaluator reports `INF-014 PASS`.

The live validation completed two fresh lifecycle runs with separate state directories. Each passed infrastructure, SSM/Docker/Compose, PHP baseline/remediation/reset, repeatability, GuardDuty-aware destroy, and independent absence verification. The final runtime evaluations were PASS=56, FAIL=0, SKIP=14 for each lifecycle; each post-cleanup absence evaluation was PASS=2, FAIL=0. Raw account and resource artifacts are retained privately and are not published.
