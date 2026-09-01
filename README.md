# Agentbot

Agentbot is a local bootstrap CLI for agent policy, curated Agent Skills, and
registered workspace outputs. It keeps authored policy in canonical Markdown,
renders provider-specific files, and makes every mutating flow explicit.

The supported interfaces are `./install.sh` from the checkout and `agentbot`
after installation. Run `agentbot help` for the complete command index or
`agentbot help COMMAND` for one command's options, effects, and examples.

## Requirements

- Bash, Git, Python 3, and PyYAML
- Node.js/npm and `npx` for skill installation and updates
- an optional `graphify` CLI for generic Graphify Agent Skills integration
- an optional Dotfiles-installed `boost` CLI for Claude/Codex shell integration

Install Python requirements in a repository-local environment when needed:

```bash
python3 -m pip install -r requirements.txt
```

## Install

Clone the repository anywhere, then run the explicit install flow:

```bash
git clone <your-remote>/agent_bootstrap /any/path/agent_bootstrap
cd /any/path/agent_bootstrap
./install.sh install
```

Install checks the repository first, installs enabled skills, synchronizes the
optional generic Graphify skill, configures an installed Boost CLI for Claude
and Codex, refreshes managed global outputs, runs Doctor, and links
`bin/agentbot` to `~/bin/agentbot`. Ensure `~/bin` is on `PATH`.

Installation does not copy the repository. The active launcher remains linked
to the checkout that installed it, which may differ from another development
clone or from Dotfiles' expected sibling checkout. Verify what will run before
maintenance with:

```bash
command -v agentbot
readlink -f "$(command -v agentbot)"
```

`AGENTBOT_HOME` is resolved from the executable location and exported for child
commands. Private state lives under
`${XDG_CONFIG_HOME:-$HOME/.config}/agentbot`; it is never stored in the clone.

## Common workflows

```bash
agentbot                         # open the TTY menu
agentbot status                 # inspect current managed state
agentbot doctor                 # validate skills, locks, links, and outputs
agentbot update --dry-run       # preview the update transaction
agentbot update                 # plan, confirm when required, then apply
agentbot token                  # manage the optional private GitHub token
agentbot boot /path/to/repo     # render and register one repository
agentbot workspaces             # list registered workspaces
agentbot resync --dry-run --all # preview all registered workspaces
```

The TUI uses the same command model and lifecycle paths as the direct CLI. Its
Command Lib is a selectable index rather than a second hand-maintained help
document. GitHub token input is silent; only a fingerprint is shown unless the
user accepts an explicit reveal warning.

## Skills

[`skills.sources.yaml`](skills.sources.yaml) is the canonical curated-source
manifest. Global per-skill pins live in `~/.agents/.skill-lock.json`; the
committed [`skills-lock.json`](skills-lock.json) is only a project stub.

```bash
./install.sh skills install
./install.sh skills update
./install.sh skills list
./install.sh skills doctor
./install.sh skills prune          # report skills no active source wants
./install.sh skills prune --yes    # and remove them
./install.sh skills remove-manual  # preview user-placed skills
./install.sh skills remove-manual gpt-taste mermaid --yes
./install.sh full                  # install, then update, in one command
```

`skills prune` reconciles the store against the manifest and classifies every
skill: `excluded` (its source installs it, the manifest excludes it),
`orphaned` (pinned to a source that is no longer active), `stale-pin` (in the
lock with no directory), and `manual` (user-placed, never removed unless you
pass `--include-manual`). It reports by default and only writes with `--yes`.

For manual skills, prefer `skills remove-manual`: it accepts exact names and
never treats an empty selection as permission to remove everything. The
interactive Agentbot menu exposes the same operation as an unchecked checkbox
list, confirms the selected names before deletion, and refreshes every agent
surface afterward. Graphify installations stamped by Agentbot's separate
Graphify integration are protected and do not appear in this list.

A `skills: all` source can refuse specific upstream names, which is how you keep
a repository's own test fixtures out of every agent's context:

```yaml
  - id: some-source
    repo: owner/repo
    skills: all
    exclude:
      - alpha
      - beta
```

`repo` is `owner/name` on GitHub. Prefix a supported host to install from
another forge:

```yaml
  - id: gitlab-ci-official
    repo: gitlab.com/gitlab-org/ci-cd/gitlab-ci-skill
    skills:
      - gitlab-ci-skill
```

