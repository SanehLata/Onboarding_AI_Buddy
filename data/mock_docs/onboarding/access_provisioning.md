# Access Provisioning Guide

**Last Updated:** January 2025
**Owner:** IT Security & Engineering People Team
**Tags:** onboarding, access, provisioning, servicenow, ad-groups, permissions

---

## Overview

This page explains how access is provisioned for new engineers at TechCorp, what systems require approval, expected timelines, and how to request additional access after onboarding.

---

## How Access Provisioning Works

When you join a team, the Onboarding Buddy system automatically raises access tickets on your behalf within minutes of your profile being created. You do not need to raise these yourself.

The system creates tickets for all systems required by your team. You can track the status of your tickets in ServiceNow at `https://techcorp.service-now.com`.

---

## Access by System

### Jira
- **Ticket type:** ACCESS_REQUEST
- **Default level:** Developer
- **Approval required:** No
- **SLA:** Provisioned within 24 hours
- **Action required:** None — check your email for the login invitation

### Confluence
- **Ticket type:** ACCESS_REQUEST
- **Default level:** Contributor (read + edit)
- **Approval required:** No
- **SLA:** Provisioned within 24 hours
- **Action required:** None — same login as Jira (Atlassian SSO)

### GitHub
- **Ticket type:** ACCESS_REQUEST
- **Default level:** Write access to team repositories
- **Approval required:** Yes — your manager approves
- **SLA:** Provisioned within 8 hours after manager approval
- **Action required:** Accept the organisation invite sent to your corporate email

### ServiceNow
- **Ticket type:** CHANGE_REQUEST
- **Default level:** Requester (raise and track tickets)
- **Approval required:** Yes — your manager approves
- **SLA:** Provisioned within 48 hours
- **Action required:** None — SSO login via Okta

### Unix / Linux Servers
- **Ticket type:** SECURITY_REQUEST
- **Default level:** Development and staging environments only
- **Approval required:** Yes — manager approval + security review
- **SLA:** 72 hours
- **Action required:** Submit your SSH public key via ServiceNow — see `vpn_access.md`

### Snowflake
- **Ticket type:** DATA_ACCESS_REQUEST
- **Default level:** Read access to curated datasets
- **Approval required:** Yes — manager approval + data governance review
- **SLA:** 48 hours
- **Action required:** None — SSO login via Okta once provisioned

---

## Active Directory (AD) Groups

AD groups control access to internal services, shared drives, and security-sensitive systems.

Your Onboarding Buddy system will request the following AD groups for your team:

| Team | AD Groups Requested |
|---|---|
| Payments Engineering | `grp-payments-eng`, `grp-engineering-all`, `grp-kafka-dev` |
| Risk & Compliance | `grp-risk-eng`, `grp-engineering-all`, `grp-snowflake-read` |
| Platform Engineering | `grp-platform-eng`, `grp-engineering-all`, `grp-kubernetes-dev` |
| Data Engineering | `grp-data-eng`, `grp-engineering-all`, `grp-snowflake-write-dev` |
| Auth & Identity | `grp-auth-eng`, `grp-engineering-all`, `grp-security-review` |

AD group provisioning takes up to 24 hours after manager approval.

---

## Tracking Your Access Tickets

1. Log into ServiceNow: `https://techcorp.service-now.com`
2. Navigate to **My Requests**
3. You will see all tickets raised by the Onboarding Buddy system
4. Each ticket shows current status: `Open`, `In Progress`, `Pending Approval`, `Resolved`

If any ticket has been in `Open` status for more than 48 hours, contact your manager.

---

## Requesting Additional Access

If you need access to a system not covered in your standard onboarding:

1. Log into ServiceNow
2. Select **New Request → Access Request**
3. Fill in the system name, access level required, and business justification
4. Your manager will receive an approval request automatically
5. CC your manager on Slack to expedite approval

---

## Production Access

Production environment access is not included in standard onboarding. To request production access:

- Must have completed 30 days at TechCorp
- Must have manager recommendation
- Must complete the **Production Access Security Briefing** (1-hour session, scheduled via ServiceNow)
- Submit a `PROD_ACCESS_REQUEST` in ServiceNow

Production access is reviewed every 6 months. Unused access is revoked automatically.

---

## Access Revocation

If you change teams or leave TechCorp, access is revoked within 24 hours of the change being processed by HR. If you believe your access has been incorrectly revoked, contact `it-helpdesk@techcorp.com`.

---

## Related Documents

- `vpn_access.md` — VPN and SSH key setup
- `day1_checklist.md` — First day checklist
- `tools_setup.md` — Developer environment setup
