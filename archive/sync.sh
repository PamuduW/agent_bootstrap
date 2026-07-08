#!/usr/bin/env bash
# sync.sh is deprecated — all functionality has moved into install.sh.
#
# Use the interactive menu instead:
#   ./install.sh
#
# Or for scripted usage:
#   ./install.sh global

echo ""
echo "  Note: sync.sh is deprecated. Use ./install.sh instead."
echo ""
echo "  Interactive:   ./install.sh"
echo "  Scripted:      ./install.sh global"
echo ""

exec "$(dirname "$0")/install.sh" "$@"
