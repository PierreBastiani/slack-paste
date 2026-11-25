#!/usr/bin/env python3
"""Put a markdown message on the macOS clipboard so Slack's composer formats it on paste.

Clipboard payloads (https://github.com/PierreBastiani/slack-paste/blob/main/FINDINGS.md explains each one):
  text/plain  the markdown itself. Slack converts it when its "is this markdown?" check passes.
  text/html   pandoc rendering of the same markdown. Slack uses it only when the check fails
              (e.g. a message whose only markup is _italic_ at the very start), so formatting
              survives either way. HTML alone pastes nothing.
  slack/block-kit (--blocks)  Block Kit JSON built from the markdown, written into Chromium's
              org.chromium.web-custom-data pasteboard entry. Slack inserts it as is: tables keep
              bold/links/code in cells and column alignment, which the markdown path drops.

Usage: slack_clip.py [--blocks] [--code-tables] [--dump FILE] < message.md
  --code-tables  render pipe tables as an aligned code block (for workspaces without table blocks)
  --dump FILE    also write the payloads as JSON (for tests); --no-copy skips the clipboard
"""
import argparse
import base64
import json
import os
import re
import shutil
import struct
import subprocess
import sys

TABLE_LINE = re.compile(r"^\s*\|.*\|\s*$")


# ---------- markdown helpers ----------

def pandoc(md: str, to: str, extra=()) -> str:
    if not shutil.which("pandoc"):
        sys.exit("pandoc not found: brew install pandoc")
    return subprocess.run(["pandoc", "-f", "gfm", "-t", to, *extra], input=md, text=True,
                          capture_output=True, check=True).stdout


def code_tables(md: str) -> str:
    """Replace each pipe-table block with an aligned plain-text rendering in a code fence."""
    out, buf = [], []

    def flush():
        if buf:
            txt = subprocess.run(["pandoc", "-f", "markdown", "-t", "plain", "--columns=95"],
                                 input="\n".join(buf) + "\n", text=True, capture_output=True,
                                 check=True).stdout.strip("\n")
            out.extend(["```", txt, "```"])
            buf.clear()

    in_fence = False
    for line in md.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and TABLE_LINE.match(line):
            buf.append(line)
            continue
        flush()
        out.append(line)
    flush()
    return "\n".join(out) + "\n"


# ---------- markdown -> Block Kit (own implementation on markdown-it-py) ----------

EMOJI = re.compile(r":([a-z0-9_+\-]+):")


def _md():
    try:
        from markdown_it import MarkdownIt
    except ImportError:
        sys.exit("--blocks needs markdown-it-py: pip install markdown-it-py "
                 "(or run through: uv run --with markdown-it-py==4.3.0)")
    return MarkdownIt("commonmark").enable(["table", "strikethrough"])


def inline_elements(children):
    els, styles, links = [], [], []

    def style():
        s = {}
        for d in styles:
            s.update(d)
        return s

    def text(t, extra=None):
        if not t:
            return
        st = {**style(), **(extra or {})}
        parts = [t] if st.get("code") else EMOJI.split(t)
        for i, part in enumerate(parts):
            if i % 2 and not st.get("code"):
                els.append({"type": "emoji", "name": part})
                continue
            if not part:
                continue
            el = {"type": "link", "url": links[-1], "text": part} if links else {"type": "text", "text": part}
            if st:
                el["style"] = st
            els.append(el)

    for tok in children or []:
        t = tok.type
        if t == "text":
            text(tok.content)
        elif t in ("softbreak", "hardbreak"):
            text("\n")
        elif t == "strong_open":
            styles.append({"bold": True})
        elif t == "em_open":
            styles.append({"italic": True})
        elif t == "s_open":
            styles.append({"strike": True})
        elif t in ("strong_close", "em_close", "s_close"):
            styles.pop()
        elif t == "code_inline":
            text(tok.content, {"code": True})
        elif t == "link_open":
            links.append(tok.attrs.get("href", ""))
        elif t == "link_close":
            links.pop()
        elif t == "image":
            src = tok.attrs.get("src", "")
            links.append(src)
            text(tok.content or src)
            links.pop()
        elif tok.content:
            text(tok.content)
    # merge neighbours with the same kind, url and style
    merged = []
    for e in els:
        p = merged[-1] if merged else None
        if p and p["type"] == e["type"] and e["type"] in ("text", "link") and p.get("url") == e.get("url") \
                and p.get("style") == e.get("style"):
            p["text"] += e["text"]
        else:
            merged.append(dict(e))
    return merged


