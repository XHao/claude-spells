#!/usr/bin/env bash
# Install claude-spells marketplace into ~/.claude/settings.json
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SETTINGS="$HOME/.claude/settings.json"

if ! command -v jq &>/dev/null; then
  echo "Error: jq is required. Install it with: brew install jq"
  exit 1
fi

# Create settings dir if needed
mkdir -p "$(dirname "$SETTINGS")"

# Create settings file if it doesn't exist
if [ ! -f "$SETTINGS" ]; then
  echo '{}' > "$SETTINGS"
fi

# Register the marketplace as a local directory (idempotent)
UPDATED=$(jq \
  --arg path "$REPO_DIR" \
  '.extraKnownMarketplaces["claude-spells"] = {"source": {"source": "directory", "path": $path}}' \
  "$SETTINGS")

echo "$UPDATED" > "$SETTINGS"

echo "Registered claude-spells marketplace in $SETTINGS"
echo "Marketplace directory: $REPO_DIR"
echo ""
echo "Next steps:"
echo "  1. Open Claude Code"
echo "  2. Run: /plugin install jfr-analyzer@claude-spells"
