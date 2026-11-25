# to-slack

Draft a Slack message from the conversation in standard markdown, review it, then copy it so that
pressing Cmd+V in Slack's message box gives real formatting: headings, bullet and numbered lists,
links, code blocks and native Slack tables. Ask for it with "slack this", "send to the channel" or
"post this in Slack".

The skill writes the draft, shows it to you and waits for your yes before it copies anything. It
also carries Slack's paste rules (what the composer converts and what it drops), so the draft is
written in markup that survives the paste.

## What it runs

The skill runs one script, `skills/to-slack/scripts/md-to-slack.sh`, which calls
`skills/to-slack/scripts/slack_clip.py` with `python3`:

- **Clipboard:** it writes the message to the macOS clipboard through `osascript` (AppKit's
  `NSPasteboard`): the markdown as plain text, an HTML rendering made by `pandoc`, and with
  `--blocks` a Slack Block Kit version inside Chrome's web clipboard entry. It replaces what was on
  the clipboard. It keeps a copy of the markdown in `$TMPDIR/md-to-slack-rich.md`.
- **No network.** The script sends nothing anywhere and reads no file other than the message you
  approved. Slack only sees the message when you paste it yourself.
- **Dependencies:** `pandoc` (`brew install pandoc`). `--blocks` imports `markdown-it-py`; when it
  isn't installed, the script runs through `uv run --with markdown-it-py==4.3.0`, which downloads
  that pinned package from PyPI once.

macOS only. Where the script can't run (claude.ai chat, Cowork, another OS), the skill gives the
draft as one markdown code block to copy by hand; Slack still converts most of it.

## Modes

| Flag | Clipboard | Use it for |
|---|---|---|
| `--rich` | markdown + HTML | everyday messages |
| `--blocks` | the above + Slack Block Kit | tables with bold, code, links or alignment |
| `--code-tables` | tables as aligned code blocks | workspaces where pasted tables stay as pipes |
| none, `--copy` | Slack mrkdwn on stdout or the clipboard | bots and API sends only |

## Install

In Claude Code: `/plugin install to-slack --marketplace PierreBastiani/slack-paste`. In any Agent
Skills client: `npx skills add PierreBastiani/slack-paste`.

## More

How Slack's composer handles a paste, tested in the Slack web and desktop apps, with the lab that
measured it: https://github.com/PierreBastiani/slack-paste

By Pierre Bastiani, https://pierre.kensae.com. MIT license.
