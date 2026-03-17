# Data Pipeline — Architecture & Developer Guide

**Last Updated:** January 2025
**Owner:** Data Engineering Team
**Tags:** architecture, data-pipeline, airflow, dbt, snowflake, kafka, etl

---

## Overview

TechCorp's data pipeline ingests events from operational systems, transforms them into analytics-ready datasets, and loads them into Snowflake for consumption by analysts, data scientists, and the Risk team's ML models.

**Team:** Data Engineering
**Manager:** Marcus Lee (marcus.lee@techcorp.com)
**Slack:** `#data-eng` | Alerts: `#pipeline-alerts`

---

## Architecture Overview

```
Operational Systems          Ingestion Layer         Transformation        Analytics
┌──────────────┐            ┌────────────┐          ┌──────────┐         ┌──────────┐
│  PostgreSQL  │──CDC──────▶│            │          │          │         │ Snowflake│
│  (Payments) │            │   Kafka    │──────────▶│   dbt    │────────▶│  (Prod)  │
│  PostgreSQL  │──CDC──────▶│   (MSK)   │          │          │         └──────────┘
│  (Auth)     │            └────────────┘          └──────────┘
│  PostgreSQL  │──CDC──────▶┌────────────┐
│  (Risk)     │            │  Airflow   │──────────▶┌──────────┐
└──────────────┘            │  (Batch)  │           │  Raw S3  │
                            └────────────┘          └──────────┘
```

### Two Ingestion Patterns

**1. Streaming (Kafka → Snowflake)**
Used for high-volume, low-latency data:
- Payment transaction events
- Fraud score updates
- Auth login events

Events flow from Kafka topics into Snowflake staging tables via a Kafka Snowflake connector. Latency: under 60 seconds.

**2. Batch (Airflow → S3 → Snowflake)**
Used for bulk historical loads and systems without Kafka:
- Finance reconciliation exports
- Third-party vendor data
- Regulatory reporting snapshots

Batch jobs run on defined schedules managed in Airflow. Data lands in S3 raw buckets then is loaded via Snowflake COPY commands.

---

## Airflow

**URL:** `https://airflow.techcorp.internal` (VPN required)
**Version:** Apache Airflow 2.8

### DAG Structure
All DAGs live in the `data-pipelines` GitHub repository under `/dags`. DAGs are deployed automatically via ArgoCD on merge to main.

**DAG naming convention:**
- `batch_{source}_{frequency}` — e.g., `batch_finance_daily`
- `stream_{source}_{destination}` — e.g., `stream_payments_snowflake`
- `transform_{domain}_{model_group}` — e.g., `transform_payments_daily_summary`

### Adding a New DAG
1. Create your DAG file in `/dags` following the template in `/dags/templates/batch_template.py`
2. All DAGs must include: owner, start_date, retries (minimum 2), retry_delay (5 minutes), SLA (in minutes)
3. Add a Jira ticket reference in the DAG description
4. Open a PR — another Data Engineering member must review

### Monitoring DAGs
- Airflow UI shows run history, duration, and failure logs
- All DAG failures trigger a PagerDuty alert if the DAG has `sla_miss_callback` set
- `#pipeline-alerts` Slack channel receives automatic failure notifications

---

## dbt

**Version:** dbt-snowflake 1.7
**Project:** `techcorp_analytics`

### Layer Structure

| Layer | Purpose | Example |
|---|---|---|
| `raw` | Unmodified source data | `raw.payments_transactions` |
| `staging` | Cleaned, renamed, typed | `staging.stg_payments_transactions` |
| `intermediate` | Business logic joins | `int_customer_payment_summary` |
| `mart` | Analytics-ready tables | `mart.daily_revenue_by_product` |

### Running dbt Locally
```bash
# Set up profile
cp profiles.yml.example ~/.dbt/profiles.yml
# Fill in your Snowflake credentials

# Install dependencies
dbt deps

# Run all models
dbt run

# Run specific model + dependencies
dbt run --select +mart.daily_revenue_by_product

# Run tests
dbt test

# Generate and serve docs
dbt docs generate
dbt docs serve
```

### Adding a New dbt Model
1. Create the `.sql` file in the appropriate layer directory
2. Add a corresponding YAML entry in the `schema.yml` of that layer with at minimum:
   - `description`
   - `columns` with descriptions for all columns
   - At least one `not_null` and one `unique` test on the primary key
3. Run `dbt test` — all tests must pass before PR

---

## Snowflake Structure

**Databases:**
| Database | Purpose | Access |
|---|---|---|
| `RAW_DB` | Unprocessed source data | Data Engineering only |
| `ANALYTICS_DB` | dbt-transformed marts | Analysts + Data Scientists |
| `SANDBOX_DB` | Ad-hoc exploration | All engineers with Snowflake access |

**Roles:**
- `ENGINEER_READONLY` — Read access to ANALYTICS_DB (default for new joiners)
- `ENGINEER_SANDBOX` — Write access to SANDBOX_DB
- `DATA_ENG_WRITER` — Write access to RAW_DB and ANALYTICS_DB (Data Engineering team only)

---

## SLAs

| Pipeline | SLA | Alert if breached |
|---|---|---|
| Payments streaming | Data in Snowflake within 2 minutes | PagerDuty P2 |
| Daily batch jobs | Complete by 6:00 AM EST | PagerDuty P2 |
| dbt transforms | Complete by 8:00 AM EST | PagerDuty P2 |
| ML feature pipeline | Complete by 7:00 AM EST | PagerDuty P1 (blocks Risk models) |

---

## Related Documents

- `system_overview.md` — Platform architecture
- `logging_standards.md` — Logging in pipeline jobs
- `incident_response.md` — What to do when a pipeline fails
