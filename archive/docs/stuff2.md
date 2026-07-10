These seven pieces were meant to be **one pipeline**: you curate once in `agent_bootstrap`, then **re-apply** to every machine and every repo when something changes. Today you have the **manual half** of that (global skills, `base/` templates, `agentboot --minimal`). The archived half is **automation + memory across repos**.

---

## The mental model they share

The old design split files into two kinds:

| Kind | You edit | Examples |
|------|----------|----------|
| **Canonical** | Yes | `global/AGENTS.md`, each repo’s `AGENTS.md`, memory vault markdown |
| **Generated** | No — disposable | `CLAUDE.md`, Copilot instructions, `.cursor/rules/*.mdc`, `.cursor/mcp.json` |

Rule from the harness doc: **`AGENTS.md` is the one authored instruction file.** Everything else for Copilot/Cursor/Claude was supposed to **point at or merge** that text — not drift into separate rule sets.

**Your routine today (slim):**

```text
New repo → agentboot → edit ## Project in AGENTS.md → git commit
Skills change → cd agent_bootstrap → ./install.sh skills install
Global baseline change → edit global/AGENTS.md → copy/symlink manually or install.sh global
```

**Your routine with the full stack restored:**

```text
Change catalog or global/AGENTS.md once
  → ./install.sh all   (or interactive Apply)
  → every tracked repo + ~/.codex + ~/.claude + Cursor MCP updated in one shot
```

That’s the day-to-day difference: **less per-repo/per-tool fiddling**, more **“I changed the source, re-render.”**

---

## 1. Package catalog

**Intended to work:** A JSON registry (`catalog/packages.json`) of “things you might install” — Cursor plugins, MCP servers, skill bundles — with metadata: display name, which tools they support, which MCP keys they own, where they came from.

Packages had states:

- **Managed** — you explicitly curate in the catalog  
- **Detected** — found in Cursor’s plugin cache or already copied into a repo  
- **Enabled** — selected for the next render  

`import-local` would copy a plugin from `~/.cursor/plugins/cache/...` into the bootstrap repo, register it in the catalog, and wire its MCP keys.

**Day-to-day effect:** Instead of remembering “GitLab plugin needs the GitLab MCP key” or hunting cache folders, you’d say “enable GitLab package” and the system knows what artifacts and MCP entries belong together.

**Without it:** You manage skills via `skills.sources.yaml` (good) and MCP via Cursor’s UI or hand-edited JSON (scattered). No single “what’s in my bundle?” view beyond reading YAML/JSON yourself.

**When you’d miss it:** When you add/remove Cursor plugins often and want one place that says “these four packages = these MCP servers + these rules.”

---

## 2. `agentos.yaml` profiles

**Intended to work:** Declarative map of **who gets what**. The archived `safe-default` profile says: global skills only, no executable scripts from community packs, read-first MCP.

`export_targets` defines paths per surface:

- Codex → `~/.codex/AGENTS.md` from `global/AGENTS.md`  
- Claude → same content to `CLAUDE.md` + `AGENTS.md`  
- Cursor → global `mcp.json` + generated workspace rules  
- Copilot → `.github/copilot-instructions.md`  
- Repo → **merged** outputs (global + repo overlay)

**Day-to-day effect:** You pick a profile (`safe-default` vs a future `full-dev` with more MCP) instead of mentally tracking “does Copilot get the same text as Codex?” Profiles are the **policy layer** — conservative vs permissive.

**Without it:** You rely on convention and docs (“AGENTS.md is canonical”). Works fine if you’re disciplined; profiles would encode that discipline in config.

**When you’d miss it:** When you want different trust levels (e.g. freelance client repo vs personal infra repo) without maintaining separate bootstrap forks.

---

## 3. Workspace render

**Intended to work:** Given a git repo path, `render.py` would:

