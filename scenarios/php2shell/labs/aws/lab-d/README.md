# PHP2Shell Lab D — AWS EC2

Lab D is the AWS investigation and remediation target. It runs on an EC2
instance separate from Lab C. Its base model uses pinned PHP 8.4.26 and its
update override selects pinned PHP 8.4.27, mirroring local Lab B.

This directory contains Compose models only. It is not evidence that an EC2
instance exists, that either image has been deployed, or that a runtime or
vulnerability conclusion has been verified. The complete
`scenarios/php2shell/labs/` layout must be present on the instance so relative
read-only application and Nginx mounts resolve.

## Intended environment

- Compose project: `vulharness-php2shell-lab-d`
- Base PHP image: pinned upstream PHP 8.4.26 FPM Bookworm image
- Update override: pinned upstream PHP 8.4.27 FPM Bookworm image
- Runtime target: loopback `127.0.0.1:8080` on the EC2 host
- Inspection transport: authenticated AWS Systems Manager

The base and update files express desired configuration; merging them does not
update a running container or establish the serving PHP version. Keep the
inspection endpoint loopback-only. Do not add public ingress, SSH, or arbitrary
remote commands.

## Use and cleanup

Choose exactly one AWS infrastructure method in the [AWS lab plan](../README.md),
then follow the [canonical participant lab guide](../../../walkthroughs/participant-lab-guide.md)
for baseline collection, shared SSM remediation, independent evaluation, reset,
and exact-ID cleanup. CloudFormation and Terraform provision infrastructure;
the shared SSM workflow supplies runtime evidence.

Cleanup must cover this Compose project and every AWS resource owned by the
selected deployment. Review `cleanup --dry-run`, confirm only the exact tagged
targets, perform interactive cleanup only when authorized, and run independent
absence verification. GuardDuty-managed dependencies remain under the documented
account-owner authorization boundary.
