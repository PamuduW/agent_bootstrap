# Quickstart

## 1. Review the global baseline

Edit the canonical machine-level policy in:

- [`global/AGENTS.md`](global/AGENTS.md)

Project-specific behavior belongs in each repo's `AGENTS.md`.

## 2. Start the control plane

```bash
./install.sh
```

This opens the terminal-first menu for:

- package visibility and enablement
- tracked workspace management
- applying global and repo outputs
- status checks

## 3. Use non-interactive commands when needed

```bash
./install.sh status
./install.sh global
./install.sh workspace ~/Dev/my-repo
./install.sh all ~/Dev
./install.sh import-local create-plugin
./install.sh remove-managed superpowers
./install.sh delete-local postman
./install.sh doctor
```

The `workspace` command expects the root of a git repo.

## 4. Understand the generated outputs

The system renders compatibility files from canonical `AGENTS.md` sources:

- global Codex and Claude files under `~/.codex/` and `~/.claude/`
- repo `CLAUDE.md`
- repo `.github/copilot-instructions.md`
- repo `.cursor/rules/bootstrap-skills.mdc`
- repo `.cursor/mcp.json`

Do not hand-edit generated compatibility files.

## 5. Run tests

```bash
python3 -m unittest tests.test_bootstrap_engine
```

## 6. OpenClaw future path

The future OpenClaw adapter plan lives in:

- [`docs/openclaw-plan.md`](docs/openclaw-plan.md)
