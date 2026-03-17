# Payments API — Architecture & Developer Guide

**Last Updated:** January 2025
**Owner:** Payments Engineering Team
**Tags:** architecture, payments, api, transactions, kafka, pci

---

## Overview

The Payments Service handles all payment processing at TechCorp. It manages transaction lifecycle from initiation through settlement, integrates with external payment gateways (Stripe and Adyen), and publishes transaction events to Kafka for downstream consumption by the Risk and Data Engineering teams.

**Team:** Payments Engineering
**Manager:** Sarah Mitchell (sarah.mitchell@techcorp.com)
**Slack:** `#payments-eng` | Alerts: `#payments-alerts`
**SLA:** 99.95% availability | P95 latency < 200ms

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Java 17 |
| Framework | Spring Boot 3.x |
| Database | PostgreSQL 15 (RDS) — primary transactions DB |
| Cache | Redis 7 — idempotency keys and rate limiting |
| Messaging | Kafka (MSK) — event publishing |
| Gateway Integrations | Stripe API v3, Adyen Checkout API |
| Deployment | Kubernetes (EKS) |

---

## Core Concepts

### Transaction Lifecycle

```
INITIATED → AUTHORISED → CAPTURED → SETTLED
              ↓               ↓
           DECLINED        REFUNDED
              ↓
           FAILED
```

Every state transition is persisted in PostgreSQL and published as a Kafka event.

### Idempotency
All payment initiation endpoints require an `Idempotency-Key` header. This prevents duplicate charges if a client retries a request. Keys are stored in Redis with a 24-hour TTL.

### PCI Compliance
The Payments Service is PCI DSS Level 1 compliant. Key implications for developers:
- Card numbers are never stored in plain text — tokenised via Stripe Vault or Adyen Token Service
- All access to cardholder data requires an approved access request
- No logging of card numbers, CVVs, or full PANs anywhere in the codebase — the pre-commit hook will reject this
- Production database access for Payments requires additional security sign-off

---

## Core API Endpoints

### POST `/payments/initiate`
Creates a new payment transaction.

**Request:**
```json
{
  "amount": 10050,
  "currency": "GBP",
  "payment_method_token": "tok_visa_4242",
  "merchant_reference": "ORDER-98765",
  "customer_id": "cust_abc123",
  "metadata": {
    "order_id": "ORDER-98765",
    "product_type": "subscription"
  }
}
```

**Response:**
```json
{
  "transaction_id": "txn_xyz789",
  "status": "INITIATED",
  "amount": 10050,
  "currency": "GBP",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Headers required:**
- `Authorization: Bearer <jwt>`
- `Idempotency-Key: <uuid>`

### POST `/payments/{transaction_id}/capture`
Captures a previously authorised transaction.

### POST `/payments/{transaction_id}/refund`
Initiates a full or partial refund.

**Request:**
```json
{
  "amount": 5000,
  "reason": "customer_request",
  "reference": "REFUND-12345"
}
```

### GET `/payments/{transaction_id}`
Returns full transaction details including status history.

### GET `/payments/merchant/{merchant_reference}`
Looks up a transaction by the merchant's own reference number.

---

## Kafka Events Published

The Payments Service publishes to the following Kafka topics:

| Topic | Event Types | Consumers |
|---|---|---|
| `payments.transactions` | `INITIATED`, `AUTHORISED`, `CAPTURED`, `DECLINED`, `FAILED` | Risk Service, Data Pipeline |
| `payments.refunds` | `REFUND_INITIATED`, `REFUND_COMPLETED`, `REFUND_FAILED` | Data Pipeline, Finance Systems |
| `payments.settlements` | `SETTLEMENT_BATCH_COMPLETED` | Finance Systems |

**Event Schema (payments.transactions):**
```json
{
  "event_type": "TRANSACTION_AUTHORISED",
  "transaction_id": "txn_xyz789",
  "amount": 10050,
  "currency": "GBP",
  "gateway": "stripe",
  "risk_score": null,
  "timestamp": "2025-01-15T10:30:05Z",
  "metadata": {}
}
```

---

## Gateway Integrations

### Stripe
- Used for card-present and most card-not-present transactions
- Webhooks received at `/payments/webhooks/stripe` — validated using Stripe signature header
- Stripe dashboard access available to Payments team via LastPass shared account

### Adyen
- Used for European card transactions and alternative payment methods
- Webhooks received at `/payments/webhooks/adyen`
- Adyen test environment available via `https://ca-test.adyen.com`

---

## Error Codes

| Code | Meaning | Action |
|---|---|---|
| `INSUFFICIENT_FUNDS` | Card declined — insufficient funds | Notify customer |
| `CARD_EXPIRED` | Card expiry date in the past | Ask customer to update payment method |
| `GATEWAY_TIMEOUT` | External gateway did not respond in 10s | Retry with exponential backoff |
| `DUPLICATE_TRANSACTION` | Idempotency key already used | Return cached response, do not retry |
| `FRAUD_DECLINE` | Blocked by Risk Service | Do not retry — log for review |

---

## Related Documents

- `system_overview.md` — Platform architecture
- `incident_response.md` — What to do when payments go down
- `deployment_guide.md` — Deploying the payments service
