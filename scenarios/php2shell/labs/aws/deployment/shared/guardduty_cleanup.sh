#!/usr/bin/env bash

# GuardDuty-aware cleanup helper. The caller must provide aws_cli(),
# AWS_PROFILE, AWS_REGION, DEPLOYMENT_ID, and DEPLOYMENT_METHOD.
#
# This helper never changes GuardDuty configuration. It only operates on
# GuardDuty-managed endpoint resources inside one exact, deployment-owned VPC
# after an explicit opt-in.

GUARDDUTY_RELEASE_AUTHORIZED="${VULHARNESS_ALLOW_GUARDDUTY_CLEANUP:-0}"
GUARDDUTY_WAIT_ATTEMPTS="${VULHARNESS_GUARDDUTY_WAIT_ATTEMPTS:-24}"
GUARDDUTY_WAIT_SECONDS="${VULHARNESS_GUARDDUTY_WAIT_SECONDS:-5}"

guardduty_endpoint_service() {
    printf 'com.amazonaws.%s.guardduty-data' "$AWS_REGION"
}

guardduty_plan() {
    vpc_id="$1"
    endpoint_json="$(aws_cli ec2 describe-vpc-endpoints \
        --filters Name=vpc-id,Values="$vpc_id" \
        --output json)"
    instance_json="$(aws_cli ec2 describe-instances \
        --filters Name=vpc-id,Values="$vpc_id" \
        --query 'Reservations[].Instances[]' \
        --output json)"
    eni_json="$(aws_cli ec2 describe-network-interfaces \
        --filters Name=vpc-id,Values="$vpc_id" \
        --output json)"
    security_group_json="$(aws_cli ec2 describe-security-groups \
        --filters Name=vpc-id,Values="$vpc_id" \
        --output json)"
    python3 - "$endpoint_json" "$instance_json" "$eni_json" "$security_group_json" "$vpc_id" "$DEPLOYMENT_ID" "$DEPLOYMENT_METHOD" "$(guardduty_endpoint_service)" <<'PY'
import json
import sys

endpoints = json.loads(sys.argv[1]).get("VpcEndpoints", [])
instances = json.loads(sys.argv[2])
enis = json.loads(sys.argv[3]).get("NetworkInterfaces", [])
security_group_records = json.loads(sys.argv[4]).get("SecurityGroups", [])
vpc_id, deployment_id, method, service = sys.argv[5:9]
required = {
    "VulHarnessProject": "VulHarness",
    "VulHarnessScenario": "php2shell",
    "VulHarnessEnvironment": "aws-ec2",
    "VulHarnessDeployment": deployment_id,
    "VulHarnessDeploymentMethod": method,
}

def tag_map(resource):
    return {tag.get("Key"): tag.get("Value") for tag in resource.get("Tags", [])}

owned_instances = set()
for instance in instances:
    tags = tag_map(instance)
    if all(tags.get(key) == value for key, value in required.items()):
        owned_instances.add(instance.get("InstanceId"))

guardduty = []
ambiguous = []
endpoint_eni_ids = set()
security_groups = set()
for group in security_group_records:
    if tag_map(group).get("GuardDutyManaged") == "true":
        security_groups.add(group.get("GroupId"))
for endpoint in endpoints:
    tags = tag_map(endpoint)
    if endpoint.get("VpcId") != vpc_id:
        ambiguous.append(endpoint.get("VpcEndpointId", "<unknown>"))
        continue
    if endpoint.get("ServiceName") == service and tags.get("GuardDutyManaged") == "true":
        guardduty.append(endpoint.get("VpcEndpointId"))
        endpoint_eni_ids.update(endpoint.get("NetworkInterfaceIds", []))
        security_groups.update(group.get("GroupId") for group in endpoint.get("Groups", []) if group.get("GroupId"))
    else:
        ambiguous.append(endpoint.get("VpcEndpointId", "<unknown>"))

unrelated_enis = []
for eni in enis:
    eni_id = eni.get("NetworkInterfaceId")
    if eni_id in endpoint_eni_ids:
        continue
    instance_id = eni.get("Attachment", {}).get("InstanceId")
    if instance_id in owned_instances:
        continue
    unrelated_enis.append(eni_id or "<unknown>")

print(json.dumps({
    "guardduty_endpoint_ids": sorted(item for item in guardduty if item),
    "ambiguous_endpoint_ids": sorted(item for item in ambiguous if item),
    "endpoint_network_interface_ids": sorted(endpoint_eni_ids),
    "guardduty_security_group_ids": sorted(item for item in security_groups if item),
    "unrelated_network_interface_ids": sorted(unrelated_enis),
}, sort_keys=True))
PY
}

guardduty_wait_absent() {
    kind="$1"
    resource_id="$2"
    attempt=1
    while [ "$attempt" -le "$GUARDDUTY_WAIT_ATTEMPTS" ]; do
        if [ "$kind" = endpoint ]; then
            output="$(aws_cli ec2 describe-vpc-endpoints --vpc-endpoint-ids "$resource_id" --query 'VpcEndpoints[0].VpcEndpointId' --output text 2>/tmp/vulharness-guardduty-wait.err || true)"
        elif [ "$kind" = eni ]; then
            output="$(aws_cli ec2 describe-network-interfaces --network-interface-ids "$resource_id" --query 'NetworkInterfaces[0].NetworkInterfaceId' --output text 2>/tmp/vulharness-guardduty-wait.err || true)"
        else
            output="$(aws_cli ec2 describe-security-groups --group-ids "$resource_id" --query 'SecurityGroups[0].GroupId' --output text 2>/tmp/vulharness-guardduty-wait.err || true)"
        fi
        if [ -z "$output" ] || [ "$output" = None ] || grep -Fq 'NotFound' /tmp/vulharness-guardduty-wait.err; then
            return 0
        fi
        sleep "$GUARDDUTY_WAIT_SECONDS"
        attempt=$((attempt + 1))
    done
    printf 'TIMEOUT: GuardDuty %s %s did not disappear after bounded polling. Deployment ID=%s last_state=%s\n' "$kind" "$resource_id" "$DEPLOYMENT_ID" "$output" >&2
    return 1
}

