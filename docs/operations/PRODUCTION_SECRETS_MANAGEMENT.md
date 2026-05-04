# Production Secrets Management Runbook

This document defines how to securely manage, rotate, and audit credentials in production deployments of AegisAIS.

---

## 1. Overview

**Goal**: Prevent credential leakage, enforce rotation policies, and maintain audit trails.

**Scope**:

- API keys (third-party integrations)
- Database passwords
- TLS certificates
- JWT signing keys
- Service account credentials

**Out of Scope**:

- Source code secrets (handled by .gitignore)
- Development/demo credentials

---

## 2. Development Environment (NOT Production)

### Current State ⚠️

Files to **NEVER** commit with real credentials:

- `apps/api/.env` — Contains demo LLM_API_KEY
- `infra/docker/.env` — Contains demo AISSTREAM_API_KEY, REDIS_PASSWORD
- `apps/web/.env.local` — May contain local API endpoint

### Safe Practices for Dev

```bash
# Copy example file
cp apps/api/.env.example apps/api/.env

# Edit with demo values (these are safe to upload to GitHub)
# LLM_API_KEY=demo-key-12345
# AISSTREAM_API_KEY=demo-key-abcde

# For local testing with real credentials, add to .gitignore:
echo ".env.local" >> .gitignore
echo ".env.production" >> .gitignore

# Store real test credentials ONLY in local .env.local (untracked)
cp apps/api/.env apps/api/.env.local
# Then edit .env.local with real credentials
```

---

## 3. Staging Environment (Semi-Production)

### Credential Sources

Use **one of these methods** (choose a single approach per deployment):

#### Option A: GitHub Secrets (Simpler, GitHub-hosted)

```bash
# 1. Store secrets in GitHub repo settings
# Navigate to: Settings → Secrets and variables → Actions
# Create:
#   - STAGING_AISSTREAM_API_KEY
#   - STAGING_OPENSKY_USERNAME
#   - STAGING_OPENSKY_PASSWORD
#   - STAGING_DB_PASSWORD
#   - STAGING_JWT_SECRET

# 2. Reference in GitHub Actions workflow (.github/workflows/deploy-staging.yml)
- name: Deploy to Staging
  env:
    AISSTREAM_API_KEY: ${{ secrets.STAGING_AISSTREAM_API_KEY }}
    OPENSKY_USERNAME: ${{ secrets.STAGING_OPENSKY_USERNAME }}
    OPENSKY_PASSWORD: ${{ secrets.STAGING_OPENSKY_PASSWORD }}
  run: |
    docker build -t aegisais:staging .
    docker push aegisais:staging
    kubectl set env deployment/aegisais-api AISSTREAM_API_KEY="$AISSTREAM_API_KEY"
```

#### Option B: HashiCorp Vault (Enterprise, recommended for larger teams)

```bash
# 1. Configure Vault backend
vault secrets enable -path=aegisais kv

# 2. Store secrets
vault kv put aegisais/staging/api \
  aisstream_api_key="sk-..." \
  opensky_username="user@..." \
  opensky_password="pass" \
  jwt_secret="$(openssl rand -base64 32)"

# 3. Configure Kubernetes auth
vault write auth/kubernetes/config \
  kubernetes_host="https://staging-k8s.example.com:6443"

# 4. Create policy for AegisAIS pod
vault policy write aegisais-staging - <<EOF
path "aegisais/staging/api" {
  capabilities = ["read"]
}
EOF

# 5. Pod fetches secrets at startup
# See: infra/k8s/overlays/staging/kustomization.yaml
```

#### Option C: AWS Secrets Manager (AWS-native)

```bash
# 1. Store secret
aws secretsmanager create-secret \
  --name aegisais/staging/api \
  --secret-string '{
    "aisstream_api_key":"sk-...",
    "opensky_username":"user",
    "opensky_password":"pass",
    "jwt_secret":"..."
  }'

# 2. Grant pod IAM role permission
# Attach policy:
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:*:*:secret:aegisais/staging/api"
    }
  ]
}

# 3. Pod fetches at startup (using IRSA or EC2 role)
```

### Staging Deployment Process

```bash
# 1. Deploy with secrets injected
kubectl create namespace aegisais-staging
kubectl apply -f infra/k8s/overlays/staging/  # Includes secret refs

# 2. Verify no secrets in logs
kubectl logs deployment/aegisais-api -n aegisais-staging | grep -i "api.key\|password" || echo "✓ Clean"

# 3. Test integration endpoints
kubectl exec -it deployment/aegisais-api -n aegisais-staging -- python -c "
  from app.modules.integrations.adapters_aisstream import test_connection
  test_connection()
"
```

---

## 4. Production Environment (HIGH SECURITY)

### Mandatory Requirements

