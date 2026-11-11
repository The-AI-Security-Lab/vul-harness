#!/usr/bin/env bash

# Offline cleanup-safety tests for the non-CLI deployment wrappers. These tests
# stub AWS/Terraform calls and never contact AWS or destroy resources.

set -Eeuo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

fail() {
    printf 'FAIL: %s\n' "$*" >&2
    exit 1
}

pass() {
    printf 'PASS: %s\n' "$*"
}

test_cloudformation_external_dependency_guard() (
    source "$SCRIPT_DIR/cloudformation/cf-lab.sh"
    DEPLOYMENT_ID='vh-cfn-test'
    DEPLOYMENT_METHOD='cloudformation'
    STACK_NAME='vulharness-php2shell-cloudformation-vh-cfn-test'
    DRY_RUN=0
    validate_inputs() { :; }
    stack_exists() { return 0; }
    validate_stack_tags() { :; }
    aws_cli() {
        if [ "$1" = cloudformation ] && [ "$2" = describe-stacks ]; then
            printf '%s\n' '{"Stacks":[{"Outputs":[{"OutputKey":"VpcId","OutputValue":"vpc-cf-test"}]}]}'
        elif [ "$1" = ec2 ] && [ "$2" = describe-vpc-endpoints ]; then
            if [[ "$*" == *'VpcEndpoints[].{Id:'* ]]; then
                printf '%s\n' '[{"Id":"vpce-cf-external","Tags":[{"Key":"GuardDutyManaged","Value":"true"}]}]'
            else
                printf '%s\n' '{"VpcEndpoints":[{"VpcEndpointId":"vpce-cf-external","VpcId":"vpc-cf-test","ServiceName":"com.amazonaws.us-east-1.guardduty-data","Tags":[{"Key":"GuardDutyManaged","Value":"true"}],"NetworkInterfaceIds":[],"Groups":[]}]}'
            fi
        elif [ "$1" = ec2 ] && [ "$2" = describe-instances ]; then
            printf '%s\n' '[]'
        elif [ "$1" = ec2 ] && [ "$2" = describe-network-interfaces ]; then
            if [[ "$*" == *'Name=group-id'* ]]; then
                printf '%s\n' ''
            else
                printf '%s\n' '{"NetworkInterfaces":[]}'
            fi
        elif [ "$1" = ec2 ] && [ "$2" = describe-security-groups ]; then
            printf '%s\n' '{"SecurityGroups":[]}'
        else
            fail "unexpected CloudFormation test call: $*"
        fi
    }
    if (cleanup) > /tmp/vulharness-cf-cleanup.out 2> /tmp/vulharness-cf-cleanup.err; then
        fail 'CloudFormation cleanup ignored an external VPC dependency'
    fi
    grep -Eq 'GuardDuty endpoint release requires|ambiguous or unrelated VPC endpoints|unowned VPC dependencies remain' /tmp/vulharness-cf-cleanup.err || fail 'CloudFormation blocker was not reported'
    pass 'CloudFormation cleanup refuses an unowned VPC dependency'
)

