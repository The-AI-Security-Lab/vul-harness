# AWS CLI infrastructure deployment

This method creates the approved PHP2Shell Lab C and Lab D EC2 infrastructure. It does not install Docker, copy the repository, start Compose, inspect PHP, or execute commands through SSM.

Part 1 live validation completed successfully for both Lab C and Lab D. The validation covered EC2 infrastructure and SSM readiness only; it did not establish Docker or PHP runtime readiness.

## Prerequisites and AWS context

The operator must be authorized to create and remove disposable resources in the approved AWS account. The AWS CLI must be installed and a local profile supplied by the operator must be configured with the required least-privilege EC2, VPC, IAM, and SSM permissions.

The default profile and region are:

```bash
export AWS_PROFILE="REPLACE_WITH_YOUR_PROFILE"
export AWS_REGION="us-east-1"
aws configure list --profile "$AWS_PROFILE"
aws sts get-caller-identity --profile "$AWS_PROFILE" --region "$AWS_REGION"
```

Do not store credentials, tokens, or private keys in the repository.

Run from the repository root:

```bash
./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh deploy
```

The script accepts the selected profile and region through flags or environment variables:

```bash
AWS_PROFILE="REPLACE_WITH_YOUR_PROFILE" AWS_REGION="REPLACE_WITH_YOUR_REGION" \
  ./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh deploy
```

Deployment generates a unique ID unless `VULHARNESS_DEPLOYMENT_ID` is supplied. For a new deployment:

```bash
./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh deploy
```

For an interrupted deployment, export the original ID and run `deploy` again:

```bash
export VULHARNESS_DEPLOYMENT_ID="REPLACE_WITH_EXISTING_DEPLOYMENT_ID"
./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh deploy
```

The same ID is safely resumable when existing resources have the expected exact ownership tags and properties. The script discovers resources using the exact VulHarness deployment tags, preserves the existing expiration timestamp, validates resources before reuse, creates only missing resources, and refuses conflicting, ambiguous, incorrectly tagged, or orphaned resources. If Lab C exists without Lab D, Lab C is validated and only Lab D is created; resources are not silently repaired or overwritten.

## Lifecycle commands

```bash
export VULHARNESS_DEPLOYMENT_ID="REPLACE_WITH_DEPLOYMENT_ID"
./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" status

./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" cleanup --dry-run

./scenarios/php2shell/labs/aws/deployment/cli/aws-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" cleanup
```

Confirmed cleanup requires an interactive `DELETE <deployment-id>` confirmation. If the exact VPC contains an isolated GuardDuty-managed endpoint, add `--allow-guardduty-cleanup`; the script validates scope and releases only that endpoint, its dependent ENI, and its unreferenced GuardDuty security group. It then terminates the tagged instances and removes only deployment-owned volumes, route table, Internet Gateway, security group, subnet, VPC, instance profile, and IAM role. Failed operations are reported and the command can be retried.

Cleanup is a manual participant action. Keep the deployment ID, review the dry-run target list, and confirm cleanup after the workshop. EC2, EBS, public IPv4, and related resources can incur AWS charges until they are removed. The full deployment resources for the validated run were user-confirmed deleted, but cleanup command output and independent post-cleanup inventory were not supplied for review; automated cleanup verification is not claimed.

## Infrastructure validation

Deployment validation checks exactly two tagged instances, Lab C/D tags, `t4g.small`, ARM64, Amazon Linux 2023 ARM64, encrypted 20-GiB gp3 roots, IMDSv2 required, no SSH key pair, the dedicated SSM profile, zero security-group ingress rules, and SSM `Online` status. EC2 `instance-running` and `instance-status-ok` waiters are used before SSM polling; network and IAM dependencies use bounded polling.

The completed Part 1 live validation reached `Status: HEALTHY` for both Lab C and Lab D, with encrypted root storage, required IMDSv2, zero inbound security-group rules, and SSM `Online` status.

SSM `Online` is not evidence that Docker, PHP, the serving runtime, or the PHP inspection endpoint is ready.

`status` returns `0` for a healthy infrastructure deployment, `2` for an inspectable partial or unhealthy deployment, and `1` for an inspection or ownership error. A partial deployment is never reported healthy.

`cleanup --dry-run` returns `0` when the exact deployment-owned target set can be inspected, including partial deployments. It performs no deletion. Dependency release, volume availability, and deletion retries are bounded; timeout output includes the deployment ID, affected resource IDs, last observed state, and recovery commands.

Route-table setup uses `create-route` when the deployment route is absent. It uses `replace-route` only for an existing default route already targeting the deployment-owned Internet Gateway, and refuses to replace an unrelated target.

EC2 `run-instances` receives JSON `TagSpecifications` whose `Tags` entries are objects with `Key` and `Value` fields. The offline regression test validates the exact instance and root-volume payloads for both labs, including hyphenated deployment IDs and UTC expiration timestamps.

## Troubleshooting

- **Missing default route:** A partially created route table may have only its local route. Re-run `deploy` with the same deployment ID. The script creates the missing `0.0.0.0/0` route and refuses to replace an unrelated route.
- **Malformed EC2 `TagSpecifications`:** Each `Tags` entry must be a JSON object containing `Key` and `Value`. Use the repository script after updating it and resume the same deployment; do not adopt unrelated instances.
- **VPC CIDR conflict:** Choose an unused `VULHARNESS_VPC_CIDR` with a new deployment ID. Never reuse an unrelated VPC.
- **Partial deployment:** Run `status` followed by `cleanup --dry-run`. Partial status is inspectable but not healthy and returns `2`; an inspectable cleanup dry-run returns `0`. Resume with the same ID only after reviewing exact ownership tags.
- **Missing deployment ID:** `deploy` generates one. `status`, cleanup, and resume require `--deployment-id` or `VULHARNESS_DEPLOYMENT_ID`.
- **Managed VPC dependency during cleanup:** AWS-managed services such as GuardDuty may create an untagged VPC endpoint inside a newly created VPC. The CLI will not delete or detach an endpoint without matching deployment ownership tags. Inspect the endpoint, coordinate with the account owner, and rerun the exact cleanup only after the unrelated dependency is safely released.

The script does not modify or adopt the existing `php2shell-container` instance.