1. **Never store credentials in:**
   - Source code (.env committed to Git)
   - Docker images (hardcoded in Dockerfile)
   - Kubernetes manifests (plain ConfigMaps)
   - Logs or error messages

2. **Always use:**
   - Encrypted secret store (Vault, AWS Secrets Manager, Azure Key Vault)
   - Short-lived tokens (JWT expiry: 1 hour)
   - Service account credentials with minimal privileges
   - Audit logging for all secret access

### Recommended Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ AegisAIS Production Pod (EKS Cluster)                       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Container Startup                                    │   │
│  │ 1. Pod Identity / Service Account (IRSA)             │   │
│  │ 2. Authenticate to Vault / Secrets Manager           │   │
│  │ 3. Fetch secrets → /var/run/secrets/vault/           │   │
│  │ 4. Load into environment (NOT persistent)            │   │
│  │ 5. Start application                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Runtime Secret Management                            │   │
│  │ - Secrets NOT written to disk                        │   │
│  │ - In-memory only (wiped on pod termination)          │   │
│  │ - Rotation: redeploy pod with new credential         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### AWS Secrets Manager (Recommended for NATO EU Sovereign)

```bash
# 1. Create secret in AWS Secrets Manager
aws secretsmanager create-secret \
  --name aegisais/prod/api \
  --description "Production secrets for AegisAIS API" \
  --kms-key-id arn:aws:kms:eu-west-1:ACCOUNT:key/KMS-KEY-ID \
  --secret-string '{
    "aisstream_api_key":"sk-prod-...",
    "aisstream_subscription_key":"sub-...",
    "opensky_username":"prod_user",
    "opensky_password":"STRONG_PASSWORD",
    "db_password":"DB_STRONG_PASSWORD",
    "jwt_secret":"'"$(openssl rand -base64 32)"'",
    "redis_password":"REDIS_STRONG_PASSWORD",
    "mqtt_password":"MQTT_STRONG_PASSWORD"
  }'

# 2. Create IAM role for pod (IRSA on EKS)
aws iam create-role \
  --role-name aegisais-prod-pod-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT:oidc-provider/oidc.eks.eu-west-1.amazonaws.com/id/EXAMPLEID"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.eu-west-1.amazonaws.com/id/EXAMPLEID:sub": "system:serviceaccount:aegisais:aegisais-sa"
        }
      }
    }]
  }'

# 3. Attach secrets retrieval policy
aws iam put-role-policy \
  --role-name aegisais-prod-pod-role \
  --policy-name aegisais-secrets-read \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:eu-west-1:ACCOUNT:secret:aegisais/prod/api-*"
    }, {
      "Effect": "Allow",
      "Action": "kms:Decrypt",
      "Resource": "arn:aws:kms:eu-west-1:ACCOUNT:key/KMS-KEY-ID"
    }]
  }'

# 4. Create Kubernetes ServiceAccount with IRSA annotation
kubectl create serviceaccount aegisais-sa -n aegisais
kubectl annotate serviceaccount aegisais-sa -n aegisais \
  eks.amazonaws.com/role-arn=arn:aws:iam::ACCOUNT:role/aegisais-prod-pod-role

# 5. Deploy pods with secret injection
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aegisais-api
  namespace: aegisais
spec:
  replicas: 3
  template:
    spec:
      serviceAccountName: aegisais-sa
      containers:
      - name: api
        image: aegisais/api:vX.Y.Z
        env:
        - name: AWS_ROLE_ARN
          value: arn:aws:iam::ACCOUNT:role/aegisais-prod-pod-role
        - name: AWS_WEB_IDENTITY_TOKEN_FILE
          value: /var/run/secrets/eks.amazonaws.com/serviceaccount/token
        - name: AWS_REGION
          value: eu-west-1
        - name: SECRET_NAME
          value: aegisais/prod/api
        lifecycle:
          postStart:
            exec:
              command: ["/bin/sh", "-c", "
                aws secretsmanager get-secret-value --secret-id $SECRET_NAME \
                  --query 'SecretString' --output text | \
                  python -m json.tool > /tmp/secrets.json && \
                export AISSTREAM_API_KEY=\$(jq -r '.aisstream_api_key' /tmp/secrets.json) && \
                export OPENSKY_USERNAME=\$(jq -r '.opensky_username' /tmp/secrets.json) && \
                rm /tmp/secrets.json
              "]
EOF
```

---

## 5. Credential Rotation Policy

### Schedule

- **API Keys**: Every 90 days
- **Database Passwords**: Every 180 days
- **TLS Certificates**: 30 days before expiry
- **JWT Signing Keys**: Every 365 days (with grace period for old key acceptance)

### Rotation Process

