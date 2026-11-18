# PHP2Shell labs

The `labs/` folder contains the scenario environments and the provider-specific
tools that create, inspect, change, and remove them. It is not the participant
learning sequence; use the [participant guide](../walkthroughs/participant-lab-guide.md)
for that sequence.

## Responsibilities

| Area | Responsibility |
| --- | --- |
| `local/` | Docker Compose Labs A and B for manual inspection, remediation, and reset. |
| `aws/lab-c/` and `aws/lab-d/` | AWS runtime definitions and expected lab-specific configuration. |
| `aws/deployment/` | Independent AWS CLI, CloudFormation, Terraform, and shared SSM operations. |

Choose one AWS provisioning method per deployment. The wrappers create the
tagged VPC, subnet, route table, security group, IAM role/profile, EC2
instances, and volumes for Labs C and D. They do not replace runtime bootstrap,
PHP inspection, or independent evaluation. The shared SSM workflow installs and
starts the approved runtime without SSH or inbound access.

Detailed implementation references remain available:

- [AWS architecture and deployment plan](aws/README.md)
- [Local Lab A](local/lab-a/README.md)
- [Local Lab B](local/lab-b/README.md)
- [AWS CLI wrapper](aws/deployment/cli/README.md)
- [CloudFormation wrapper](aws/deployment/cloudformation/README.md)
- [Terraform wrapper](aws/deployment/terraform/README.md)
- [Shared SSM runtime](aws/deployment/shared/README.md)

## Manual AWS reference

This is a read-only inspection reference. It does not describe a second,
resource-by-resource provisioning procedure.

### Find the deployed resources

Use the AWS Console in the deployment Region and open **EC2 → Instances**.
Filter by the exact deployment tags documented in the [AWS deployment plan](aws/README.md):

- `VulHarnessProject=VulHarness`
- `VulHarnessScenario=php2shell`
- `VulHarnessDeployment=<deployment-id>`
- `VulHarnessDeploymentMethod=<aws-cli|cloudformation|terraform>`
- `VulHarnessLab=lab-c` or `VulHarnessLab=lab-d`
- `VulHarnessOwner=<approved-owner>`

The deployment ID and method are the ownership boundary. Do not infer ownership
from an instance name, age, expiry, or a matching PHP version.

For each matching instance, inspect its VPC, subnet, security group, IAM
instance profile, and state. Then inspect the matching VPC, subnets, route
table, Internet Gateway, volumes, network interfaces, and deployment tags.
The wrappers require exact project, scenario, deployment, method, and ownership
matches before acting.

### Find method-specific resources

- For CloudFormation, open **CloudFormation → Stacks** and locate the stack
  whose name and tags contain the exact deployment ID. The stack is the
  method-specific lifecycle boundary; do not select an unrelated stack.
- For Terraform, use the retained local state directory specified by the
  Terraform documentation and compare its outputs and tags with the exact
  deployment ID. Do not delete state before independent AWS absence
  verification succeeds.
- For AWS CLI, use the wrapper's `status` and `cleanup --dry-run` commands to
  obtain the exact tagged inventory. Do not replace those scoped queries with
  account-wide deletion filters.

### Connect and inspect the runtime

Select the matching EC2 instance, choose **Connect**, select **Session Manager**,
and choose **Connect**. Session Manager requires an online managed instance and
appropriate IAM permissions. It is the approved administration path; do not add
SSH keys or inbound security-group rules.

Inside the session, use the lab's documented Compose project and inspect the
runtime without changing infrastructure:

```bash
sudo docker compose ls
sudo docker compose -f /opt/vulharness/scenarios/php2shell/labs/aws/lab-c/compose.lab-c.yaml ps
sudo docker ps --filter 'label=com.docker.compose.project=vulharness-php2shell-lab-c'
sudo docker compose -f /opt/vulharness/scenarios/php2shell/labs/aws/lab-c/compose.lab-c.yaml exec -T php-fpm php -v
PHP_CONTAINER="$(sudo docker compose -f /opt/vulharness/scenarios/php2shell/labs/aws/lab-c/compose.lab-c.yaml ps -q php-fpm)"
sudo docker inspect "$PHP_CONTAINER" --format '{{.Config.Image}}'
```

For Lab D, substitute `/opt/vulharness/scenarios/php2shell/labs/aws/lab-d/compose.lab-d.yaml`
and the project label `vulharness-php2shell-lab-d`. Use the [Lab C](aws/lab-c/README.md)
or [Lab D](aws/lab-d/README.md) README for the expected project and image.
`php -v` is direct runtime evidence; an image tag or infrastructure success
message alone is not proof of the running PHP binary. Compare the observed
runtime with the evaluator output and record the source, timestamp, SAPI, image
identity, and limitations.

### Cleanup boundary

Cleanup is a destructive wrapper operation, not a manual inspection step.
Review the method-specific dry run, exact tags, dependency blockers, and
GuardDuty guidance before using the required approval and confirmation. Keep
Terraform state until independent absence verification passes. The wrappers do
not modify unrelated resources or account-level GuardDuty settings.
