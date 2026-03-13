# MCP Server Inventory

This document details every MCP server discovered in the installed Cursor plugins.

---

## 1. Atlassian (Jira + Confluence)

| Property | Value |
|----------|-------|
| **Server Name** | `atlassian` |
| **Plugin** | Atlassian |
| **Connects To** | Atlassian Cloud (Jira, Confluence, Rovo) |
| **Transport Type** | HTTP (streamable-http) |
| **URL** | `https://mcp.atlassian.com/v1/mcp` |
| **Authentication** | OAuth 2.0 via Atlassian Cloud — browser-based auth flow initiated by `mcp_auth` tool call |
| **Required Env Vars** | None (auth is handled via OAuth browser flow) |
| **Source Config** | `~/.cursor/plugins/cache/cursor-public/atlassian/5d300c892a43513c4c5d3ecb534bf9c78b6d6389/.mcp.json` |

### Setup Steps

1. Add the server config to `.cursor/mcp.json` (see `mcp.json` in this directory)
2. Open Cursor and start a chat
3. The agent will detect the server needs auth and call `mcp_auth`
4. Complete the OAuth flow in your browser (Atlassian account login)
5. Once authenticated, all Jira/Confluence tools become available

### Available Capabilities

- Search across Jira and Confluence (Rovo Search)
- Create/read Jira issues, search with JQL
- Read/create/update Confluence pages, search with CQL
- Look up Jira account IDs
- Get project metadata and issue types

### Alternative Config (Gemini)

The plugin also ships a `gemini-extension.json` with server name `atlassian-rovo-mcp-server` pointing to the same URL.

---

## 2. GitLab

| Property | Value |
|----------|-------|
| **Server Name** | `GitLab` |
| **Plugin** | GitLab |
| **Connects To** | GitLab.com (or self-managed instance) |
| **Transport Type** | HTTP (streamable-http) |
| **URL** | `https://gitlab.com/api/v4/mcp` |
| **Authentication** | OAuth 2.0 via GitLab — browser-based auth flow initiated by `mcp_auth` tool call |
| **Required Env Vars** | None for gitlab.com (auth via OAuth). For self-managed: change URL to `https://gitlab.example.com/api/v4/mcp` |
| **License Requirement** | GitLab Premium or Ultimate with GitLab Duo enabled |
| **Source Config** | `~/.cursor/plugins/cache/cursor-public/gitlab/e89ebfc384db30e3d06c840853ad67d22f5f9c94/.mcp.json` |

### Setup Steps

1. Add the server config to `.cursor/mcp.json`
2. Open Cursor and start a chat
3. The agent will detect the server needs auth and call `mcp_auth`
4. Complete the OAuth flow in your browser (GitLab login)
5. Requires GitLab Premium/Ultimate with Duo enabled

### Self-Managed GitLab

A `.mcp.json.self-managed.example` file is provided in the plugin:

```json
{
  "mcpServers": {
    "GitLab": {
      "type": "http",
      "url": "https://gitlab.example.com/api/v4/mcp"
    }
  }
}
```

Replace `gitlab.example.com` with your instance URL.

### Available Capabilities

- Create/read issues and merge requests
- Search issues, MRs, projects, labels
- Semantic code search
- Pipeline management (list, create, retry, cancel)
- Get pipeline jobs
- Add/read comments on work items
- Get MR diffs and commits

---

## 3. JFrog (conditional)

| Property | Value |
|----------|-------|
| **Server Name** | `jfrog` |
| **Plugin** | JFrog |
| **Connects To** | JFrog Platform (Artifactory, Xray, Curation) |
| **Transport Type** | HTTP (streamable-http) |
| **URL** | `https://<JFROG_PLATFORM_URL>/mcp` |
| **Authentication** | OAuth via JFrog Cloud |
| **Required Env Vars** | `JFROG_PLATFORM_URL` — your JFrog instance URL (e.g., `myteam.jfrog.io`) |
| **Availability** | JFrog Cloud/SaaS only. Admin must enable MCP Server (Administration > General > Settings > MCP Server > ON) |
| **Source Config** | `~/.cursor/plugins/cache/cursor-public/jfrog/2f314801d29a41473e2edd01c6d625a3f75387b7/mcp.json` |

**Note:** This server is only added to MCP configs when `JFROG_PLATFORM_URL` is set at install time. Without it, the JFrog entry is skipped to avoid deploying a broken URL.

### Setup Steps

1. Set `JFROG_PLATFORM_URL` environment variable to your JFrog instance (e.g., `myteam.jfrog.io`)
2. Run `./install.sh global --force` (or `./install.sh global` on a fresh setup) — the JFrog server is automatically injected
3. Ensure your JFrog admin has enabled the MCP Server feature
4. Authentication is handled via OAuth — no API keys needed

### Available Capabilities

- JFrog Catalog queries (global OSS intelligence for 12M+ packages)
- Vulnerability lookups (CVE search, severity, affected versions)
- Curation status checks (approved/blocked/inconclusive)
- Artifactory package queries (internal repos, versions)
- AQL artifact search
- DevSecOps report generation
- Repository management

---

## 4. Cursor IDE Browser (Built-in)

| Property | Value |
|----------|-------|
| **Server Name** | `cursor-ide-browser` |
| **Plugin** | Built-in (Cursor IDE) |
| **Connects To** | Local browser automation |
| **Transport Type** | Internal (managed by Cursor) |
| **Authentication** | None required |
| **Required Env Vars** | None |

### Notes

This is a built-in MCP server provided by Cursor itself, not from a plugin. It provides browser automation capabilities (navigate, click, type, screenshot, etc.) for frontend testing and web interaction. It is not configurable via `mcp.json` — it's managed internally by the Cursor IDE.

### Available Capabilities

- Browser navigation and interaction
- Page snapshots and element inspection
- Form filling and clicking
- Tab management
- CPU profiling
- Canvas creation for visualizations

---

## MCP Servers NOT Found in Plugins

The following plugins do **not** include MCP server configurations:

| Plugin | Notes |
|--------|-------|
| **Cursor Team Kit** | Skills and rules only, no MCP server |
| **Superpowers** | Skills, commands, hooks only, no MCP server |
| **Continual Learning** | Skills and hooks only, no MCP server |
| **Grafana Assistant** | Rules and skills only. Uses `grafana-assistant` CLI tool (not MCP) for Grafana interaction |