```bash
#!/bin/bash
# Rotate AISSTREAM API key in production

NEW_API_KEY="sk-new-key-from-aisstream"

# 1. Update secret in AWS Secrets Manager
aws secretsmanager update-secret \
  --secret-id aegisais/prod/api \
  --secret-string "$(aws secretsmanager get-secret-value \
    --secret-id aegisais/prod/api \
    --query 'SecretString' --output text | \
    jq '.aisstream_api_key = "'$NEW_API_KEY'"' )"

# 2. Roll out new pods (triggers re-fetch of secrets)
kubectl rollout restart deployment/aegisais-api -n aegisais

# 3. Verify pods are ready
kubectl rollout status deployment/aegisais-api -n aegisais --timeout=5m

# 4. Audit: confirm rotation completed
aws secretsmanager describe-secret --secret-id aegisais/prod/api | \
  jq '.RotationDetails'

# 5. Disable old key in external service (e.g., AIStream dashboard)
# Manual: Revoke old key after 24 hours (grace period for in-flight requests)
```

---

## 6. Audit and Compliance

### Logging

```bash
# All secret access is logged:
# - AWS CloudTrail: secretsmanager:GetSecretValue API calls
# - CloudWatch: "Secret accessed by pod aegisais-api at 2026-04-10T14:23:15Z"
# - Pod logs: NO actual secret values (only "credential loaded" message)

# Query audit logs
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=aegisais/prod/api \
  --max-results 50 | \
  jq '.Events[] | {EventTime, EventName, Username, SourceIPAddress}'
```

### Compliance Checklist

- [ ] No secrets in Git history (`git log --all -S "password=" --oneline`)
- [ ] No secrets in container images (`docker history aegisais:latest | grep -i "api.key"`)
- [ ] Audit logs enabled for all secret access
- [ ] Rotation schedule automated (CloudWatch Events → Lambda)
- [ ] Credentials encrypted at rest (KMS, vault encryption)
- [ ] Credentials encrypted in transit (TLS 1.2+)
- [ ] Pod-to-secret manager communication uses private networks (no internet exposure)

---

## 7. Incident Response

### If Credential is Compromised

```bash
# 1. IMMEDIATE: Revoke credential in source system
#    e.g., AIStream dashboard → delete API key
aws secretsmanager update-secret \
  --secret-id aegisais/prod/api \
  --secret-string "$(aws secretsmanager get-secret-value \
    --secret-id aegisais/prod/api \
    --query 'SecretString' --output text | \
    jq '.aisstream_api_key = "revoked"' )"

# 2. Generate new credential
#    e.g., AIStream dashboard → create new API key → note new key

# 3. Update secret store with new credential
aws secretsmanager update-secret \
  --secret-id aegisais/prod/api \
  --secret-string "$(aws secretsmanager get-secret-value \
    --secret-id aegisais/prod/api \
    --query 'SecretString' --output text | \
    jq '.aisstream_api_key = "NEW_KEY"' )"

# 4. Redeploy all pods
kubectl rollout restart deployment/aegisais-api -n aegisais

# 5. Document incident
cat > /tmp/incident.md << EOF
- Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)
- Credential: AISSTREAM_API_KEY
- Action: Revoked, rotated, redeployed
- Pods restarted: $(kubectl get pods -n aegisais -o name)
EOF
```

---

## 8. Reference Implementation

### Kubernetes Deployment with Secrets Injection

```yaml
# infra/k8s/overlays/production/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aegisais-api
  namespace: aegisais
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
  template:
    spec:
      serviceAccountName: aegisais-prod-sa
      imagePullSecrets:
        - name: dockerhub-secret
      containers:
        - name: api
          image: aegisais/api:v1.2.0 # Pinned version
          imagePullPolicy: Always
          env:
            - name: ENV
              value: production
            - name: AWS_REGION
              value: eu-west-1
            - name: AWS_ROLE_ARN
              valueFrom:
                fieldRef:
                  fieldPath: metadata.annotations['eks.amazonaws.com/role-arn']
            - name: AWS_WEB_IDENTITY_TOKEN_FILE
              value: /var/run/secrets/eks.amazonaws.com/serviceaccount/token
          envFrom:
            - configMapRef:
                name: aegisais-config # Non-secret config
          ports:
            - containerPort: 8001
              name: api
          livenessProbe:
            httpGet:
              path: /health
              port: 8001
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8001
            initialDelaySeconds: 10
            periodSeconds: 5
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 2000m
              memory: 2Gi
          volumeMounts:
            - name: secrets
              mountPath: /var/run/secrets/vault
              readOnly: true
      volumes:
        - name: secrets
          projected:
            sources:
              - secret:
                  name: aegisais-api-secrets
```

---

## Next Steps

1. **For Development**: Use demo credentials stored in `infra/docker/.env` (committed, safe)
2. **For Staging**: Choose credential backend (GitHub Secrets or Vault) and configure
3. **For Production**: Implement AWS Secrets Manager + IRSA (most secure for NATO sovereign deployments)
4. **For Operations**: Set up rotation schedule and audit logging