1. Require a **real** `AGENTS.md` in the repo (authored by you, not a generated stub)  
2. **Merge** `global/AGENTS.md` + repo `## Project` overlay into generated files  
3. Write Copilot + Cursor + Claude compatibility files  
4. Add generated paths to `.gitignore` so you don’t commit disposable outputs  
5. Optionally write `.cursor/rules/bootstrap-skills.mdc` listing enabled skill paths  

Merge order was explicit: generated header → full global baseline → repo-specific section.

**Day-to-day effect:**

- **Open any repo in Cursor/Copilot/Claude** — each tool sees the **same** global habits (WSL, skill pick list, interaction rules) **plus** that repo’s `## Project`, without you maintaining four parallel files.  
- **Edit one file** (`AGENTS.md`) when project context changes; re-run render instead of updating Copilot and Cursor separately.

**Without it:** `agentboot` copies static `base/AGENTS.md` once. Global updates in `agent_bootstrap/global/AGENTS.md` do **not** automatically flow into old repos unless you re-copy or edit by hand. `CLAUDE.md` is a static pointer, not a merged view.

**When you’d miss it:** When you have 5+ active repos and keep tweaking global agent behavior — you’ll feel sync pain.

---

## 4. MCP bundle render

**Intended to work:** Master list in `archive/mcp/mcp.json` (GitLab, Context7, AWS tools, Notion, …). Each catalog package declares which `mcp_keys` it needs. Render filters the master list to **only servers for enabled packages**, then writes:

- `~/.cursor/mcp.json` (global)  
- `<repo>/.cursor/mcp.json` (per workspace, if that was in scope)

**Day-to-day effect:** Enable “Deploy on AWS” in catalog → AWS MCP servers appear in Cursor for that workspace. Disable GitLab package → GitLab MCP drops out. No orphaned servers, no duplicate config across repos.

**Without it:** MCP setup is per-project in Cursor settings or committed `.cursor/mcp.json` files you maintain yourself. Adding a new MCP server means touching each repo or your global Cursor config manually.

**When you’d miss it:** When MCP sprawl gets annoying — especially if different repos should get different MCP subsets (client repo: no AWS; infra repo: full AWS pack).

---

## 5. `agentboot --full`

**Intended to work:** One command in a new repo:

```text
agentboot --full
  → AGENTS.md + CLAUDE.md (minimal, same as today)
  → .github/copilot-instructions.md
  → .cursor/rules/...
  → .cursor/mcp.json (filtered)
```

Idempotent: skip existing unless `--force`.

**Day-to-day effect:** Clone repo → `agentboot --full` → open in VS Code/Cursor → Copilot and Cursor already have instructions and MCP, not just Claude/Codex via `AGENTS.md`.

**Today:** `--full` warns and only does minimal copy. You’d manually add Copilot/Cursor files or skip them.

**When you’d miss it:** If you actually use Copilot instructions and Cursor rules daily and don’t want to set them up per repo.

---

## 6. Tracked workspaces

**Intended to work:** When you run `install.sh workspace ~/Dev/my-app` or `install.sh all ~/Dev`, the system:

- Records paths in `state/operator_state.json` (local, gitignored)  
- Renders that repo  
- Later: `install.sh all` or interactive **Apply** re-renders **every tracked repo** after you change global baseline, catalog, or MCP master list  

Discovery could also scan for existing artifacts and Cursor cache.

**Day-to-day effect:** The “render everything I care about” button.

Example: You add a skill to `global/AGENTS.md` and enable a new MCP package. One Apply → all tracked repos get updated Copilot/Cursor files without visiting each project.

**Without it:** Each repo is a island. Global change = you remember which repos need attention.

**When you’d miss it:** Same as workspace render pain, but amplified — it’s the **batch** version.

---

## 7. Obsidian memory vault

**Intended to work:** Tier 3 memory in the harness stack — **after** per-repo `AGENTS.md` (tier 1) and global skills (tier 2), **before** any server/Hermes/vector DB stuff.

Structure (from the v4 design doc):

