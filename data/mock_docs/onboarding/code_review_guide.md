# Code Review Guide

**Last Updated:** January 2025
**Owner:** Engineering Leadership
**Tags:** onboarding, code-review, pull-requests, git, quality

---

## Overview

Code review is one of the most important practices in TechCorp Engineering. This guide explains what we expect from both authors and reviewers.

---

## As a PR Author

### Before You Open a PR
- Ensure all unit tests pass locally: `pytest` or `mvn test`
- Run pre-commit hooks: `pre-commit run --all-files`
- Self-review your diff — read every line as if you are the reviewer
- Remove all debug logs, commented-out code, and TODO comments (or create Jira tickets for them)
- Confirm the PR references the Jira ticket in the title: `[JIRA-123] Add payment retry logic`

### PR Size
Keep PRs small and focused. A PR should do one thing.

| PR Size | Lines Changed | Outcome |
|---|---|---|
| Ideal | < 200 lines | Fast, thorough review |
| Acceptable | 200–400 lines | Review may take longer |
| Too large | > 400 lines | Break it up — reviewer will ask you to |

### Writing a Good PR Description
Every PR description should include:

```markdown
## What
Brief description of what this PR does.

## Why
The business or technical reason this change is needed. Link the Jira ticket.

## How
Summary of the approach taken and any notable technical decisions.

## Testing
How you tested this. Include: unit tests added, manual testing steps, edge cases considered.

## Screenshots (if UI changes)
Before and after screenshots.

## Checklist
- [ ] Unit tests added or updated
- [ ] Pre-commit hooks pass
- [ ] Reviewed my own diff
- [ ] No secrets or credentials in code
```

---

## As a Reviewer

### Response Time
- **Acknowledge** a review request within 2 hours during business hours
- **Complete** the review within 1 business day
- If you cannot review within 1 business day, comment on the PR to let the author know

### How to Comment

**Use these prefixes to signal your intent clearly:**

| Prefix | Meaning |
|---|---|
| `BLOCKING:` | Must be fixed before merge — this is a defect or a significant issue |
| `SUGGESTION:` | Improvement worth considering but not required |
| `QUESTION:` | Asking for clarification — not requesting a change |
| `NIT:` | Minor style or formatting point — author can decide |
| `PRAISE:` | Genuinely good code — say so explicitly |

**Example comments:**
```
BLOCKING: This will throw a NullPointerException if `user` is None — add a null check here.

SUGGESTION: Consider extracting this logic into a separate function for testability.

QUESTION: Why is the retry limit set to 3 here? Is this a business requirement?

NIT: s/recieve/receive

PRAISE: Clean use of the repository pattern here — makes this very easy to test.
```

### What to Look For
- **Correctness** — Does the code do what the PR description says?
- **Edge cases** — What happens with null inputs, empty lists, or unexpected values?
- **Security** — Any hardcoded credentials, injection vulnerabilities, or exposed sensitive data?
- **Performance** — Any obvious N+1 queries or unbounded loops?
- **Tests** — Are the tests meaningful or just coverage padding?
- **Naming** — Are variables, functions, and classes clearly named?

### What Not to Do
- Do not block a PR over personal style preferences not covered by the linter
- Do not leave a review as `Changes Requested` without at least one `BLOCKING:` comment
- Do not approve without reading the code — rubber stamp approvals are harmful
- Do not make the review process adversarial — we are improving the code, not criticising the person

---

## Merging a PR

- All `BLOCKING:` comments must be resolved before merging
- At least one approval required — two for changes to core services
- Do not merge your own PR — someone else must click merge
- Use **Squash and Merge** for feature branches — keeps the main branch history clean
- Delete the branch after merging

---

## Hotfixes

For urgent production fixes:
- Branch from `main`, prefix with `hotfix/`
- PR requires one approval from a senior engineer
- Can bypass the standard review turnaround time — message in `#incidents` for expedited review
- Must still pass all automated checks

---

## Related Documents

- `team_norms.md` — Git branch naming conventions
- `deployment_guide.md` — What happens after your PR is merged
- `logging_standards.md` — What to log in your code
