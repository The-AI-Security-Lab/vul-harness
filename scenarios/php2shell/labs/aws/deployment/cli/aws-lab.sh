#!/usr/bin/env bash

# VulHarness PHP2Shell AWS infrastructure deployment.
#
# This script creates infrastructure only. It does not install Docker, copy the
# repository, start Compose, inspect PHP, or execute commands through SSM.

set -Eeuo pipefail

export AWS_PAGER=""

AWS_PROFILE="${AWS_PROFILE:-vul-harness-lab-nov26}"
AWS_REGION="${AWS_REGION:-us-east-1}"
DEPLOYMENT_ID="${VULHARNESS_DEPLOYMENT_ID:-}"
EXPIRES_AT="${VULHARNESS_EXPIRES_AT:-}"
EXPIRES_AT_EXPLICIT=0
[ -n "${VULHARNESS_EXPIRES_AT:-}" ] && EXPIRES_AT_EXPLICIT=1
OWNER="${VULHARNESS_OWNER:-workshop}"
VPC_CIDR="${VULHARNESS_VPC_CIDR:-10.254.0.0/16}"
SUBNET_CIDR="${VULHARNESS_SUBNET_CIDR:-10.254.1.0/24}"
SSM_WAIT_ATTEMPTS="${VULHARNESS_SSM_WAIT_ATTEMPTS:-40}"
SSM_WAIT_SECONDS="${VULHARNESS_SSM_WAIT_SECONDS:-15}"
DEPENDENCY_WAIT_ATTEMPTS="${VULHARNESS_DEPENDENCY_WAIT_ATTEMPTS:-20}"
DEPENDENCY_WAIT_SECONDS="${VULHARNESS_DEPENDENCY_WAIT_SECONDS:-5}"
RETRY_ATTEMPTS="${VULHARNESS_RETRY_ATTEMPTS:-5}"
RETRY_SECONDS="${VULHARNESS_RETRY_SECONDS:-3}"

PROJECT="VulHarness"
SCENARIO="php2shell"
ENVIRONMENT="aws-ec2"
MANAGED_BY="aws-cli"
DEPLOYMENT_METHOD="aws-cli"
INSTANCE_TYPE="t4g.small"
ROOT_VOLUME_SIZE="20"
AMI_NAME_PATTERN="al2023-ami-2023.*-kernel-6.1-arm64"
AMI_OWNER="amazon"

VPC_ID=""
SUBNET_ID=""
IGW_ID=""
ROUTE_TABLE_ID=""
SECURITY_GROUP_ID=""
ROLE_NAME=""
INSTANCE_PROFILE_NAME=""
LAB_C_INSTANCE_ID=""
LAB_D_INSTANCE_ID=""
AMI_ID=""

TMP_DIR=""
CLEANUP_FAILURES=0
CLEANUP_LAST_SUCCESS=0
LAST_OBSERVED="none"
EXTERNAL_DEPENDENCY_IDS=""

usage() {
    cat <<'EOF'
Usage:
  aws-lab.sh [options] deploy
  aws-lab.sh [options] status
  aws-lab.sh [options] cleanup --dry-run
  aws-lab.sh [options] cleanup

Options:
  --profile PROFILE         AWS CLI profile (default: vul-harness-lab-nov26)
  --region REGION           AWS region (default: us-east-1)
  --deployment-id ID        Existing deployment ID for status/cleanup/resume
  --expires-at TIMESTAMP    UTC expiry, for example 2026-11-10T23:59:59Z
  --allow-guardduty-cleanup Explicitly authorize verified GuardDuty endpoint cleanup
  --dry-run                 Show cleanup targets without deleting
  --help                    Show this help

Environment overrides:
  AWS_PROFILE, AWS_REGION, VULHARNESS_DEPLOYMENT_ID,
  VULHARNESS_EXPIRES_AT, VULHARNESS_OWNER, VULHARNESS_VPC_CIDR,
  VULHARNESS_SUBNET_CIDR, VULHARNESS_SSM_WAIT_ATTEMPTS,
  VULHARNESS_SSM_WAIT_SECONDS, VULHARNESS_DEPENDENCY_WAIT_ATTEMPTS,
  VULHARNESS_DEPENDENCY_WAIT_SECONDS, VULHARNESS_RETRY_ATTEMPTS,
  VULHARNESS_RETRY_SECONDS

The deploy command creates infrastructure only. Docker, Compose, PHP, and
runtime inspection are intentionally outside this stage.
EOF
}

die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

on_error() {
    status=$?
    if [ "${BASH_SUBSHELL:-0}" -gt 0 ]; then
        exit "$status"
    fi
    if [ "$status" -eq 2 ] && [ "${COMMAND:-}" = "status" ]; then
        exit "$status"
    fi
    if [ -n "${DEPLOYMENT_ID:-}" ]; then
        printf 'ERROR: deployment stopped with status %s.\n' "$status" >&2
        printf 'Affected resource IDs: vpc=%s subnet=%s igw=%s route_table=%s security_group=%s lab_c=%s lab_d=%s\n' \
            "${VPC_ID:-<unknown>}" "${SUBNET_ID:-<unknown>}" "${IGW_ID:-<unknown>}" "${ROUTE_TABLE_ID:-<unknown>}" \
            "${SECURITY_GROUP_ID:-<unknown>}" "${LAB_C_INSTANCE_ID:-<unknown>}" "${LAB_D_INSTANCE_ID:-<unknown>}" >&2
        printf 'Last observed state: %s\n' "${LAST_OBSERVED:-none}" >&2
        printf 'The deployment ID is %s. Inspect it before retrying or cleaning up:\n' "$DEPLOYMENT_ID" >&2
        printf '  VULHARNESS_DEPLOYMENT_ID=%s %s status\n' "$DEPLOYMENT_ID" "$0" >&2
        printf '  VULHARNESS_DEPLOYMENT_ID=%s %s cleanup --dry-run\n' "$DEPLOYMENT_ID" "$0" >&2
    fi
    exit "$status"
}

timeout_report() {
    reason="$1"
    printf 'TIMEOUT: %s\n' "$reason" >&2
    printf 'Deployment ID: %s\n' "${DEPLOYMENT_ID:-<unknown>}" >&2
    printf 'Affected resource IDs: vpc=%s subnet=%s igw=%s route_table=%s security_group=%s lab_c=%s lab_d=%s\n' \
        "${VPC_ID:-<unknown>}" "${SUBNET_ID:-<unknown>}" "${IGW_ID:-<unknown>}" "${ROUTE_TABLE_ID:-<unknown>}" \
        "${SECURITY_GROUP_ID:-<unknown>}" "${LAB_C_INSTANCE_ID:-<unknown>}" "${LAB_D_INSTANCE_ID:-<unknown>}" >&2
    printf 'Last observed state: %s\n' "${LAST_OBSERVED:-none}" >&2
    printf 'Recovery: VULHARNESS_DEPLOYMENT_ID=%s %s status\n' "$DEPLOYMENT_ID" "$0" >&2
    printf 'Recovery: VULHARNESS_DEPLOYMENT_ID=%s %s cleanup --dry-run\n' "$DEPLOYMENT_ID" "$0" >&2
}

retry_aws() {
    label="$1"
    shift
    attempt=1
    while [ "$attempt" -le "$RETRY_ATTEMPTS" ]; do
        if "$@"; then
            return 0
        fi
        if [ "$attempt" -eq "$RETRY_ATTEMPTS" ]; then
            timeout_report "retry limit reached for $label"
            return 1
        fi
        sleep_seconds=$((RETRY_SECONDS * attempt))
        printf 'Retrying %s in %ss (attempt %s/%s)\n' "$label" "$sleep_seconds" "$attempt" "$RETRY_ATTEMPTS" >&2
        sleep "$sleep_seconds"
        attempt=$((attempt + 1))
    done
}

wait_for_subnet_available() {
    attempt=1
    while [ "$attempt" -le "$DEPENDENCY_WAIT_ATTEMPTS" ]; do
        state="$(aws_cli ec2 describe-subnets --subnet-ids "$SUBNET_ID" --query 'Subnets[0].State' --output text 2>/dev/null || true)"
        LAST_OBSERVED="subnet=$SUBNET_ID state=$state"
        [ "$state" = "available" ] && return 0
        sleep "$DEPENDENCY_WAIT_SECONDS"
        attempt=$((attempt + 1))
    done
    timeout_report "subnet $SUBNET_ID did not become available"
    return 1
}

wait_for_igw_attachment() {
    attempt=1
    while [ "$attempt" -le "$DEPENDENCY_WAIT_ATTEMPTS" ]; do
        state="$(aws_cli ec2 describe-internet-gateways --internet-gateway-ids "$IGW_ID" --query 'InternetGateways[0].Attachments[0].State' --output text 2>/dev/null || true)"
        LAST_OBSERVED="internet_gateway=$IGW_ID attachment_state=$state vpc=$VPC_ID"
        [ "$state" = "available" ] && return 0
        sleep "$DEPENDENCY_WAIT_SECONDS"
        attempt=$((attempt + 1))
    done
    timeout_report "Internet Gateway $IGW_ID did not become available in VPC $VPC_ID"
    return 1
}

