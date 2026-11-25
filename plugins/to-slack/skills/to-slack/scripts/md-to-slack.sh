#!/usr/bin/env bash
# md-to-slack.sh — convert standard markdown for Slack.
#
# Modes:
#
#   --rich (for pasting into the Slack composer)
#     Clipboard = the markdown as plain text + a pandoc HTML rendering. Slack converts the
#     markdown when its "is this markdown?" check passes and falls back to the HTML when it
#     does not. Pipe tables are left as markdown: Slack turns them into native table blocks.
#     Requires pandoc. Implemented in slack_clip.py (paste rules: ../SKILL.md; findings: https://github.com/PierreBastiani/slack-paste/blob/main/FINDINGS.md).
#   --blocks   --rich + Slack Block Kit JSON (slack/block-kit) built from the markdown: tables
#              keep bold, links and code in cells and column alignment. Needs markdown-it-py
#              (or uv, used automatically).
#   --code-tables  with --rich/--blocks: tables as aligned code blocks (workspaces without tables)
#
#   default / --copy (mrkdwn text, for API sends, not composer pasting)
#     Converts to Slack mrkdwn (*bold*, <url|text>). The composer does NOT interpret pasted
#     mrkdwn: <url|text> only works via chat.postMessage. --copy pipes it to pbcopy.
#
# Usage:
#   md-to-slack.sh --rich < message.md
#   md-to-slack.sh --blocks < message.md
#   echo "## Hi **bold**" | md-to-slack.sh
#
# mrkdwn conversions:
#   # Heading        -> *Heading*       (slack has no headings; bold line is the convention)
#   **bold**         -> *bold*
#   __bold__         -> *bold*
#   *italic*         -> _italic_
#   _italic_         -> _italic_         (already correct)
#   ~~strike~~       -> ~strike~
#   [text](url)      -> <url|text>
#   | a | b |        -> wrapped in ``` block (slack has no native tables)
#   ```code```       -> preserved verbatim

set -euo pipefail

COPY=0
RICH=0
RICH_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --copy) COPY=1 ;;
    --rich) RICH=1 ;;
    --blocks) RICH=1; RICH_ARGS+=(--blocks) ;;
    --code-tables) RICH_ARGS+=(--code-tables) ;;
    --dump) RICH_ARGS+=(--dump "$2"); shift ;;
    --no-copy) RICH_ARGS+=(--no-copy) ;;
    *) break ;;
  esac
  shift
done

if [[ $RICH -eq 1 ]]; then
  HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ " ${RICH_ARGS[*]-} " == *" --blocks "* ]] && ! python3 -c 'import markdown_it' 2>/dev/null; then
    command -v uv >/dev/null || { echo "--blocks needs markdown-it-py (pip install markdown-it-py) or uv" >&2; exit 1; }
    exec uv run -q --with markdown-it-py==4.3.0 python3 "$HERE/slack_clip.py" ${RICH_ARGS[@]+"${RICH_ARGS[@]}"}
  fi
  exec python3 "$HERE/slack_clip.py" ${RICH_ARGS[@]+"${RICH_ARGS[@]}"}
fi

CONVERTED=$(perl -CSDA -e '
my @lines = <STDIN>;
my $in_code = 0;
my $in_table = 0;
my @out;

for my $line (@lines) {
  # Code fences pass through; toggle state and skip transforms.
  if ($line =~ /^```/) {
    if ($in_table) { push @out, "```\n"; $in_table = 0; }
    $in_code = !$in_code;
    push @out, $line;
    next;
  }
  if ($in_code) { push @out, $line; next; }

  # Markdown table: wrap the consecutive |-lines block in a code fence.
  if ($line =~ /^\s*\|.*\|\s*\n?$/) {
    if (!$in_table) { push @out, "```\n"; $in_table = 1; }
    push @out, $line;
    next;
  }
  if ($in_table) { push @out, "```\n"; $in_table = 0; }

  chomp(my $l = $line);

  # Line-start bullets: convert "* item" to "• item". Slack renders literal "*"
  # not as a bullet. "- item" we leave alone (renders as dash, often intentional).
  $l =~ s/^(\s*)\*(\s+)/$1\x{2022}$2/;

  # Bold first, with a placeholder, so italic does not eat half of **x**.
  $l =~ s/\*\*([^*\n]+)\*\*/\x{1}$1\x{1}/g;
  $l =~ s/__([^_\n]+)__/\x{1}$1\x{1}/g;

  # Italic *x* -> _x_  (require non-space adjacent to asterisks; protects bullet "* item")
  $l =~ s/\*(\S(?:[^*\n]*?\S)?)\*/_$1_/g;

  # Strikethrough.
  $l =~ s/~~([^~\n]+)~~/~$1~/g;

  # Restore bold marker.
  $l =~ s/\x{1}([^\x{1}]+)\x{1}/*$1*/g;

  # Headings (any level) -> bold line.
  $l =~ s/^#{1,6}\s+(.*)$/*$1*/;

  # Links [text](url) -> <url|text>.
  $l =~ s/\[([^\]]+)\]\(([^)]+)\)/<$2|$1>/g;

  push @out, "$l\n";
}
if ($in_table) { push @out, "```\n"; }
print @out;
' "$@")

if [[ $COPY -eq 1 ]]; then
  printf '%s' "$CONVERTED" | pbcopy
  CHARS=$(printf '%s' "$CONVERTED" | wc -c | tr -d ' ')
  LINES=$(printf '%s' "$CONVERTED" | wc -l | tr -d ' ')
  PREVIEW=$(printf '%s' "$CONVERTED" | head -c 120 | tr '\n' ' ')
  printf '%s\n' "----- copied to clipboard ($CHARS chars, $LINES lines) -----"
  printf '  preview: %s...\n' "$PREVIEW"
  printf '  paste in Slack with Cmd+V\n'
else
  printf '%s' "$CONVERTED"
fi
