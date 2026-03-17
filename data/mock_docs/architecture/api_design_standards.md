# API Design Standards

**Last Updated:** January 2025
**Owner:** Architecture Guild
**Tags:** architecture, api-design, rest, standards, versioning

---

## Overview

All internal and external APIs at TechCorp follow these design standards. Consistency across services reduces the cognitive load for developers integrating with multiple services and makes onboarding faster.

---

## General Principles

1. **REST over RPC** — use resource-oriented URLs, not action-oriented ones
2. **Predictable** — a developer should be able to guess the endpoint structure for a new resource
3. **Fail clearly** — errors should be informative and machine-readable
4. **Versioned** — breaking changes go in a new version, never silently

---

## URL Structure

```
https://{service}.techcorp.internal/v{version}/{resource}/{id}/{sub-resource}
```

**Examples:**
```
GET  /v1/payments/txn_abc123                  — get a transaction
POST /v1/payments                             — create a transaction
GET  /v1/payments/txn_abc123/refunds          — list refunds for a transaction
POST /v1/payments/txn_abc123/refunds          — create a refund
GET  /v1/users/usr_xyz/permissions            — get user permissions
```

**Rules:**
- Always lowercase, hyphen-separated for multi-word resources: `/payment-methods` not `/paymentMethods`
- Resource names are always plural nouns: `/transactions` not `/transaction`
- Actions that don't map to CRUD use a verb suffix: `/payments/txn_abc/capture`, `/payments/txn_abc/void`
- Never put verbs in the base path: `/v1/getPayments` is wrong

---

## HTTP Methods

| Method | Use | Idempotent |
|---|---|---|
| GET | Retrieve a resource or list | Yes |
| POST | Create a resource or trigger an action | No |
| PUT | Replace a resource entirely | Yes |
| PATCH | Update specific fields of a resource | No |
| DELETE | Remove a resource | Yes |

---

## Request & Response Format

All requests and responses use JSON. Always set:
```
Content-Type: application/json
Accept: application/json
```

### Standard Response Envelope

**Success (single resource):**
```json
{
  "data": {
    "id": "txn_abc123",
    "status": "CAPTURED",
    "amount": 10050
  }
}
```

**Success (list):**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 143,
    "next_cursor": "cursor_xyz"
  }
}
```

**Error:**
```json
{
  "error": {
    "code": "PAYMENT_DECLINED",
    "message": "The payment was declined by the issuing bank.",
    "details": "Insufficient funds.",
    "request_id": "req_abc123",
    "documentation_url": "https://docs.techcorp.com/errors/PAYMENT_DECLINED"
  }
}
```

---

## HTTP Status Codes

| Code | When to use |
|---|---|
| 200 | Successful GET, PUT, PATCH |
| 201 | Successful POST that created a resource |
| 204 | Successful DELETE (no body) |
| 400 | Client sent invalid data |
| 401 | Missing or invalid authentication |
| 403 | Authenticated but not authorised |
| 404 | Resource does not exist |
| 409 | Conflict — e.g., duplicate idempotency key |
| 422 | Validation error — data format is correct but values are invalid |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
| 503 | Service unavailable |

Never return 200 with an error body. The HTTP status code must reflect the actual outcome.

---

## Pagination

All list endpoints must support cursor-based pagination:

```
GET /v1/transactions?cursor=cursor_xyz&per_page=20
```

- Default page size: 20
- Maximum page size: 100
- Always return a `next_cursor` in the response — `null` when there are no more results
- Do not use offset-based pagination for large datasets — it degrades at scale

---

## Versioning

- Version is in the URL path: `/v1/`, `/v2/`
- Backwards-compatible changes do not require a version bump: adding a new optional field, adding a new endpoint
- Breaking changes always require a new version: removing a field, changing a field type, changing auth behaviour
- Old versions are supported for 12 months after a new version is released
- Deprecation notice must be emailed to all API consumers and posted in `#announcements` at least 90 days before sunset

---

## Required Headers

| Header | Required | Purpose |
|---|---|---|
| `Authorization` | Yes | `Bearer <jwt>` |
| `Content-Type` | Yes (POST/PUT/PATCH) | `application/json` |
| `Idempotency-Key` | Yes (POST payment/refund) | Prevent duplicate processing |
| `X-Request-ID` | Recommended | Passed through to logs for tracing |
| `X-Client-Version` | Recommended | Helps debug client-specific issues |

---

## Related Documents

- `auth_service.md` — How to authenticate API requests
- `payments_api.md` — Payments API reference
- `logging_standards.md` — What to log in API handlers