wait_for_route_association() {
    attempt=1
    while [ "$attempt" -le "$DEPENDENCY_WAIT_ATTEMPTS" ]; do
        association="$(aws_cli ec2 describe-route-tables --filters Name=association.subnet-id,Values="$SUBNET_ID" --query 'RouteTables[0].RouteTableId' --output text 2>/dev/null || true)"
        LAST_OBSERVED="subnet=$SUBNET_ID route_table_association=$association expected=$ROUTE_TABLE_ID"
        [ "$association" = "$ROUTE_TABLE_ID" ] && return 0
        sleep "$DEPENDENCY_WAIT_SECONDS"
        attempt=$((attempt + 1))
    done
    timeout_report "route table $ROUTE_TABLE_ID was not associated with subnet $SUBNET_ID"
    return 1
}

wait_for_route_disassociation() {
    attempt=1
    while [ "$attempt" -le "$DEPENDENCY_WAIT_ATTEMPTS" ]; do
        association_count="$(aws_cli ec2 describe-route-tables --route-table-ids "$ROUTE_TABLE_ID" --query 'length(RouteTables[0].Associations[?SubnetId!=null])' --output text 2>/dev/null || true)"
        LAST_OBSERVED="route_table=$ROUTE_TABLE_ID subnet_association_count=${association_count:-unknown} expected=0"
        [ "$association_count" = "0" ] && return 0
        sleep "$DEPENDENCY_WAIT_SECONDS"
        attempt=$((attempt + 1))
    done
    timeout_report "route table association for route table $ROUTE_TABLE_ID was not released"
    return 1
}

wait_for_iam_profile() {
    attempt=1
    while [ "$attempt" -le "$DEPENDENCY_WAIT_ATTEMPTS" ]; do
        attached_role="$(aws_cli iam get-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME" --query 'InstanceProfile.Roles[0].RoleName' --output text 2>/dev/null || true)"
        LAST_OBSERVED="instance_profile=$INSTANCE_PROFILE_NAME role=${attached_role:-None} expected=$ROLE_NAME"
        [ "$attached_role" = "$ROLE_NAME" ] && return 0
        sleep "$DEPENDENCY_WAIT_SECONDS"
        attempt=$((attempt + 1))
    done
    timeout_report "IAM role $ROLE_NAME was not visible on instance profile $INSTANCE_PROFILE_NAME"
    return 1
}

wait_for_profile_empty() {
    attempt=1
    while [ "$attempt" -le "$DEPENDENCY_WAIT_ATTEMPTS" ]; do
        attached_role="$(aws_cli iam get-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME" --query 'InstanceProfile.Roles[0].RoleName' --output text 2>/dev/null || true)"
        LAST_OBSERVED="instance_profile=$INSTANCE_PROFILE_NAME role=${attached_role:-None} expected=None"
        [ -z "$attached_role" ] || [ "$attached_role" = "None" ] && return 0
        sleep "$DEPENDENCY_WAIT_SECONDS"
        attempt=$((attempt + 1))
    done
    timeout_report "IAM role was not released from instance profile $INSTANCE_PROFILE_NAME"
    return 1
}

wait_for_role_policy_detached() {
    attempt=1
    while [ "$attempt" -le "$DEPENDENCY_WAIT_ATTEMPTS" ]; do
        policy_count="$(aws_cli iam list-attached-role-policies --role-name "$ROLE_NAME" --query 'length(AttachedPolicies[?PolicyArn==`arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore`])' --output text 2>/dev/null || true)"
        LAST_OBSERVED="role=$ROLE_NAME ssm_policy_count=${policy_count:-unknown} expected=0"
        [ "$policy_count" = "0" ] && return 0
        sleep "$DEPENDENCY_WAIT_SECONDS"
        attempt=$((attempt + 1))
    done
    timeout_report "SSM policy was not released from IAM role $ROLE_NAME"
    return 1
}

wait_for_igw_detached() {
    attempt=1
    while [ "$attempt" -le "$DEPENDENCY_WAIT_ATTEMPTS" ]; do
        attachment_count="$(aws_cli ec2 describe-internet-gateways --internet-gateway-ids "$IGW_ID" --query 'length(InternetGateways[0].Attachments)' --output text 2>/dev/null || true)"
        LAST_OBSERVED="internet_gateway=$IGW_ID attachment_count=${attachment_count:-unknown} expected=0"
        [ "$attachment_count" = "0" ] && return 0
        sleep "$DEPENDENCY_WAIT_SECONDS"
        attempt=$((attempt + 1))
    done
    timeout_report "Internet Gateway $IGW_ID was not detached"
    return 1
}

wait_for_volume_available() {
    volume_id="$1"
    attempt=1
    while [ "$attempt" -le "$DEPENDENCY_WAIT_ATTEMPTS" ]; do
        state="$(aws_cli ec2 describe-volumes --volume-ids "$volume_id" --query 'Volumes[0].State' --output text 2>/dev/null || true)"
        LAST_OBSERVED="volume=$volume_id state=$state expected=available"
        [ "$state" = "available" ] && return 0
        sleep "$DEPENDENCY_WAIT_SECONDS"
        attempt=$((attempt + 1))
    done
    timeout_report "volume $volume_id did not become available"
    return 1
}

wait_for_ec2_ready() {
    if ! aws_cli ec2 wait instance-running --instance-ids "$LAB_C_INSTANCE_ID" "$LAB_D_INSTANCE_ID"; then
        LAST_OBSERVED="lab_c=$LAB_C_INSTANCE_ID lab_d=$LAB_D_INSTANCE_ID running_waiter=failed"
        timeout_report 'EC2 running waiter failed'
        return 1
    fi
    if ! aws_cli ec2 wait instance-status-ok --instance-ids "$LAB_C_INSTANCE_ID" "$LAB_D_INSTANCE_ID"; then
        LAST_OBSERVED="lab_c=$LAB_C_INSTANCE_ID lab_d=$LAB_D_INSTANCE_ID status_ok_waiter=failed"
        timeout_report 'EC2 instance-status-ok waiter failed'
        return 1
    fi
}

trap on_error ERR

require_command() {
    command -v "$1" >/dev/null 2>&1 || die "required command is unavailable: $1"
}

aws_cli() {
    aws --profile "$AWS_PROFILE" --region "$AWS_REGION" --no-cli-pager "$@"
}

source "$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../shared" && pwd)/guardduty_cleanup.sh"

normalize_ids() {
    tr '\t' '\n' | awk 'NF && $0 != "None" { print }'
}

count_lines() {
    awk 'NF { count += 1 } END { print count + 0 }'
}

generate_deployment_id() {
    random_suffix="$(od -An -N4 -tx4 /dev/urandom | tr -d ' \n')"
    DEPLOYMENT_ID="vh-$(date -u +%Y%m%d%H%M%S)-${random_suffix:0:8}"
}

generate_expiry() {
    EXPIRES_AT="$(python3 -c 'from datetime import datetime, timedelta, timezone; print((datetime.now(timezone.utc) + timedelta(hours=24)).replace(microsecond=0).isoformat().replace("+00:00", "Z"))')"
}

validate_inputs() {
    [ -n "$DEPLOYMENT_ID" ] || die "deployment ID is required for this command; pass --deployment-id or VULHARNESS_DEPLOYMENT_ID"
    printf '%s\n' "$DEPLOYMENT_ID" | grep -Eq '^[a-z0-9][a-z0-9-]{0,31}$' || die "deployment ID must match ^[a-z0-9][a-z0-9-]{0,31}$"
    printf '%s\n' "$OWNER" | grep -Eq '^[A-Za-z0-9_.:/=+@-]{1,64}$' || die "owner contains unsupported tag characters"

    if [ -z "$EXPIRES_AT" ]; then
        generate_expiry
    fi
    printf '%s\n' "$EXPIRES_AT" | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$' || die "expiration must be an ISO-8601 UTC timestamp such as 2026-11-10T23:59:59Z"
}

validate_prerequisites() {
    require_command aws
    require_command date
    require_command grep
    require_command awk
    require_command od
    require_command python3
    require_command tr

    profiles="$(aws configure list-profiles 2>/dev/null || true)"
    printf '%s\n' "$profiles" | grep -Fxq "$AWS_PROFILE" || die "AWS profile is not configured: $AWS_PROFILE"

    identity_error="$(mktemp)"
    if ! caller_account="$(aws_cli sts get-caller-identity --query Account --output text 2>"$identity_error")"; then
        message="$(sed -n '1,3p' "$identity_error")"
        rm -f "$identity_error"
        die "AWS authentication failed for profile $AWS_PROFILE in $AWS_REGION: $message"
    fi
    rm -f "$identity_error"
    [ -n "$caller_account" ] && [ "$caller_account" != "None" ] || die "AWS caller identity did not return an account"

    az_count="$(aws_cli ec2 describe-availability-zones --filters Name=state,Values=available --query 'length(AvailabilityZones)' --output text)"
    [ "$az_count" -gt 0 ] || die "no available Availability Zones were returned in $AWS_REGION"

    printf 'Prerequisites: profile=%s region=%s authenticated=yes\n' "$AWS_PROFILE" "$AWS_REGION"
}

common_filters() {
    printf '%s\n' \
        "Name=tag:VulHarnessProject,Values=$PROJECT" \
        "Name=tag:VulHarnessScenario,Values=$SCENARIO" \
        "Name=tag:VulHarnessEnvironment,Values=$ENVIRONMENT" \
        "Name=tag:VulHarnessDeployment,Values=$DEPLOYMENT_ID" \
        "Name=tag:VulHarnessManagedBy,Values=$MANAGED_BY" \
        "Name=tag:VulHarnessDeploymentMethod,Values=$DEPLOYMENT_METHOD"
}

