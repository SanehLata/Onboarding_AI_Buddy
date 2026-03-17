# System Overview — TechCorp Platform Architecture

**Last Updated:** January 2025
**Owner:** Architecture Guild
**Tags:** architecture, system-overview, microservices, platform

---

## Overview

TechCorp operates a microservices-based platform hosted on AWS (eu-west-1 primary, us-east-1 DR). The platform processes over 2 million transactions per day across payment processing, risk scoring, and data analytics workloads.

This document is the starting point for understanding our architecture. Read this before any team-specific architecture docs.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Clients                              │
│              (Web, Mobile, Partner APIs)                    │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway (Kong)                        │
│         Rate limiting · Auth · Routing · Logging            │
└──────┬──────────┬──────────┬───────────┬────────────────────┘
       │          │          │           │
       ▼          ▼          ▼           ▼
  ┌─────────┐ ┌───────┐ ┌────────┐ ┌──────────┐
  │ Auth    │ │Payment│ │  Risk  │ │   Data   │
  │Service  │ │Service│ │Service │ │ Pipeline │
  └────┬────┘ └───┬───┘ └───┬────┘ └────┬─────┘
       │          │         │            │
       └──────────┴────┬────┘            │
                       ▼                 ▼
               ┌──────────────┐   ┌────────────┐
               │   Kafka      │   │  Snowflake │
               │ Event Bus    │   │  Data WH   │
               └──────────────┘   └────────────┘
```

---

## Core Services

### API Gateway (Kong)
- **Purpose:** Single entry point for all external traffic
- **Responsibilities:** TLS termination, rate limiting, JWT validation, request routing
- **Team:** Platform Engineering
- **SLA:** 99.99% uptime

### Auth Service
- **Purpose:** Authentication and authorisation for all internal and external requests
- **Tech:** Python / FastAPI, PostgreSQL, Redis
- **Team:** Auth & Identity
- **See:** `auth_service.md` for full details

### Payments Service
- **Purpose:** Payment processing, transaction management, gateway integrations
- **Tech:** Java / Spring Boot, PostgreSQL, Kafka
- **Team:** Payments Engineering
- **See:** `payments_api.md` for full details

### Risk Service
- **Purpose:** Real-time fraud detection and risk scoring
- **Tech:** Python, Scikit-learn, Kafka, PostgreSQL
- **Team:** Risk & Compliance

### Data Pipeline
- **Purpose:** ETL from operational databases to Snowflake data warehouse
- **Tech:** Python / Apache Airflow, dbt, Snowflake
- **Team:** Data Engineering
- **See:** `data_pipeline.md` for full details

---

## Infrastructure

### Cloud Provider
- **Primary:** AWS eu-west-1 (Ireland)
- **DR:** AWS us-east-1 (Virginia) — warm standby

### Container Orchestration
- Kubernetes (EKS) — all production services run on Kubernetes
- Helm charts for all service deployments
- ArgoCD for GitOps-based continuous deployment

### Databases
| Database | Type | Used By | Backup Policy |
|---|---|---|---|
| PostgreSQL (RDS) | Relational | Auth, Payments, Risk | Daily snapshots, 30-day retention |
| Redis (ElastiCache) | Cache / Session | Auth, Payments | No persistence — cache only |
| Snowflake | Data Warehouse | Data Engineering, Risk | Managed by Snowflake |
| DynamoDB | NoSQL | Platform config store | Point-in-time recovery enabled |

### Messaging
- **Kafka (MSK):** Async event streaming between Payments, Risk, and Data Pipeline
- **SQS:** Task queues for async job processing
- **SNS:** Fan-out notifications for alerts and events

---

## Observability Stack

| Tool | Purpose | URL |
|---|---|---|
| Grafana | Dashboards and metrics visualisation | `https://grafana.techcorp.internal` |
| Prometheus | Metrics collection | Internal — accessed via Grafana |
| Datadog | APM, log management, synthetics | `https://app.datadoghq.com` |
| PagerDuty | Alerting and on-call management | `https://techcorp.pagerduty.com` |
| CloudWatch | AWS infrastructure logs | AWS Console |

All services must emit:
- Request rate, error rate, and latency (RED metrics)
- Custom business metrics relevant to the service
- Structured JSON logs — see `logging_standards.md`

---

## Security Architecture

- All inter-service communication uses mutual TLS (mTLS) via Istio service mesh
- Secrets managed via AWS Secrets Manager — never in environment variables or code
- Network segmentation: public, private, and data subnets — no direct internet access to private services
- All data at rest encrypted using AES-256
- Penetration testing conducted quarterly

---

## Related Documents

- `microservices_map.md` — Detailed service dependency map
- `auth_service.md` — Auth service deep dive
- `payments_api.md` — Payments API reference
- `data_pipeline.md` — Data pipeline architecture
