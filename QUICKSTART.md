# Quickstart

See **[README.md](README.md)** for the full slim bootstrap guide.

**TL;DR:**

**Sibling of dotfiles (recommended):**

```bash
git clone <your-remote>/agent_bootstrap ~/Dev/agent_bootstrap   # next to ~/Dev/dotfiles
cd ~/Dev/agent_bootstrap
./install.sh
```

**Standalone anywhere:**

```bash
git clone <your-remote>/agent_bootstrap /any/path/agent_bootstrap
cd /any/path/agent_bootstrap
./install.sh
```

Then in any project repo: `agentboot`.

Update skills later: `./install.sh skills update`.

Deferred features (catalog, MCP, workspace render, memory vault): [`archive/README.md`](archive/README.md).
