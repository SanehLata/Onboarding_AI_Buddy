# Deployment Guide

**Last Updated:** January 2025
**Owner:** Platform Engineering
**Tags:** runbooks, deployment, cicd, kubernetes, argocd, rollback

---

## Overview

This guide covers how to deploy services at TechCorp — from merging a PR to verifying a production release. All services follow the same pipeline unless explicitly noted in their own README.

---

## Deployment Pipeline

```
PR Merged to main
       │
       ▼
GitHub Actions CI
  ├── Unit tests
  ├── Integration tests
  ├── Linting & pre-commit
  └── Docker image build + push to ECR
       │
       ▼
ArgoCD Sync (automatic)
  ├── Deploys to DEV automatically
  └── Deploys to STAGING automatically after DEV is healthy
       │
       ▼
Production Deployment (manual gate)
  └── Engineer triggers via ArgoCD UI or CLI
```

---

## Step-by-Step: Deploying to Production

### Prerequisites
- PR merged and all CI checks green
- Deployment ticket created in Jira (type: `DEPLOYMENT`)
- Deployment announced in `#deployments` Slack channel
- No active P1 incidents
- Not a Friday after 3:00 PM

### Step 1: Verify Staging
```bash
# Check the staging deployment is healthy
kubectl get pods -n staging -l app={service-name}

# Check recent logs for errors
kubectl logs -n staging -l app={service-name} --tail=100

# Run a smoke test against staging
curl https://{service-name}.staging.techcorp.internal/health
```

### Step 2: Create a Jira Deployment Ticket
- Go to Jira and create a `DEPLOYMENT` issue
- Include: service name, version, what changed, rollback plan
- Get manager or senior engineer sign-off in the Jira ticket

### Step 3: Announce in Slack
Post in `#deployments`:
```
🚀 DEPLOYMENT STARTING
Service: payments-service
Version: v2.4.1
Changes: JIRA-1234 — Add retry logic for Stripe timeouts
Engineer: Your Name
Rollback: kubectl rollout undo deployment/payments-service -n production
```

### Step 4: Trigger the Production Deployment

**Via ArgoCD UI:**
1. Go to `https://argocd.techcorp.internal`
2. Find your application
3. Click **Sync** → Select `production` environment → **Synchronize**

**Via CLI:**
```bash
argocd app sync {service-name}-production --prune
```

### Step 5: Monitor the Rollout
```bash
# Watch the rollout progress
kubectl rollout status deployment/{service-name} -n production

# Monitor pod health
kubectl get pods -n production -l app={service-name} -w

# Watch error rate in Grafana
# Dashboard: Production Services Overview → select your service
```

Monitor for a minimum of **30 minutes** post-deployment before closing the Jira ticket.

### Step 6: Confirm Deployment
Post in `#deployments`:
```
✅ DEPLOYMENT COMPLETE
Service: payments-service
Version: v2.4.1
Status: Healthy — error rate nominal, latency normal
```

---

## Rollback Procedure

If error rates spike or critical functionality breaks after deployment, roll back immediately. Do not wait to investigate — rollback first, investigate second.

### Immediate Rollback (Kubernetes)
```bash
# Roll back to the previous version
kubectl rollout undo deployment/{service-name} -n production

# Verify rollback is progressing
kubectl rollout status deployment/{service-name} -n production

# Confirm pods are healthy
kubectl get pods -n production -l app={service-name}
```

### Rollback via ArgoCD
1. Go to ArgoCD UI → Select the application
2. Click **History and Rollback**
3. Select the previous successful deployment
4. Click **Rollback**

### Post-Rollback
1. Post in `#deployments` and `#incidents`:
```
⚠️ ROLLBACK COMPLETED
Service: payments-service
Rolled back to: v2.4.0
Reason: Error rate increased from 0.1% to 4.2% post-deployment
Next steps: Investigation in progress
```
2. Create a P2 incident in ServiceNow
3. Notify your manager

---

## Hotfix Deployments

For urgent production fixes that cannot wait for the standard pipeline:

1. Branch from `main`: `hotfix/JIRA-XXX-description`
2. Make the fix — keep it minimal
3. Open a PR and request expedited review in `#payments-eng` (or your team channel)
4. One senior engineer approval is sufficient for a hotfix
5. Merge and follow the standard deployment steps above
6. Ensure a proper fix follows in the next sprint if the hotfix was a workaround

---

## Environment Reference

| Environment | URL Pattern | Deployment | Who Can Deploy |
|---|---|---|---|
| Development | `*.dev.techcorp.internal` | Automatic on merge | All engineers |
| Staging | `*.staging.techcorp.internal` | Automatic after dev is healthy | All engineers |
| Production | `*.techcorp.internal` | Manual gate | Engineers with prod access |

---

## Related Documents

- `incident_response.md` — If something goes wrong post-deployment
- `logging_standards.md` — How to read logs during monitoring
- `on_call_guide.md` — On-call procedures if a deployment triggers an alert