apply_tags() {
    resource_id="$1"
    resource_kind="$2"
    lab_id="${3:-}"
    name="${4:-}"
    tag_args=(
        "Key=VulHarnessProject,Value=$PROJECT"
        "Key=VulHarnessScenario,Value=$SCENARIO"
        "Key=VulHarnessEnvironment,Value=$ENVIRONMENT"
        "Key=VulHarnessDeployment,Value=$DEPLOYMENT_ID"
        "Key=VulHarnessManagedBy,Value=$MANAGED_BY"
        "Key=VulHarnessDeploymentMethod,Value=$DEPLOYMENT_METHOD"
        "Key=VulHarnessOwner,Value=$OWNER"
        "Key=VulHarnessExpires,Value=$EXPIRES_AT"
        "Key=VulHarnessResource,Value=$resource_kind"
    )
    if [ -n "$lab_id" ]; then
        tag_args+=("Key=VulHarnessLab,Value=$lab_id")
    fi
    if [ -n "$name" ]; then
        tag_args+=("Key=Name,Value=$name")
    fi
    aws_cli ec2 create-tags --resources "$resource_id" --tags "${tag_args[@]}"
}

ec2_tag_value() {
    resource_id="$1"
    key="$2"
    aws_cli ec2 describe-tags \
        --filters "Name=resource-id,Values=$resource_id" "Name=key,Values=$key" \
        --query 'Tags[0].Value' --output text
}

validate_ec2_tags() {
    resource_id="$1"
    resource_kind="$2"
    lab_id="${3:-}"
    name="${4:-}"
    expected_tags=(
        "VulHarnessProject=$PROJECT"
        "VulHarnessScenario=$SCENARIO"
        "VulHarnessEnvironment=$ENVIRONMENT"
        "VulHarnessDeployment=$DEPLOYMENT_ID"
        "VulHarnessManagedBy=$MANAGED_BY"
        "VulHarnessDeploymentMethod=$DEPLOYMENT_METHOD"
        "VulHarnessOwner=$OWNER"
        "VulHarnessExpires=$EXPIRES_AT"
        "VulHarnessResource=$resource_kind"
    )
    [ -n "$lab_id" ] && expected_tags+=("VulHarnessLab=$lab_id")
    [ -n "$name" ] && expected_tags+=("Name=$name")
    for expected_tag in "${expected_tags[@]}"; do
        key="${expected_tag%%=*}"
        expected_value="${expected_tag#*=}"
        actual_value="$(ec2_tag_value "$resource_id" "$key")"
        [ "$actual_value" = "$expected_value" ] || die "resource $resource_id has unexpected $key tag: $actual_value"
    done
}

tag_spec() {
    resource_type="$1"
    resource_kind="$2"
    lab_id="$3"
    name="$4"
    python3 - "$resource_type" "$resource_kind" "$lab_id" "$name" \
        "$PROJECT" "$SCENARIO" "$ENVIRONMENT" "$DEPLOYMENT_ID" "$MANAGED_BY" "$DEPLOYMENT_METHOD" "$OWNER" "$EXPIRES_AT" <<'PY'
import json
import sys

(
    resource_type,
    resource_kind,
    lab_id,
    name,
    project,
    scenario,
    environment,
    deployment_id,
    managed_by,
    deployment_method,
    owner,
    expires_at,
) = sys.argv[1:]

tags = [
    {"Key": "VulHarnessProject", "Value": project},
    {"Key": "VulHarnessScenario", "Value": scenario},
    {"Key": "VulHarnessEnvironment", "Value": environment},
    {"Key": "VulHarnessDeployment", "Value": deployment_id},
    {"Key": "VulHarnessManagedBy", "Value": managed_by},
    {"Key": "VulHarnessDeploymentMethod", "Value": deployment_method},
    {"Key": "VulHarnessOwner", "Value": owner},
    {"Key": "VulHarnessExpires", "Value": expires_at},
    {"Key": "VulHarnessResource", "Value": resource_kind},
]
if lab_id:
    tags.append({"Key": "VulHarnessLab", "Value": lab_id})
if name:
    tags.append({"Key": "Name", "Value": name})

print(json.dumps({"ResourceType": resource_type, "Tags": tags}, separators=(",", ":")))
PY
}

find_vpc() {
    ids="$(aws_cli ec2 describe-vpcs --filters $(common_filters | tr '\n' ' ') 'Name=tag:VulHarnessResource,Values=vpc' --query 'Vpcs[].VpcId' --output text | normalize_ids)"
    count="$(printf '%s\n' "$ids" | count_lines)"
    [ "$count" -le 1 ] || die "more than one owned VPC has deployment ID $DEPLOYMENT_ID"
    VPC_ID="$(printf '%s\n' "$ids" | sed -n '1p')"
}

find_subnet() {
    ids="$(aws_cli ec2 describe-subnets --filters $(common_filters | tr '\n' ' ') 'Name=tag:VulHarnessResource,Values=public-subnet' --query 'Subnets[].SubnetId' --output text | normalize_ids)"
    count="$(printf '%s\n' "$ids" | count_lines)"
    [ "$count" -le 1 ] || die "more than one owned public subnet has deployment ID $DEPLOYMENT_ID"
    SUBNET_ID="$(printf '%s\n' "$ids" | sed -n '1p')"
}

find_igw() {
    ids="$(aws_cli ec2 describe-internet-gateways --filters $(common_filters | tr '\n' ' ') 'Name=tag:VulHarnessResource,Values=internet-gateway' --query 'InternetGateways[].InternetGatewayId' --output text | normalize_ids)"
    count="$(printf '%s\n' "$ids" | count_lines)"
    [ "$count" -le 1 ] || die "more than one owned Internet Gateway has deployment ID $DEPLOYMENT_ID"
    IGW_ID="$(printf '%s\n' "$ids" | sed -n '1p')"
}

find_route_table() {
    ids="$(aws_cli ec2 describe-route-tables --filters $(common_filters | tr '\n' ' ') 'Name=tag:VulHarnessResource,Values=route-table' --query 'RouteTables[].RouteTableId' --output text | normalize_ids)"
    count="$(printf '%s\n' "$ids" | count_lines)"
    [ "$count" -le 1 ] || die "more than one owned route table has deployment ID $DEPLOYMENT_ID"
    ROUTE_TABLE_ID="$(printf '%s\n' "$ids" | sed -n '1p')"
}

find_security_group() {
    ids="$(aws_cli ec2 describe-security-groups --filters $(common_filters | tr '\n' ' ') 'Name=tag:VulHarnessResource,Values=security-group' --query 'SecurityGroups[].GroupId' --output text | normalize_ids)"
    count="$(printf '%s\n' "$ids" | count_lines)"
    [ "$count" -le 1 ] || die "more than one owned security group has deployment ID $DEPLOYMENT_ID"
    SECURITY_GROUP_ID="$(printf '%s\n' "$ids" | sed -n '1p')"
}

find_instance() {
    lab_id="$1"
    include_terminated="${2:-no}"
    if [ "$include_terminated" = "yes" ]; then
        instance_query='Reservations[].Instances[].InstanceId'
    else
        instance_query='Reservations[].Instances[?State.Name!=`terminated`].InstanceId'
    fi
    ids="$(aws_cli ec2 describe-instances \
        --filters $(common_filters | tr '\n' ' ') \
        "Name=tag:VulHarnessResource,Values=instance" \
        "Name=tag:VulHarnessLab,Values=$lab_id" \
        --query "$instance_query" --output text | normalize_ids)"
    count="$(printf '%s\n' "$ids" | count_lines)"
    [ "$count" -le 1 ] || die "more than one non-terminated owned instance exists for $lab_id"
    if [ "$lab_id" = "lab-c" ]; then
        LAB_C_INSTANCE_ID="$(printf '%s\n' "$ids" | sed -n '1p')"
    else
        LAB_D_INSTANCE_ID="$(printf '%s\n' "$ids" | sed -n '1p')"
    fi
}

find_all_instances() {
    ids="$(aws_cli ec2 describe-instances \
        --filters $(common_filters | tr '\n' ' ') \
        'Name=tag:VulHarnessResource,Values=instance' \
        --query 'Reservations[].Instances[?State.Name!=`terminated`].InstanceId' --output text | normalize_ids)"
    printf '%s\n' "$ids"
}

find_volumes() {
    aws_cli ec2 describe-volumes --filters $(common_filters | tr '\n' ' ') 'Name=tag:VulHarnessResource,Values=volume' --query 'Volumes[].VolumeId' --output text | normalize_ids
}

