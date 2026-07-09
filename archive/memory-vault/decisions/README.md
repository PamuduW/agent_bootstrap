# Decisions (ADRs)

Architecture Decision Records — **accepted decisions, not drafts**.

## Filename

```
YYYY-MM-DD-slug.md
```

Example: `2026-07-08-three-plane-architecture.md`

## Template

```markdown
# ADR: Title

**Date:** YYYY-MM-DD
**Status:** accepted | superseded | deprecated

## Context
What problem or choice forced a decision?

## Decision
What we chose.

## Consequences
Trade-offs, what becomes easier/harder.
```

## Rules

- One decision per file; slug matches the topic
- **Immutable once accepted** — supersede with a new dated ADR, don't edit in place
- Agents may draft; you approve and commit
