# Day 1 Checklist — New Developer Onboarding

**Last Updated:** January 2025
**Owner:** Engineering People Team
**Tags:** onboarding, day1, checklist, new-joiner

---

## Welcome to TechCorp Engineering

This checklist covers everything you need to complete on your first day. Work through it top to bottom. If anything is blocked, contact your manager or raise a ServiceNow ticket.

---

## Morning (9:00 AM – 12:00 PM)

### 1. Account Setup
- [ ] Log into your corporate laptop using the credentials emailed to your personal address
- [ ] Set up multi-factor authentication (MFA) on your corporate account — see `vpn_access.md` for instructions
- [ ] Change your temporary password immediately via the IT portal at `https://accounts.techcorp.com`
- [ ] Verify your corporate email is working by sending a test email to `it-helpdesk@techcorp.com`

### 2. Slack Setup
- [ ] Download Slack desktop app and sign into `techcorp.slack.com`
- [ ] Join your team channel — ask your manager for the channel name
- [ ] Join `#engineering-general` and `#announcements`
- [ ] Set your profile photo and display name (First Last, Team Name)
- [ ] Introduce yourself in your team channel

### 3. Access Requests
Your Onboarding Buddy system will have raised the following access tickets automatically. Check their status:
- [ ] Jira access ticket — should be provisioned within 4 hours
- [ ] Confluence access ticket — should be provisioned within 24 hours
- [ ] GitHub org invite — check your corporate email, approve within 24 hours
- [ ] ServiceNow access — provisioned within 48 hours

If any ticket has not been raised, notify your manager immediately.

---

## Afternoon (1:00 PM – 5:00 PM)

### 4. Development Environment
- [ ] Install required tools — see `tools_setup.md` for the full installation guide
- [ ] Clone your team's primary repository from GitHub — ask your manager for the repo name
- [ ] Run the local development environment using the README instructions in the repo
- [ ] Verify the app starts locally without errors

### 5. VPN & Remote Access
- [ ] Install the VPN client — see `vpn_access.md`
- [ ] Connect to the corporate VPN and verify you can reach internal services
- [ ] Test SSH access to the bastion host once Unix access is provisioned

### 6. First Meetings
- [ ] 1:1 with your manager — confirm time if not already in your calendar
- [ ] Meet your onboarding buddy (a senior engineer assigned to you for your first 30 days)
- [ ] Attend team standup — ask your manager for the time and Zoom link

---

## End of Day Checklist

Before finishing Day 1, confirm:
- [ ] All access requests are raised and tracking
- [ ] Local dev environment is running
- [ ] You are connected to Slack and active in your team channel
- [ ] Your 1:1 with your manager happened or is scheduled
- [ ] You have read `team_norms.md`

---

## Need Help?

| Issue | Contact |
|---|---|
| Laptop or hardware | `it-helpdesk@techcorp.com` |
| Access not provisioned | Raise ticket in ServiceNow or contact your manager |
| VPN issues | `vpn-support@techcorp.com` |
| General onboarding questions | Your assigned onboarding buddy or manager |

---

## Related Documents

- `team_norms.md` — How your team works day to day
- `tools_setup.md` — Complete developer environment setup guide
- `vpn_access.md` — VPN and remote access instructions
- `communication_channels.md` — Slack channels, email lists, and meeting cadences
