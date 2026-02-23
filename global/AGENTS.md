# Global Agent Working Agreement

## Default behavior
- I plan first. Before opening files, I list up to 3 files I need and why.
- I use rg for discovery and open only the smallest relevant file sections.
- I avoid pasting whole files. I quote only the necessary lines.
- I keep diffs minimal and reversible. One focused change at a time.
- I keep command output small (tail/sed ranges). I avoid huge logs.

## Safety
- I ask before destructive commands (rm, git reset --hard, mass delete).
- I ask before installing packages or changing system configuration.

## Definition of done
- I provide a minimal diff and the exact verify commands (tests/lint/build), then I stop.