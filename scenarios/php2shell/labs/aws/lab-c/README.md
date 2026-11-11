# PHP2Shell Lab C — AWS EC2

> **Implemented scaffold — deployed through the shared AWS workflow**

Lab C is the first PHP2Shell AWS EC2 environment. It runs on its own EC2 instance with Nginx and PHP-FPM, using the same application assets and pinned PHP 8.4.27 image as local Lab A. The infrastructure methods, shared SSM bootstrap, and runtime evaluator have been live-validated.

The scaffold is not evidence that an EC2 instance exists, that Docker or PHP is running, or that any security conclusion has been verified.

## Intended environment

- Compose project: `vulharness-php2shell-lab-c`
- PHP image: pinned upstream PHP 8.4.27 FPM Bookworm image
- Nginx endpoint on the EC2 host: `127.0.0.1:8080`
- Application and Nginx assets: shared read-only from `../../local/lab-a/`
- Intended inspection transport: authenticated AWS Systems Manager access

The full `scenarios/php2shell/labs/` layout must be present on the instance so the relative bind mounts resolve. The endpoint must remain on loopback and must not receive a public load balancer, public port mapping, or security-group ingress rule.

## Prerequisites and cleanup

The approved workshop deployment uses `us-east-1`, Amazon Linux 2023 ARM64, `t4g.small`, encrypted 20-GiB gp3 storage, IMDSv2, zero inbound security-group rules, a dedicated SSM role, exact ownership tags, and a dedicated VPC. Review the [AWS lab plan](../README.md) before provisioning.

Cleanup must cover the Compose project and every AWS resource created for this lab. Use the selected infrastructure method's exact deployment ID, dry-run, confirmation, and independent absence-verification commands. GuardDuty-managed dependencies require the documented account-owner authorization boundary.

See the [AWS EC2 lab plan](../README.md) and the AWS stage in the canonical [Scenario 1 participant guide](../../../walkthroughs/participant-lab-guide.md).
