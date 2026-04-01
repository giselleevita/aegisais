# AegisAIS Incident Response Runbook

**Classification:** NATO RESTRICTED | TLP:AMBER  
**Version:** 1.0  
**Last Updated:** 2025-01-01

## 1. Incident Classification

| Severity          | Definition                                          | Response SLA | Escalation             |
| ----------------- | --------------------------------------------------- | ------------ | ---------------------- |
| **P0 – Critical** | System compromise, data breach, active exploitation | 15 minutes   | CISO + NATO NCIRC      |
| **P1 – High**     | Service degradation, unauthorized access attempt    | 1 hour       | Security Lead + DevOps |
| **P2 – Medium**   | Anomalous activity, policy violation                | 4 hours      | Security Lead          |
| **P3 – Low**      | Configuration drift, vulnerability disclosure       | 24 hours     | DevOps                 |

## 2. Detection Phase

### 2.1 Automated Detection

- **Prometheus alerts** → `infra/monitoring/alert_rules.yml`
- **Falco runtime rules** → Container escape, unexpected exec, unusual network activity
- **AegisAIS anomaly pipeline** → Alerts on system-level anomalies (not just AIS)
- **Audit log anomalies** → Unusual API patterns, bulk data export, auth failures

### 2.2 Manual Detection Indicators

- Unexpected API traffic patterns (bulk vessel downloads, unusual auth volume)
- Unauthorized container images in cluster
- Redis key enumeration patterns
- Database query anomalies (pg_stat_statements review)

## 3. Triage Phase

### 3.1 Initial Assessment Checklist

```
□ Confirm incident (not false positive)
□ Classify severity (P0-P3)
□ Identify scope (which systems/data affected)
□ Activate incident channel (dedicated secure comms)
□ Assign Incident Commander (IC)
□ Begin timeline documentation
```

### 3.2 Evidence Collection

```bash
# Preserve container state before restart
kubectl get pods -o wide > /evidence/pods_$(date +%s).txt
kubectl logs <pod> --all-containers > /evidence/logs_$(date +%s).txt

# Database audit trail
psql -c "SELECT * FROM audit_log WHERE created_at > NOW() - INTERVAL '24 hours'" > /evidence/audit.csv

# Redis state snapshot
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb /evidence/redis_$(date +%s).rdb
```

## 4. Containment Phase

### 4.1 Network Isolation

```bash
# Isolate compromised pod(s) with network policy
kubectl label pod <pod> quarantine=true
kubectl apply -f infra/k8s/overlays/quarantine/network-policy.yaml
```

### 4.2 Credential Rotation

```bash
# Rotate all secrets
kubectl delete secret aegisais-secrets
kubectl create secret generic aegisais-secrets \
  --from-literal=SECRET_KEY=$(openssl rand -hex 32) \
  --from-literal=DATABASE_URL="..." \
  --from-literal=REDIS_PASSWORD=$(openssl rand -hex 16)

# Force all user sessions to re-authenticate
redis-cli FLUSHDB  # Revokes all JWTs via Redis token store
```

### 4.3 Database Lockdown

```sql
-- Revoke all active sessions
UPDATE refresh_tokens SET revoked = true WHERE revoked = false;
-- Disable compromised user accounts
UPDATE users SET is_active = false WHERE id IN (<compromised_user_ids>);
```

## 5. Eradication Phase

### 5.1 Container Scanning

```bash
# Scan current images with Trivy
trivy image aegisais/api:latest --severity HIGH,CRITICAL
trivy image aegisais/bff:latest --severity HIGH,CRITICAL
trivy image aegisais/web:latest --severity HIGH,CRITICAL
```

### 5.2 Dependency Audit

```bash
# Python dependencies
pip-audit --strict
# Node.js dependencies
npm audit --audit-level=high
```

### 5.3 Infrastructure Review

```bash
# Check for unauthorized K8s resources
kubectl get all --all-namespaces | grep -v kube-system
# Review RBAC policies
kubectl get clusterrolebindings -o wide
kubectl get rolebindings --all-namespaces -o wide
```

## 6. Recovery Phase

### 6.1 Service Restoration

```bash
# Rolling restart with fresh images
kubectl rollout restart deployment/aegisais-api
kubectl rollout restart deployment/aegisais-bff
kubectl rollout restart deployment/aegisais-web

# Verify health
curl -s https://aegisais.local/v1/health | jq .
```

### 6.2 Data Integrity Verification

```bash
# Verify alert evidence hashes (BL-009)
python -c "
from app.modules.alerts.models import derive_evidence_hash
# Re-derive and compare evidence hashes for recent alerts
"
```

## 7. Post-Incident Phase

### 7.1 Required Documentation

- Incident timeline (from detection to resolution)
- Root cause analysis
- Impact assessment (data accessed, systems affected)
- Remediation actions taken
- Lessons learned

### 7.2 NATO Notification Requirements

- **P0/P1**: Notify NATO NCIRC within 72 hours per STANAG 2900
- **Data breach**: Notify affected member nations per NATO Cyber Defence Policy
- All incidents: Log in incident register, review in next security committee meeting

### 7.3 Post-Incident Improvements

- Update detection rules based on TTPs observed
- Add indicators of compromise to watchlists
- Update this runbook with lessons learned
- Schedule tabletop exercise for similar scenarios

## 8. Contact Matrix

| Role               | Contact | Backup |
| ------------------ | ------- | ------ |
| Incident Commander | [TBD]   | [TBD]  |
| Security Lead      | [TBD]   | [TBD]  |
| DevOps Lead        | [TBD]   | [TBD]  |
| NATO NCIRC POC     | [TBD]   | [TBD]  |
| Legal Counsel      | [TBD]   | [TBD]  |