discover_existing_resources() {
    find_vpc
    find_subnet
    find_igw
    find_route_table
    find_security_group
    find_instance lab-c yes
    find_instance lab-d yes
    VOLUME_IDS="$(find_volumes)"
    ROLE_NAME="vh-php2shell-$DEPLOYMENT_ID-role"
    INSTANCE_PROFILE_NAME="vh-php2shell-$DEPLOYMENT_ID-profile"

    role_exists=0
    profile_exists=0
    aws_cli iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1 && role_exists=1 || true
    aws_cli iam get-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME" >/dev/null 2>&1 && profile_exists=1 || true

    other_resource_ids="$SUBNET_ID$IGW_ID$ROUTE_TABLE_ID$SECURITY_GROUP_ID$LAB_C_INSTANCE_ID$LAB_D_INSTANCE_ID$VOLUME_IDS"
    if [ -z "$VPC_ID" ] && { [ -n "$other_resource_ids" ] || [ "$role_exists" -eq 1 ] || [ "$profile_exists" -eq 1 ]; }; then
        die "deployment $DEPLOYMENT_ID has tagged resources without its owned VPC; refusing to create duplicates"
    fi

    if [ -n "$VPC_ID" ]; then
        existing_expiration="$(ec2_tag_value "$VPC_ID" VulHarnessExpires)"
        [ -n "$existing_expiration" ] && [ "$existing_expiration" != "None" ] || die "owned VPC $VPC_ID is missing its expiration tag"
        if [ "$EXPIRES_AT_EXPLICIT" -eq 1 ] && [ "$EXPIRES_AT" != "$existing_expiration" ]; then
            die "deployment $DEPLOYMENT_ID expiration mismatch: existing=$existing_expiration requested=$EXPIRES_AT"
        fi
        if [ "$EXPIRES_AT_EXPLICIT" -eq 0 ]; then
            EXPIRES_AT="$existing_expiration"
        fi
    fi

    [ -z "$VPC_ID" ] || validate_ec2_tags "$VPC_ID" vpc "" "vulharness-php2shell-$DEPLOYMENT_ID-vpc"
    [ -z "$SUBNET_ID" ] || validate_ec2_tags "$SUBNET_ID" public-subnet "" "vulharness-php2shell-$DEPLOYMENT_ID-public"
    [ -z "$IGW_ID" ] || validate_ec2_tags "$IGW_ID" internet-gateway "" "vulharness-php2shell-$DEPLOYMENT_ID-igw"
    [ -z "$ROUTE_TABLE_ID" ] || validate_ec2_tags "$ROUTE_TABLE_ID" route-table "" "vulharness-php2shell-$DEPLOYMENT_ID-public-route"
    [ -z "$SECURITY_GROUP_ID" ] || validate_ec2_tags "$SECURITY_GROUP_ID" security-group "" "vulharness-php2shell-$DEPLOYMENT_ID-sg"
    [ -z "$LAB_C_INSTANCE_ID" ] || validate_ec2_tags "$LAB_C_INSTANCE_ID" instance lab-c "vulharness-php2shell-lab-c-$DEPLOYMENT_ID"
    [ -z "$LAB_D_INSTANCE_ID" ] || validate_ec2_tags "$LAB_D_INSTANCE_ID" instance lab-d "vulharness-php2shell-lab-d-$DEPLOYMENT_ID"
    for volume_id in $VOLUME_IDS; do
        [ -n "$volume_id" ] || continue
        volume_lab="$(ec2_tag_value "$volume_id" VulHarnessLab)"
        validate_ec2_tags "$volume_id" volume "$volume_lab" "vulharness-php2shell-$volume_lab-$DEPLOYMENT_ID-root"
    done
    [ "$role_exists" -eq 0 ] || role_tags_match || die "IAM role $ROLE_NAME exists but does not have this deployment's ownership tags"
    [ "$profile_exists" -eq 0 ] || profile_tags_match || die "instance profile $INSTANCE_PROFILE_NAME exists but does not have this deployment's ownership tags"
}

ensure_vpc() {
    find_vpc
    if [ -n "$VPC_ID" ]; then
        cidr="$(aws_cli ec2 describe-vpcs --vpc-ids "$VPC_ID" --query 'Vpcs[0].CidrBlock' --output text)"
        [ "$cidr" = "$VPC_CIDR" ] || die "owned VPC $VPC_ID has CIDR $cidr, expected $VPC_CIDR"
        default_vpc="$(aws_cli ec2 describe-vpcs --vpc-ids "$VPC_ID" --query 'Vpcs[0].IsDefault' --output text)"
        [ "$default_vpc" = "False" ] || die "owned deployment VPC cannot be the default VPC"
        dns_support="$(aws_cli ec2 describe-vpc-attribute --vpc-id "$VPC_ID" --attribute enableDnsSupport --query 'EnableDnsSupport.Value' --output text)"
        dns_hostnames="$(aws_cli ec2 describe-vpc-attribute --vpc-id "$VPC_ID" --attribute enableDnsHostnames --query 'EnableDnsHostnames.Value' --output text)"
        [ "$dns_support" = "True" ] || die "owned VPC $VPC_ID does not have DNS support enabled"
        [ "$dns_hostnames" = "True" ] || die "owned VPC $VPC_ID does not have DNS hostnames enabled"
        validate_ec2_tags "$VPC_ID" vpc "" "vulharness-php2shell-$DEPLOYMENT_ID-vpc"
        printf 'VPC: reusing owned %s\n' "$VPC_ID"
    else
        existing_cidr="$(aws_cli ec2 describe-vpcs --filters Name=cidr-block,Values="$VPC_CIDR" --query 'Vpcs[].VpcId' --output text | normalize_ids)"
        [ -z "$existing_cidr" ] || die "VPC CIDR $VPC_CIDR is already in use; choose VULHARNESS_VPC_CIDR explicitly"
        VPC_ID="$(aws_cli ec2 create-vpc --cidr-block "$VPC_CIDR" --query 'Vpc.VpcId' --output text)"
        apply_tags "$VPC_ID" vpc "" "vulharness-php2shell-$DEPLOYMENT_ID-vpc"
        aws_cli ec2 modify-vpc-attribute --vpc-id "$VPC_ID" --enable-dns-support '{"Value":true}'
        aws_cli ec2 modify-vpc-attribute --vpc-id "$VPC_ID" --enable-dns-hostnames '{"Value":true}'
        printf 'VPC: created %s\n' "$VPC_ID"
    fi
}

ensure_subnet() {
    find_subnet
    if [ -n "$SUBNET_ID" ]; then
        subnet_vpc="$(aws_cli ec2 describe-subnets --subnet-ids "$SUBNET_ID" --query 'Subnets[0].VpcId' --output text)"
        subnet_cidr="$(aws_cli ec2 describe-subnets --subnet-ids "$SUBNET_ID" --query 'Subnets[0].CidrBlock' --output text)"
        [ "$subnet_vpc" = "$VPC_ID" ] || die "owned subnet $SUBNET_ID is not in owned VPC $VPC_ID"
        [ "$subnet_cidr" = "$SUBNET_CIDR" ] || die "owned subnet $SUBNET_ID has CIDR $subnet_cidr, expected $SUBNET_CIDR"
        public_ip="$(aws_cli ec2 describe-subnets --subnet-ids "$SUBNET_ID" --query 'Subnets[0].MapPublicIpOnLaunch' --output text)"
        [ "$public_ip" = "True" ] || die "owned subnet $SUBNET_ID does not assign public IPv4 addresses on launch"
        validate_ec2_tags "$SUBNET_ID" public-subnet "" "vulharness-php2shell-$DEPLOYMENT_ID-public"
        printf 'Subnet: reusing owned %s\n' "$SUBNET_ID"
    else
        existing_subnet="$(aws_cli ec2 describe-subnets --filters Name=vpc-id,Values="$VPC_ID" Name=cidr-block,Values="$SUBNET_CIDR" --query 'Subnets[].SubnetId' --output text | normalize_ids)"
        [ -z "$existing_subnet" ] || die "subnet CIDR $SUBNET_CIDR is already in use in VPC $VPC_ID"
        az="$(aws_cli ec2 describe-instance-type-offerings --location-type availability-zone --filters Name=instance-type,Values="$INSTANCE_TYPE" --query 'sort_by(InstanceTypeOfferings,&Location)[0].Location' --output text)"
        [ -n "$az" ] && [ "$az" != "None" ] || die "instance type $INSTANCE_TYPE is not offered in $AWS_REGION"
        SUBNET_ID="$(aws_cli ec2 create-subnet --vpc-id "$VPC_ID" --cidr-block "$SUBNET_CIDR" --availability-zone "$az" --query 'Subnet.SubnetId' --output text)"
        aws_cli ec2 modify-subnet-attribute --subnet-id "$SUBNET_ID" --map-public-ip-on-launch
        apply_tags "$SUBNET_ID" public-subnet "" "vulharness-php2shell-$DEPLOYMENT_ID-public"
        printf 'Subnet: created %s in %s\n' "$SUBNET_ID" "$az"
    fi
    wait_for_subnet_available
}

ensure_igw() {
    find_igw
    if [ -n "$IGW_ID" ]; then
        attachment_vpc="$(aws_cli ec2 describe-internet-gateways --internet-gateway-ids "$IGW_ID" --query 'InternetGateways[0].Attachments[0].VpcId' --output text)"
        [ "$attachment_vpc" = "None" ] || [ "$attachment_vpc" = "$VPC_ID" ] || die "owned Internet Gateway $IGW_ID is attached to another VPC"
        if [ "$attachment_vpc" = "None" ]; then
            aws_cli ec2 attach-internet-gateway --internet-gateway-id "$IGW_ID" --vpc-id "$VPC_ID"
        fi
        wait_for_igw_attachment
        validate_ec2_tags "$IGW_ID" internet-gateway "" "vulharness-php2shell-$DEPLOYMENT_ID-igw"
        printf 'Internet Gateway: reusing owned %s\n' "$IGW_ID"
    else
        IGW_ID="$(aws_cli ec2 create-internet-gateway --query 'InternetGateway.InternetGatewayId' --output text)"
        apply_tags "$IGW_ID" internet-gateway "" "vulharness-php2shell-$DEPLOYMENT_ID-igw"
        aws_cli ec2 attach-internet-gateway --internet-gateway-id "$IGW_ID" --vpc-id "$VPC_ID"
        wait_for_igw_attachment
        printf 'Internet Gateway: created %s\n' "$IGW_ID"
    fi
}

