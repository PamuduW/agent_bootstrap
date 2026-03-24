#!/usr/bin/env bash
# sync.sh is deprecated — all functionality has moved into install.sh.
#
# Use the interactive mode instead:
#   ./install.sh            (menu option 2: Initialize)
#
# Or for scripted/CI usage:
#   ./install.sh --global   (deploys configs based on current selections)

echo ""
echo "  Note: sync.sh is deprecated. Use ./install.sh instead."
echo ""
echo "  Interactive:   ./install.sh          (select option 2: Initialize)"
echo "  CI / scripted: ./install.sh --global"
echo ""

exec "$(dirname "$0")/install.sh" "$@"
