#!/usr/bin/env bash
set -euo pipefail

# ── Setup script for gentle_pong sound pack + peon-ping patches ──
# Run this on any new machine after cloning the repo:
#
#   git clone <repo> && cd sounds && ./setup.sh
#
# What it does:
#   1. Installs peon-ping via Homebrew (if not already installed)
#   2. Generates the gentle_pong sound pack
#   3. Sets the peon-ping config (volume, active pack, etc.)
#   4. Patches the Homebrew cellar with:
#      - Audio device pre-roll (prevents headset audio cutoff)
#      - Sound suppression when terminal is focused
#   5. Re-run after `brew upgrade peon-ping` to re-apply patches

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PEON_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks/peon-ping"
CONFIG="$PEON_DIR/config.json"

# ── Colors ────────────────────────────────────────────────────────
green()  { printf '\033[32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }
red()    { printf '\033[31m%s\033[0m\n' "$*"; }

# ── 1. Install peon-ping ─────────────────────────────────────────
if command -v peon >/dev/null 2>&1; then
  green "peon-ping already installed: $(peon --version 2>/dev/null || echo 'unknown version')"
else
  yellow "Installing peon-ping..."
  brew tap peonping/tap
  brew install peon-ping
  green "peon-ping installed"
fi

# ── 2. Generate sound pack ───────────────────────────────────────
yellow "Generating gentle_pong sound pack..."
cd "$SCRIPT_DIR"
python3 generate.py
green "Sound pack installed"

# ── 3. Set config ────────────────────────────────────────────────
yellow "Writing config..."
cat > "$CONFIG" << 'JSON'
{
  "active_pack": "gentle_pong",
  "volume": 1.0,
  "enabled": true,
  "desktop_notifications": true,
  "categories": {
    "session.start": true,
    "task.acknowledge": true,
    "task.complete": true,
    "task.error": true,
    "input.required": true,
    "resource.limit": true,
    "user.spam": true
  },
  "annoyed_threshold": 3,
  "annoyed_window_seconds": 10,
  "silent_window_seconds": 0,
  "pack_rotation": [],
  "pack_rotation_mode": "random"
}
JSON
green "Config written: $CONFIG"

# ── 4. Patch Homebrew cellar ─────────────────────────────────────
PEON_SH="$(brew --prefix peon-ping)/libexec/peon.sh"

if [ ! -f "$PEON_SH" ]; then
  red "Could not find peon.sh at $PEON_SH"
  exit 1
fi

yellow "Patching peon.sh..."

# Patch A: Audio device pre-roll (silent WAV before real sound)
# Prevents first ~300ms of audio being swallowed when headset/speakers
# are in low-power mode.
if grep -q 'silence=.*\.silence\.wav' "$PEON_SH"; then
  green "  Pre-roll patch already applied"
else
  sed -i '' '/^    mac)$/{
N
s|      nohup afplay -v "\$vol" "\$file" >/dev/null 2>\&1 \&|      local silence="${HOME}/.claude/hooks/peon-ping/.silence.wav"\
      nohup bash -c '"'"'afplay -v 0 "'"'"'"'"'"'"'"'"'"\$silence"'"'"'"'"'"'"'"'"'"; afplay -v "'"'"'"'"'"'"'"'"'"\$vol"'"'"'"'"'"'"'"'"'" "'"'"'"'"'"'"'"'"'"\$file"'"'"'"'"'"'"'"'"'"'"'"' >/dev/null 2>\&1 \&|
}' "$PEON_SH" 2>/dev/null && green "  Pre-roll patch applied" || yellow "  Pre-roll patch: manual apply needed (see README)"
fi

# Patch B: Suppress sounds when terminal is focused
if grep -q 'terminal_is_focused.*play_sound\|play_sound.*terminal_is_focused' "$PEON_SH" || \
   grep -B1 'play_sound' "$PEON_SH" | grep -q 'terminal_is_focused'; then
  green "  Focus suppression patch already applied"
else
  sed -i '' 's|^# --- Play sound ---|# --- Play sound: only when terminal is NOT frontmost ---|' "$PEON_SH"
  sed -i '' '/play_sound "\$SOUND_FILE" "\$VOLUME"/{
s|  play_sound "\$SOUND_FILE" "\$VOLUME"|  if ! terminal_is_focused; then\
    play_sound "\$SOUND_FILE" "\$VOLUME"\
  fi|
}' "$PEON_SH" 2>/dev/null && green "  Focus suppression patch applied" || yellow "  Focus suppression patch: manual apply needed (see README)"
fi

# Patch C: Lowercase ghostty in focus detection
if grep -q '|ghostty)' "$PEON_SH"; then
  green "  Ghostty case fix already applied"
else
  sed -i '' 's/|Ghostty)/|Ghostty|ghostty)/' "$PEON_SH" 2>/dev/null && \
    green "  Ghostty case fix applied" || yellow "  Ghostty case fix: manual apply needed"
fi

# ── Done ──────────────────────────────────────────────────────────
echo ""
green "All done! Sounds will play on your next Claude Code session."
echo ""
echo "  Re-run this script after 'brew upgrade peon-ping' to re-apply patches."
echo "  Preview sounds:  cd $SCRIPT_DIR && python3 generate.py --preview-all"