ensure_route_table() {
    find_route_table
    if [ -n "$ROUTE_TABLE_ID" ]; then
        route_vpc="$(aws_cli ec2 describe-route-tables --route-table-ids "$ROUTE_TABLE_ID" --query 'RouteTables[0].VpcId' --output text)"
        [ "$route_vpc" = "$VPC_ID" ] || die "owned route table $ROUTE_TABLE_ID is not in owned VPC $VPC_ID"
        validate_ec2_tags "$ROUTE_TABLE_ID" route-table "" "vulharness-php2shell-$DEPLOYMENT_ID-public-route"
        printf 'Route table: reusing owned %s\n' "$ROUTE_TABLE_ID"
    else
        ROUTE_TABLE_ID="$(aws_cli ec2 create-route-table --vpc-id "$VPC_ID" --query 'RouteTable.RouteTableId' --output text)"
        apply_tags "$ROUTE_TABLE_ID" route-table "" "vulharness-php2shell-$DEPLOYMENT_ID-public-route"
        printf 'Route table: created %s\n' "$ROUTE_TABLE_ID"
    fi
    default_route_count="$(aws_cli ec2 describe-route-tables --route-table-ids "$ROUTE_TABLE_ID" --query 'length(RouteTables[0].Routes[?DestinationCidrBlock==`0.0.0.0/0`])' --output text)"
    case "$default_route_count" in
        0)
            aws_cli ec2 create-route --route-table-id "$ROUTE_TABLE_ID" --destination-cidr-block 0.0.0.0/0 --gateway-id "$IGW_ID" >/dev/null
            printf 'Route: created default route through %s\n' "$IGW_ID"
            ;;
        1)
            default_route_gateway="$(aws_cli ec2 describe-route-tables --route-table-ids "$ROUTE_TABLE_ID" --query 'RouteTables[0].Routes[?DestinationCidrBlock==`0.0.0.0/0`].GatewayId | [0]' --output text)"
            default_route_state="$(aws_cli ec2 describe-route-tables --route-table-ids "$ROUTE_TABLE_ID" --query 'RouteTables[0].Routes[?DestinationCidrBlock==`0.0.0.0/0`].State | [0]' --output text)"
            if [ "$default_route_gateway" != "$IGW_ID" ]; then
                die "route table $ROUTE_TABLE_ID has an unrelated 0.0.0.0/0 target ($default_route_gateway); refusing to replace it"
            fi
            if [ "$default_route_state" = "active" ]; then
                printf 'Route: existing default route already targets owned %s\n' "$IGW_ID"
            else
                aws_cli ec2 replace-route --route-table-id "$ROUTE_TABLE_ID" --destination-cidr-block 0.0.0.0/0 --gateway-id "$IGW_ID" >/dev/null
                printf 'Route: replaced owned non-active default route through %s\n' "$IGW_ID"
            fi
            ;;
        *)
            die "route table $ROUTE_TABLE_ID returned an unexpected number of 0.0.0.0/0 routes: $default_route_count"
            ;;
    esac
    association="$(aws_cli ec2 describe-route-tables --filters Name=association.subnet-id,Values="$SUBNET_ID" --query 'RouteTables[0].RouteTableId' --output text)"
    if [ "$association" = "None" ] || [ -z "$association" ]; then
        aws_cli ec2 associate-route-table --route-table-id "$ROUTE_TABLE_ID" --subnet-id "$SUBNET_ID" >/dev/null
        wait_for_route_association
    else
        [ "$association" = "$ROUTE_TABLE_ID" ] || die "subnet $SUBNET_ID already uses an unrelated route table $association"
    fi
}

ensure_security_group() {
    find_security_group
    if [ -n "$SECURITY_GROUP_ID" ]; then
        group_vpc="$(aws_cli ec2 describe-security-groups --group-ids "$SECURITY_GROUP_ID" --query 'SecurityGroups[0].VpcId' --output text)"
        inbound_count="$(aws_cli ec2 describe-security-groups --group-ids "$SECURITY_GROUP_ID" --query 'length(SecurityGroups[0].IpPermissions)' --output text)"
        [ "$group_vpc" = "$VPC_ID" ] || die "owned security group $SECURITY_GROUP_ID is not in owned VPC $VPC_ID"
        [ "$inbound_count" = "0" ] || die "owned security group $SECURITY_GROUP_ID has inbound rules; refusing to alter it"
        validate_ec2_tags "$SECURITY_GROUP_ID" security-group "" "vulharness-php2shell-$DEPLOYMENT_ID-sg"
        printf 'Security group: reusing owned %s\n' "$SECURITY_GROUP_ID"
    else
        SECURITY_GROUP_ID="$(aws_cli ec2 create-security-group --group-name "vulharness-php2shell-$DEPLOYMENT_ID" --description "VulHarness PHP2Shell $DEPLOYMENT_ID; no inbound access" --vpc-id "$VPC_ID" --query 'GroupId' --output text)"
        apply_tags "$SECURITY_GROUP_ID" security-group "" "vulharness-php2shell-$DEPLOYMENT_ID-sg"
        printf 'Security group: created %s with zero inbound rules\n' "$SECURITY_GROUP_ID"
    fi
}

