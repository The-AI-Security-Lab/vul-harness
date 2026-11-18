# CloudFormation infrastructure deployment

This is the independent CloudFormation method for PHP2Shell Labs C and D. It creates its own VPC, subnet, Internet Gateway, route table, zero-ingress security group, SSM IAM role/profile, launch templates, and two `t4g.small` ARM64 EC2 instances. It does not reuse the AWS CLI or Terraform deployment.

The stack uses the `cloudformation` deployment-method tag and a unique deployment ID. The shared [SSM runtime workflow](../shared/ssm_runtime.py) and [independent evaluator](../../../../evals/aws-lifecycle/aws_evaluate.py) operate against the method tag and deployment ID.

## Commands

```bash
export AWS_PROFILE="REPLACE_WITH_YOUR_PROFILE"
export AWS_REGION="us-east-1"
export VULHARNESS_DEPLOYMENT_ID="REPLACE_WITH_DEPLOYMENT_ID"
./scenarios/php2shell/labs/aws/deployment/cloudformation/cf-lab.sh deploy

./scenarios/php2shell/labs/aws/deployment/cloudformation/cf-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" status

./scenarios/php2shell/labs/aws/deployment/cloudformation/cf-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" cleanup --dry-run

./scenarios/php2shell/labs/aws/deployment/cloudformation/cf-lab.sh \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --deployment-id "$VULHARNESS_DEPLOYMENT_ID" cleanup
```

Confirmed cleanup requires typing `DELETE <deployment-id>`. If the exact stack VPC contains a verified GuardDuty-managed endpoint, add `--allow-guardduty-cleanup` to the confirmed cleanup command. The wrapper validates that the endpoint, ENI, security group, and VPC have no unrelated consumers, releases only those exact GuardDuty resources, and then deletes the stack. Without the opt-in it refuses to delete. Stack deletion is not independent cleanup verification; run the evaluator after the CloudFormation delete waiter completes.

The method requires the approved AWS CLI profile, `us-east-1`, CloudFormation permissions, EC2/VPC/IAM permissions for the stack, and permission to pass the deployment-owned instance role. It does not use SSH or execute SSM commands during infrastructure deployment.
