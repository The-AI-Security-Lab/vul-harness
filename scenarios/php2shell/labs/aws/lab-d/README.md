# PHP2Shell Lab D — AWS EC2

> **Implemented scaffold — deployed through the shared AWS workflow**

Lab D is the second PHP2Shell AWS EC2 environment. It runs on an EC2 instance separate from Lab C. Its base model uses the same pinned PHP 8.4.26 image as local Lab B, and its update override selects the pinned PHP 8.4.27 image. The infrastructure methods, shared SSM bootstrap, and runtime evaluator have been live-validated.

The scaffold is not evidence that an EC2 instance exists, that either image has been deployed there, or that any runtime or vulnerability conclusion has been verified.

## Intended environment

- Compose project: `vulharness-php2shell-lab-d`
- Base PHP image: pinned upstream PHP 8.4.26 FPM Bookworm image
- Update override: pinned upstream PHP 8.4.27 FPM Bookworm image
- Nginx endpoint on the EC2 host: `127.0.0.1:8080`
- Application and Nginx assets: shared read-only from `../../local/lab-a/`
- Intended inspection transport: authenticated AWS Systems Manager access

The base and update files are designed to be supplied together when the update is eventually deployed. Static merging does not update a running container and does not establish a serving PHP version.

The full `scenarios/php2shell/labs/` layout must be present on the instance so the relative bind mounts resolve. The endpoint must remain on loopback and must not receive a public load balancer, public port mapping, or security-group ingress rule.

## Prerequisites and cleanup

The approved workshop deployment uses `us-east-1`, Amazon Linux 2023 ARM64, `t4g.small`, encrypted 20-GiB gp3 storage, IMDSv2, zero inbound security-group rules, a dedicated SSM role, exact ownership tags, and a dedicated VPC. Review the [AWS lab plan](../README.md) before provisioning.

Cleanup must cover the Compose project and every AWS resource created for this lab. Use the selected infrastructure method's exact deployment ID, dry-run, confirmation, and independent absence-verification commands. GuardDuty-managed dependencies require the documented account-owner authorization boundary.

See the [AWS EC2 lab plan](../README.md) and the AWS stage in the canonical [Scenario 1 participant guide](../../../walkthroughs/participant-lab-guide.md).