Supported hosts are `github.com` and `gitlab.com`. The host prefix is also the
only form that accepts the nested group paths GitLab allows and GitHub does
not. Sources are cloned locally before install, so the Skills CLI itself never
needs to know which forge a source came from; the lock records the host as each
skill's `sourceType`.

Add a source to the manifest, then use `skills install`. Source discovery is
performed once per update plan, and apply verifies that the repository,
manifest, lock, and remote source revisions still match that plan.

Any source that fails to install makes the command exit nonzero, including when
other sources succeeded: a partial install leaves skills missing that the
manifest asked for. The report lists the ok / failed / skipped counts. Sources
that are deliberately skipped are not failures. A folder
copied directly into `~/.agents/skills/` remains a manual skill; Status and
Doctor report it as outside managed sources until the manifest owns it.

Graphify is separate from the curated `npx skills` manifest. Dotfiles owns CLI
installation. Agentbot runs only `graphify install --platform agents` when the
optional CLI already exists; it never builds project graphs or installs hooks.

Boost follows the same ownership split: Dotfiles owns the verified CLI binary;
Agentbot owns assistant setup and reporting. `agentbot install` skips Boost when
the CLI is absent. When present, it disables tracing upload and Boost
auto-update, enables local File Optimization for allowlisted reads, previews
Claude/Codex-only setup with BoostGraph disabled, and rejects graph, MCP, or
indexing changes before running Boost interactively.
Agentbot never passes `--accept-terms`; Boost presents its own agreement. Use
`agentbot boost status|setup|off` for inspection, repair, or removal.

A few details worth knowing.

A host row reads `unregistered` when Boost's hook files exist but the host's
config registers none of them, since the filter only runs once the host is told
about it, and `partial` when something registered is missing from disk. Both
Claude and Codex are judged this way.

`unsafe-config` also covers repository-level overrides. Boost reads the first
`.boost/config.toml` it finds — working directory, then git root, then home —
and does not merge them, so a repository config silently drops the global
`tracing.upload = false` inside that repository. Agentbot checks registered
workspaces and names any that leave upload enabled; `boost setup` cannot fix
those, because it writes the global file that is being shadowed.

Boost feature flags are a declared set, not a free-for-all. Boost's report UI
writes `user = <bool>` under `[feature_flags]`, and a user value beats JFrog's
remote default, so these change how both agents behave. `BOOST_FEATURE_POLICY`
in `src/boost.py` declares the intended value for each, and `agentbot boost
setup` writes the whole set:

| Flag | Policy | Why |
| --- | --- | --- |
| `boost-agent-facing-redaction` | on | Scrubs secrets and abbreviates paths in what the agent sees, not just in the local database |
| `boost-files-optimization` | on | Converts allowlisted document reads and shrinks large images in temporary local copies; originals remain unchanged and unsupported inputs fail open |
| `boost-mcp-toon-format` | on | Lossless JSON→TOON reformat of MCP responses; costs nothing when no MCP tool is called |
| `boost-english-abbreviation` | off | Aimed at article prose; in a code workspace it only makes tool output lossy |
| `boost-graph-integration` | off | BoostGraph writes MCP config and marker blocks into managed `CLAUDE.md`/`AGENTS.md` |

Two consequences worth knowing. **A toggle made in Boost's UI is reverted on the
next setup** — that is the intended behaviour, since one command should put the
machine in a known state, but it means the UI is not where these get changed.
Edit the policy map instead. And **leaving a flag unpinned is not neutral**: its
effective value falls back to a remote default JFrog can change without warning,
so an unpinned flag counts as diverged.

The `Feature flags` row lists what is pinned; `Flags off policy` appears with a
Doctor warning when something has changed them since setup. Flags outside the
declared set are left alone entirely.

A `stale` row means the hook and awareness files predate the installed CLI.
Boost stamps each one with the release that wrote it, and upgrading the binary
does not rewrite them — Dotfiles owns the binary, Agentbot owns the
integration, and neither triggers the other. `dotfiles full-update` closes this
in passing, since it runs `agentbot install` after the upgrade and setup
re-runs `boost init`; a bare `dotfiles update` does not. `agentbot boost setup`
rewrites them. Files carrying no version marker are left alone, since upstream
owns that comment.

