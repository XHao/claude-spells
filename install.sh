#!/usr/bin/env bash
# Install claude-spells marketplace into ~/.claude/settings.json
set -euo pipefail

MARKETPLACE_PATH="$(cd "$(dirname "$0")" && pwd)/marketplace.json"
SETTINGS="$HOME/.claude/settings.json"

if ! command -v jq &>/dev/null; then
  echo "Error: jq is required. Install it with: brew install jq"
  exit 1
fi

# Create settings file if it doesn't exist
if [ ! -f "$SETTINGS" ]; then
  mkdir -p "$(dirname "$SETTINGS")"
  echo '{}' > "$SETTINGS"
fi

# Inject the marketplace entry (idempotent)
UPDATED=$(jq \
  --arg path "$MARKETPLACE_PATH" \
  '.extraKnownMarketplaces["claude-spells"] = {"source": {"source": "file", "path": $path}}' \
  "$SETTINGS")

echo "$UPDATED" > "$SETTINGS"

echo "Registered claude-spells marketplace in $SETTINGS"
echo "Marketplace file: $MARKETPLACE_PATH"
echo ""
echo "Next steps:"
echo "  1. Open Claude Code"
echo "  2. Run: /plugin install jfr-analyzer@claude-spells"
