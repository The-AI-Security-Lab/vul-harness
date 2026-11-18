# PHP2Shell Lab C — AWS EC2

Lab C is the AWS fixed-version reference environment. It uses the pinned PHP
8.4.27 FPM Bookworm image on its own EC2 instance and mirrors the runtime
inspection model used by local Lab A.

This directory contains the Compose model only. It is not evidence that an EC2
instance exists or that Docker, PHP, or the serving runtime is ready. The
complete `scenarios/php2shell/labs/` layout must be present on the instance so
the relative read-only application and Nginx mounts resolve.

## Intended environment

- Compose project: `vulharness-php2shell-lab-c`
- Runtime target: loopback `127.0.0.1:8080` on the EC2 host
- Inspection transport: authenticated AWS Systems Manager
- PHP image: pinned upstream PHP 8.4.27 FPM Bookworm image

Keep the inspection endpoint loopback-only. Do not add a public load balancer,
public port mapping, security-group ingress rule, SSH access, or an arbitrary
remote-command path.

## Use and cleanup

Choose exactly one AWS infrastructure method in the [AWS lab plan](../README.md),
then follow the [canonical participant lab guide](../../../walkthroughs/participant-lab-guide.md)
for deployment scope, shared SSM bootstrap, runtime evaluation, reset, and
exact-ID cleanup. CloudFormation and Terraform provision infrastructure; the
shared SSM workflow supplies runtime evidence.

Cleanup must cover this Compose project and every AWS resource owned by the
selected deployment. Review `cleanup --dry-run`, confirm only the exact tagged
targets, perform interactive cleanup only when authorized, and run independent
absence verification. GuardDuty-managed dependencies remain under the documented
account-owner authorization boundary.
