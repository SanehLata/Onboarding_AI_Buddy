# Logging Standards

**Last Updated:** January 2025
**Owner:** Platform Engineering
**Tags:** runbooks, logging, observability, datadog, structured-logs, python, java

---

## Overview

Consistent, structured logging makes debugging faster and on-call less painful. All TechCorp services must follow these standards. Non-compliant logs are harder to query in Datadog and slow down incident resolution.

---

## Core Principles

1. **Structured JSON only** — no free-text log lines
2. **Log at the right level** — too much noise is as bad as too little
3. **Never log sensitive data** — no passwords, tokens, card numbers, or PII
4. **Always include context** — request ID, user ID, service name, environment
5. **Logs are for debugging** — not for analytics (use Kafka events for that)

---

## Log Levels

| Level | When to Use | Examples |
|---|---|---|
| `DEBUG` | Detailed diagnostic info — disabled in production by default | SQL queries, internal state, function entry/exit |
| `INFO` | Normal operational events | Request received, payment processed, user logged in |
| `WARNING` | Something unexpected but handled | Retry attempt, deprecated API used, rate limit approaching |
| `ERROR` | An error occurred — needs investigation | Database connection failed, external API returned 500, validation error |
| `CRITICAL` | Service is broken — immediate action required | Cannot connect to database, out of memory, unrecoverable state |

**Production log level:** `INFO` and above. `DEBUG` is disabled by default and must be enabled temporarily via feature flag.

---

## Required Log Fields

Every log line must include these fields:

| Field | Type | Description |
|---|---|---|
| `timestamp` | ISO 8601 | `2025-01-15T10:30:00.123Z` |
| `level` | string | `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `service` | string | Service name: `payments-service`, `auth-service` |
| `environment` | string | `production`, `staging`, `development` |
| `message` | string | Human-readable description of the event |
| `request_id` | string | UUID — passed from `X-Request-ID` header or generated |
| `trace_id` | string | Datadog trace ID for APM correlation |

---

## Python Logging Setup

Use the standard `structlog` library — it is already in `requirements.txt` for all Python services.

```python
import structlog

log = structlog.get_logger()

# Bind context that applies to all logs in this request
log = log.bind(
    request_id=request.headers.get("X-Request-ID", str(uuid4())),
    user_id=current_user.id if current_user else None,
    service="payments-service",
    environment=settings.ENVIRONMENT
)

# Log events
log.info("payment_initiated", transaction_id="txn_abc123", amount=10050, currency="GBP")
log.warning("retry_attempt", attempt=2, max_retries=3, error="Gateway timeout")
log.error("payment_failed", transaction_id="txn_abc123", error_code="GATEWAY_ERROR", error=str(e))
```

**Output (JSON):**
```json
{
  "timestamp": "2025-01-15T10:30:00.123Z",
  "level": "info",
  "service": "payments-service",
  "environment": "production",
  "event": "payment_initiated",
  "request_id": "req_xyz789",
  "user_id": "usr_abc123",
  "transaction_id": "txn_abc123",
  "amount": 10050,
  "currency": "GBP"
}
```

---

## Java Logging Setup

Use `logback` with the `logstash-logback-encoder` for JSON output — already configured in the base Spring Boot template.

```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import net.logstash.logback.argument.StructuredArguments;

private static final Logger log = LoggerFactory.getLogger(PaymentService.class);

// Info
log.info("Payment initiated",
    StructuredArguments.kv("transaction_id", transactionId),
    StructuredArguments.kv("amount", amount),
    StructuredArguments.kv("currency", currency)
);

// Error with exception
log.error("Payment processing failed",
    StructuredArguments.kv("transaction_id", transactionId),
    StructuredArguments.kv("error_code", "GATEWAY_TIMEOUT"),
    exception
);
```

---

## What NOT to Log

**Never log these — the pre-commit hook will reject code containing these patterns:**

```python
# ❌ NEVER — card data
log.info("Processing card", card_number=card.number, cvv=card.cvv)

# ❌ NEVER — tokens or passwords
log.info("User login", password=password, auth_token=token)

# ❌ NEVER — full PII without masking
log.info("User registered", email=email, phone=phone, ssn=ssn)

# ✅ OK — masked PII
log.info("User registered", email_domain=email.split("@")[1], user_id=user.id)

# ✅ OK — partial identifiers
log.info("Card charged", last_four=card.number[-4:], transaction_id=txn.id)
```

---

## Querying Logs in Datadog

**URL:** `https://app.datadoghq.com/logs`

### Common Queries

```
# All errors for a service in the last hour
service:payments-service level:error

# Trace a specific request
@request_id:"req_xyz789"

# Find all failed payments
service:payments-service @event:payment_failed

# High latency requests
service:payments-service @duration:>1000

# Errors by user
service:auth-service level:error @user_id:"usr_abc123"
```

### Useful Filters
- Use `@field:value` for structured field queries
- Use `*` as wildcard: `@transaction_id:txn_*`
- Time range: use the top-right time picker or `last 15m`, `last 1h`, `last 24h`
- Save frequent queries as Saved Views for your team

---

## Log Retention

| Environment | Retention |
|---|---|
| Production | 30 days (indexed), 90 days (archived to S3) |
| Staging | 7 days |
| Development | 3 days |

For compliance or audit purposes, archived logs can be retrieved from S3 via the Platform team — raise a ServiceNow ticket.

---

## Adding Metrics from Logs

Datadog can generate metrics from log patterns — useful for custom business metrics.

Example: track payment failure rate by error code:
1. Go to Datadog → Logs → Generate Metrics
2. Filter: `service:payments-service @event:payment_failed`
3. Group by: `@error_code`
4. This creates a metric you can graph and alert on

---

## Related Documents

- `incident_response.md` — How to use logs during an incident
- `deployment_guide.md` — Monitoring logs after deployment
- `system_overview.md` — Observability stack overview
