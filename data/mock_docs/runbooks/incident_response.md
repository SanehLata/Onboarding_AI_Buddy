# Incident Response Runbook

**Last Updated:** January 2025
**Owner:** Platform Engineering & Engineering Leadership
**Tags:** runbooks, incidents, on-call, sre, pagerduty, postmortem

---

## Overview

This runbook defines TechCorp's incident response process from alert to post-incident review. Follow this process for all P1 and P2 incidents.

---

## Incident Severity Definitions

| Severity | Definition | Examples | Response Time |
|---|---|---|---|
| **P1 — Critical** | Complete service outage or data loss affecting customers | Payment processing down, auth service unavailable, database corruption | 15 minutes |
| **P2 — High** | Significant degradation affecting a subset of customers | Error rate > 5%, latency > 2x baseline, pipeline SLA breach > 1 hour | 1 hour |
| **P3 — Medium** | Minor degradation, no customer impact | Single pod crash-looping (auto-healing), non-critical pipeline delay | Next business day |
| **P4 — Low** | Informational, no action required immediately | Capacity warning, minor threshold alert | Scheduled sprint work |

---

## Phase 1: Detection & Acknowledgement

### Automated Detection
Most incidents are detected by:
- PagerDuty alerts (from Prometheus/Grafana thresholds)
- Datadog monitors
- Customer support tickets escalated to engineering
- Synthetic monitoring failures

### Manual Detection
If you notice something wrong that hasn't triggered an alert:
1. Verify it is not just your local environment
2. Check Grafana dashboards to confirm the issue is real
3. Trigger a manual PagerDuty incident if severity is P1 or P2

### Acknowledgement
- **P1/P2:** Acknowledge in PagerDuty within 15 minutes — this stops escalation
- Post in `#incidents` immediately:
```
🔴 [P1 INCIDENT OPEN] {Short description}
On-call: {Your name}
Detected: {Time}
Investigating...
```

---

## Phase 2: Initial Assessment (First 15 Minutes)

Work through this checklist in order — do not skip steps:

### 1. Define the Blast Radius
- Which service(s) are affected?
- Which customers/users are impacted — all, some, specific region?
- What is the business impact — payments failing, users cannot log in, data not loading?

### 2. Check Recent Changes
```bash
# Check recent deployments
kubectl rollout history deployment/{service-name} -n production

# Check ArgoCD for recent syncs
argocd app history {service-name}-production
```
**If a deployment happened in the last 2 hours — consider rollback as your first action.**

### 3. Check Service Health
```bash
# Pod status
kubectl get pods -n production -l app={service-name}

# Recent error logs
kubectl logs -n production -l app={service-name} --tail=200 | grep -i error

# CPU and memory
kubectl top pods -n production -l app={service-name}
```

### 4. Check Dependencies
Use `microservices_map.md` to identify if a dependency is the root cause:
```bash
# Check Auth Service
curl https://auth.techcorp.internal/health

# Check database connectivity
kubectl exec -n production {pod-name} -- python -c "import psycopg2; print('DB OK')"

# Check Kafka consumer lag
kafka-consumer-groups.sh --bootstrap-server {broker} --describe --group {consumer-group}
```

---

## Phase 3: Communication During Incident

### Status Updates
Post in `#incidents` every **15 minutes** for P1, every **30 minutes** for P2:
```
[INCIDENT UPDATE] [P1] [Payments Service] — 10:45 AM
Status: Identified
Impact: ~30% of payment transactions failing with gateway timeout
Root cause: Stripe API returning 504 errors — confirmed via Stripe status page
Action taken: Enabled Adyen fallback routing for affected transaction types
Next update: 11:00 AM
```

### Stakeholder Notification
**P1 incidents:** Your manager must be notified immediately via Slack DM, even outside business hours.

For customer-facing P1s, the on-call engineer notifies the Head of Engineering who decides on external communication.

---

## Phase 4: Resolution

### Fix Categories

**1. Rollback** — if caused by a recent deployment
```bash
kubectl rollout undo deployment/{service-name} -n production
```
See `deployment_guide.md` for full rollback procedure.

**2. Scaling** — if caused by traffic spike
```bash
kubectl scale deployment/{service-name} -n production --replicas=10
```

**3. Pod restart** — if caused by memory leak or deadlock
```bash
kubectl rollout restart deployment/{service-name} -n production
```

**4. Configuration fix** — update ConfigMap or Secret and trigger restart

**5. Database fix** — requires DBA involvement — escalate to your manager

### Confirming Resolution
Before marking an incident resolved:
- Error rate has returned to baseline for at least 10 minutes
- Latency has returned to normal
- No new alerts have fired in the last 5 minutes
- Affected customers can complete their actions successfully

### Resolution Post
```
✅ [P1 INCIDENT RESOLVED] [Payments Service] — 11:10 AM
Duration: 45 minutes
Root cause: Stripe API degradation
Resolution: Routed traffic to Adyen fallback — Stripe recovered at 11:05 AM, traffic restored
Post-incident review: Scheduled for tomorrow 2:00 PM
Jira ticket: JIRA-5678
```

---

## Phase 5: Post-Incident Review

All P1 and P2 incidents require a post-incident review (PIR) within 48 hours.

### PIR Process
1. Schedule a 45-minute blameless review meeting within 48 hours — invite: on-call engineer, team lead, affected team members
2. Complete the PIR template in Confluence at `/wiki/incidents/template`
3. The PIR must include:
   - Timeline of events
   - Root cause (5 Whys analysis)
   - What went well
   - What could be improved
   - Action items with owners and Jira tickets

### PIR is Blameless
We focus on the system, not the individual. Language matters:
- ❌ "John forgot to check the error rate"
- ✅ "The deployment process did not include an automated error rate gate"

---

## Escalation Matrix

| Situation | Escalate to |
|---|---|
| Cannot identify root cause in 30 minutes | Your team manager |
| Database corruption or data loss | Manager + Head of Engineering immediately |
| Security incident suspected | `security@techcorp.com` + Manager |
| Third-party provider outage confirmed | Manager — they handle external comms |
| Multiple services affected simultaneously | Platform Engineering on-call |

---

## Useful Commands Reference

```bash
# Get all pods in production
kubectl get pods -n production

# Describe a pod (shows events and errors)
kubectl describe pod {pod-name} -n production

# Stream logs from all pods of a service
kubectl logs -n production -l app={service-name} -f

# Get recent events in namespace
kubectl get events -n production --sort-by='.lastTimestamp' | tail -20

# Check HPA (horizontal pod autoscaler) status
kubectl get hpa -n production

# Port forward to a pod for local debugging
kubectl port-forward pod/{pod-name} 8080:8080 -n production
```

---

## Related Documents

- `deployment_guide.md` — Rollback procedure
- `database_failover.md` — Database-specific incident response
- `logging_standards.md` — How to query logs
- `on_call_guide.md` — On-call expectations