role_tags_match() {
    for expected_tag in \
        "VulHarnessProject=$PROJECT" \
        "VulHarnessScenario=$SCENARIO" \
        "VulHarnessEnvironment=$ENVIRONMENT" \
        "VulHarnessDeployment=$DEPLOYMENT_ID" \
        "VulHarnessManagedBy=$MANAGED_BY" \
        "VulHarnessDeploymentMethod=$DEPLOYMENT_METHOD" \
        "VulHarnessOwner=$OWNER" \
        "VulHarnessExpires=$EXPIRES_AT" \
        "VulHarnessResource=iam-role"; do
        key="${expected_tag%%=*}"
        expected_value="${expected_tag#*=}"
        actual_value="$(aws_cli iam list-role-tags --role-name "$ROLE_NAME" --query "Tags[?Key==\`$key\`].Value | [0]" --output text)"
        [ "$actual_value" = "$expected_value" ] || return 1
    done
}

profile_tags_match() {
    for expected_tag in \
        "VulHarnessProject=$PROJECT" \
        "VulHarnessScenario=$SCENARIO" \
        "VulHarnessEnvironment=$ENVIRONMENT" \
        "VulHarnessDeployment=$DEPLOYMENT_ID" \
        "VulHarnessManagedBy=$MANAGED_BY" \
        "VulHarnessDeploymentMethod=$DEPLOYMENT_METHOD" \
        "VulHarnessOwner=$OWNER" \
        "VulHarnessExpires=$EXPIRES_AT" \
        "VulHarnessResource=instance-profile"; do
        key="${expected_tag%%=*}"
        expected_value="${expected_tag#*=}"
        actual_value="$(aws_cli iam list-instance-profile-tags --instance-profile-name "$INSTANCE_PROFILE_NAME" --query "Tags[?Key==\`$key\`].Value | [0]" --output text)"
        [ "$actual_value" = "$expected_value" ] || return 1
    done
}

ensure_iam() {
    ROLE_NAME="vh-php2shell-$DEPLOYMENT_ID-role"
    INSTANCE_PROFILE_NAME="vh-php2shell-$DEPLOYMENT_ID-profile"
    [ "${#ROLE_NAME}" -le 64 ] || die "deployment ID produces an IAM role name longer than 64 characters"

    if aws_cli iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
        role_tags_match || die "IAM role $ROLE_NAME exists but does not have this deployment's ownership tags"
        printf 'IAM role: reusing owned %s\n' "$ROLE_NAME"
    else
        trust_file="$TMP_DIR/trust-policy.json"
        printf '%s\n' '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}' > "$trust_file"
        aws_cli iam create-role --role-name "$ROLE_NAME" --assume-role-policy-document "file://$trust_file" --description "VulHarness PHP2Shell $DEPLOYMENT_ID EC2 role" >/dev/null
        aws_cli iam tag-role --role-name "$ROLE_NAME" --tags \
            "Key=VulHarnessProject,Value=$PROJECT" \
            "Key=VulHarnessScenario,Value=$SCENARIO" \
            "Key=VulHarnessEnvironment,Value=$ENVIRONMENT" \
            "Key=VulHarnessDeployment,Value=$DEPLOYMENT_ID" \
            "Key=VulHarnessManagedBy,Value=$MANAGED_BY" \
            "Key=VulHarnessDeploymentMethod,Value=$DEPLOYMENT_METHOD" \
            "Key=VulHarnessOwner,Value=$OWNER" \
            "Key=VulHarnessExpires,Value=$EXPIRES_AT" \
            "Key=VulHarnessResource,Value=iam-role"
        printf 'IAM role: created %s\n' "$ROLE_NAME"
    fi

    policy_arns="$(aws_cli iam list-attached-role-policies --role-name "$ROLE_NAME" --query 'AttachedPolicies[].PolicyArn' --output text | normalize_ids)"
    unexpected_policies="$(printf '%s\n' "$policy_arns" | awk '$0 != "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore" && NF { print }')"
    [ -z "$unexpected_policies" ] || die "IAM role $ROLE_NAME has permissions beyond AmazonSSMManagedInstanceCore"
    if ! printf '%s\n' "$policy_arns" | grep -Fxq 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'; then
        aws_cli iam attach-role-policy --role-name "$ROLE_NAME" --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
    fi

    if aws_cli iam get-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME" >/dev/null 2>&1; then
        profile_tags_match || die "instance profile $INSTANCE_PROFILE_NAME exists but does not have this deployment's ownership tags"
        attached_role="$(aws_cli iam get-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME" --query 'InstanceProfile.Roles[0].RoleName' --output text)"
        [ "$attached_role" = "None" ] || [ "$attached_role" = "$ROLE_NAME" ] || die "instance profile $INSTANCE_PROFILE_NAME contains an unrelated role"
        printf 'Instance profile: reusing owned %s\n' "$INSTANCE_PROFILE_NAME"
    else
        aws_cli iam create-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME" --tags \
            "Key=VulHarnessProject,Value=$PROJECT" \
            "Key=VulHarnessScenario,Value=$SCENARIO" \
            "Key=VulHarnessEnvironment,Value=$ENVIRONMENT" \
            "Key=VulHarnessDeployment,Value=$DEPLOYMENT_ID" \
            "Key=VulHarnessManagedBy,Value=$MANAGED_BY" \
            "Key=VulHarnessDeploymentMethod,Value=$DEPLOYMENT_METHOD" \
            "Key=VulHarnessOwner,Value=$OWNER" \
            "Key=VulHarnessExpires,Value=$EXPIRES_AT" \
            "Key=VulHarnessResource,Value=instance-profile" >/dev/null
        printf 'Instance profile: created %s\n' "$INSTANCE_PROFILE_NAME"
    fi

    attached_role="$(aws_cli iam get-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME" --query 'InstanceProfile.Roles[0].RoleName' --output text)"
    if [ "$attached_role" = "None" ]; then
        aws_cli iam add-role-to-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME" --role-name "$ROLE_NAME"
    elif [ "$attached_role" != "$ROLE_NAME" ]; then
        die "instance profile $INSTANCE_PROFILE_NAME is attached to unrelated role $attached_role"
    fi
    wait_for_iam_profile
}

create_instance() {
    lab_id="$1"
    instance_name="vulharness-php2shell-$lab_id-$DEPLOYMENT_ID"
    run_instance_once() {
        instance_id="$(aws_cli ec2 run-instances \
            --image-id "$AMI_ID" \
            --instance-type "$INSTANCE_TYPE" \
            --count 1 \
            --subnet-id "$SUBNET_ID" \
            --security-group-ids "$SECURITY_GROUP_ID" \
            --iam-instance-profile Name="$INSTANCE_PROFILE_NAME" \
            --associate-public-ip-address \
            --block-device-mappings "DeviceName=/dev/xvda,Ebs={VolumeSize=$ROOT_VOLUME_SIZE,VolumeType=gp3,Encrypted=true,DeleteOnTermination=true}" \
            --metadata-options HttpTokens=required,HttpEndpoint=enabled,HttpPutResponseHopLimit=2,InstanceMetadataTags=disabled \
            --tag-specifications "$(tag_spec instance instance "$lab_id" "$instance_name")" "$(tag_spec volume volume "$lab_id" "$instance_name-root")" \
            --query 'Instances[0].InstanceId' --output text)"
        [ -n "$instance_id" ] && [ "$instance_id" != "None" ]
    }
    retry_aws "run-instances $lab_id" run_instance_once
    if [ "$lab_id" = "lab-c" ]; then
        LAB_C_INSTANCE_ID="$instance_id"
    else
        LAB_D_INSTANCE_ID="$instance_id"
    fi
    printf '%s: created %s\n' "$lab_id" "$instance_id"
}

ensure_instances() {
    find_instance lab-c yes
    if [ -n "$LAB_C_INSTANCE_ID" ]; then
        state="$(aws_cli ec2 describe-instances --instance-ids "$LAB_C_INSTANCE_ID" --query 'Reservations[0].Instances[0].State.Name' --output text)"
        [ "$state" != "terminated" ] || die "deployment ID already has a terminated Lab C instance; use a new deployment ID"
        LAB_C_INSTANCE_ID=""
    fi
    find_instance lab-d yes
    if [ -n "$LAB_D_INSTANCE_ID" ]; then
        state="$(aws_cli ec2 describe-instances --instance-ids "$LAB_D_INSTANCE_ID" --query 'Reservations[0].Instances[0].State.Name' --output text)"
        [ "$state" != "terminated" ] || die "deployment ID already has a terminated Lab D instance; use a new deployment ID"
        LAB_D_INSTANCE_ID=""
    fi
    find_instance lab-c
    find_instance lab-d
    if [ -n "$LAB_C_INSTANCE_ID" ]; then
        validate_instance lab-c "$LAB_C_INSTANCE_ID"
    fi
    if [ -n "$LAB_D_INSTANCE_ID" ]; then
        validate_instance lab-d "$LAB_D_INSTANCE_ID"
    fi
    [ -n "$LAB_C_INSTANCE_ID" ] || create_instance lab-c
    [ -n "$LAB_D_INSTANCE_ID" ] || create_instance lab-d
    wait_for_ec2_ready
}

wait_for_ssm() {
    instance_id="$1"
    lab_id="$2"
    attempt=1
    while [ "$attempt" -le "$SSM_WAIT_ATTEMPTS" ]; do
        ping_status="$(aws_cli ssm describe-instance-information --filters Key=InstanceIds,Values="$instance_id" --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null || true)"
        if [ "$ping_status" = "Online" ]; then
            printf 'SSM: %s (%s) Online\n' "$lab_id" "$instance_id"
            return 0
        fi
        LAST_OBSERVED="lab=$lab_id instance=$instance_id ssm_ping=${ping_status:-unknown}"
        printf 'SSM: waiting for %s (%s), attempt %s/%s\n' "$lab_id" "$instance_id" "$attempt" "$SSM_WAIT_ATTEMPTS"
        sleep "$SSM_WAIT_SECONDS"
        attempt=$((attempt + 1))
    done
    timeout_report "SSM did not report Online for $lab_id ($instance_id); no remote command was attempted"
    return 1
}

validate_instance() {
    lab_id="$1"
    instance_id="$2"
    [ -n "$instance_id" ] || die "$lab_id instance is missing"

    state="$(aws_cli ec2 describe-instances --instance-ids "$instance_id" --query 'Reservations[0].Instances[0].State.Name' --output text)"
    instance_type="$(aws_cli ec2 describe-instances --instance-ids "$instance_id" --query 'Reservations[0].Instances[0].InstanceType' --output text)"
    architecture="$(aws_cli ec2 describe-instances --instance-ids "$instance_id" --query 'Reservations[0].Instances[0].Architecture' --output text)"
    image_id="$(aws_cli ec2 describe-instances --instance-ids "$instance_id" --query 'Reservations[0].Instances[0].ImageId' --output text)"
    key_name="$(aws_cli ec2 describe-instances --instance-ids "$instance_id" --query 'Reservations[0].Instances[0].KeyName' --output text)"
    profile_name="$(aws_cli ec2 describe-instances --instance-ids "$instance_id" --query 'Reservations[0].Instances[0].IamInstanceProfile.Arn' --output text | sed 's#^.*/##')"
    metadata_tokens="$(aws_cli ec2 describe-instances --instance-ids "$instance_id" --query 'Reservations[0].Instances[0].MetadataOptions.HttpTokens' --output text)"
    group_id="$(aws_cli ec2 describe-instances --instance-ids "$instance_id" --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text)"
    image_name="$(aws_cli ec2 describe-images --image-ids "$image_id" --query 'Images[0].Name' --output text)"
    root_volume="$(aws_cli ec2 describe-instances --instance-ids "$instance_id" --query 'Reservations[0].Instances[0].BlockDeviceMappings[?DeviceName==`/dev/xvda`].Ebs.VolumeId | [0]' --output text)"
    validate_ec2_tags "$instance_id" instance "$lab_id" "vulharness-php2shell-$lab_id-$DEPLOYMENT_ID"
    validate_ec2_tags "$root_volume" volume "$lab_id" "vulharness-php2shell-$lab_id-$DEPLOYMENT_ID-root"
    volume_size="$(aws_cli ec2 describe-volumes --volume-ids "$root_volume" --query 'Volumes[0].Size' --output text)"
    volume_type="$(aws_cli ec2 describe-volumes --volume-ids "$root_volume" --query 'Volumes[0].VolumeType' --output text)"
    encrypted="$(aws_cli ec2 describe-volumes --volume-ids "$root_volume" --query 'Volumes[0].Encrypted' --output text)"
    inbound_count="$(aws_cli ec2 describe-security-groups --group-ids "$group_id" --query 'length(SecurityGroups[0].IpPermissions)' --output text)"
    ping_status="$(aws_cli ssm describe-instance-information --filters Key=InstanceIds,Values="$instance_id" --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null || true)"

    [ "$state" = "running" ] || die "$lab_id validation failed: state=$state"
    [ "$instance_type" = "$INSTANCE_TYPE" ] || die "$lab_id validation failed: instance type=$instance_type"
    [ "$architecture" = "arm64" ] || die "$lab_id validation failed: architecture=$architecture"
    printf '%s\n' "$image_name" | grep -Eq '^al2023-ami-.*-arm64$' || die "$lab_id validation failed: AMI=$image_name"
    [ "$key_name" = "None" ] || [ -z "$key_name" ] || die "$lab_id validation failed: an SSH key pair is attached"
    [ "$profile_name" = "$INSTANCE_PROFILE_NAME" ] || die "$lab_id validation failed: instance profile=$profile_name"
    [ "$metadata_tokens" = "required" ] || die "$lab_id validation failed: IMDSv2 is not required"
    [ "$group_id" = "$SECURITY_GROUP_ID" ] || die "$lab_id validation failed: unexpected security group=$group_id"
    [ "$inbound_count" = "0" ] || die "$lab_id validation failed: security group has inbound rules"
    [ "$volume_size" = "$ROOT_VOLUME_SIZE" ] || die "$lab_id validation failed: root volume size=$volume_size"
    [ "$volume_type" = "gp3" ] || die "$lab_id validation failed: root volume type=$volume_type"
    [ "$encrypted" = "True" ] || die "$lab_id validation failed: root volume is not encrypted"
    [ "$ping_status" = "Online" ] || die "$lab_id validation failed: SSM status=$ping_status"

    printf 'Validated %s: instance=%s type=%s architecture=%s AMI=%s encrypted_root=yes IMDSv2=required inbound_rules=0 SSM=Online\n' "$lab_id" "$instance_id" "$instance_type" "$architecture" "$image_name"
}

validate_deployment() {
    find_vpc
    find_subnet
    find_igw
    find_route_table
    find_security_group
    find_instance lab-c
    find_instance lab-d
    [ -n "$VPC_ID" ] || die "deployment VPC not found"
    [ -n "$SUBNET_ID" ] || die "deployment subnet not found"
    [ -n "$IGW_ID" ] || die "deployment Internet Gateway not found"
    [ -n "$ROUTE_TABLE_ID" ] || die "deployment route table not found"
    [ -n "$SECURITY_GROUP_ID" ] || die "deployment security group not found"
    [ -n "$LAB_C_INSTANCE_ID" ] || die "Lab C instance not found"
    [ -n "$LAB_D_INSTANCE_ID" ] || die "Lab D instance not found"
    all_instance_ids="$(find_all_instances)"
    [ "$(printf '%s\n' "$all_instance_ids" | count_lines)" -eq 2 ] || die "deployment must contain exactly two non-terminated EC2 instances"
    validate_instance lab-c "$LAB_C_INSTANCE_ID"
    validate_instance lab-d "$LAB_D_INSTANCE_ID"
    printf 'Infrastructure validation passed: exactly two tagged instances; PHP runtime readiness remains unverified.\n'
}

deploy() {
    TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/vulharness-aws.XXXXXX")"
    trap 'rm -rf "$TMP_DIR"' EXIT
    validate_prerequisites
    validate_inputs
    discover_existing_resources
    validate_inputs
    printf 'Deployment ID: %s\n' "$DEPLOYMENT_ID"
    printf 'Expiration: %s\n' "$EXPIRES_AT"

    AMI_ID="$(aws_cli ec2 describe-images --owners "$AMI_OWNER" --filters Name=state,Values=available Name=name,Values="$AMI_NAME_PATTERN" --query 'reverse(sort_by(Images,&CreationDate))[0].ImageId' --output text)"
    [ -n "$AMI_ID" ] && [ "$AMI_ID" != "None" ] || die "no Amazon Linux 2023 ARM64 kernel-6.1 AMI was found"
    printf 'AMI: %s\n' "$AMI_ID"

    ensure_vpc
    ensure_subnet
    ensure_igw
    ensure_route_table
    ensure_security_group
    ensure_iam
    ensure_instances
    wait_for_ssm "$LAB_C_INSTANCE_ID" lab-c
    wait_for_ssm "$LAB_D_INSTANCE_ID" lab-d
    validate_deployment
    printf 'Deployment complete. Docker, Compose, PHP, and runtime inspection were not performed.\n'
    printf 'Export this ID for later commands: export VULHARNESS_DEPLOYMENT_ID=%s\n' "$DEPLOYMENT_ID"
}

print_resource() {
    kind="$1"
    resource_id="$2"
    if [ -n "$resource_id" ]; then
        printf '%-20s %s\n' "$kind" "$resource_id"
    else
        printf '%-20s %s\n' "$kind" '<none>'
    fi
}

collect_cleanup_targets() {
    find_vpc
    find_subnet
    find_igw
    find_route_table
    find_security_group
    find_instance lab-c yes
    find_instance lab-d yes
    ROLE_NAME="vh-php2shell-$DEPLOYMENT_ID-role"
    INSTANCE_PROFILE_NAME="vh-php2shell-$DEPLOYMENT_ID-profile"
    VOLUME_IDS="$(find_volumes)"
    CLEANUP_TARGET_STATE="complete"
    [ -n "$VPC_ID" ] || CLEANUP_TARGET_STATE="partial"
    [ -n "$SUBNET_ID" ] || CLEANUP_TARGET_STATE="partial"
    [ -n "$IGW_ID" ] || CLEANUP_TARGET_STATE="partial"
    [ -n "$ROUTE_TABLE_ID" ] || CLEANUP_TARGET_STATE="partial"
    [ -n "$SECURITY_GROUP_ID" ] || CLEANUP_TARGET_STATE="partial"
    [ -n "$LAB_C_INSTANCE_ID" ] || CLEANUP_TARGET_STATE="partial"
    [ -n "$LAB_D_INSTANCE_ID" ] || CLEANUP_TARGET_STATE="partial"

    printf 'Exact cleanup targets for deployment %s:\n' "$DEPLOYMENT_ID"
    print_resource vpc "$VPC_ID"
    print_resource subnet "$SUBNET_ID"
    print_resource internet-gateway "$IGW_ID"
    print_resource route-table "$ROUTE_TABLE_ID"
    print_resource security-group "$SECURITY_GROUP_ID"
    print_resource lab-c-instance "$LAB_C_INSTANCE_ID"
    print_resource lab-d-instance "$LAB_D_INSTANCE_ID"
    printf '%s\n' "$VOLUME_IDS" | while read -r volume_id; do print_resource volume "$volume_id"; done
    if aws_cli iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then print_resource iam-role "$ROLE_NAME"; fi
    if aws_cli iam get-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME" >/dev/null 2>&1; then print_resource instance-profile "$INSTANCE_PROFILE_NAME"; fi
    collect_external_dependencies
    for dependency_id in $EXTERNAL_DEPENDENCY_IDS; do
        print_resource external-vpc-dependency "$dependency_id"
    done
    printf 'Cleanup target state: %s\n' "$CLEANUP_TARGET_STATE"
}

collect_external_dependencies() {
    EXTERNAL_DEPENDENCY_IDS=""
    [ -n "$VPC_ID" ] || return 0
    endpoint_ids="$(aws_cli ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=$VPC_ID" --query 'VpcEndpoints[].VpcEndpointId' --output text 2>/dev/null | normalize_ids || true)"
    for endpoint_id in $endpoint_ids; do
        endpoint_tags="$(aws_cli ec2 describe-vpc-endpoints --vpc-endpoint-ids "$endpoint_id" --query 'VpcEndpoints[0].Tags' --output json 2>/dev/null || printf '[]')"
        if ! python3 - "$endpoint_tags" "$DEPLOYMENT_ID" "$DEPLOYMENT_METHOD" <<'PY'
import json
import sys

tags = {item.get("Key"): item.get("Value") for item in json.loads(sys.argv[1])}
expected = {
    "VulHarnessProject": "VulHarness",
    "VulHarnessScenario": "php2shell",
    "VulHarnessEnvironment": "aws-ec2",
    "VulHarnessDeployment": sys.argv[2],
    "VulHarnessDeploymentMethod": sys.argv[3],
}
raise SystemExit(0 if all(tags.get(key) == value for key, value in expected.items()) else 1)
PY
        then
            EXTERNAL_DEPENDENCY_IDS="$EXTERNAL_DEPENDENCY_IDS $endpoint_id"
            printf 'Cleanup blocker: unowned VPC endpoint %s remains in VPC %s; it will not be modified.\n' "$endpoint_id" "$VPC_ID" >&2
        fi
    done
}

verify_cleanup_ownership() {
    [ -n "$VPC_ID" ] || [ -z "$SUBNET_ID$IGW_ID$ROUTE_TABLE_ID$SECURITY_GROUP_ID$LAB_C_INSTANCE_ID$LAB_D_INSTANCE_ID$VOLUME_IDS" ] || die "cleanup found resources without the tagged VPC"
    if aws_cli iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
        role_tags_match || die "refusing cleanup: IAM role ownership tags do not match"
    fi
    if aws_cli iam get-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME" >/dev/null 2>&1; then
        profile_tags_match || die "refusing cleanup: instance profile ownership tags do not match"
    fi
    if [ -n "$EXTERNAL_DEPENDENCY_IDS" ] && [ "$DRY_RUN" -eq 0 ] && [ "$GUARDDUTY_RELEASE_AUTHORIZED" != 1 ]; then
        die "refusing confirmed cleanup while unowned VPC dependencies remain: $EXTERNAL_DEPENDENCY_IDS; coordinate with the resource owner and rerun cleanup"
    fi
}

cleanup_delete() {
    label="$1"
    shift
    if retry_aws "$label" "$@"; then
        CLEANUP_LAST_SUCCESS=1
        printf 'Deleted: %s\n' "$label"
    else
        CLEANUP_LAST_SUCCESS=0
        printf 'FAILED: %s\n' "$label" >&2
        CLEANUP_FAILURES=$((CLEANUP_FAILURES + 1))
    fi
    return 0
}

cleanup() {
    validate_prerequisites
    validate_inputs
    discover_existing_resources
    validate_inputs
    collect_cleanup_targets
    verify_cleanup_ownership
    if [ "$DRY_RUN" -eq 1 ]; then
        printf 'Dry run only: no resources were changed.\n'
        return 0
    fi

    [ -t 0 ] || die "confirmed cleanup requires an interactive terminal"
    printf 'Type DELETE %s to permanently remove only these resources: ' "$DEPLOYMENT_ID"
    read -r confirmation
    [ "$confirmation" = "DELETE $DEPLOYMENT_ID" ] || die "cleanup confirmation did not match; nothing was changed"

    for instance_id in "$LAB_C_INSTANCE_ID" "$LAB_D_INSTANCE_ID"; do
        if [ -n "$instance_id" ]; then
            state="$(aws_cli ec2 describe-instances --instance-ids "$instance_id" --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null || true)"
            if [ "$state" = "terminated" ]; then
                printf 'Already terminated: instance %s\n' "$instance_id"
            else
                cleanup_delete "instance $instance_id" aws_cli ec2 terminate-instances --instance-ids "$instance_id"
            fi
        fi
    done
    for instance_id in "$LAB_C_INSTANCE_ID" "$LAB_D_INSTANCE_ID"; do
        if [ -n "$instance_id" ]; then
            state="$(aws_cli ec2 describe-instances --instance-ids "$instance_id" --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null || true)"
            if [ "$state" != "terminated" ]; then
                cleanup_delete "instance $instance_id terminated" aws_cli ec2 wait instance-terminated --instance-ids "$instance_id"
            fi
        fi
    done

    for volume_id in $VOLUME_IDS; do
        [ -n "$volume_id" ] || continue
        volume_state="$(aws_cli ec2 describe-volumes --volume-ids "$volume_id" --query 'Volumes[0].State' --output text 2>/dev/null || true)"
        if [ "$volume_state" = "in-use" ]; then
            if wait_for_volume_available "$volume_id"; then
                volume_state="available"
            else
                CLEANUP_FAILURES=$((CLEANUP_FAILURES + 1))
                volume_state="unavailable"
            fi
        fi
        if [ "$volume_state" = "available" ]; then
            cleanup_delete "volume $volume_id" aws_cli ec2 delete-volume --volume-id "$volume_id"
        elif [ -n "$volume_state" ] && [ "$volume_state" != "None" ]; then
            printf 'Remaining: volume %s state=%s\n' "$volume_id" "$volume_state" >&2
            CLEANUP_FAILURES=$((CLEANUP_FAILURES + 1))
        fi
    done

    if [ -n "$VPC_ID" ]; then
        guardduty_release "$VPC_ID" || die "GuardDuty-aware cleanup could not release the exact deployment-VPC dependency"
    fi

    if [ -n "$ROUTE_TABLE_ID" ]; then
        association_id="$(aws_cli ec2 describe-route-tables --route-table-ids "$ROUTE_TABLE_ID" --query 'RouteTables[0].Associations[?SubnetId!=null].RouteTableAssociationId | [0]' --output text 2>/dev/null || true)"
        association_released=1
        if [ -n "$association_id" ] && [ "$association_id" != "None" ]; then
            cleanup_delete "route-table association $association_id" aws_cli ec2 disassociate-route-table --association-id "$association_id"
            if [ "$CLEANUP_LAST_SUCCESS" -eq 1 ]; then
                wait_for_route_disassociation || association_released=0
            else
                association_released=0
            fi
        fi
        if [ "$association_released" -eq 1 ]; then
            cleanup_delete "route table $ROUTE_TABLE_ID" aws_cli ec2 delete-route-table --route-table-id "$ROUTE_TABLE_ID"
        else
            printf 'Remaining: route table %s because its subnet association was not released\n' "$ROUTE_TABLE_ID" >&2
            CLEANUP_FAILURES=$((CLEANUP_FAILURES + 1))
        fi
    fi
    if [ -n "$IGW_ID" ]; then
        igw_detached=1
        if [ -n "$VPC_ID" ]; then
            cleanup_delete "Internet Gateway $IGW_ID detached" aws_cli ec2 detach-internet-gateway --internet-gateway-id "$IGW_ID" --vpc-id "$VPC_ID"
            if [ "$CLEANUP_LAST_SUCCESS" -eq 1 ]; then
                wait_for_igw_detached || igw_detached=0
            else
                igw_detached=0
            fi
        fi
        if [ "$igw_detached" -eq 1 ]; then
            cleanup_delete "Internet Gateway $IGW_ID" aws_cli ec2 delete-internet-gateway --internet-gateway-id "$IGW_ID"
        else
            printf 'Remaining: Internet Gateway %s because detachment was not confirmed\n' "$IGW_ID" >&2
            CLEANUP_FAILURES=$((CLEANUP_FAILURES + 1))
        fi
    fi
    [ -z "$SECURITY_GROUP_ID" ] || cleanup_delete "security group $SECURITY_GROUP_ID" aws_cli ec2 delete-security-group --group-id "$SECURITY_GROUP_ID"
    [ -z "$SUBNET_ID" ] || cleanup_delete "subnet $SUBNET_ID" aws_cli ec2 delete-subnet --subnet-id "$SUBNET_ID"
    [ -z "$VPC_ID" ] || cleanup_delete "VPC $VPC_ID" aws_cli ec2 delete-vpc --vpc-id "$VPC_ID"

    if aws_cli iam get-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME" >/dev/null 2>&1; then
        cleanup_delete "role removed from profile $INSTANCE_PROFILE_NAME" aws_cli iam remove-role-from-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME" --role-name "$ROLE_NAME"
        if [ "$CLEANUP_LAST_SUCCESS" -eq 1 ] && wait_for_profile_empty; then
            cleanup_delete "instance profile $INSTANCE_PROFILE_NAME" aws_cli iam delete-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME"
        else
            printf 'Remaining: instance profile %s because role detachment was not confirmed\n' "$INSTANCE_PROFILE_NAME" >&2
            CLEANUP_FAILURES=$((CLEANUP_FAILURES + 1))
        fi
    fi
    if aws_cli iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
        cleanup_delete "SSM policy detached from $ROLE_NAME" aws_cli iam detach-role-policy --role-name "$ROLE_NAME" --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
        if [ "$CLEANUP_LAST_SUCCESS" -eq 1 ] && wait_for_role_policy_detached; then
            cleanup_delete "IAM role $ROLE_NAME" aws_cli iam delete-role --role-name "$ROLE_NAME"
        else
            printf 'Remaining: IAM role %s because policy detachment was not confirmed\n' "$ROLE_NAME" >&2
            CLEANUP_FAILURES=$((CLEANUP_FAILURES + 1))
        fi
    fi

    if [ "$CLEANUP_FAILURES" -ne 0 ]; then
        printf 'Cleanup incomplete: %s operation(s) failed. Re-run status or cleanup --dry-run.\n' "$CLEANUP_FAILURES" >&2
        return 1
    fi
    printf 'Cleanup complete for deployment %s.\n' "$DEPLOYMENT_ID"
}

status() {
    validate_prerequisites
    validate_inputs
    discover_existing_resources
    validate_inputs
    collect_cleanup_targets
    if [ -n "$LAB_C_INSTANCE_ID" ] && [ -n "$LAB_D_INSTANCE_ID" ]; then
        INSTANCE_PROFILE_NAME="vh-php2shell-$DEPLOYMENT_ID-profile"
        SECURITY_GROUP_ID="${SECURITY_GROUP_ID:-}"
        if (validate_deployment); then
            printf 'Status: HEALTHY; infrastructure and SSM checks passed.\n'
            printf 'PHP runtime readiness remains unverified.\n'
            return 0
        fi
        printf 'Status: UNHEALTHY; tagged resources are inspectable but infrastructure validation failed.\n'
        return 2
    else
        printf 'Status: INCOMPLETE; partial deployment is inspectable but not healthy.\n'
        printf 'Use cleanup --dry-run to review exact tagged resources.\n'
        return 2
    fi
}

parse_args() {
    COMMAND=""
    DRY_RUN=0
    while [ "$#" -gt 0 ]; do
        case "$1" in
            deploy|status|cleanup)
                [ -z "$COMMAND" ] || die "only one command may be provided"
                COMMAND="$1"
                ;;
            --dry-run)
                DRY_RUN=1
                ;;
            --allow-guardduty-cleanup)
                GUARDDUTY_RELEASE_AUTHORIZED=1
                ;;
            --profile)
                shift
                [ "$#" -gt 0 ] || die "--profile requires a value"
                AWS_PROFILE="$1"
                ;;
            --region)
                shift
                [ "$#" -gt 0 ] || die "--region requires a value"
                AWS_REGION="$1"
                ;;
            --deployment-id)
                shift
                [ "$#" -gt 0 ] || die "--deployment-id requires a value"
                DEPLOYMENT_ID="$1"
                ;;
            --expires-at)
                shift
                [ "$#" -gt 0 ] || die "--expires-at requires a value"
                EXPIRES_AT="$1"
                EXPIRES_AT_EXPLICIT=1
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                die "unknown argument: $1"
                ;;
        esac
        shift
    done
    [ -n "$COMMAND" ] || { usage >&2; exit 2; }
    if [ "$COMMAND" = "deploy" ] && [ -z "$DEPLOYMENT_ID" ]; then
        generate_deployment_id
    fi
    validate_inputs
    case "$COMMAND" in
        deploy) deploy ;;
        status) status ;;
        cleanup) cleanup ;;
    esac
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    parse_args "$@"
fi
