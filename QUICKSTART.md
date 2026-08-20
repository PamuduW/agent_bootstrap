# Quickstart

See **[README.md](README.md)** for the full slim bootstrap guide.

**TL;DR:**

**Sibling of dotfiles (recommended):**

```bash
git clone <your-remote>/agent_bootstrap ~/Dev/agent_bootstrap   # next to ~/Dev/dotfiles
cd ~/Dev/agent_bootstrap
./install.sh install
```

**Standalone anywhere:**

```bash
git clone <your-remote>/agent_bootstrap /any/path/agent_bootstrap
cd /any/path/agent_bootstrap
./install.sh install
```

Then in any project folder or project repo: `agentbot boot`. It creates or
preserves `AGENTS.md`, renders the default Claude/Cursor surfaces, and records
the canonical folder or Git root in private local state. Copilot instructions
are opt-in with `agentbot boot --copilot`.

Useful explicit selections:

```bash
agentbot boot --claude
agentbot boot --copilot
agentbot boot --cursor
agentbot boot --codex
```

Preview or refresh a registered workspace:

```bash
agentbot workspace ~/Dev/existing-project
agentbot workspace --yes ~/Dev/existing-project
agentbot workspaces
agentbot resync --dry-run --all
agentbot resync --yes --all
```

`AGENTS.md` is always present because it is the canonical repository policy.
The local registry is `${XDG_CONFIG_HOME:-$HOME/.config}/agentbot/workspaces.json`;
it is not written into the project or tracked by Git.

On a controlling TTY, `./install.sh` or `agentbot` with no arguments opens the
Agentbot menu. Headless runs should use an explicit command such as
`agentbot status` or `./install.sh doctor`.

Update skills later: `./install.sh skills update`.

Active phases: [`docs/roadmap.md`](docs/roadmap.md). Deferred features:
[`archive/docs/stuff.md`](archive/docs/stuff.md).
