# On-Call Guide for Engineers

**Last Updated:** January 2025
**Owner:** Platform Engineering & Engineering Leadership
**Tags:** onboarding, on-call, incidents, pagerduty, alerts, sre

---

## Overview

All TechCorp engineers join the on-call rotation after their first 30 days. This guide explains what on-call means, how to handle alerts, and what to do during an incident.

---

## On-Call Basics

### What Is On-Call?
On-call means you are the first responder for production alerts during your shift. You are expected to acknowledge alerts within 15 minutes and begin investigating immediately.

### Rotation Schedule
- Each on-call shift is 1 week (Monday 9:00 AM to Monday 9:00 AM EST)
- You are scheduled approximately once every 6 to 8 weeks per team
- The schedule is managed in **PagerDuty** — your manager will add you before your first rotation
- Swap requests are handled in PagerDuty — give at least 48 hours notice

### Compensation
- Weekday on-call: standard working hours — no additional compensation
- Weekend and out-of-hours on-call: compensation policy is in the Engineering HR Confluence space

---

## Alert Severity Levels

| Priority | Response Time | Examples |
|---|---|---|
| P1 — Critical | 15 minutes | Payment processing down, auth service unavailable, data loss |
| P2 — High | 1 hour | Degraded performance, elevated error rates > 5%, pipeline delays > 30 min |
| P3 — Medium | Next business day | Non-critical service degradation, minor data quality issues |
| P4 — Low | Scheduled sprint work | Threshold warnings, capacity planning alerts |

---

## When an Alert Fires

### Step 1: Acknowledge (within 15 minutes for P1/P2)
- Open PagerDuty and acknowledge the alert to stop escalation
- Post in `#incidents` on Slack: "Acknowledged [alert name] — investigating"

### Step 2: Assess the Situation
- Check the alert details in PagerDuty for context
- Check the monitoring dashboards in Grafana: `https://grafana.techcorp.internal`
- Check recent deployments in the `#deployments` Slack channel — was anything deployed in the last hour?
- Check error logs in CloudWatch or Datadog

### Step 3: Communicate
- For P1: Immediately notify your manager via Slack DM and post status in `#incidents`
- For P2: Post in `#incidents` and update every 30 minutes until resolved
- Use this status template:
```
[INCIDENT UPDATE] [P1/P2] [Service Name]
Status: Investigating / Identified / Fixing / Resolved
Impact: What is broken and who is affected
Last action: What you just did
Next action: What you are doing next
ETA: Your best estimate for resolution
```

### Step 4: Resolve or Escalate
- If you can identify and fix the issue within 30 minutes, resolve it and update `#incidents`
- If you cannot resolve within 30 minutes, escalate to your manager
- If the issue requires a rollback, follow the rollback procedure in `deployment_guide.md`

### Step 5: Post-Incident
- Log the incident in ServiceNow within 1 hour of resolution
- Write a brief post-incident summary in Confluence within 24 hours
- The post-incident review template is at `/wiki/incidents/template`

---

## Common Runbooks

For common alert types, refer to the runbook library:

| Alert | Runbook |
|---|---|
| Database connection exhausted | `database_failover.md` |
| Deployment failure or rollback needed | `deployment_guide.md` |
| Service unresponsive | `incident_response.md` |
| Pipeline SLA breach | Runbook in Data Engineering Confluence space |
| Auth service error spike | Runbook in Auth & Identity Confluence space |

---

## Useful Tools During On-Call

| Tool | URL | Purpose |
|---|---|---|
| PagerDuty | `https://techcorp.pagerduty.com` | Alert management and escalation |
| Grafana | `https://grafana.techcorp.internal` | Metrics and dashboards |
| Datadog | `https://app.datadoghq.com` | Logs and APM traces |
| CloudWatch | AWS Console → CloudWatch | AWS infrastructure logs |
| ServiceNow | `https://techcorp.service-now.com` | Incident logging |
| Confluence | `/wiki/incidents` | Post-incident reports |

---

## Your First On-Call Shift

For your first rotation, you will be shadowed by a senior engineer. You will:
- Receive and acknowledge alerts with your buddy observing
- Walk through the investigation process together
- Your buddy will make the final calls — you are learning, not solely responsible

After your first shift, debrief with your buddy and your manager.

---

## Related Documents

- `incident_response.md` — Detailed incident response procedures
- `deployment_guide.md` — How to roll back a deployment
- `logging_standards.md` — How to read and query logs
