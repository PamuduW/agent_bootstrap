# Skills and integrations

## Curated sources

`skills.sources.yaml` is the canonical list of enabled repositories and skill
selections. Sources can select named skills or `skills: all`; an `exclude` list
removes unwanted upstream folders. GitHub uses `owner/repo`; explicit
`github.com/` and `gitlab.com/` prefixes are supported.

Agentbot clones each source before invoking the Skills CLI. A planned update
records the repository, manifest, global lock, and remote revisions, then
checks those inputs again before apply. A source failure makes the operation
fail even if other sources installed successfully.

## Lock ownership

Global `-g` installations are pinned in `~/.agents/.skill-lock.json`. The
repository `skills-lock.json` is a project-install stub. The formats and scopes
are different; do not copy the global lock into the project lock.

The global lock is the authority for curated machine installations. The
project stub remains empty until this repository intentionally adopts
project-local skill restoration.

## Reconciliation and removal

`skills prune` classifies candidates as `excluded`, `orphaned`, `stale-pin`, or
`manual`. It previews by default and requires `--yes` to write. Manual skills
are preserved unless explicitly included. `skills remove-manual` accepts exact
names and never treats an empty selection as permission to remove everything.
Agentbot-protected Graphify output is not a manual-removal candidate.

## Graphify

Dotfiles owns the `graphify` executable. Agentbot runs
`graphify install --platform agents` only when the CLI exists, then refreshes
assistant links and managed outputs. A missing CLI is a valid skip. Agentbot
does not build project graphs, install hooks, or add Graphify to the curated
Git-source manifest.

## Boost

Dotfiles owns the verified `boost` executable. Agentbot owns Claude, Codex,
and Cursor setup, feature policy, diagnostics, and removal through
`agentbot boost status|setup|off`. Setup wires whichever of those CLIs are
installed and skips the rest. A later run picks up a newly installed CLI.

Setup disables tracing upload and Boost auto-update, keeps BoostGraph and its
MCP changes disabled, and writes the declared policy from
`BOOST_FEATURE_POLICY` in `src/boost.py`. Repository `.boost/config.toml` files
can shadow global configuration; Doctor reports registered workspaces that
violate policy.

**Setup accepts Boost's preview terms on your behalf.** `boost init` is passed
`--accept-terms`, which accepts the JFrog Online Preview Agreement and Privacy
Notice without prompting. This is a deliberate choice recorded here rather than
a prompt suppressed quietly: on a fresh machine the unanswered prompt sat for
the full command timeout and then failed the whole Agentbot install. Boost
stores the acceptance in its own `~/.boost/config.toml`, so it only ever
applies the first time on a given machine. Selecting the Boost CLI component is
what opts you into this; if you would rather accept it yourself, remove
`--accept-terms` from `BoostIntegration.setup` and answer the prompt.