`agentbot boost off` removes one host per call and never passes `--dry-run`
alongside `--uninstall`. In Boost v0.12.6 that combination is not a preview: it
performs the removal and prints the plan as though it had not.

Boost's `status-line` component edits `~/.claude/statusline-command.sh` in
place, keeping the Agentbot marker; Agentbot detects that, leaves the file alone
instead of refreshing it, and Doctor reports it. Run `agentbot boost off` to get
the managed statusline back. The managed statusline calls `boost status-line`
itself to show session savings; set `AGENTBOT_STATUSLINE_BOOST=0` to skip that
process spawn per render.

## Workspaces and policy ownership

`base/AGENTS.md` is the canonical project scaffold. A generated workspace
always includes `AGENTS.md`; Claude and Cursor outputs are selected
compatibility surfaces. Agentbot rewrites only its marked managed block and
preserves project-owned content. Unmarked conflicting files are not replaced.

Successful apply registers the canonical path in the private workspace
registry. Preview is the default for `workspace` and `resync`; `--yes` is
required to write. Removing a workspace record never deletes workspace files.

`global/AGENTS.md` is the sole authored machine policy. Global Codex and Claude
outputs, skill links, and the Claude statusline are generated from canonical
sources; do not edit generated adapters directly.

## Update safety

Update has two gates:

1. Validate the exact Agentbot origin, inspect local changes, fetch, and
   classify current/ahead/behind/diverged history. A clean confirmed behind
   checkout is fast-forwarded with `git pull --ff-only`. Dirty, ahead, and
   diverged state can be replaced after explicit approval.
2. Build one read-only lifecycle plan, confirm source-owned deltas once, verify
   the snapshot again, and apply skills plus managed surfaces under the shared
   rollback boundary.

Before replacement, Agentbot stashes tracked and untracked changes and creates
a timestamped `recovery/agentbot-*` branch for local commits. It resets only
after verifying those backups and a clean worktree. It never runs `git clean`,
deletes ignored files, removes recovery data, commits, pushes, or force-pushes.
A changed checkout exits with status 2 so its caller can restart the new code.
Detached, missing-upstream, declined, failed-fetch, and failed-recovery states
stop before downstream work.

`dotfiles full-update` is the unattended system-maintenance entrypoint. It
authorizes Agentbot repository recovery, reruns `agentbot install` once after a
self-update, and then runs `agentbot update --yes`. Inspect preserved work with
`git branch --list 'recovery/*'`, `git stash list`, `git show <recovery-branch>`,
and `git stash show --stat <stash-object-id>`.

## Architecture

```text
agent_bootstrap/
├── install.sh             # repository gate, prerequisites, token scope, CLI adapter
├── bin/agentbot           # repository gate and TTY launcher
├── src/
│   ├── commands.py        # canonical command metadata
│   ├── cli.py             # parser, composition root, exit policy
│   ├── lifecycle.py       # install/update/workspace orchestration
│   ├── diagnostics.py     # shared Status and Doctor snapshot
│   └── ...                # render, skills, Graphify, workspace modules
├── scripts/lib/tui.sh     # shared terminal presentation primitives
├── scripts/menus/         # thin interactive adapters
├── base/ and global/      # canonical policy sources
├── tests/                 # Python and focused shell suites
└── archive/               # retired designs and deferred capabilities
```

Python owns lifecycle behavior. Bash is limited to bootstrap/self-update,
controlling-TTY presentation, secret scoping, and process adapters.

## Validation

Run the complete local gate:

```bash
bash tests/run.sh
```

For the same Python quality checks used in CI, install the development-only
tools in a repository-local virtual environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
PATH="$PWD/.venv/bin:$PATH" bash tests/run.sh
```

The gate runs Ruff and coverage when installed, all Python and shell suites
exactly once, Bash syntax, production ShellCheck when installed, and
`git diff --check`, with per-suite timings.
Focused troubleshooting can use `python3 -m unittest discover -s tests` or an
individual shell suite under `tests/shell/`.

## Project documentation

- [Roadmap](docs/roadmap.md) — active delivered and planned work
- [Quick start](QUICKSTART.md) — compact first-use guide
- [Archive index](archive/docs/README.md) — retired designs and restore notes
- [Deferred capability map](archive/docs/stuff.md) — intentionally inactive work
