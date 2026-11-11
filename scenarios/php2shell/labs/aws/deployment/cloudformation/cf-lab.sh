#!/usr/bin/env bash

set -Eeuo pipefail
export AWS_PAGER=""

AWS_PROFILE="${AWS_PROFILE:-vul-harness-lab-nov26}"
AWS_REGION="${AWS_REGION:-us-east-1}"
DEPLOYMENT_ID="${VULHARNESS_DEPLOYMENT_ID:-}"
EXPIRES_AT="${VULHARNESS_EXPIRES_AT:-}"
OWNER="${VULHARNESS_OWNER:-workshop}"
DEPLOYMENT_METHOD="cloudformation"
VPC_CIDR="${VULHARNESS_VPC_CIDR:-10.253.0.0/16}"
SUBNET_CIDR="${VULHARNESS_SUBNET_CIDR:-10.253.1.0/24}"
STACK_NAME=""
TEMPLATE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/template.yaml"

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
aws_cli() { aws --profile "$AWS_PROFILE" --region "$AWS_REGION" --no-cli-pager "$@"; }
source "$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../shared" && pwd)/guardduty_cleanup.sh"

usage() {
    cat <<'EOF'
Usage:
  cf-lab.sh deploy
  cf-lab.sh status
  cf-lab.sh cleanup --dry-run
  cf-lab.sh cleanup

Options:
  --profile PROFILE
  --region REGION
  --deployment-id ID
  --expires-at TIMESTAMP
  --owner OWNER
  --allow-guardduty-cleanup
  --dry-run
EOF
}

generate_id() {
    suffix="$(od -An -N4 -tx4 /dev/urandom | tr -d ' \n')"
    DEPLOYMENT_ID="vh-cfn-$(date -u +%Y%m%d%H%M%S)-${suffix:0:8}"
}

generate_expiry() {
    EXPIRES_AT="$(python3 -c 'from datetime import datetime,timedelta,timezone; print((datetime.now(timezone.utc)+timedelta(hours=24)).replace(microsecond=0).isoformat().replace("+00:00","Z"))')"
}

validate_inputs() {
    [ -n "$DEPLOYMENT_ID" ] || die 'deployment ID is required for status/cleanup'
    printf '%s\n' "$DEPLOYMENT_ID" | grep -Eq '^[a-z0-9][a-z0-9-]{0,31}$' || die 'deployment ID has invalid characters'
    [ -n "$EXPIRES_AT" ] || generate_expiry
    printf '%s\n' "$EXPIRES_AT" | grep -Eq '^20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$' || die 'expiration must be UTC ISO-8601'
    STACK_NAME="vulharness-php2shell-cloudformation-$DEPLOYMENT_ID"
    [ "${#STACK_NAME}" -le 128 ] || die 'deployment ID produces an invalid CloudFormation stack name'
}

ami_id() {
    aws_cli ec2 describe-images --owners amazon --filters Name=state,Values=available Name=name,Values='al2023-ami-2023.*-kernel-6.1-arm64' --query 'reverse(sort_by(Images,&CreationDate))[0].ImageId' --output text
}

availability_zone() {
    aws_cli ec2 describe-instance-type-offerings --location-type availability-zone --filters Name=instance-type,Values=t4g.small --query 'sort_by(InstanceTypeOfferings,&Location)[0].Location' --output text
}

stack_exists() { aws_cli cloudformation describe-stacks --stack-name "$STACK_NAME" >/dev/null 2>&1; }

validate_stack_tags() {
    stack_tags="$(aws_cli cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].Tags' --output json)"
    python3 - "$stack_tags" "$DEPLOYMENT_ID" <<'PY'
import json, sys
tags = {item["Key"]: item["Value"] for item in json.loads(sys.argv[1])}
expected = {
    "VulHarnessProject": "VulHarness",
    "VulHarnessScenario": "php2shell",
    "VulHarnessEnvironment": "aws-ec2",
    "VulHarnessDeployment": sys.argv[2],
    "VulHarnessManagedBy": "cloudformation",
    "VulHarnessDeploymentMethod": "cloudformation",
}
for key, value in expected.items():
    if tags.get(key) != value:
        raise SystemExit(f"stack ownership mismatch for {key}: {tags.get(key)!r}")
PY
}

stack_vpc_id() {
    aws_cli cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query 'Stacks[0].Outputs[?OutputKey==`VpcId`].OutputValue | [0]' \
        --output text
}

external_vpc_dependency_ids() {
    vpc_id="$1"
    endpoint_json="$(aws_cli ec2 describe-vpc-endpoints \
        --filters Name=vpc-id,Values="$vpc_id" \
        --query 'VpcEndpoints[].{Id:VpcEndpointId,Tags:Tags}' \
        --output json)"
    python3 - "$endpoint_json" "$DEPLOYMENT_ID" <<'PY'
import json
import sys

endpoints = json.loads(sys.argv[1])
deployment_id = sys.argv[2]
expected = {
    "VulHarnessProject": "VulHarness",
    "VulHarnessScenario": "php2shell",
    "VulHarnessEnvironment": "aws-ec2",
    "VulHarnessDeployment": deployment_id,
    "VulHarnessManagedBy": "cloudformation",
    "VulHarnessDeploymentMethod": "cloudformation",
}
for endpoint in endpoints:
    actual = {tag.get("Key"): tag.get("Value") for tag in endpoint.get("Tags", [])}
    if not all(actual.get(key) == value for key, value in expected.items()):
        print(endpoint.get("Id", "<unknown>"))
PY
}

