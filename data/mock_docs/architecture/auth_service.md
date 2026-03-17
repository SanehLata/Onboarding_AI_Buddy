# Auth Service — Architecture & Developer Guide

**Last Updated:** January 2025
**Owner:** Auth & Identity Team
**Tags:** architecture, auth, authentication, authorisation, oauth2, jwt, sso

---

## Overview

The Auth Service is TechCorp's centralised authentication and authorisation platform. It handles all user login flows, token issuance, session management, and permission enforcement across every internal and external-facing application.

**Team:** Auth & Identity
**Manager:** Rachel Kim (rachel.kim@techcorp.com)
**Slack:** `#auth-eng`
**On-call:** PagerDuty — Auth & Identity rotation

---

## Responsibilities

- User authentication via username/password, SSO (Okta), and API key
- JWT access token and refresh token issuance
- Token validation for all downstream services
- OAuth2 authorisation server for third-party integrations
- Role-based access control (RBAC) — permission definitions and enforcement
- Multi-factor authentication (MFA) flows

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11 |
| Framework | FastAPI |
| Database | PostgreSQL 15 (RDS) |
| Cache | Redis 7 (ElastiCache) |
| Identity Provider | Okta |
| Protocol | OAuth2, OpenID Connect |
| Token Format | JWT (RS256 signed) |
| Deployment | Kubernetes (EKS) |

---

## Core API Endpoints

### POST `/auth/login`
Authenticates a user with email and password. Returns an access token and refresh token.

**Request:**
```json
{
  "email": "user@techcorp.com",
  "password": "••••••••",
  "mfa_code": "123456"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiJ9...",
  "refresh_token": "eyJhbGciOiJSUzI1NiJ9...",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

### POST `/auth/refresh`
Issues a new access token using a valid refresh token.

### POST `/auth/logout`
Revokes the refresh token and invalidates the session.

### GET `/auth/me`
Returns the authenticated user's profile and permissions.

### POST `/auth/validate`
Internal endpoint — used by other services to validate a JWT without making a full auth call. Returns user claims if valid.

---

## JWT Structure

All access tokens are signed using RS256. Services validate tokens using the public key available at `/auth/.well-known/jwks.json`.

**Access Token Claims:**
```json
{
  "sub": "user_id_uuid",
  "email": "user@techcorp.com",
  "roles": ["engineer", "payments-team"],
  "permissions": ["payments:read", "payments:write"],
  "iat": 1704067200,
  "exp": 1704070800,
  "iss": "https://auth.techcorp.internal"
}
```

**Token Lifetimes:**
- Access token: 1 hour
- Refresh token: 30 days (rotated on each use)

---

## How Other Services Authenticate Requests

Every service in TechCorp validates incoming requests by checking the JWT in the `Authorization: Bearer <token>` header.

**Recommended approach (Python):**
```python
import httpx

def validate_token(token: str) -> dict:
    response = httpx.post(
        "https://auth.techcorp.internal/auth/validate",
        headers={"Authorization": f"Bearer {token}"}
    )
    response.raise_for_status()
    return response.json()  # Returns user claims
```

Do not implement your own JWT validation logic — always use the `/auth/validate` endpoint to ensure revocation is respected.

---

## SSO Integration (Okta)

External users authenticate via Okta SSO. The flow is standard OAuth2 Authorization Code with PKCE:

1. User is redirected to `https://techcorp.okta.com/oauth2/v1/authorize`
2. User authenticates with Okta (includes MFA)
3. Okta redirects back with an authorisation code
4. Auth service exchanges code for Okta tokens
5. Auth service issues TechCorp JWT to the client

SSO client configuration is managed in Terraform — do not edit it manually in the Okta console.

---

## RBAC — Roles and Permissions

Roles are defined in PostgreSQL and cached in Redis with a 5-minute TTL.

**Standard Engineering Roles:**
| Role | Description |
|---|---|
| `engineer` | Base role for all engineers |
| `senior-engineer` | Additional production access |
| `team-lead` | Can approve access requests |
| `admin` | Full system access — requires approval |

**Service-Level Permissions:**
Each service defines its own permission scopes. Example for Payments:
- `payments:read` — Read transaction data
- `payments:write` — Initiate or modify transactions
- `payments:admin` — Administrative operations

---

## Known Issues & Limitations

- Refresh token rotation is not yet implemented for mobile clients — tracked in JIRA-2341
- The `/auth/validate` endpoint adds ~5ms latency — consider caching the result for hot paths
- MFA is mandatory for all human users but optional for service accounts — this will be enforced in Q2

---

## Related Documents

- `system_overview.md` — Platform architecture context
- `microservices_map.md` — Which services depend on Auth