def section(els):
    return {"type": "rich_text_section", "elements": els}


def to_blocks(md: str) -> list:
    toks = _md().parse(md)
    blocks, i = [], 0

    def rich(*elements):
        blocks.append({"type": "rich_text", "elements": list(elements)})

    while i < len(toks):
        tok = toks[i]
        t = tok.type
        if t == "paragraph_open":
            rich(section(inline_elements(toks[i + 1].children)))
            i += 3
        elif t == "heading_open":
            level = min(int(tok.tag[1]), 3)
            txt = "".join(c.content for c in toks[i + 1].children or [] if c.content)
            blocks.append({"type": "header", "text": {"type": "plain_text", "text": txt, "emoji": True},
                           "level": level})
            i += 3
        elif t == "hr":
            blocks.append({"type": "divider"})
            i += 1
        elif t in ("fence", "code_block"):
            el = {"type": "rich_text_preformatted",
                  "elements": [{"type": "text", "text": tok.content.rstrip("\n")}]}
            lang = (tok.info or "").strip().split(" ")[0]
            if lang:
                el["language"] = lang
            rich(el)
            i += 1
        elif t in ("bullet_list_open", "ordered_list_open"):
            stack, runs, item = [], [], None
            while i < len(toks):
                tk = toks[i]
                if tk.type in ("bullet_list_open", "ordered_list_open"):
                    stack.append("ordered" if tk.type == "ordered_list_open" else "bullet")
                elif tk.type in ("bullet_list_close", "ordered_list_close"):
                    stack.pop()
                    if not stack:
                        i += 1
                        break
                elif tk.type == "list_item_open":
                    item = None
                elif tk.type == "inline":
                    els = inline_elements(tk.children)
                    indent, style_ = len(stack) - 1, stack[-1]
                    if item is not None:
                        item["elements"] += [{"type": "text", "text": "\n"}] + els
                    else:
                        item = section(els)
                        run = runs[-1] if runs else None
                        if not run or run["style"] != style_ or run.get("indent", 0) != indent:
                            run = {"type": "rich_text_list", "style": style_, "elements": []}
                            if indent:
                                run["indent"] = indent
                            runs.append(run)
                        run["elements"].append(item)
                i += 1
            rich(*runs)
        elif t == "blockquote_open":
            depth, els = 0, []
            while i < len(toks):
                tk = toks[i]
                depth += tk.nesting if tk.type.startswith("blockquote") else 0
                if tk.type == "inline":
                    if els:
                        els.append({"type": "text", "text": "\n"})
                    els += inline_elements(tk.children)
                i += 1
                if depth == 0:
                    break
            rich({"type": "rich_text_quote", "elements": els})
        elif t == "table_open":
            rows, row, aligns = [], [], []
            while toks[i].type != "table_close":
                tk = toks[i]
                if tk.type == "tr_open":
                    row = []
                elif tk.type == "tr_close":
                    rows.append(row)
                elif tk.type in ("th_open", "td_open"):
                    if not rows:
                        m = re.search(r"text-align:(\w+)", tk.attrs.get("style", "") or "")
                        aligns.append(m.group(1) if m else None)
                    els = inline_elements(toks[i + 1].children)
                    plain = len(els) == 1 and els[0]["type"] == "text" and "style" not in els[0]
                    if not els:
                        row.append({"type": "raw_text", "text": " "})
                    elif plain:
                        row.append({"type": "raw_text", "text": els[0]["text"]})
                    else:
                        row.append({"type": "rich_text", "elements": [section(els)]})
                i += 1
            i += 1
            table = {"type": "table", "rows": rows}
            if any(aligns):
                table["column_settings"] = [{"align": a or "left"} for a in aligns]
            blocks.append(table)
        else:
            i += 1

    # Blank line between consecutive text blocks, as Slack's own converter does.
    out = []
    for b in blocks:
        prev = out[-1] if out else None
        if prev and prev["type"] == "rich_text" and b["type"] == "rich_text":
            out.append({"type": "rich_text", "elements": [section([{"type": "text", "text": "\n"}])]})
        out.append(b)
    return out


