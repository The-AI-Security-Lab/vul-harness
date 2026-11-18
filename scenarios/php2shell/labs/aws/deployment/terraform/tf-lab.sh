#!/usr/bin/env bash

set -Eeuo pipefail

export AWS_SDK_LOAD_CONFIG="${AWS_SDK_LOAD_CONFIG:-1}"
AWS_PROFILE="${AWS_PROFILE:-vul-harness-lab-nov26}"
AWS_REGION="${AWS_REGION:-us-east-1}"
DEPLOYMENT_ID="${VULHARNESS_DEPLOYMENT_ID:-}"
EXPIRES_AT="${VULHARNESS_EXPIRES_AT:-}"
OWNER="${VULHARNESS_OWNER:-workshop}"
DEPLOYMENT_METHOD="terraform"
STATE_ROOT="${VULHARNESS_TERRAFORM_STATE_DIR:-.vulharness-terraform-state}"
TF_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
STATE_DIR=""
STATE_FILE=""

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
progress() { printf '[VulHarness] PHP2Shell | terraform | %s %s\n' "$1" "$2" >&2; }
aws_cli() { aws --profile "$AWS_PROFILE" --region "$AWS_REGION" --no-cli-pager "$@"; }
source "$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../shared" && pwd)/guardduty_cleanup.sh"
usage() {
    cat <<'EOF'
Usage:
  tf-lab.sh deploy
  tf-lab.sh status
  tf-lab.sh cleanup --dry-run
  tf-lab.sh cleanup

Options:
  --profile PROFILE
  --region REGION
  --deployment-id ID
  --expires-at TIMESTAMP
  --owner OWNER
  --state-dir DIRECTORY
  --allow-guardduty-cleanup
  --dry-run
EOF
}

generate_id() {
    suffix="$(od -An -N4 -tx4 /dev/urandom | tr -d ' \n')"
    DEPLOYMENT_ID="vh-tf-$(date -u +%Y%m%d%H%M%S)-${suffix:0:8}"
}

generate_expiry() {
    EXPIRES_AT="$(python3 -c 'from datetime import datetime,timedelta,timezone; print((datetime.now(timezone.utc)+timedelta(hours=24)).replace(microsecond=0).isoformat().replace("+00:00","Z"))')"
}