test_terraform_external_dependency_guard() (
    source "$SCRIPT_DIR/terraform/tf-lab.sh"
    DEPLOYMENT_ID='vh-tf-test'
    DEPLOYMENT_METHOD='terraform'
    STATE_FILE="$(mktemp "${TMPDIR:-/tmp}/vulharness-tf-state.XXXXXX")"
    trap 'rm -f "$STATE_FILE" /tmp/vulharness-tf-cleanup.out /tmp/vulharness-tf-cleanup.err' EXIT
    printf '%s\n' 'state' > "$STATE_FILE"
    DRY_RUN=0
    validate_inputs() { :; }
    verify_state_ownership() { :; }
    terraform_vpc_id() { printf '%s\n' 'vpc-tf-test'; }
    tf() { fail 'Terraform cleanup reached destroy/plan despite the external dependency'; }
    aws_cli() {
        if [ "$1" = ec2 ] && [ "$2" = describe-vpc-endpoints ]; then
            if [[ "$*" == *'VpcEndpoints[].{Id:'* ]]; then
                printf '%s\n' '[{"Id":"vpce-tf-external","Tags":[{"Key":"GuardDutyManaged","Value":"true"}]}]'
            else
                printf '%s\n' '{"VpcEndpoints":[{"VpcEndpointId":"vpce-tf-external","VpcId":"vpc-tf-test","ServiceName":"com.amazonaws.us-east-1.guardduty-data","Tags":[{"Key":"GuardDutyManaged","Value":"true"}],"NetworkInterfaceIds":[],"Groups":[]}]}'
            fi
        elif [ "$1" = ec2 ] && [ "$2" = describe-instances ]; then
            printf '%s\n' '[]'
        elif [ "$1" = ec2 ] && [ "$2" = describe-network-interfaces ]; then
            if [[ "$*" == *'Name=group-id'* ]]; then
                printf '%s\n' ''
            else
                printf '%s\n' '{"NetworkInterfaces":[]}'
            fi
        elif [ "$1" = ec2 ] && [ "$2" = describe-security-groups ]; then
            printf '%s\n' '{"SecurityGroups":[]}'
        else
            fail "unexpected Terraform test call: $*"
        fi
    }
    if (cleanup) > /tmp/vulharness-tf-cleanup.out 2> /tmp/vulharness-tf-cleanup.err; then
        fail 'Terraform cleanup ignored an external VPC dependency'
    fi
    grep -Eq 'GuardDuty-managed endpoints require|GuardDuty endpoint release requires|ambiguous or unrelated VPC endpoints|unowned VPC dependencies remain' /tmp/vulharness-tf-cleanup.err || fail 'Terraform blocker was not reported'
    pass 'Terraform cleanup refuses an unowned VPC dependency'
)

test_guardduty_orphan_security_group_release() (
    AWS_REGION='us-east-1'
    DEPLOYMENT_ID='vh-gd-test'
    DEPLOYMENT_METHOD='cloudformation'
    GUARDDUTY_WAIT_ATTEMPTS=1
    GUARDDUTY_WAIT_SECONDS=0
    source "$SCRIPT_DIR/shared/guardduty_cleanup.sh"
    GUARDDUTY_RELEASE_AUTHORIZED=1
    deleted=''
    aws_cli() {
        if [ "$1" = ec2 ] && [ "$2" = describe-vpc-endpoints ]; then
            printf '%s\n' '{"VpcEndpoints":[]}'
        elif [ "$1" = ec2 ] && [ "$2" = describe-instances ]; then
            printf '%s\n' '[]'
        elif [ "$1" = ec2 ] && [ "$2" = describe-network-interfaces ]; then
            if [[ "$*" == *'Name=group-id'* ]]; then
                printf '%s\n' ''
            else
                printf '%s\n' '{"NetworkInterfaces":[]}'
            fi
        elif [ "$1" = ec2 ] && [ "$2" = describe-security-groups ]; then
            if [[ "$*" == *'VpcId'* ]]; then
                printf '%s\n' 'vpc-gd-test'
            elif [[ "$*" == *'GuardDutyManaged'* ]]; then
                printf '%s\n' 'true'
            elif [[ "$*" == *'GroupId'* ]]; then
                printf '%s\n' ''
            else
                printf '%s\n' '{"SecurityGroups":[{"GroupId":"sg-gd-test","VpcId":"vpc-gd-test","Tags":[{"Key":"GuardDutyManaged","Value":"true"}]}]}'
            fi
        elif [ "$1" = ec2 ] && [ "$2" = delete-security-group ]; then
            deleted="$4"
        else
            fail "unexpected GuardDuty test call: $*"
        fi
    }
    guardduty_release vpc-gd-test
    [ "$deleted" = sg-gd-test ] || fail 'orphan GuardDuty SG was not released'
    pass 'releases only an exact unreferenced GuardDuty security group'
)

test_cloudformation_external_dependency_guard
test_terraform_external_dependency_guard
test_guardduty_orphan_security_group_release
printf '%s\n' 'All deployment cleanup guard tests passed.'
