#!/usr/bin/env bash

# Offline regression tests for aws-lab.sh. These tests source the script and
# replace AWS calls with a deterministic stub; they never contact AWS.

set -Eeuo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
source "$SCRIPT_DIR/aws-lab.sh"

CALL_LOG="$(mktemp "${TMPDIR:-/tmp}/vulharness-aws-test.XXXXXX")"
RUN_ARGS_FILE="$(mktemp "${TMPDIR:-/tmp}/vulharness-aws-args.XXXXXX")"
trap 'rm -f "$CALL_LOG" "$RUN_ARGS_FILE"' EXIT

fail() {
    printf 'FAIL: %s\n' "$*" >&2
    exit 1
}

pass() {
    printf 'PASS: %s\n' "$*"
}

assert_contains() {
    needle="$1"
    grep -Fq -- "$needle" "$CALL_LOG" || fail "expected AWS call: $needle"
}

assert_not_contains() {
    needle="$1"
    if grep -Fq -- "$needle" "$CALL_LOG"; then
        fail "unexpected AWS call: $needle"
    fi
}

reset_case() {
    : > "$CALL_LOG"
    VPC_ID="vpc-owned"
    SUBNET_ID="subnet-owned"
    IGW_ID="igw-owned"
    ROUTE_TABLE_ID="rtb-owned"
    ROUTE_MODE="new"
    ROUTE_COUNT="0"
    DEPLOYMENT_ID="vh-test-route"
    DEPLOYMENT_METHOD="aws-cli"
    LAB_C_INSTANCE_ID=""
    LAB_D_INSTANCE_ID=""
    RUN_MODE=0
    RUN_INSTANCE_COUNT=0
    RUN_ARGS=()
}

find_route_table() {
    :
}

validate_ec2_tags() {
    :
}

wait_for_route_association() {
    :
}

aws_cli() {
    printf '%s\n' "$*" >> "$CALL_LOG"
    if [ "$RUN_MODE" -eq 1 ] && [ "$1" = "ec2" ] && [ "$2" = "run-instances" ]; then
        printf '%s\n' "$@" > "$RUN_ARGS_FILE"
        printf 'i-test-instance\n'
        return 0
    fi
    if [ "$1" = "ec2" ] && [ "$2" = "describe-route-tables" ]; then
        if printf '%s' "$*" | grep -Fq 'VpcId'; then
            printf '%s\n' "$VPC_ID"
        elif printf '%s' "$*" | grep -Fq 'length(RouteTables[0].Routes'; then
            printf '%s\n' "$ROUTE_COUNT"
        elif printf '%s' "$*" | grep -Fq 'GatewayId'; then
            if [ "$ROUTE_MODE" = "unrelated" ]; then
                printf '%s\n' 'igw-unrelated'
            else
                printf '%s\n' "$IGW_ID"
            fi
        elif printf '%s' "$*" | grep -Fq 'Routes[?DestinationCidrBlock' && printf '%s' "$*" | grep -Fq 'State'; then
            printf '%s\n' 'active'
        elif printf '%s' "$*" | grep -Fq 'association.subnet-id'; then
            printf '%s\n' 'None'
        fi
    fi
}