- `active-context.md` — short, current focus (“working on Flutter app + agent_bootstrap slim”)  
- `preferences.md` — how you like explanations, tooling habits  
- `decisions/` — ADR-style “why we chose X”  
- `lessons/` — durable notes (WSL quirks, CI patterns)  
- `projects/` — one file per long-running effort  
- `exports/` — **generated summaries** per agent (Codex, Cursor, …) — not the full vault dumped into every prompt  

**Critical rule:** Vault is source of truth; agent summaries are views. **Do not inject the whole vault every session.**

Workflow: agents **draft** updates (“you always use conventional commits” → propose `preferences.md` edit); **you commit** what’s true. Human approval gate against memory poisoning.

**Day-to-day effect:**

- Start a session: agent reads `active-context.md` or a small export — knows what you’re working on **this week** without re-explaining.  
- Cross-repo memory: “we decided slim bootstrap, no Hermes on laptop” lives in `decisions/`, not duplicated in 10 `AGENTS.md` files.  
- Long-term: lessons from one project inform the next without bloating every repo’s `## Project`.

**Without it:** Context lives in chat history, scattered notes, or you repeat yourself in each repo’s `AGENTS.md`. Fine for 1–2 projects; gets fuzzy across many.

**When you’d miss it:** When you catch yourself re-teaching the same preferences/decisions every few days, or when `## Project` sections get huge because they’re doing double duty as memory.

---

## How they chain together (one story)

```text
You enable "gitlab" + "deploy-on-aws" in catalog
        ↓
agentos.yaml safe-default says what surfaces get exports
        ↓
MCP render filters mcp.json to GitLab + AWS keys only
        ↓
Workspace render merges global/AGENTS.md + repo ## Project
        → Copilot, Cursor rules, CLAUDE.md
        ↓
Tracked workspaces re-run that for ~/Dev/* in one Apply
        ↓
Obsidian vault holds cross-cutting memory agents don't duplicate into every AGENTS.md
```

---

## What actually changes in your coding life?

| Area | Slim (now) | Full deferred stack |
|------|------------|---------------------|
| **New repo** | `agentboot`, edit `AGENTS.md`, maybe skills install | Same + auto Copilot/Cursor/MCP; tracked for future updates |
| **Global habit change** | Edit `global/AGENTS.md`; manually propagate | One Apply → all tracked repos + global homes |
| **Tool parity** | Strong for Codex/Claude via `AGENTS.md`; Copilot/Cursor more manual | All four surfaces stay aligned from one canonical file |
| **MCP** | Cursor UI / hand config | Package-driven, filtered, reproducible |
| **Memory** | Per-repo `## Project` + chat | Durable vault for preferences/decisions; small injected slices |
| **Cognitive load** | Lower system complexity, more manual sync | Higher setup once, less ongoing drift |
| **Risk** | You forget to update old repos | Generated files + gitignore; less duplicate editing |

---

## Honest take for *your* setup

The harness doc’s own line applies: **markdown + skills + per-repo `AGENTS.md` already cover ~80%**. You’re on WSL, CLI-first, slim bootstrap — that’s intentional.

You’d **feel** these deferred features when:

1. **Many active repos** and global agent instructions change often  
2. **Copilot + Cursor rules** matter as much as Codex/Claude  
3. **MCP packages** multiply and you want per-repo subsets  
4. **Context repetition** across sessions/projects becomes annoying  

You can **defer indefinitely** if:

- You keep few repos with agent files  
- `AGENTS.md` + `skills.sources.yaml` + dotfiles menus are enough  
- MCP stays “whatever Cursor has globally”  

The vault is the odd one out — it’s less about tooling automation and more about **how you remember things across months**. It doesn’t require the render pipeline; you could populate `archive/memory-vault/` and reference it manually long before restoring catalog/render.

**See also:** [stuff.md](./stuff.md) (deferred map) · [stuff3.md](./stuff3.md) (implementation phases).