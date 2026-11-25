# How Slack's composer handles a paste

Tested 2026-11-24 in the Slack web client (Chrome on macOS, free workspace on a Pro trial, new
composer with the ¶ heading menu), and on 2026-11-25 in the Slack desktop app for macOS in a second,
paid workspace: `--rich` and `--blocks` gave the same messages there, formatted table cells included. Method: the lab in `lab/` puts typed payloads on the macOS
pasteboard, presses Cmd+V in the composer, records the composer DOM, then sends and reads the stored
blocks back with `conversations.history`. The rules below were read from the client bundle and every
one was checked against a live paste. Raw results stay in `lab/results/` (not committed).

Slack ships these behaviors behind flags (`enableMarkdownPasteDetection`, `supportsPortableContent`,
`getIsTablePastingEnabled`), so another workspace or the desktop app may differ. Re-run the lab there.

## 1. Which clipboard type wins

Checked in this order:

1. No `text/plain` at all: nothing is pasted (HTML alone pastes an empty line).
2. `slack/block-kit` (JSON array of blocks): inserted as blocks, no markdown step.
3. `text/markdown` that passes the *complex* check below: converted, no toast.
4. `text/plain` that passes the *any* check (or the *complex* check when the copy came from Slack,
   i.e. `slack/texty` or `slack/html` is present): converted by the markdown engine.
5. Tab-separated plain text (spreadsheet copy): becomes a table block, header row in bold.
6. Otherwise `text/html` if present, through Slack's HTML importer; else the plain text as typed.

Skips: Cmd+Shift+V (plain paste), a paste inside a code block, the "plain text mode" preference.

The web-only types (`text/markdown`, `slack/*`) travel on macOS inside the
`org.chromium.web-custom-data` pasteboard entry, a Chromium pickle (`lab/webcustom.py` encodes it).

## 2. "Is this markdown?" check

*Complex* (one is enough): a fence with a language (` ```python `), a pipe table (a line starting with
`|` followed by a `|---|` separator line), `##`–`######` headings, `# Title` (but not `# 12`), a line
that is only `---`.

*Any* = complex, or one of: `**bold**` (2+ chars), `*italic*`, `~~strike~~`, `` `code ``,
`[text](url)`, a line starting with `- `, `* `, `1. ` or `> `, and `__bold__` / `_italic_` **only after
whitespace**. Bold and italic patterns are tested with URLs removed.

Consequences seen live: `_italic_` or `__bold__` at the very start, a fence without a language, a list
starting at `5.`, a table without outer pipes, and HTML tags all stay literal when nothing else in the
paste triggers the check. One trigger anywhere converts the whole paste.

## 3. Markdown → blocks

The engine is stock markdown-it, default preset, `html:false, linkify:false, typographer:false`.

| Markdown | Result |
|---|---|
| `**b**` `__b__` `*i*` `_i_` `~~s~~` `` `c` `` | bold, italic, strike, code (nesting works) |
| `~single~`, `<b>`, `<u>`, footnotes, `- [ ]` | literal text |
| `[t](url)` | link; bare URLs are linked by the composer itself |
| `![alt](src)` | a link to src with the alt text |
| `#` / `##` / `###`–`######` | heading level 1 / 2 / 3 (4–6 capped at 3), plain text only |
| `---` | divider |
| `-` `*` lists, nested | bullet lists with indent levels; `+` starts a separate list |
| `1.` lists | ordered list; a list starting at another number stays text |
| `>` quotes | quote; nested quotes flattened; only paragraphs and fences survive inside |
| fences | code block, language kept from the info string |
| pipe tables | native table block; cells are `raw_text`: bold, code and link URLs dropped, alignment dropped |
| single newlines | kept as line breaks; blank lines kept between blocks |
| `\*` escapes | unescaped |

Stored form: headings become `rich_text_header` (level, bold fallback), `---` becomes
`rich_text_divider`, tables stay `table` blocks.

## 4. `slack/block-kit` on the clipboard

Inserted as given and accepted by the server on send:

- `table` with `rich_text` cells (bold, links, code, emoji, mentions) and `column_settings` alignment.
  Markdown cannot produce this.
- `rich_text` with `style.underline`, user mentions, nested `rich_text_list` indents.
- `header` → heading, `divider` → divider, `section` mrkdwn → rich text, `context` → text,
  `markdown` block kept.
- Dropped: ordered-list `offset`, `date` elements (fallback text only).

## 5. HTML importer (used only when the plain text is not markdown)

Kept: `b strong i em u s strike code`, bold/italic/underline set by CSS `style` (Google Docs copies
work), `a` with http or mailto (not `javascript:`), `pre` → code lines, `blockquote` (flattened), `hr`,
simple `ul`.

Dropped or flattened: color, background, `del kbd mark sup sub small img`, `h1`–`h6` (plain
paragraphs), `ol` (numbers become text), nested list structure, `details dl abbr`. An HTML `<table>`
without tab-separated plain text is ignored.

## 6. Copying a rendered reply

Selecting a reply rendered by a chat UI (a VS Code webview, ChatGPT or Claude in a browser) and
pressing Cmd+C gives Chrome's copy of the selection: `text/html` of the rendered page and
`text/plain` with the markdown already stripped. The plain text no longer looks like markdown, so
Slack uses its HTML importer (section 5). Measured with `lab/readme_shots.py` (`ui_markdown`
payloads, a real Cmd+C from a rendered page):

- Headings become plain paragraphs. Bold, links, inline code, bullets (nested too), simple numbered
  lists and code blocks survive; code blocks lose their language.
- A table inside a longer reply collapses into one line (`CheckOwnerStatusBuild ci OK…`). A table
  copied alone arrives as tab-separated text, not as a table block.

A chat UI's copy button usually copies the raw markdown, which goes through section 3 instead.

## 7. What this means for a clipboard tool

- Put markdown as `text/plain` **and** an HTML rendering. When the check passes, markdown wins; when
  it fails, the HTML still carries the formatting. Plain only loses the cases in section 2.
- Do not pre-render tables to code blocks: a pipe table becomes a real table.
- For formatted table cells or alignment, write `slack/block-kit` into the Chromium custom-data entry.
- Writing `text/markdown` skips the *any* check but only fires on *complex* markdown.
