# Global Agent Working Agreement

## Default behavior
- Plan first. Before opening files, list up to 3 files you need and why.
- Use ripgrep (rg) to locate relevant sections before reading files.
- Never paste whole files. Quote only the smallest relevant chunk.
- Prefer minimal diffs. One focused change at a time.
- Keep command output small (tail, sed ranges). Avoid huge logs.

## Safety
- Ask before running destructive commands (rm, git reset --hard, mass delete).
- Ask before installing packages or changing system config.

## Definition of done
- Proposed patch (diff) + exact commands to verify (tests/lint/build), then stop.