validate_inputs() {
    [ -n "$DEPLOYMENT_ID" ] || die 'deployment ID is required for status/cleanup'
    printf '%s\n' "$DEPLOYMENT_ID" | grep -Eq '^[a-z0-9][a-z0-9-]{0,31}$' || die 'deployment ID has invalid characters'
    case "$STATE_ROOT" in
        /*) ;;
        *) STATE_ROOT="$(pwd -P)/$STATE_ROOT" ;;
    esac
    STATE_DIR="$STATE_ROOT/$DEPLOYMENT_ID"
    STATE_FILE="$STATE_DIR/terraform.tfstate"
    mkdir -p "$STATE_DIR"
    if [ -z "$EXPIRES_AT" ] && [ -s "$STATE_FILE" ]; then
        EXPIRES_AT="$(TF_DATA_DIR="$STATE_DIR/.terraform" terraform -chdir="$TF_DIR" output -state="$STATE_FILE" -raw expires_at 2>/dev/null || true)"
    fi
    [ -n "$EXPIRES_AT" ] || generate_expiry
    printf '%s\n' "$EXPIRES_AT" | grep -Eq '^20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$' || die 'expiration must be UTC ISO-8601'
}

tf() {
    TF_DATA_DIR="$STATE_DIR/.terraform" terraform -chdir="$TF_DIR" "$@" -state="$STATE_FILE"
}

tf_init() {
    TF_DATA_DIR="$STATE_DIR/.terraform" terraform -chdir="$TF_DIR" init "$@"
}

verify_state_ownership() {
    [ -s "$STATE_FILE" ] || die "Terraform state not found: $STATE_FILE"
    python3 - "$STATE_FILE" "$DEPLOYMENT_ID" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)
deployment_id = sys.argv[2]
required = {
    "aws_vpc", "aws_subnet", "aws_internet_gateway", "aws_route_table",
    "aws_security_group", "aws_iam_role", "aws_iam_instance_profile",
    "aws_launch_template", "aws_instance",
}
resources = payload.get("resources", [])
seen = set()
checked = 0
for resource in resources:
    if resource.get("type") not in required:
        continue
    for instance in resource.get("instances", []):
        seen.add(resource.get("type"))
        attrs = instance.get("attributes", {}) or {}
        tags = attrs.get("tags", {}) or {}
        if not tags:
            tag_specs = attrs.get("tag_specifications", []) or []
            for specification in tag_specs:
                tags = specification.get("tags", {}) or {}
                if tags:
                    break
        if not tags:
            continue
        checked += 1
        expected = {
            "VulHarnessProject": "VulHarness",
            "VulHarnessScenario": "php2shell",
            "VulHarnessEnvironment": "aws-ec2",
            "VulHarnessDeployment": deployment_id,
            "VulHarnessManagedBy": "terraform",
            "VulHarnessDeploymentMethod": "terraform",
        }
        for key, value in expected.items():
            if tags.get(key) != value:
                raise SystemExit(f"Terraform ownership mismatch for {resource.get('type')}.{resource.get('name')}: {key}={tags.get(key)!r}")
missing = required - seen
if missing:
    raise SystemExit("Terraform state is missing resource types: " + ", ".join(sorted(missing)))
if checked == 0:
    raise SystemExit("Terraform state contains no tagged deployment resources")
PY
}

state_summary() {
    python3 - "$STATE_FILE" "$DEPLOYMENT_ID" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)
resources = []
for resource in payload.get("resources", []):
    for instance in resource.get("instances", []):
        attributes = instance.get("attributes", {}) or {}
        resources.append(f"{resource.get('type')}.{resource.get('name')}={attributes.get('id', '<unknown>')}")
print(f"Terraform state: {sys.argv[1]}")
print(f"Deployment: {sys.argv[2]}")
print(f"Resources: {len(resources)}")
for resource in sorted(resources):
    print(f"  {resource}")
PY
}

terraform_vpc_id() {
    TF_DATA_DIR="$STATE_DIR/.terraform" terraform -chdir="$TF_DIR" output \
        -state="$STATE_FILE" -raw vpc_id
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
    "VulHarnessManagedBy": "terraform",
    "VulHarnessDeploymentMethod": "terraform",
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
    progress 'deploy' STARTED
    validate_inputs
    progress "Terraform init for $DEPLOYMENT_ID" STARTED
    tf_init -input=false -no-color
    progress "Terraform init for $DEPLOYMENT_ID" OK
    progress "Terraform apply for $DEPLOYMENT_ID" REQUESTED
    tf apply -input=false -auto-approve -no-color \
        -var="profile=$AWS_PROFILE" -var="region=$AWS_REGION" -var="deployment_id=$DEPLOYMENT_ID" -var="expires_at=$EXPIRES_AT" -var="owner=$OWNER"
    progress "deployment verification for $DEPLOYMENT_ID" STARTED
    verify_state_ownership
    print_deployment_summary
    progress "deployment verification for $DEPLOYMENT_ID" OK
    printf 'Terraform deployment applied: %s\n' "$DEPLOYMENT_ID"
    printf 'State retained at: %s\n' "$STATE_FILE"
    progress "Terraform apply for $DEPLOYMENT_ID" OK
    progress 'deploy' OK
}

terraform_output_raw() {
    output_name="$1"
    TF_DATA_DIR="$STATE_DIR/.terraform" terraform -chdir="$TF_DIR" output \
        -state="$STATE_FILE" -raw "$output_name"
}

print_deployment_summary() {
    account_id="$(aws_cli sts get-caller-identity --query 'Account' --output text 2>/dev/null || printf '<unavailable>')"
    vpc_id="$(terraform_output_raw vpc_id)"
    subnet_id="$(terraform_output_raw subnet_id)"
    security_group_id="$(terraform_output_raw security_group_id)"
    lab_c_instance_id="$(terraform_output_raw lab_c_instance_id)"
    lab_d_instance_id="$(terraform_output_raw lab_d_instance_id)"
    instance_type="$(aws_cli ec2 describe-instances \
        --instance-ids "$lab_c_instance_id" "$lab_d_instance_id" \
        --query 'Reservations[].Instances[].InstanceType | [0]' --output text)"
    printf '\nDeployment summary:\n'
    printf '%-20s %s\n' 'Deployment ID' "$DEPLOYMENT_ID"
    printf '%-20s %s\n' 'Deployment method' "$DEPLOYMENT_METHOD"
    printf '%-20s %s\n' 'AWS account' "$account_id"
    printf '%-20s %s\n' 'Region' "$AWS_REGION"
    printf '%-20s %s\n' 'VPC' "$vpc_id"
    printf '%-20s %s\n' 'Subnet' "$subnet_id"
    printf '%-20s %s\n' 'Security group' "$security_group_id"
    printf '%-20s %s\n' 'Lab C EC2 instance' "$lab_c_instance_id"
    printf '%-20s %s\n' 'Lab D EC2 instance' "$lab_d_instance_id"
    printf '%-20s %s\n' 'Instance type' "$instance_type"
    printf '%-20s %s\n' 'Deployment status' 'Success'
}

status() {
    progress 'status' STARTED
    validate_inputs
    [ -s "$STATE_FILE" ] || { printf 'Status: INCOMPLETE; Terraform state not found: %s\n' "$STATE_FILE"; progress 'status' FAILED; return 2; }
    verify_state_ownership
    state_summary
    progress 'status' OK
}

cleanup() {
    progress 'cleanup' STARTED
    validate_inputs
    [ -s "$STATE_FILE" ] || { printf 'Cleanup target: Terraform state not found: %s\n' "$STATE_FILE"; progress 'cleanup' SKIPPED; return 0; }
    verify_state_ownership
    vpc_id="$(terraform_vpc_id)"
    [ -n "$vpc_id" ] && [ "$vpc_id" != None ] || die "Terraform state did not report a VPC output"
    guardduty_plan_json="$(guardduty_preflight "$vpc_id" "$([ "${DRY_RUN:-0}" -eq 1 ] && printf 0 || printf 1)")" || {
        printf 'ERROR: GuardDuty-aware cleanup preflight failed for deployment %s; rerun status or cleanup --dry-run after resolving the dependency.\n' "$DEPLOYMENT_ID" >&2
        return 1
    }
    guardduty_ids="$(python3 -c 'import json,sys; print("\n".join(json.loads(sys.argv[1])["guardduty_endpoint_ids"]))' "$guardduty_plan_json")"
    if [ "${DRY_RUN:-0}" -eq 1 ]; then
        [ -z "$guardduty_ids" ] || printf 'Cleanup target: Terraform provider will release verified GuardDuty endpoints: %s\n' "$guardduty_ids"
        tf plan -destroy -input=false -no-color \
            -var="profile=$AWS_PROFILE" -var="region=$AWS_REGION" -var="deployment_id=$DEPLOYMENT_ID" -var="expires_at=$EXPIRES_AT" -var="owner=$OWNER"
        printf 'Dry run only: no resources were changed.\n'
        progress 'cleanup' OK
        return 0
    fi
    [ -t 0 ] || die 'confirmed cleanup requires an interactive terminal'
    printf 'Type DELETE %s to permanently remove this Terraform deployment: ' "$DEPLOYMENT_ID"
    read -r confirmation
    [ "$confirmation" = "DELETE $DEPLOYMENT_ID" ] || die 'cleanup confirmation did not match'
    progress "Terraform destroy for $DEPLOYMENT_ID" REQUESTED
    tf destroy -input=false -auto-approve -no-color \
        -var="profile=$AWS_PROFILE" -var="region=$AWS_REGION" -var="deployment_id=$DEPLOYMENT_ID" -var="expires_at=$EXPIRES_AT" -var="owner=$OWNER"
    printf 'Terraform destroy completed; retain state until independent AWS absence verification succeeds.\n'
    progress "Terraform destroy for $DEPLOYMENT_ID" OK
    progress 'cleanup' OK
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
            --state-dir) shift; STATE_ROOT="$1" ;;
            --allow-guardduty-cleanup) GUARDDUTY_RELEASE_AUTHORIZED=1 ;;
            --help|-h) usage; return 0 ;;
            *) die "unknown argument: $1" ;;
        esac
        shift
    done
    [ -n "$COMMAND" ] || { usage >&2; return 2; }
    if [ "$COMMAND" = deploy ] && [ -z "$DEPLOYMENT_ID" ]; then generate_id; fi
    case "$COMMAND" in deploy) deploy ;; status) status ;; cleanup) cleanup ;; esac
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then parse_args "$@"; fi
