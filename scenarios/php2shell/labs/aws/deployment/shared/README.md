# Shared SSM runtime workflow

`ssm_runtime.py` is the common runtime deployment path for AWS CLI, CloudFormation, and Terraform infrastructure. It discovers exactly one method-tagged Lab C or Lab D instance, sends a bounded `AWS-RunShellScript` command through Systems Manager, transfers the approved Compose/application assets with SHA-256 verification, installs Docker on Amazon Linux 2023, verifies Docker Compose, and starts the selected workload. Cleanup remains method-specific and must independently verify AWS resource absence; managed VPC dependencies such as GuardDuty endpoints are never modified by the workflow.

It never uses SSH, opens inbound security-group rules, stores credentials on the instance, or targets the protected `php2shell-container` instance.

Examples:

```bash
python3 scenarios/php2shell/labs/aws/deployment/shared/ssm_runtime.py bootstrap \
  --method aws-cli --deployment-id <deployment-id> --lab-id lab-c

python3 scenarios/php2shell/labs/aws/deployment/shared/ssm_runtime.py bootstrap \
  --method aws-cli --deployment-id <deployment-id> --lab-id lab-d

python3 scenarios/php2shell/labs/aws/deployment/shared/ssm_runtime.py remediate \
  --method aws-cli --deployment-id <deployment-id> --lab-id lab-d
```

The evaluator remains separate from this workflow and independently queries AWS, SSM, Docker state, and the loopback runtime endpoint.
