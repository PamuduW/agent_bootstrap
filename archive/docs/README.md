# Archived MCP research inputs

This directory contains historical inputs for the planned Agentbot MCP manager.
Nothing under `archive/` is read by Agentbot at runtime.

| File | Purpose |
|---|---|
| [`../mcp/mcp.json`](../mcp/mcp.json) | Snapshot of previously evaluated MCP server definitions |
| [`../catalog/packages.json`](../catalog/packages.json) | Snapshot of package provenance and surface mappings |

Treat both files as research evidence, not desired live state. Recheck every
server, authentication method, package version, and client schema before reuse.
The current design work belongs in active `docs/`; removed implementation code
remains recoverable from Git history.
