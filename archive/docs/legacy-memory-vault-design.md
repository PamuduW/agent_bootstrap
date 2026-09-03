# Legacy public memory-vault design

> Historical design only. This document is not an active memory store and is
> not a source of truth. Phase 4 stores actual memory in a separate private
> repository.

The early Agentbot prototype kept a Git-tracked Markdown vault beside the
bootstrap configuration. Its generic organization used active context,
preferences, decisions, lessons, project indexes, and agent-relationship
notes. Agents could draft changes, while a human reviewed and committed them.

That prototype was retired because a public configuration repository cannot be
treated as private memory. Moving the directory under `archive/` did not change
its visibility or make its contents safe to publish. The prototype was removed
from the current branch during the Phase 4 migration gate; its previous files
remain recoverable from Git history if historical investigation is required.

The current Phase 4 design is maintained in the parent setup workspace under
`docs/designs/memory/`. That workspace location is stated as text because this
repository can also be cloned independently. The design uses one private,
Markdown-only repository with explicit validation, approval, backup, and Git
transport contracts. This historical note contains no active memory records,
personal preferences, project notes, or synchronization instructions.
