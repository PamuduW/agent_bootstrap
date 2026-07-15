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

Then in any project repo: `agentbot boot`.

Update skills later: `./install.sh skills update`.

Deferred features: [`archive/docs/stuff.md`](archive/docs/stuff.md) (map) · [`archive/docs/stuff3.md`](archive/docs/stuff3.md) (phases).
