#!/usr/bin/env bash
# claude-spells installer
#
# Usage:
#   ./install.sh           Register marketplace (first-time setup)
#   ./install.sh update    Print /plugin commands to update all installed plugins

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SETTINGS="$HOME/.claude/settings.json"
MARKETPLACE="$REPO_DIR/.claude-plugin/marketplace.json"

if ! command -v jq &>/dev/null; then
  echo "Error: jq is required. Install it with: brew install jq"
  exit 1
fi

# ── update subcommand ────────────────────────────────────────────────────────
if [ "${1:-}" = "update" ]; then
  echo "Run the following commands inside Claude Code to update all plugins:"
  echo ""
  jq -r '.plugins[].name' "$MARKETPLACE" | while read -r name; do
    echo "  /plugin uninstall $name"
    echo "  /plugin install ${name}@claude-spells"
  done
  echo "  /reload-plugins"
  echo ""
  echo "Tip: paste all lines at once, or run them one by one."
  exit 0
fi

# ── default: register marketplace ───────────────────────────────────────────
mkdir -p "$(dirname "$SETTINGS")"

if [ ! -f "$SETTINGS" ]; then
  echo '{}' > "$SETTINGS"
fi

UPDATED=$(jq \
  --arg path "$REPO_DIR" \
  '.extraKnownMarketplaces["claude-spells"] = {"source": {"source": "directory", "path": $path}}' \
  "$SETTINGS")

echo "$UPDATED" > "$SETTINGS"

# Print all plugin names from marketplace.json
PLUGINS=$(jq -r '.plugins[].name' "$MARKETPLACE" | tr '\n' ' ')

echo "Registered claude-spells marketplace in $SETTINGS"
echo "Marketplace directory: $REPO_DIR"
echo ""
echo "Next steps — run inside Claude Code:"
echo ""
for name in $(jq -r '.plugins[].name' "$MARKETPLACE"); do
  echo "  /plugin install ${name}@claude-spells"
done
echo "  /reload-plugins"
