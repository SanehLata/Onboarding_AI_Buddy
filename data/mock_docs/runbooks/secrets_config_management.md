# Secrets & Configuration Management

**Last Updated:** January 2025
**Owner:** Platform Engineering
**Tags:** runbooks, secrets, configuration, aws-secrets-manager, kubernetes, environment-variables, security

---

## Overview

This runbook covers how secrets and configuration are managed at TechCorp. Following these standards is mandatory — mishandled secrets are one of the most common causes of security incidents.

---

## The Golden Rules

1. **Never hardcode secrets in code** — no API keys, passwords, or tokens in source files
2. **Never commit a `.env` file** — it is in `.gitignore` for a reason
3. **Never log secret values** — even partially (last 4 chars of a token is still risky)
4. **Never share secrets over Slack or email** — use the approved methods below
5. **Rotate secrets immediately** if you suspect they have been exposed

---

## Where Secrets Live

### Production & Staging: AWS Secrets Manager
All production and staging secrets are stored in AWS Secrets Manager.

**Naming convention:**
```
{environment}/{service-name}/{secret-name}
```

**Examples:**
```
production/payments-service/database-url
production/payments-service/stripe-api-key
staging/auth-service/okta-client-secret
```

### Development: `.env` file (local only)
For local development, use a `.env` file in the project root. Never commit this file.

```bash
# Copy the template
cp .env.example .env

# Fill in development values
# Get dev credentials from your manager or the team's 1Password vault
```

---

## Accessing Secrets in Your Service

### Python (using `boto3`)

The Kubernetes pod has an IAM role attached that grants read access to the relevant secrets. You do not need AWS credentials in the pod itself.

```python
import boto3
import json
from functools import lru_cache

@lru_cache(maxsize=None)
def get_secret(secret_name: str) -> dict:
    client = boto3.client("secretsmanager", region_name="eu-west-1")
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])

# Usage
secrets = get_secret("production/payments-service/stripe-api-key")
stripe_key = secrets["api_key"]
```

### Java (Spring Boot)
Spring Boot services use the `aws-secretsmanager-jdbc` driver which automatically resolves secrets at startup. Configuration is in `application.yml`:

```yaml
spring:
  datasource:
    url: ${DATABASE_URL}   # Injected from Kubernetes secret (see below)
```

### Kubernetes Secrets (for env vars)
Secrets are injected into pods as environment variables via Kubernetes Secrets, which are populated from AWS Secrets Manager by the External Secrets Operator.

```yaml
# This is already set up in the Helm chart — you do not need to edit this
env:
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: payments-service-secrets
        key: database-url
```

---

## Adding a New Secret

### Step 1: Add to AWS Secrets Manager
```bash
# Create a new secret
aws secretsmanager create-secret \
  --name "production/payments-service/new-api-key" \
  --secret-string '{"api_key": "your-secret-value"}'

# Update an existing secret
aws secretsmanager put-secret-value \
  --secret-id "production/payments-service/new-api-key" \
  --secret-string '{"api_key": "new-value"}'
```

> You need the `SecretsManagerWriter` IAM role to create or update secrets. Request via ServiceNow if you don't have it.

### Step 2: Add to ExternalSecret Kubernetes resource
Edit the `ExternalSecret` manifest in the service's Helm chart:
```yaml
spec:
  data:
    - secretKey: new-api-key      # Key name in Kubernetes Secret
      remoteRef:
        key: production/payments-service/new-api-key
        property: api_key
```

### Step 3: Reference in your code
Use the environment variable or fetch via boto3 as shown above.

### Step 4: Add to `.env.example`
Add a placeholder (not the real value) so future developers know this variable is needed:
```bash
# .env.example
NEW_API_KEY=your-api-key-here   # Get from 1Password: TechCorp Dev Secrets vault
```

---

## Configuration (Non-Secret)

Non-sensitive configuration (feature flags, timeouts, limits) uses Kubernetes ConfigMaps, not Secrets Manager.

```yaml
# config.yaml in Helm chart
apiVersion: v1
kind: ConfigMap
metadata:
  name: payments-service-config
data:
  PAYMENT_RETRY_LIMIT: "3"
  PAYMENT_TIMEOUT_MS: "10000"
  FEATURE_NEW_RETRY_LOGIC: "false"
```

Access in Python:
```python
import os
retry_limit = int(os.getenv("PAYMENT_RETRY_LIMIT", "3"))
```

### Feature Flags
For runtime feature flag changes without a deployment, use the ConfigMap and update it:
```bash
kubectl edit configmap payments-service-config -n production
# Change the value
# The pod reads this on restart — trigger a rolling restart:
kubectl rollout restart deployment/payments-service -n production
```

---

## Secret Rotation

Secrets are rotated on the following schedule:

| Secret Type | Rotation Frequency | Automated |
|---|---|---|
| Database passwords | Every 90 days | Yes — RDS rotation via Secrets Manager |
| External API keys (Stripe, Adyen) | Every 180 days | No — manual via Platform team |
| Internal service tokens | Every 90 days | Yes — automated pipeline |
| SSH keys | Every 365 days | No — manual process |

### Emergency Rotation (if a secret is compromised)
1. Immediately notify `security@techcorp.com`
2. Rotate the secret in AWS Secrets Manager:
```bash
aws secretsmanager rotate-secret \
  --secret-id "production/payments-service/stripe-api-key"
```
3. Trigger a rolling restart of all services using the secret:
```bash
kubectl rollout restart deployment/{service-name} -n production
```
4. Verify the service is healthy after rotation
5. File a security incident report in ServiceNow

---

## Auditing Secret Access

All secret access is logged in CloudTrail. To check who accessed a secret:

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=production/payments-service/stripe-api-key \
  --start-time 2025-01-01 \
  --end-time 2025-01-15
```

---

## Related Documents

- `deployment_guide.md` — Deploying with updated secrets
- `incident_response.md` — What to do if a secret is exposed
- `vpn_access.md` — Required for AWS Console access
