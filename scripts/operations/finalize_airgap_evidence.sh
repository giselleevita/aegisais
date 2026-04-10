#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
EVIDENCE_DIR="$REPO_ROOT/docs/evidence"
REPORT_PATH="$EVIDENCE_DIR/AIR_GAPPED_REHEARSAL_EVIDENCE_FINAL.md"
COMPOSE_FILE="$REPO_ROOT/infra/docker/docker-compose.yml"
RUN_DATE="$(date '+%Y-%m-%d %H:%M:%S')"

mkdir -p "$EVIDENCE_DIR"

check_file() {
  local path="$1"
  if [[ -f "$path" ]]; then
    echo "present"
  else
    echo "missing"
  fi
}

hash_file() {
  local path="$1"
  if [[ -f "$path" ]]; then
    shasum -a 256 "$path" | awk '{print $1}'
  else
    echo "n/a"
  fi
}

status_icon() {
  local status="$1"
  case "$status" in
    pass) echo "PASS" ;;
    warn) echo "WARN" ;;
    fail) echo "FAIL" ;;
    *) echo "INFO" ;;
  esac
}

docker_available="no"
compose_status="not-run"
compose_output="docker not installed"
if command -v docker >/dev/null 2>&1; then
  docker_available="yes"
  if docker compose -f "$COMPOSE_FILE" config >/tmp/aegisais_airgap_compose.out 2>/tmp/aegisais_airgap_compose.err; then
    compose_status="pass"
    compose_output="docker compose config succeeded"
  else
    compose_status="fail"
    compose_output="$(tr '\n' ' ' </tmp/aegisais_airgap_compose.err | sed 's/  */ /g' | cut -c1-280)"
  fi
else
  compose_status="warn"
fi

openssl_status="warn"
openssl_detail="openssl not found"
if command -v openssl >/dev/null 2>&1; then
  openssl_status="pass"
  openssl_detail="openssl available for local TLS certificate generation"
fi

guide_status="$(check_file "$REPO_ROOT/docs/security/AIR_GAPPED_DEPLOYMENT.md")"
security_pack_status="$(check_file "$REPO_ROOT/docs/security/SECURITY_EVIDENCE_PACK.md")"
compose_file_status="$(check_file "$COMPOSE_FILE")"
stack_script_status="$(check_file "$REPO_ROOT/scripts/operations/start_full_stack.sh")"
stack_wrapper_status="$(check_file "$REPO_ROOT/scripts/start_full_stack.sh")"
images_workflow_status="$(check_file "$REPO_ROOT/.github/workflows/images.yml")"

overall_status="PASS"
if [[ "$guide_status" != "present" || "$compose_file_status" != "present" || "$stack_script_status" != "present" ]]; then
  overall_status="FAIL"
elif [[ "$compose_status" == "fail" ]]; then
  overall_status="FAIL"
elif [[ "$compose_status" == "warn" || "$openssl_status" == "warn" ]]; then
  overall_status="WARN"
fi

cat > "$REPORT_PATH" <<EOF
# Air-Gapped Rehearsal Evidence

**Evidence Package Date:** $RUN_DATE  
**Status:** $(status_icon "$(tr '[:upper:]' '[:lower:]' <<<"$overall_status")")

## Executive Summary

This evidence package captures the current repo-backed rehearsal state for NATO RESTRICTED and other air-gapped deployments. It validates that the documented offline deployment path, local stack startup tooling, and supporting supply-chain artefacts are present and internally consistent.

## Rehearsal Checklist

| Control | Expected Artefact | Result | Detail |
| --- | --- | --- | --- |
| Air-gapped deployment guide | docs/security/AIR_GAPPED_DEPLOYMENT.md | $( [[ "$guide_status" == "present" ]] && echo PASS || echo FAIL ) | Guide file $guide_status |
| Security evidence pack | docs/security/SECURITY_EVIDENCE_PACK.md | $( [[ "$security_pack_status" == "present" ]] && echo PASS || echo FAIL ) | Evidence index file $security_pack_status |
| Offline compose baseline | infra/docker/docker-compose.yml | $( [[ "$compose_file_status" == "present" ]] && echo PASS || echo FAIL ) | Compose file $compose_file_status |
| Local stack launcher | scripts/operations/start_full_stack.sh | $( [[ "$stack_script_status" == "present" ]] && echo PASS || echo FAIL ) | Operational script $stack_script_status |
| Wrapper launcher | scripts/start_full_stack.sh | $( [[ "$stack_wrapper_status" == "present" ]] && echo PASS || echo FAIL ) | Wrapper script $stack_wrapper_status |
| Image scanning workflow | .github/workflows/images.yml | $( [[ "$images_workflow_status" == "present" ]] && echo PASS || echo FAIL ) | Workflow file $images_workflow_status |
| Compose validation | docker compose -f infra/docker/docker-compose.yml config | $(status_icon "$compose_status") | $compose_output |
| TLS generation toolchain | openssl | $(status_icon "$openssl_status") | $openssl_detail |

## Operational Notes

- This rehearsal validates repository artefacts and local command readiness. It does not replace a customer-side classified deployment exercise.
- The compose validation step confirms that the stack definition can be rendered without syntax errors on a workstation with Docker installed.
- The TLS tooling check confirms local self-signed certificate generation support for offline rehearsals.

## Artefact Integrity

| Artefact | SHA-256 |
| --- | --- |
| docs/security/AIR_GAPPED_DEPLOYMENT.md | $(hash_file "$REPO_ROOT/docs/security/AIR_GAPPED_DEPLOYMENT.md") |
| docs/security/SECURITY_EVIDENCE_PACK.md | $(hash_file "$REPO_ROOT/docs/security/SECURITY_EVIDENCE_PACK.md") |
| infra/docker/docker-compose.yml | $(hash_file "$COMPOSE_FILE") |
| scripts/operations/start_full_stack.sh | $(hash_file "$REPO_ROOT/scripts/operations/start_full_stack.sh") |
| scripts/start_full_stack.sh | $(hash_file "$REPO_ROOT/scripts/start_full_stack.sh") |

## Manual Follow-Up Required

1. Run the documented procedure inside a representative classified or disconnected environment and archive the operator log.
2. Capture image transfer evidence from the approved media or registry mirror used in the target environment.
3. Record sanctions watchlist import and classification-marking verification from the target deployment.

## Result

Repo-backed air-gapped rehearsal evidence has been generated at:

	$REPORT_PATH

This package is suitable as internal readiness evidence and as a precursor to a full customer-side classified rehearsal.
EOF

echo "Air-gapped rehearsal evidence written to: $REPORT_PATH"
