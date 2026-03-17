# Team Norms & Working Agreements

**Last Updated:** January 2025
**Owner:** Engineering Leadership
**Tags:** onboarding, team-norms, culture, working-agreements

---

## Overview

These are the shared working agreements across TechCorp Engineering. Individual teams may have additional norms — your manager will walk you through team-specific ones in your first 1:1.

---

## Core Principles

**1. Default to async**
We are a hybrid team. Not everything needs a meeting. Use Slack threads, Confluence pages, and Jira comments for decisions that don't require real-time discussion. If a Slack thread runs longer than 10 messages with no resolution, move it to a meeting.

**2. Write things down**
If you make a decision, document it. Architecture decisions go in Confluence under the ADR (Architecture Decision Record) template. Meeting outcomes go in the meeting notes page. Runbook changes are committed to the repo.

**3. Blameless culture**
When something breaks, we focus on the system, not the person. Post-incident reviews are blameless. Admitting a mistake early is always better than hiding it. We assume good intent.

**4. Own your work end to end**
Engineers at TechCorp are responsible for their code in production. You write it, you deploy it, you monitor it, you fix it. On-call rotations apply to all engineers after their first 30 days.

**5. Code review is collaborative, not gatekeeping**
PRs should be reviewed within one business day. Review comments are suggestions unless marked `BLOCKING:`. Respond to all comments before merging, even if just to acknowledge.

---

## Communication Norms

### Slack
- **Response time:** Acknowledge messages in your team channel within 2 hours during business hours
- **Status updates:** Set your Slack status when in meetings, out of office, or heads-down focused
- **Direct messages:** For quick clarifications only. Anything that needs context or a decision goes in a channel
- **@here and @channel:** Only for urgent production issues or time-sensitive announcements
- **Threads:** Always use threads when replying to a channel message

### Email
- Used for formal communications, external vendors, and HR matters
- Internal engineering communication should default to Slack
- Aim to respond to emails within 24 hours

### Meetings
- All meetings must have an agenda shared at least 2 hours before
- Start on time. End on time or early.
- If you cannot add value, decline the meeting — that is acceptable and encouraged
- All recurring meetings have a rotating note-taker

---

## Development Norms

### Git & Pull Requests
- Branch naming: `feature/JIRA-123-short-description`, `fix/JIRA-456-bug-name`, `hotfix/JIRA-789-issue`
- Commit messages follow Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`
- PRs must reference the Jira ticket number in the title
- No PR should be larger than 400 lines of change — break it up if needed
- All PRs require at least one approval before merging
- Do not merge your own PRs — have someone else do it

### Code Quality
- All new code must have unit tests with minimum 80% coverage
- Run `pre-commit` hooks locally before pushing — they check linting and formatting
- No secrets, credentials, or API keys in code — use environment variables
- All database migrations must be reversible

### Deployments
- No deployments on Fridays after 3:00 PM or before major holidays
- Production deployments require a deployment ticket in Jira
- All production deployments must be monitored for 30 minutes post-release
- Rollback procedure must be documented before deployment — see `deployment_guide.md`

---

## On-Call

All engineers join the on-call rotation after their first 30 days. On-call responsibilities:

- Respond to P1 alerts within 15 minutes
- Respond to P2 alerts within 1 hour
- Log all incidents in ServiceNow
- Write a brief incident summary in Confluence within 24 hours of resolution
- Escalate to your manager if you cannot resolve within 30 minutes

On-call schedule is managed in PagerDuty. Your manager will add you before your first rotation.

---

## Performance & Growth

- Engineering performance reviews happen twice a year (June and December)
- Engineers are expected to maintain an up-to-date Jira board — your manager reviews sprint progress weekly
- Each engineer sets quarterly OKRs aligned with the team roadmap
- Learning budget: $1,500 per year for courses, books, and conferences — submit via Workday

---

## Related Documents

- `communication_channels.md` — Full list of Slack channels and email lists
- `day1_checklist.md` — Your first day guide
- `deployment_guide.md` — How we deploy to production
