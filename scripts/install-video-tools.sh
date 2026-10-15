#!/usr/bin/env bash
# Installs the video/collage toolkit for Claude Code:
#   ffmpeg 9.0.x (static build), ghost-editor, claude-motion-design, lemo-opuscar.
# Idempotent: safe to re-run; already-installed parts are skipped.
# Used as a SessionStart hook in cloud sessions (see .claude/settings.json).
set -uo pipefail

SKILLS="$HOME/.claude/skills"
BIN="$HOME/.local/bin"
LOG="${VIDEO_TOOLS_LOG:-/tmp/install-video-tools.log}"
mkdir -p "$SKILLS" "$BIN"
export PATH="$BIN:$PATH"

say() { echo "[video-tools] $*"; }

clone_or_pull() { # <repo> <dest>
  if [ -d "$2/.git" ]; then git -C "$2" pull -q --ff-only || true
  else git clone -q --depth 1 "https://github.com/$1.git" "$2"; fi
}

pip_install() {
  pip3 install -q "$@" 2>/dev/null || pip3 install -q --break-system-packages "$@"
}

# 1. ffmpeg 9.0.x (BtbN static GPL build of the 9.0 release branch)
if ! "$BIN/ffmpeg" -version 2>/dev/null | head -1 | grep -q 'version n\?9\.'; then
  say "installing ffmpeg 9.0"
  tmp=$(mktemp -d)
  curl -fsSL -o "$tmp/ff.tar.xz" \
    https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n9.0-latest-linux64-gpl-9.0.tar.xz &&
    tar -xJf "$tmp/ff.tar.xz" -C "$tmp" &&
    install -m 755 "$tmp"/ffmpeg-*/bin/ffmpeg "$tmp"/ffmpeg-*/bin/ffprobe "$BIN/"
  rm -rf "$tmp"
fi
# make sure the new ffmpeg wins over the distro one for every process
grep -q "$BIN" "$HOME/.bashrc" 2>/dev/null || echo "export PATH=\"$BIN:\$PATH\"" >> "$HOME/.bashrc"
[ -n "${CLAUDE_ENV_FILE:-}" ] && echo "export PATH=\"$BIN:\$PATH\"" >> "$CLAUDE_ENV_FILE"

# 2. claude-motion-design (HTML + Playwright + ffmpeg)
if [ ! -f "$SKILLS/motion-design/SKILL.md" ]; then
  say "installing motion-design"
  tmp=$(mktemp -d)
  clone_or_pull howseen-ai/claude-motion-design "$tmp/cmd" && cp -r "$tmp/cmd/skill/motion-design" "$SKILLS/"
  rm -rf "$tmp"
  pip_install playwright imageio-ffmpeg numpy pillow >>"$LOG" 2>&1
fi

# 3. ghost-editor (talking-head reels, captions, B-roll, 13 styles)
if [ ! -f "$SKILLS/ghost-editor/SKILL.md" ]; then
  say "installing ghost-editor"
  clone_or_pull kurbaitaev/ghost-editor "$SKILLS/ghost-editor"
  pip_install numpy opencv-python-headless pillow openai-whisper google-genai >>"$LOG" 2>&1
  python3 "$SKILLS/ghost-editor/scripts/library_restore.py" >>"$LOG" 2>&1 || say "ghost-editor library download failed (see $LOG)"
fi

# 4. lemo-opuscar (film styles made in code) — plugin skill + its library in ~/lemo-opuscar
if [ ! -f "$SKILLS/lemo-opuscar/SKILL.md" ]; then
  say "installing lemo-opuscar"
  tmp=$(mktemp -d)
  git clone -q --depth 1 --filter=blob:none --sparse https://github.com/lemomo-ai/lemo-opuscar.git "$tmp/lo" &&
    git -C "$tmp/lo" sparse-checkout set plugin/skills/lemo-opuscar &&
    cp -r "$tmp/lo/plugin/skills/lemo-opuscar" "$SKILLS/"
  rm -rf "$tmp"
fi
if [ -f "$SKILLS/lemo-opuscar/scripts/setup.sh" ] && [ ! -d "$HOME/lemo-opuscar/node_modules" ]; then
  (cd "$HOME" && sh "$SKILLS/lemo-opuscar/scripts/setup.sh" && sh "$SKILLS/lemo-opuscar/scripts/setup.sh" deps) >>"$LOG" 2>&1 ||
    say "lemo-opuscar deps failed (see $LOG)"
fi

# Playwright's own Chromium is pre-installed in cloud containers (PLAYWRIGHT_BROWSERS_PATH); elsewhere fetch it.
[ -z "${PLAYWRIGHT_BROWSERS_PATH:-}" ] && python3 -m playwright install chromium >>"$LOG" 2>&1

say "ffmpeg: $("$BIN/ffmpeg" -version 2>/dev/null | head -1 | cut -d' ' -f1-3)"
say "skills: $(ls "$SKILLS" | tr '\n' ' ')"
exit 0
