# Local Markdown ticket template

```markdown
---
ticket: <slug>/NN
status: ready
blocked_by: []
touches: [<area>]
devices: []
model: standard
worker:
---
# NN: <title, a behaviour not a component>

**Story:** As a <actor>, I want <capability>, so that <benefit>.

**Delivers:** the end-to-end behaviour this ticket makes work, from the actor's side. Brief: `.scratch/<slug>/alignment.md` · <outcome and approach it realises>.

**Blocked by:** <NN: title>, or "None (can start immediately)".

## Acceptance criteria
- [ ] Given <state>, when <action>, then <observable outcome>.
      Verify (code|agent|user): <command, test name or user check>
- [ ] …

## Comments
```
