These seven pieces are meant to become **one pipeline**: you curate once in
`agent_bootstrap`, then preview or re-apply selected workspace policy when
something changes. Phases 0–2 now provide the live foundation: global skills,
`base/` templates, the standalone Agentbot menu, profile-driven rendering, and
private local workspace registration/resync. Catalog/MCP and durable memory
remain deferred.

---

## The mental model they share

The old design split files into two kinds:

| Kind | You edit | Examples |
|------|----------|----------|
| **Canonical** | Yes | `global/AGENTS.md`, each repo’s `AGENTS.md`, memory vault markdown |
| **Generated** | No — disposable | `CLAUDE.md`, Copilot instructions, `.cursor/rules/*.mdc`, `.cursor/mcp.json` |

Rule from the harness doc: **`AGENTS.md` is the one authored instruction file.** Everything else for Copilot/Cursor/Claude was supposed to **point at or merge** that text — not drift into separate rule sets.

**Your routine today:**

```text
New repo → agentbot boot → edit ## Project in AGENTS.md → git commit
Skills change → cd agent_bootstrap → ./install.sh skills install
Workspace policy change → agentbot resync --dry-run --all → agentbot resync --yes --all
Global machine baseline change → edit global/AGENTS.md → ./install.sh global
```

**The deferred catalog routine:**

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

**Live Phase 2 profile:** `agentos.yaml` is a deliberately small allowlist for
workspace output targets. `safe-default` selects `AGENTS.md`, Claude, Copilot,
and Cursor and rejects executable community-skill policy or arbitrary output
paths. Catalog/MCP profile filtering is still deferred.

The live output paths are fixed per surface:

- Codex / agents → canonical project `AGENTS.md`
- Claude → generated `CLAUDE.md` pointer to `AGENTS.md`
- Cursor → `.cursor/rules/agentbot-policy.mdc`
- Copilot → `.github/copilot-instructions.md`  
- Project policy → managed `AGENTS.md` baseline plus `## Project` overlay

**Day-to-day effect:** You pick a profile (`safe-default` vs a future `full-dev` with more MCP) instead of mentally tracking “does Copilot get the same text as Codex?” Profiles are the **policy layer** — conservative vs permissive.

**Without it:** You rely on convention and docs (“AGENTS.md is canonical”). Works fine if you’re disciplined; profiles would encode that discipline in config.

**When you’d miss it:** When you want different trust levels (e.g. freelance client repo vs personal infra repo) without maintaining separate bootstrap forks.

---

## 3. Workspace render

**Live behavior:** `agentbot workspace PATH` previews a canonical folder or Git
root, and `agentbot workspace --yes PATH` renders and registers it. The default
profile writes `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`, and
`.cursor/rules/agentbot-policy.mdc`.

`base/AGENTS.md` is the shared project baseline. A managed `AGENTS.md` keeps
that baseline between explicit Agentbot markers and preserves the repository's
`## Project` section. An unmarked existing `AGENTS.md` is custom and is never
overwritten. Existing unowned compatibility files are reported as conflicts.

**Day-to-day effect:**

- **Open any repo in Cursor/Copilot/Claude** — each tool sees the same resolved
  canonical policy plus that repo's `## Project`, without four authored policy
  files.
- **Edit one file** (`AGENTS.md`) when project context changes; preview and
  resync instead of updating compatibility files separately.

**Without it:** each project would require manual compatibility-file updates.
The renderer deliberately does not manage MCP files, skills, Git staging, or
commits.

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

## 5. Agentbot workspace exports (Phase 2)

**Live:** One command in a new repo:

```text
agentbot boot
  → AGENTS.md + CLAUDE.md + Copilot + Cursor compatibility files
  → Phase 3: filtered MCP bundle
```

The default creates all four policy surfaces. Optional selectors narrow the
compatibility outputs but never remove the canonical `AGENTS.md`; `--codex`
means the same canonical target as `--agents`.

**Day-to-day effect:** Clone repo → `agentbot boot` → edit the authored
`AGENTS.md` → run `agentbot resync --dry-run --all` and then apply when ready.
Copilot and Cursor receive generated views of the same policy, instead of
becoming separate instruction sources.

**Current boundary:** MCP filtering remains deferred to Phase 3. Workspace
state is private local operator state, not a file in the repository.

**When you’d miss it:** If you actually use Copilot instructions and Cursor rules daily and don’t want to set them up per repo.

---

## 6. Tracked workspaces

**Live behavior:** When you run `agentbot workspace --yes ~/Dev/my-app` or
`agentbot boot` in a project, the system:

- Records the canonical Git root or plain folder in the private local
  `${XDG_CONFIG_HOME:-$HOME/.config}/agentbot/workspaces.json`.
- Renders only the selected Agentbot-owned instruction surfaces.
- Later: `agentbot resync --dry-run --all` previews every enabled record and
  `agentbot resync --yes --all` applies them independently.

The system does not discover arbitrary folders, inspect Cursor caches, delete
missing records, or silently convert a recorded Git workspace to a directory.

**Day-to-day effect:** The “render everything I care about” button.

Example: You update `base/AGENTS.md`. One preview and resync updates managed
baseline blocks and generated compatibility files without visiting each
project.

**Without it:** Each repo is an island. A policy change would require you to
remember which repos need attention.

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
Edit base/AGENTS.md or a repo's ## Project section
        ↓
agentbot boot or agentbot workspace --yes
        ↓
Managed AGENTS.md block + selected Claude/Copilot/Cursor views
        ↓
Private local workspaces.json records the opted-in folder or Git root
        ↓
agentbot resync --dry-run --all → agentbot resync --yes --all
        ↓
Future Phase 3 MCP exports and Phase 4 memory remain separate extensions
```

---

## What actually changes in your coding life?

| Area | Slim (now) | Full deferred stack |
|------|------------|---------------------|
| **New repo** | `agentbot boot`, edit `AGENTS.md`, optionally select compatibility outputs | Same Phase 2 surfaces; catalog/MCP remains deferred |
| **Workspace policy change** | Preview and resync enabled local records | Future catalog/MCP extensions may add filtered exports |
| **Tool parity** | All four policy surfaces derive from canonical `AGENTS.md` | Additional adapters only when explicitly justified |
| **MCP** | Cursor UI / hand config | Package-driven, filtered, reproducible |
| **Memory** | Per-repo `## Project` + chat | Durable vault for preferences/decisions; small injected slices |
| **Cognitive load** | Lower system complexity, more manual sync | Higher setup once, less ongoing drift |
| **Risk** | You forget to resync an old repo | Private registration plus preview/apply makes the boundary visible |

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