report_external_vpc_dependencies() {
    vpc_id="$1"
    external_ids="$(external_vpc_dependency_ids "$vpc_id")"
    if [ -n "$external_ids" ]; then
        while IFS= read -r endpoint_id; do
            [ -n "$endpoint_id" ] || continue
            printf 'External VPC dependency (not owned by VulHarness): %s\n' "$endpoint_id" >&2
        done <<< "$external_ids"
    fi
    printf '%s' "$external_ids"
}

deploy() {
    validate_inputs
    ami="$(ami_id)"
    [ -n "$ami" ] && [ "$ami" != None ] || die 'no Amazon Linux 2023 ARM64 AMI found'
    az="$(availability_zone)"
    [ -n "$az" ] && [ "$az" != None ] || die 't4g.small is not offered in the selected region'
    if stack_exists; then
        validate_stack_tags
        printf 'Resuming owned CloudFormation stack %s\n' "$STACK_NAME"
    else
        printf 'Creating CloudFormation stack %s\n' "$STACK_NAME"
    fi
    aws_cli cloudformation deploy \
        --template-file "$TEMPLATE" \
        --stack-name "$STACK_NAME" \
        --capabilities CAPABILITY_NAMED_IAM \
        --parameter-overrides DeploymentId="$DEPLOYMENT_ID" ExpiresAt="$EXPIRES_AT" Owner="$OWNER" AmiId="$ami" VpcCidr="$VPC_CIDR" SubnetCidr="$SUBNET_CIDR" AvailabilityZone="$az" \
        --tags VulHarnessProject=VulHarness VulHarnessScenario=php2shell VulHarnessEnvironment=aws-ec2 VulHarnessDeployment="$DEPLOYMENT_ID" VulHarnessManagedBy=cloudformation VulHarnessDeploymentMethod=cloudformation VulHarnessOwner="$OWNER" VulHarnessExpires="$EXPIRES_AT"
    stack_status="$(aws_cli cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].StackStatus' --output text)"
    case "$stack_status" in
        CREATE_COMPLETE|UPDATE_COMPLETE)
            printf 'CloudFormation stack deployed: %s (%s)\n' "$STACK_NAME" "$stack_status"
            ;;
        *)
            die "CloudFormation stack did not reach a complete state: $STACK_NAME status=$stack_status"
            ;;
    esac
}

status() {
    validate_inputs
    stack_exists || { printf 'Status: INCOMPLETE; stack not found: %s\n' "$STACK_NAME"; return 2; }
    validate_stack_tags
    aws_cli cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].{Status:StackStatus,Outputs:Outputs}' --output table
}

cleanup() {
    validate_inputs
    stack_exists || { printf 'Cleanup target: stack not found: %s\n' "$STACK_NAME"; return 0; }
    validate_stack_tags
    printf 'Exact cleanup target: CloudFormation stack %s\n' "$STACK_NAME"
    vpc_id="$(stack_vpc_id)"
    [ -n "$vpc_id" ] && [ "$vpc_id" != None ] || die "owned stack $STACK_NAME did not report a VPC output"
    external_ids="$(report_external_vpc_dependencies "$vpc_id")"
    if [ "${DRY_RUN:-0}" -eq 1 ]; then
        [ -z "$external_ids" ] || printf 'Cleanup blocker: unowned VPC dependencies remain; they will not be modified.\n'
        printf 'Dry run only: no resources were changed.\n'
        return 0
    fi
    guardduty_release "$vpc_id" || die 'GuardDuty-aware cleanup could not release the exact deployment-VPC dependency'
    [ -t 0 ] || die 'confirmed cleanup requires an interactive terminal'
    printf 'Type DELETE %s to permanently remove only this stack: ' "$DEPLOYMENT_ID"
    read -r confirmation
    [ "$confirmation" = "DELETE $DEPLOYMENT_ID" ] || die 'cleanup confirmation did not match'
    aws_cli cloudformation delete-stack --stack-name "$STACK_NAME"
    aws_cli cloudformation wait stack-delete-complete --stack-name "$STACK_NAME"
    printf 'CloudFormation stack deletion completed: %s\n' "$STACK_NAME"
}

parse_args() {
    COMMAND=""
    DRY_RUN=0
    while [ "$#" -gt 0 ]; do
        case "$1" in
            deploy|status|cleanup) [ -z "$COMMAND" ] || die 'only one command is allowed'; COMMAND="$1" ;;
            --dry-run) DRY_RUN=1 ;;
            --profile) shift; AWS_PROFILE="$1" ;;
            --region) shift; AWS_REGION="$1" ;;
            --deployment-id) shift; DEPLOYMENT_ID="$1" ;;
            --expires-at) shift; EXPIRES_AT="$1" ;;
            --owner) shift; OWNER="$1" ;;
            --allow-guardduty-cleanup) GUARDDUTY_RELEASE_AUTHORIZED=1 ;;
            --help|-h) usage; return 0 ;;
            *) die "unknown argument: $1" ;;
        esac
        shift
    done
    [ -n "$COMMAND" ] || { usage >&2; return 2; }
    if [ "$COMMAND" = deploy ] && [ -z "$DEPLOYMENT_ID" ]; then generate_id; fi
    validate_inputs
    case "$COMMAND" in deploy) deploy ;; status) status ;; cleanup) cleanup ;; esac
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then parse_args "$@"; fi
