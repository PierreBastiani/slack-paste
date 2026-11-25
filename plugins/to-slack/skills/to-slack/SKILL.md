---
name: to-slack
description: Draft a Slack message from the current conversation in standard markdown, show it for approval, then copy it to the macOS clipboard so Slack's composer formats it on paste (headings, lists, links, code, real tables). Use when the user says "slack this", "send to X", "post in Slack", "message for the channel", or wants to share a result on Slack.
---
# Slack message to the clipboard

macOS only. Needs `pandoc` (`brew install pandoc`); `--blocks` also needs `markdown-it-py` or `uv`.
The script is `scripts/md-to-slack.sh` in this skill's directory. The paste behavior these rules come
from is documented in https://github.com/PierreBastiani/slack-paste/blob/main/FINDINGS.md.

## 1. Audience and intent

From the conversation, work out who reads it (one person, a channel, a community), what it carries
(result, question, status, announcement) and the language: match the user's last message.
If the readers are unclear, ask once.

## 2. Draft in standard markdown

This skill covers format and readability in Slack only. For the wording itself, use a writing
skill the user has installed, if any.

Write standard markdown, never Slack mrkdwn (`*bold*` pastes as italic):
`##` headings, `**bold**`, `_italic_`, `[text](url)` links, `-` bullets, `>` quotes,
`` `code` ``, fenced code blocks, markdown tables.

Readability in the Slack chat window:
- Line 1 carries the meaning: notifications, channel previews and thread summaries show only the
  start of a message. Make it bold if the message is long.
- Short lines and short paragraphs. The message column is narrow, and a line packed with facts
  wraps into a wall of text: split it or move it down.
- One idea per bullet. Two levels of nesting at most.
- Headings only in long messages (a report, an announcement); a three-line message needs none.
- Long detail goes below the outcome, under an italic label (`_Details:_`), or in a thread reply.
  Slack folds long messages behind "Show more".
- Tabular data goes in a markdown table: Slack renders it as a real table. Keep cells short
  (2 to 4 words); a wide table scrolls sideways.
- Code, commands and IDs in `` `code` `` or a fenced block, never mixed into a sentence's bold.
- Links as `[text](url)` with words people can scan, not a bare URL in the middle of a sentence.
- Mentions: plain `@name` in the text only notifies after Slack resolves it while typing; tell the
  user to fix mentions after pasting if the message must notify someone.

Markdown that pastes badly (all tested):
- Headings: `#` = level 1, `##` = 2, `###` and deeper = 3. Plain text only: no bold or links inside.
- Bullets with `-`. A `+` bullet starts a separate list.
- Ordered lists start at `1.`; a list starting at `5.` stays plain text.
- `~single tilde~`, `- [ ]` task boxes, footnotes and HTML tags stay literal.
- Quotes keep paragraphs and code only: no lists inside a quote; `>>` nesting is flattened.
- Images become a link with the alt text.
- Tables need every line to start with `|` and a `|---|` separator. With `--rich` cells are plain
  text: bold, code, link URLs and column alignment are lost. Need them? Use `--blocks`.

## 3. Show and confirm

Show the markdown draft and ask: send this? (yes / edit / cancel).

## 4. Copy

```bash
<this skill's directory>/scripts/md-to-slack.sh --rich <<'MD'
[approved draft]
MD
```

Pick the flag:
- `--rich` (default): markdown as plain text + a pandoc HTML version.
- `--blocks`: adds Slack Block Kit built from the markdown. Use it when a table has bold, code,
  links or alignment (`|:---:|`, `|---:|`), or when the exact layout matters.
- `--code-tables` (with either): tables as an aligned code block, for a workspace where pasted
  tables do not turn into real tables.

The copy replaces the clipboard. The markdown is also saved at `$TMPDIR/md-to-slack-rich.md`.

Tell the user: "Copied. Paste in Slack with Cmd+V, Slack formats it. Cmd+Shift+V pastes it raw."

If the script cannot run (not macOS, no `osascript`, or a sandbox without access to the user's
clipboard, as in claude.ai chat), give the approved draft in one fenced `markdown` code block
instead and tell the user to copy it with the block's copy button and paste it in Slack. That puts
the markdown on the clipboard as plain text, which Slack converts. Without the script, a draft
whose only markup is `_italic_` at the very start stays unformatted, and tables lose cell
formatting (no `--blocks`).

## Clipboard quirks

Slack's composer picks one clipboard type per paste, in this order:

1. No `text/plain` → nothing is pasted. HTML alone pastes an empty line.
2. `slack/block-kit` (JSON blocks) → inserted as is. This is what `--blocks` writes, inside
   Chrome's `org.chromium.web-custom-data` pasteboard entry (Slack's desktop app is Chromium too).
3. `text/plain` that looks like markdown → Slack's markdown converter. "Looks like" = any of:
   `**bold**`, `*italic*`, `~~strike~~`, `` `code` ``, `[text](url)`, a line starting with `- `,
   `* `, `1. ` or `> `, a heading, a `---` line, a pipe table, a fence with a language. `_italic_`
   and `__bold__` count only after a space. One match converts the whole paste.
4. Tab-separated text (a spreadsheet copy) → a table with a bold header row.
5. Otherwise `text/html` → Slack's HTML importer: keeps bold, italic, underline, strike, code,
   links, code blocks, quotes, `hr` and simple bullets; drops headings, colors, images and numbered
   lists. That is why `--rich` adds HTML: a draft whose only markup is `_italic_` at the very start,
   or a fence without a language, still arrives formatted.

Also:
- Cmd+Shift+V, a paste inside a code block, or Slack's "plain text mode" preference skip conversion.
- Copying a table back out of the composer puts `[object Object]` in the plain text (Slack bug).
- Slack enables parts of this per workspace and client. If a paste does not format, check
  FINDINGS.md (link above) for the tested setup and re-run the repo's `lab/` in that workspace.

## API sends only

No flag (stdout) or `--copy` produce Slack mrkdwn (`*bold*`, `<url|text>`). Use it only for a
bot, webhook or `chat.postMessage`, never for pasting in the composer.
