# Kafka Consumer Runbook

**Last Updated:** January 2025
**Owner:** Platform Engineering & Data Engineering
**Tags:** runbooks, kafka, consumers, lag, msk, messaging, troubleshooting

---

## Overview

This runbook covers common Kafka issues at TechCorp — consumer lag, partition rebalancing, and dead letter queue handling. Kafka underpins our real-time data flow between Payments, Risk, and Data Pipeline. A Kafka issue can cascade quickly.

---

## Kafka Cluster Details

| Cluster | Broker Endpoints | Region | Used By |
|---|---|---|---|
| `msk-prod-primary` | `broker-1.kafka.techcorp.internal:9092` | eu-west-1 | All services |
| `msk-prod-dr` | `broker-1.kafka.us-east.techcorp.internal:9092` | us-east-1 | DR only |

**Kafka version:** 3.5 (MSK managed)
**Access:** Requires VPN + Unix access to the bastion host

---

## Consumer Groups

| Consumer Group | Service | Topics Consumed | SLA |
|---|---|---|---|
| `payments-risk-consumer` | Risk Service | `payments.transactions` | Lag < 1,000 messages |
| `payments-pipeline-consumer` | Data Pipeline | `payments.transactions`, `payments.refunds` | Lag < 10,000 messages |
| `auth-pipeline-consumer` | Data Pipeline | `auth.login_events` | Lag < 10,000 messages |
| `notification-consumer` | Notification Service | `payments.transactions` | Lag < 500 messages |

---

## Scenario 1: High Consumer Lag

### Symptoms
- PagerDuty alert: `KafkaConsumerLagHigh` fires when lag exceeds threshold
- Grafana dashboard: **Kafka Overview** → consumer lag chart spiking
- Downstream effects: Risk scores delayed, Snowflake data stale, notifications delayed

### Investigation

```bash
# SSH to bastion host (requires VPN)
ssh bastion

# Check consumer group lag
kafka-consumer-groups.sh \
  --bootstrap-server broker-1.kafka.techcorp.internal:9092 \
  --describe \
  --group {consumer-group-name}
```

Output shows: `TOPIC | PARTITION | CURRENT-OFFSET | LOG-END-OFFSET | LAG | CONSUMER-ID`

**Interpreting lag:**
- Lag slowly growing → consumer is processing slower than producer is publishing
- Lag suddenly large → consumer was down and missed messages
- Lag on one partition only → that partition's consumer is stuck

### Mitigation Options

**Option A: Scale up the consumer service**
```bash
kubectl scale deployment/{service-name} -n production --replicas=8
```
Each additional replica adds one more consumer thread (up to the number of partitions).

**Option B: Restart stuck consumers**
```bash
kubectl rollout restart deployment/{service-name} -n production
```
Use when one partition's consumer is stuck in a rebalancing loop.

**Option C: Increase consumer thread count**
If the service supports it, update the `KAFKA_CONSUMER_THREADS` env var via ConfigMap and redeploy.

---

## Scenario 2: Consumer Group Rebalancing Loop

### Symptoms
- Logs showing repeated: `Rebalancing group...` entries
- Consumer lag growing despite pods running
- Grafana: consumer group assignment changing every few minutes

### Root Cause
Usually caused by consumers taking longer than `max.poll.interval.ms` (default 5 minutes) to process a batch. The broker thinks the consumer is dead and triggers rebalance.

### Investigation
```bash
# Check consumer logs for rebalance messages
kubectl logs -n production -l app={service-name} | grep -i rebalance

# Check how long individual message processing is taking
kubectl logs -n production -l app={service-name} | grep "processing_time_ms"
```

### Fix
1. Identify if a single message is causing slow processing — look for processing times > 30 seconds
2. If yes — fix the slow processing or add a timeout with dead-letter queue routing
3. If processing time is fine — increase `max.poll.interval.ms` in the consumer config (update ConfigMap, redeploy)

---

## Scenario 3: Dead Letter Queue (DLQ) Backlog

### What is the DLQ?
Messages that fail processing after 3 retries are sent to a dead letter topic:
- `payments.transactions.dlq`
- `payments.refunds.dlq`
- `auth.login_events.dlq`

### Checking DLQ Depth
```bash
kafka-consumer-groups.sh \
  --bootstrap-server broker-1.kafka.techcorp.internal:9092 \
  --describe \
  --group {consumer-group-name}-dlq
```

### Investigating DLQ Messages
```bash
# Read DLQ messages (last 10)
kafka-console-consumer.sh \
  --bootstrap-server broker-1.kafka.techcorp.internal:9092 \
  --topic payments.transactions.dlq \
  --from-beginning \
  --max-messages 10 \
  --property print.headers=true
```

### Replaying DLQ Messages
Once the root cause is fixed, replay DLQ messages back to the main topic:

```bash
# Use the DLQ replay tool (Platform Engineering maintains this)
kubectl run dlq-replay --image=techcorp/kafka-tools:latest -n production \
  --env="SOURCE_TOPIC=payments.transactions.dlq" \
  --env="DEST_TOPIC=payments.transactions" \
  --env="BOOTSTRAP_SERVERS=broker-1.kafka.techcorp.internal:9092"
```

> ⚠️ **Before replaying:** ensure the root cause is fixed, or messages will just fail again and return to DLQ.

---

## Scenario 4: Kafka Broker Unavailable

### Symptoms
- Services logging: `Connection to broker failed`
- All consumers in all groups showing lag growth simultaneously

### Check MSK Status
1. Go to AWS Console → Amazon MSK → `msk-prod-primary`
2. Check **Cluster health** — look for broker status
3. Check **CloudWatch metrics** — `ActiveControllerCount` should be 1

### If One Broker is Down (MSK Multi-AZ)
MSK automatically handles single-broker failures. Producers and consumers reconnect automatically within 30 to 60 seconds. Monitor lag — it should stop growing once brokers recover.

### If Multiple Brokers Are Down
This is a P1 incident — escalate to Platform Engineering on-call and your manager immediately. Do not attempt to fix this yourself.

---

## Useful Kafka Commands Reference

```bash
# List all topics
kafka-topics.sh --bootstrap-server {broker} --list

# Describe a specific topic (partition count, replication)
kafka-topics.sh --bootstrap-server {broker} --describe --topic payments.transactions

# List all consumer groups
kafka-consumer-groups.sh --bootstrap-server {broker} --list

# Check lag for all groups at once
kafka-consumer-groups.sh --bootstrap-server {broker} --describe --all-groups

# Get latest offset for a topic
kafka-run-class.sh kafka.tools.GetOffsetShell \
  --bootstrap-server {broker} \
  --topic payments.transactions \
  --time -1
```

---

## Grafana Dashboard

**Dashboard:** Kafka Overview (search in Grafana)

Key panels to check during an incident:
- **Consumer group lag** — per group and per partition
- **Messages in per second** — producer throughput
- **Messages out per second** — consumer throughput
- **Broker disk usage** — ensure < 70%
- **Under-replicated partitions** — should always be 0

---

## Related Documents

- `incident_response.md` — General incident response
- `data_pipeline.md` — Data pipeline architecture and Kafka usage
- `logging_standards.md` — Querying Kafka-related logs in Datadog
