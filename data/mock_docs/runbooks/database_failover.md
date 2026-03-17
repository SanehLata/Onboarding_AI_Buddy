# Database Failover Runbook

**Last Updated:** January 2025
**Owner:** Platform Engineering & Data Engineering
**Tags:** runbooks, database, failover, postgresql, rds, disaster-recovery

---

## Overview

This runbook covers procedures for PostgreSQL (RDS) failover events, connection exhaustion, and recovery steps. Database incidents are always P1 or P2 — escalate to your manager immediately.

---

## Database Inventory

| Database | Service | RDS Instance | Primary Region | Replica Region |
|---|---|---|---|---|
| `payments_db` | Payments Service | `rds-payments-prod` | eu-west-1 | us-east-1 |
| `auth_db` | Auth Service | `rds-auth-prod` | eu-west-1 | us-east-1 |
| `risk_db` | Risk Service | `rds-risk-prod` | eu-west-1 | us-east-1 |

All instances run PostgreSQL 15 on RDS Multi-AZ. Automated failover is enabled — RDS will automatically promote a standby if the primary becomes unavailable.

---

## Scenario 1: RDS Automatic Failover (Multi-AZ)

### What Happens Automatically
When RDS detects primary failure, it automatically promotes the standby replica. This takes **60 to 120 seconds**. During this time, your service will see connection errors.

### What You Need to Do
In most cases, **nothing** — services are configured to retry connections with exponential backoff. Verify the following:

```bash
# Check if pods are in a crash loop (may happen during failover window)
kubectl get pods -n production -l app={service-name}

# If pods are crash-looping, check the logs
kubectl logs -n production {pod-name} | grep -i "database\|connection\|psycopg"

# Verify the new RDS endpoint is responding
psql -h {rds-endpoint} -U {username} -d {database} -c "SELECT 1;"
```

If pods are crash-looping 10 minutes after the failover started, restart the deployment:
```bash
kubectl rollout restart deployment/{service-name} -n production
```

### Verify Failover Completed
1. Go to AWS Console → RDS → `rds-{service}-prod`
2. Check **Events** tab — you should see: `Multi-AZ instance failover completed`
3. Confirm the new primary endpoint is responding

---

## Scenario 2: Connection Pool Exhaustion

### Symptoms
- Logs showing: `FATAL: remaining connection slots are reserved`
- `psycopg2.OperationalError: connection pool exhausted`
- Service returning 503 errors with database error details

### Immediate Investigation
```bash
# Connect to the database (requires prod access and VPN)
psql -h {rds-endpoint} -U admin -d {database}

-- Check total connections
SELECT count(*), state, wait_event_type, wait_event
FROM pg_stat_activity
GROUP BY state, wait_event_type, wait_event
ORDER BY count DESC;

-- Check max connections setting
SHOW max_connections;

-- Find connections by application
SELECT application_name, count(*)
FROM pg_stat_activity
GROUP BY application_name
ORDER BY count DESC;
```

### Immediate Mitigation
```bash
# Scale down the service to reduce connections
kubectl scale deployment/{service-name} -n production --replicas=2

# Wait 2 minutes, then scale back up gradually
kubectl scale deployment/{service-name} -n production --replicas=5
```

If connections are not releasing naturally, identify and terminate idle connections:
```sql
-- Terminate idle connections older than 10 minutes
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
AND query_start < NOW() - INTERVAL '10 minutes'
AND application_name != 'pgAdmin';
```

> ⚠️ **Do not terminate connections with state = 'active'** — you may interrupt live transactions.

### Root Cause Investigation (Post-Mitigation)
- Check if a recent deployment changed the connection pool size setting
- Check if a long-running query or transaction is holding connections
- Check if PgBouncer (connection pooler) is healthy:
```bash
kubectl get pods -n production -l app=pgbouncer
kubectl logs -n production -l app=pgbouncer --tail=50
```

---

## Scenario 3: Slow Queries / Lock Contention

### Symptoms
- API latency P99 increasing significantly
- Logs showing query timeouts
- Grafana showing high database CPU or high wait time

### Investigation
```sql
-- Find currently running long queries (> 30 seconds)
SELECT pid, now() - query_start AS duration, query, state
FROM pg_stat_activity
WHERE state != 'idle'
AND query_start < NOW() - INTERVAL '30 seconds'
ORDER BY duration DESC;

-- Find blocked queries
SELECT pid, usename, pg_blocking_pids(pid) AS blocked_by, query
FROM pg_stat_activity
WHERE cardinality(pg_blocking_pids(pid)) > 0;

-- Check table-level lock contention
SELECT relation::regclass, mode, granted
FROM pg_locks
WHERE NOT granted;
```

### Mitigation
If a single query is blocking others and has been running for more than 5 minutes:
```sql
-- First confirm with your manager before terminating
SELECT pg_cancel_backend({pid});   -- Graceful cancel
SELECT pg_terminate_backend({pid}); -- Force terminate if cancel doesn't work
```

---

## Scenario 4: Manual Failover to DR Region

Use only if eu-west-1 is fully unavailable and recovery time is > 2 hours.

> ⚠️ **This procedure requires Head of Engineering approval.** Do not initiate this unilaterally.

### Steps
1. Get written approval from Head of Engineering in Slack or email
2. In AWS Console → RDS → `rds-{service}-prod` → Actions → **Promote read replica** (in us-east-1)
3. Update the service's database endpoint in AWS Secrets Manager:
```bash
aws secretsmanager put-secret-value \
  --secret-id prod/{service}/database-url \
  --secret-string "postgresql://user:pass@{dr-endpoint}:5432/{database}"
```
4. Restart the service to pick up the new credentials:
```bash
kubectl rollout restart deployment/{service-name} -n production
```
5. Notify all teams via `#incidents` that the service is now running on the DR database

### Failback to Primary
When eu-west-1 is restored, schedule a maintenance window and reverse the process. Coordinate with the Data Engineering team — Snowflake CDC will need to be re-pointed.

---

## Backup & Recovery

| Backup Type | Frequency | Retention | Recovery Time |
|---|---|---|---|
| RDS Automated Snapshots | Daily | 30 days | 1–4 hours |
| RDS Transaction Logs | Continuous | 7 days | Point-in-time, ~30 min |
| Manual Snapshot | Before major deployments | 90 days | 1–4 hours |

### Restoring from a Snapshot
Only initiate a restore if data has been corrupted or accidentally deleted. **Always get Head of Engineering approval first.**

```bash
# Via AWS CLI
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier rds-{service}-restored \
  --db-snapshot-identifier {snapshot-id} \
  --db-instance-class db.r6g.xlarge
```

---

## Escalation

| Situation | Escalate To |
|---|---|
| Failover not completing after 5 minutes | Manager + AWS Support |
| Data loss or corruption suspected | Manager + Head of Engineering immediately |
| Manual DR failover needed | Head of Engineering approval required |
| Cannot connect after 10 minutes | Platform Engineering on-call |

---

## Related Documents

- `incident_response.md` — General incident response procedure
- `logging_standards.md` — How to query application logs
- `system_overview.md` — Database architecture overview