# ---------- clipboard ----------

def web_custom_data(items: dict) -> bytes:
    """Chromium pickle: uint32 size | uint32 count | (string16 type, string16 value)*"""
    def s16(s):
        raw = s.encode("utf-16-le")
        return struct.pack("<I", len(raw) // 2) + raw + b"\0" * ((-len(raw)) % 4)
    body = struct.pack("<I", len(items)) + b"".join(s16(k) + s16(v) for k, v in items.items())
    return struct.pack("<I", len(body)) + body


SET_JXA = r"""
ObjC.import('AppKit');
function run(argv) {
  const items = JSON.parse($.NSString.stringWithContentsOfFileEncodingError(argv[0], $.NSUTF8StringEncoding, null).js);
  const pb = $.NSPasteboard.generalPasteboard;
  pb.clearContents;
  for (const [type, value] of Object.entries(items)) {
    if (value.startsWith('base64:')) {
      pb.setDataForType($.NSData.alloc.initWithBase64EncodedStringOptions($(value.slice(7)), 0), $(type));
    } else {
      pb.setStringForType($(value), $(type));
    }
  }
}
"""


def copy(payload: dict, web: dict | None):
    items = {"public.utf8-plain-text": payload["plain"]}
    if payload.get("html"):
        items["public.html"] = payload["html"]
    if web:
        items["org.chromium.web-custom-data"] = "base64:" + base64.b64encode(web_custom_data(web)).decode()
    tmp = os.path.join(os.environ.get("TMPDIR", "/tmp"), "slack-clip-items.json")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
    subprocess.run(["osascript", "-l", "JavaScript", "-e", SET_JXA, tmp], check=True)
    os.unlink(tmp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", action="store_true")
    ap.add_argument("--code-tables", action="store_true")
    ap.add_argument("--dump")
    ap.add_argument("--no-copy", action="store_true")
    a = ap.parse_args()
    md = sys.stdin.read()
    if a.code_tables:
        md = code_tables(md)
    payload = {"plain": md, "html": pandoc(md, "html")}
    web = {"slack/block-kit": json.dumps(to_blocks(md), ensure_ascii=False)} if a.blocks else None
    if a.dump:
        with open(a.dump, "w", encoding="utf-8") as f:
            json.dump({**payload, **({"web": web} if web else {})}, f, ensure_ascii=False, indent=1)
    if not a.no_copy:
        copy(payload, web)
    keep = os.path.join(os.environ.get("TMPDIR", "/tmp"), "md-to-slack-rich.md")
    with open(keep, "w", encoding="utf-8") as f:
        f.write(md)
    kinds = "markdown + html" + (" + block-kit" if web else "")
    print(f"----- {kinds} {'copied to clipboard' if not a.no_copy else 'built'} ({len(md.encode())} bytes) -----")
    print("  paste in the Slack composer with Cmd+V (Cmd+Shift+V pastes it unformatted)")
    print(f"  markdown kept at: {keep}")


if __name__ == "__main__":
    main()