assert_run_tag_specifications() {
    expected_lab="$1"
    expected_instance_name="vulharness-php2shell-${expected_lab}-${DEPLOYMENT_ID}"
    expected_volume_name="${expected_instance_name}-root"
    RUN_ARGS=()
    while IFS= read -r argument; do
        RUN_ARGS+=("$argument")
    done < "$RUN_ARGS_FILE"
    instance_spec=""
    volume_spec=""
    for ((index = 0; index < ${#RUN_ARGS[@]}; index += 1)); do
        if [ "${RUN_ARGS[$index]}" = "--tag-specifications" ]; then
            instance_spec="${RUN_ARGS[$((index + 1))]}"
            volume_spec="${RUN_ARGS[$((index + 2))]}"
            break
        fi
    done
    [ -n "$instance_spec" ] || fail "$expected_lab instance TagSpecifications argument was missing"
    [ -n "$volume_spec" ] || fail "$expected_lab volume TagSpecifications argument was missing"

    python3 - "$instance_spec" "$volume_spec" "$expected_lab" "$expected_instance_name" "$expected_volume_name" <<'PY'
import json
import sys

instance_spec, volume_spec, expected_lab, expected_instance_name, expected_volume_name = sys.argv[1:]

def check(spec, resource_type, resource_kind, expected_name):
    document = json.loads(spec)
    assert document["ResourceType"] == resource_type, document
    tags = document["Tags"]
    assert tags and all(set(tag) == {"Key", "Value"} for tag in tags), tags
    values = {tag["Key"]: tag["Value"] for tag in tags}
    assert values == {
        "VulHarnessProject": "VulHarness",
        "VulHarnessScenario": "php2shell",
        "VulHarnessEnvironment": "aws-ec2",
        "VulHarnessDeployment": "vh-test-existing-deployment-e04f0bbb",
        "VulHarnessManagedBy": "aws-cli",
        "VulHarnessDeploymentMethod": "aws-cli",
        "VulHarnessOwner": "workshop-ops",
        "VulHarnessExpires": "2026-11-10T23:59:59Z",
        "VulHarnessResource": resource_kind,
        "VulHarnessLab": expected_lab,
        "Name": expected_name,
    }, values

check(instance_spec, "instance", "instance", expected_instance_name)
check(volume_spec, "volume", "volume", expected_volume_name)
PY
}

test_new_route_creation() {
    reset_case
    ROUTE_MODE="new"
    ROUTE_COUNT="0"
    ensure_route_table
    assert_contains 'ec2 create-route'
    assert_not_contains 'ec2 replace-route'
    pass 'creates a missing default route'
}

test_existing_route_and_safe_rerun() {
    reset_case
    ROUTE_MODE="owned"
    ROUTE_COUNT="1"
    ensure_route_table
    ensure_route_table
    assert_not_contains 'ec2 create-route'
    assert_not_contains 'ec2 replace-route'
    pass 'preserves an active owned route on rerun'
}

test_unrelated_route_is_not_replaced() {
    reset_case
    ROUTE_MODE="unrelated"
    ROUTE_COUNT="1"
    if (ensure_route_table); then
        fail 'an unrelated default route was accepted'
    fi
    assert_not_contains 'ec2 replace-route'
    pass 'refuses to replace an unrelated default route'
}

test_run_instance_tag_specifications() {
    reset_case
    RUN_MODE=1
    DEPLOYMENT_ID="vh-test-existing-deployment-e04f0bbb"
    EXPIRES_AT="2026-11-10T23:59:59Z"
    OWNER="workshop-ops"
    AMI_ID="ami-al2023-arm64"
    INSTANCE_PROFILE_NAME="vh-php2shell-$DEPLOYMENT_ID-profile"
    SECURITY_GROUP_ID="sg-owned"
    SUBNET_ID="subnet-owned"
    create_instance lab-c
    assert_run_tag_specifications lab-c
    create_instance lab-d
    assert_run_tag_specifications lab-d
    pass 'serializes exact JSON TagSpecifications for Lab C and Lab D instances and volumes'
}

test_run_instance_eventual_consistency_retry() {
    reset_case
    RETRY_ATTEMPTS=2
    RETRY_SECONDS=0
    RUN_COUNTER_FILE="$(mktemp "${TMPDIR:-/tmp}/vulharness-run-instance.XXXXXX")"
    aws_cli() {
        if [ "$1" = "ec2" ] && [ "$2" = "run-instances" ]; then
            printf '%s\n' call >> "$RUN_COUNTER_FILE"
            RUN_CALLS="$(wc -l < "$RUN_COUNTER_FILE" | tr -d ' ')"
            [ "$RUN_CALLS" -eq 1 ] && return 1
            printf '%s\n' 'i-eventual-consistency'
            return 0
        fi
        return 0
    }
    AMI_ID="ami-al2023-arm64"
    INSTANCE_PROFILE_NAME="vh-php2shell-$DEPLOYMENT_ID-profile"
    SECURITY_GROUP_ID="sg-owned"
    SUBNET_ID="subnet-owned"
    create_instance lab-c
    RUN_CALLS="$(wc -l < "$RUN_COUNTER_FILE" | tr -d ' ')"
    [ "$RUN_CALLS" -eq 2 ] || fail "run-instances was retried $RUN_CALLS times instead of twice"
    [ "$LAB_C_INSTANCE_ID" = "i-eventual-consistency" ] || fail 'retry did not retain the successful instance ID'
    rm -f "$RUN_COUNTER_FILE"
    pass 'retries run-instances after an eventual-consistency failure'
}

test_partial_instance_recovery() {
    reset_case
    INSTANCE_MODE="lab-c-only"
    LAB_C_INSTANCE_ID=""
    LAB_D_INSTANCE_ID=""
    find_instance() {
        if [ "$1" = "lab-c" ]; then
            LAB_C_INSTANCE_ID="i-existing-c"
        else
            LAB_D_INSTANCE_ID=""
        fi
    }
    aws_cli() {
        if [ "$1" = "ec2" ] && [ "$2" = "describe-instances" ]; then
            printf '%s\n' 'running'
        fi
    }
    validate_instance() {
        printf 'validated %s %s\n' "$1" "$2" >> "$CALL_LOG"
    }
    create_instance() {
        [ "$1" = "lab-d" ] || fail 'partial recovery attempted to recreate Lab C'
        LAB_D_INSTANCE_ID="i-new-d"
        printf 'created %s\n' "$1" >> "$CALL_LOG"
    }
    ensure_instances
    [ "$LAB_C_INSTANCE_ID" = "i-existing-c" ] || fail 'existing Lab C was not retained'
    [ "$LAB_D_INSTANCE_ID" = "i-new-d" ] || fail 'missing Lab D was not created'
    assert_contains 'validated lab-c i-existing-c'
    assert_contains 'created lab-d'
    pass 'validates existing Lab C and creates only missing Lab D'
}

test_existing_expiration_is_preserved() {
    reset_case
    VPC_ID="vpc-existing"
    SUBNET_ID=""
    IGW_ID=""
    ROUTE_TABLE_ID=""
    SECURITY_GROUP_ID=""
    LAB_C_INSTANCE_ID=""
    LAB_D_INSTANCE_ID=""
    VOLUME_IDS=""
    EXPIRES_AT="2026-11-10T00:00:00Z"
    EXPIRES_AT_EXPLICIT=0
    find_vpc() { VPC_ID="vpc-existing"; }
    find_subnet() { SUBNET_ID=""; }
    find_igw() { IGW_ID=""; }
    find_route_table() { ROUTE_TABLE_ID=""; }
    find_security_group() { SECURITY_GROUP_ID=""; }
    find_instance() { :; }
    find_volumes() { :; }
    aws_cli() { return 1; }
    ec2_tag_value() {
        [ "$1" = "vpc-existing" ] && [ "$2" = "VulHarnessExpires" ] && printf '%s\n' '2026-11-11T23:59:59Z'
    }
    role_tags_match() { :; }
    profile_tags_match() { :; }
    discover_existing_resources
    [ "$EXPIRES_AT" = "2026-11-11T23:59:59Z" ] || fail 'existing expiration timestamp was not preserved'
    pass 'preserves the existing expiration timestamp when resuming'
}

test_repeated_instance_reuse() {
    reset_case
    INSTANCE_MODE="both"
    find_instance() {
        if [ "$1" = "lab-c" ]; then
            LAB_C_INSTANCE_ID="i-existing-c"
        else
            LAB_D_INSTANCE_ID="i-existing-d"
        fi
    }
    aws_cli() {
        if [ "$1" = "ec2" ] && [ "$2" = "describe-instances" ]; then
            printf '%s\n' 'running'
        fi
    }
    validate_instance() {
        printf 'validated %s %s\n' "$1" "$2" >> "$CALL_LOG"
    }
    create_instance() {
        fail "repeated deploy attempted to create $1"
    }
    ensure_instances
    ensure_instances
    assert_not_contains 'repeated deploy attempted'
    pass 'repeated deploy calls reuse both existing instances without duplication'
}

test_ec2_waiters_are_used() {
    reset_case
    aws_cli() {
        printf '%s\n' "$*" >> "$CALL_LOG"
        return 0
    }
    LAB_C_INSTANCE_ID="i-lab-c"
    LAB_D_INSTANCE_ID="i-lab-d"
    wait_for_ec2_ready
    assert_contains 'ec2 wait instance-running'
    assert_contains 'ec2 wait instance-status-ok'
    pass 'uses running and instance-status-ok waiters'
}

test_bounded_ssm_polling() {
    reset_case
    SSM_WAIT_ATTEMPTS=2
    SSM_WAIT_SECONDS=0
    SSM_COUNTER_FILE="$(mktemp "${TMPDIR:-/tmp}/vulharness-ssm-test.XXXXXX")"
    aws_cli() {
        printf '%s\n' "$*" >> "$CALL_LOG"
        if [ "$1" = "ssm" ]; then
            printf '%s\n' call >> "$SSM_COUNTER_FILE"
            MOCK_SSM_CALLS="$(wc -l < "$SSM_COUNTER_FILE" | tr -d ' ')"
            if [ "$MOCK_SSM_CALLS" -eq 1 ]; then
                printf '%s\n' 'None'
            else
                printf '%s\n' 'Online'
            fi
        fi
    }
    wait_for_ssm i-lab-c lab-c
    MOCK_SSM_CALLS="$(wc -l < "$SSM_COUNTER_FILE" | tr -d ' ')"
    [ "$MOCK_SSM_CALLS" -eq 2 ] || fail "SSM polling made $MOCK_SSM_CALLS calls instead of 2"
    rm -f "$SSM_COUNTER_FILE"
    pass 'uses bounded SSM Online polling'
}

test_ssm_timeout_reports_recovery_state() {
    reset_case
    SSM_WAIT_ATTEMPTS=1
    SSM_WAIT_SECONDS=0
    aws_cli() {
        printf '%s\n' "$*" >> "$CALL_LOG"
        if [ "$1" = "ssm" ]; then
            printf '%s\n' 'None'
        fi
    }
    trap - ERR
    if timeout_output="$(wait_for_ssm i-lab-c lab-c 2>&1)"; then
        trap on_error ERR
        fail 'SSM timeout unexpectedly succeeded'
    fi
    trap on_error ERR
    printf '%s\n' "$timeout_output" | grep -Fq 'Deployment ID: vh-test-route' || fail 'SSM timeout omitted deployment ID'
    printf '%s\n' "$timeout_output" | grep -Fq 'Last observed state: lab=lab-c instance=i-lab-c ssm_ping=None' || fail 'SSM timeout omitted last observed state'
    printf '%s\n' "$timeout_output" | grep -Fq 'Recovery:' || fail 'SSM timeout omitted recovery commands'
    pass 'reports deployment state and recovery commands on SSM timeout'
}

test_partial_status_is_inspectable_but_unhealthy() {
    validate_prerequisites() { :; }
    validate_inputs() { :; }
    discover_existing_resources() { :; }
    collect_cleanup_targets() {
        LAB_C_INSTANCE_ID=""
        LAB_D_INSTANCE_ID=""
        printf '%s\n' 'Cleanup target state: partial'
    }
    if status; then
        fail 'partial status was reported healthy'
    else
        status_rc=$?
    fi
    [ "$status_rc" -eq 2 ] || fail "partial status returned $status_rc instead of 2"
    pass 'reports partial deployment as inspectable but unhealthy'
}

test_partial_cleanup_dry_run() {
    : > "$CALL_LOG"
    DRY_RUN=1
    validate_prerequisites() { :; }
    validate_inputs() { :; }
    discover_existing_resources() { :; }
    collect_cleanup_targets() {
        CLEANUP_TARGET_STATE="partial"
        printf '%s\n' 'vpc                 vpc-owned'
        printf '%s\n' 'subnet              subnet-owned'
        printf '%s\n' 'route-table         rtb-owned'
        printf '%s\n' 'security-group      <none>'
        printf '%s\n' 'Cleanup target state: partial'
    }
    verify_cleanup_ownership() { :; }
    cleanup
    [ ! -s "$CALL_LOG" ] || fail 'cleanup dry-run attempted an AWS operation'
    pass 'lists partial cleanup targets without deletion'
}

test_confirmed_cleanup_refuses_unowned_vpc_dependency() {
    source "$SCRIPT_DIR/aws-lab.sh"
    reset_case
    DRY_RUN=0
    VPC_ID="vpc-owned"
    validate_prerequisites() { :; }
    validate_inputs() { :; }
    discover_existing_resources() { :; }
    collect_cleanup_targets() {
        EXTERNAL_DEPENDENCY_IDS="vpce-guardduty"
    }
    aws_cli() { return 1; }
    trap - ERR
    if (cleanup) 2>"$RUN_ARGS_FILE"; then
        trap on_error ERR
        fail 'confirmed cleanup ignored an unowned VPC dependency'
    fi
    trap on_error ERR
    grep -Fq 'unowned VPC dependencies remain' "$RUN_ARGS_FILE" || fail 'cleanup blocker was not reported'
    pass 'refuses confirmed cleanup before touching an unowned VPC dependency'
}

test_new_route_creation
test_existing_route_and_safe_rerun
test_unrelated_route_is_not_replaced
test_run_instance_tag_specifications
test_run_instance_eventual_consistency_retry
test_partial_instance_recovery
test_existing_expiration_is_preserved
test_repeated_instance_reuse
test_ec2_waiters_are_used
test_bounded_ssm_polling
test_ssm_timeout_reports_recovery_state
test_partial_status_is_inspectable_but_unhealthy
test_partial_cleanup_dry_run
test_confirmed_cleanup_refuses_unowned_vpc_dependency

printf '%s\n' 'All AWS CLI regression tests passed.'