guardduty_release() {
    vpc_id="$1"
    plan="$(guardduty_plan "$vpc_id")"
    guardduty_ids="$(python3 -c 'import json,sys; print("\n".join(json.loads(sys.argv[1])["guardduty_endpoint_ids"]))' "$plan")"
    ambiguous_ids="$(python3 -c 'import json,sys; print("\n".join(json.loads(sys.argv[1])["ambiguous_endpoint_ids"]))' "$plan")"
    endpoint_eni_ids="$(python3 -c 'import json,sys; print("\n".join(json.loads(sys.argv[1])["endpoint_network_interface_ids"]))' "$plan")"
    security_group_ids="$(python3 -c 'import json,sys; print("\n".join(json.loads(sys.argv[1])["guardduty_security_group_ids"]))' "$plan")"
    unrelated_eni_ids="$(python3 -c 'import json,sys; print("\n".join(json.loads(sys.argv[1])["unrelated_network_interface_ids"]))' "$plan")"

    [ -z "$ambiguous_ids" ] || { printf 'ERROR: ambiguous or unrelated VPC endpoints in VPC %s: %s\n' "$vpc_id" "$ambiguous_ids" >&2; return 1; }
    [ -z "$unrelated_eni_ids" ] || { printf 'ERROR: unrelated VPC consumers remain in VPC %s: %s\n' "$vpc_id" "$unrelated_eni_ids" >&2; return 1; }
    [ -z "$guardduty_ids" ] && [ -z "$security_group_ids" ] && return 0
    [ "$GUARDDUTY_RELEASE_AUTHORIZED" = 1 ] || { printf 'ERROR: GuardDuty endpoint release requires --allow-guardduty-cleanup or VULHARNESS_ALLOW_GUARDDUTY_CLEANUP=1\n' >&2; return 1; }

    for endpoint_id in $guardduty_ids; do
        printf 'GuardDuty cleanup: deleting verified endpoint %s in VPC %s\n' "$endpoint_id" "$vpc_id"
        aws_cli ec2 delete-vpc-endpoints --vpc-endpoint-ids "$endpoint_id" >/dev/null
        guardduty_wait_absent endpoint "$endpoint_id" || return 1
    done
    for eni_id in $endpoint_eni_ids; do
        guardduty_wait_absent eni "$eni_id" || return 1
    done
    for group_id in $security_group_ids; do
        group_vpc="$(aws_cli ec2 describe-security-groups --group-ids "$group_id" --query 'SecurityGroups[0].VpcId' --output text 2>/dev/null || true)"
        group_tag="$(aws_cli ec2 describe-security-groups --group-ids "$group_id" --query 'SecurityGroups[0].Tags[?Key==`GuardDutyManaged`].Value | [0]' --output text 2>/dev/null || true)"
        [ "$group_vpc" = "$vpc_id" ] && [ "$group_tag" = true ] || { printf 'ERROR: refusing to delete non-GuardDuty security group %s\n' "$group_id" >&2; return 1; }
        references="$(aws_cli ec2 describe-network-interfaces --filters Name=group-id,Values="$group_id" --query 'NetworkInterfaces[].NetworkInterfaceId' --output text)"
        [ -z "$references" ] || [ "$references" = None ] || { printf 'ERROR: GuardDuty security group %s still has ENI references: %s\n' "$group_id" "$references" >&2; return 1; }
        printf 'GuardDuty cleanup: deleting verified unreferenced security group %s\n' "$group_id"
        aws_cli ec2 delete-security-group --group-id "$group_id" >/dev/null
        guardduty_wait_absent security-group "$group_id" || return 1
    done
}

guardduty_preflight() {
    vpc_id="$1"
    require_authorization="${2:-1}"
    plan="$(guardduty_plan "$vpc_id")"
    guardduty_ids="$(python3 -c 'import json,sys; print("\n".join(json.loads(sys.argv[1])["guardduty_endpoint_ids"]))' "$plan")"
    ambiguous_ids="$(python3 -c 'import json,sys; print("\n".join(json.loads(sys.argv[1])["ambiguous_endpoint_ids"]))' "$plan")"
    unrelated_eni_ids="$(python3 -c 'import json,sys; print("\n".join(json.loads(sys.argv[1])["unrelated_network_interface_ids"]))' "$plan")"
    [ -z "$ambiguous_ids" ] || { printf 'ERROR: ambiguous or unrelated VPC endpoints in VPC %s: %s\n' "$vpc_id" "$ambiguous_ids" >&2; return 1; }
    [ -z "$unrelated_eni_ids" ] || { printf 'ERROR: unrelated VPC consumers remain in VPC %s: %s\n' "$vpc_id" "$unrelated_eni_ids" >&2; return 1; }
    [ -z "$guardduty_ids" ] || [ "$require_authorization" = 0 ] || [ "$GUARDDUTY_RELEASE_AUTHORIZED" = 1 ] || { printf 'ERROR: GuardDuty-managed endpoints require explicit cleanup authorization: %s\n' "$guardduty_ids" >&2; return 1; }
    printf '%s' "$plan"
}
