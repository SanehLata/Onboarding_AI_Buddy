# Microservices Dependency Map

**Last Updated:** January 2025
**Owner:** Architecture Guild
**Tags:** architecture, microservices, dependencies, service-map

---

## Overview

This page maps every production service at TechCorp, its owning team, downstream dependencies, and Kafka topic interactions. Use this to understand the blast radius of a change before deploying.

---

## Service Inventory

| Service | Team | Language | Repo | SLA |
|---|---|---|---|---|
| API Gateway (Kong) | Platform | N/A (Kong config) | `infra-kong` | 99.99% |
| Auth Service | Auth & Identity | Python / FastAPI | `auth-service` | 99.99% |
| Payments Service | Payments Engineering | Java / Spring Boot | `payments-service` | 99.95% |
| Risk Service | Risk & Compliance | Python | `risk-service` | 99.90% |
| Notification Service | Platform | Python / FastAPI | `notification-service` | 99.90% |
| Data Pipeline | Data Engineering | Python / Airflow | `data-pipelines` | 99.80% |
| Reporting Service | Data Engineering | Python | `reporting-service` | 99.50% |
| Admin Portal (API) | Platform | Python / FastAPI | `admin-api` | 99.50% |

---

## Dependency Map

### API Gateway → Downstream
```
API Gateway (Kong)
├── Auth Service          (validates every inbound JWT)
├── Payments Service      (routes /payments/* traffic)
├── Risk Service          (routes /risk/* internal traffic)
└── Admin Portal API      (routes /admin/* traffic)
```

### Auth Service Dependencies
```
Auth Service
├── PostgreSQL (RDS)      — user store, roles, permissions
├── Redis (ElastiCache)   — session cache, token revocation list
└── Okta                  — SSO identity provider (external)
```
**No downstream service dependencies — Auth is a leaf dependency for everything else.**

### Payments Service Dependencies
```
Payments Service
├── Auth Service          — token validation on every request
├── PostgreSQL (RDS)      — transaction records
├── Redis (ElastiCache)   — idempotency keys, rate limiting
├── Stripe API            — card processing gateway (external)
├── Adyen API             — EU card processing gateway (external)
└── Kafka (MSK)           — publishes to payments.transactions, payments.refunds
```

**Services that depend on Payments:**
- Risk Service (consumes `payments.transactions`)
- Data Pipeline (consumes `payments.transactions`, `payments.refunds`)
- Notification Service (consumes `payments.transactions` for payment confirmation emails)

### Risk Service Dependencies
```
Risk Service
├── Auth Service          — token validation
├── Kafka (MSK)           — consumes payments.transactions
├── PostgreSQL (RDS)      — risk decisions, model metadata
└── Snowflake             — reads ML feature tables (batch)
```

**Services that depend on Risk:**
- Payments Service — consults Risk synchronously for real-time fraud scores on high-value transactions (> £500)

> ⚠️ **Circular dependency note:** Payments → Risk → Kafka → (async) Risk decision back to Payments. The synchronous Payments → Risk call has a 100ms timeout with fallback to `ALLOW`. If Risk is degraded, payments continue to process.

### Data Pipeline Dependencies
```
Data Pipeline (Airflow)
├── Kafka (MSK)           — consumes all service event topics
├── PostgreSQL (various)  — batch extraction via CDC
├── S3                    — raw data landing zone
├── Snowflake             — destination for all transformed data
└── dbt                   — transformation layer
```

---

## Kafka Topic Map

| Topic | Producer | Consumers |
|---|---|---|
| `payments.transactions` | Payments Service | Risk Service, Data Pipeline, Notification Service |
| `payments.refunds` | Payments Service | Data Pipeline, Finance Systems |
| `payments.settlements` | Payments Service | Finance Systems |
| `risk.decisions` | Risk Service | Payments Service (sync fallback) |
| `auth.login_events` | Auth Service | Data Pipeline, Security Monitoring |
| `notifications.outbound` | Notification Service | Email Provider (SendGrid) |

---

## Critical Paths

### Payment Processing (P99 critical)
```
Client → API Gateway → Auth (validate) → Payments → Risk (sync, 100ms timeout) → Stripe/Adyen → Kafka → Data Pipeline
```
If **Auth** is down: All payments fail.
If **Risk** is slow: Payments proceed after 100ms timeout (with elevated fraud risk).
If **Stripe** is down: Payments fail — Adyen is not an automatic fallback, requires manual routing change.

### Data Freshness (Analytics critical)
```
PostgreSQL (CDC) → Kafka → Snowflake connector → Raw tables → Airflow → dbt → Mart tables
```
If **Kafka** is down: Streaming ingestion stops — batch backfill required.
If **Airflow** is down: Batch jobs do not run — data goes stale after 24 hours.
If **dbt** fails: Mart tables stop updating — analysts see stale data.

---

## Runbook Contacts

| Service | Primary On-Call | Escalation |
|---|---|---|
| Auth Service | Auth & Identity on-call | Rachel Kim |
| Payments Service | Payments on-call | Sarah Mitchell |
| Risk Service | Risk on-call | James Thornton |
| Data Pipeline | Data Engineering on-call | Marcus Lee |
| Infrastructure / Kafka | Platform on-call | Priya Sharma |

---

## Related Documents

- `system_overview.md` — Platform architecture overview
- `incident_response.md` — Incident response procedures
- `auth_service.md` — Auth service deep dive
- `payments_api.md` — Payments service deep dive
