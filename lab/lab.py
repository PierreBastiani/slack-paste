"""Slack composer paste lab.

  uv run --with playwright python lab/lab.py login
      Opens Chrome on its own profile (lab/profile). Log in, open the conversation to test in
      (your own DM), and the URL is saved to lab/target.txt once a composer shows up.

  uv run --with playwright python lab/lab.py run [--mode plain|html|both|synthetic] [--send] [case ...]
      For each case (lab/cases/*.md by default): put the payload on the macOS clipboard, Cmd+V into
      the composer, record the composer HTML, a screenshot and every Slack API request that carries
      `blocks` (drafts.*, chat.postMessage). Without --send the composer is cleared, nothing is posted.
      Results go to lab/results/<run>/<case>.json.

  A case is a .md file. Optional front matter selects payloads:
      ---
      html: <b>bold</b>       (used by --mode html/both; default = pandoc md -> html)
      ---
"""
import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from clip import dump_clipboard, set_clipboard  # noqa: E402

LAB = Path(__file__).parent
PROFILE = LAB / "profile"
TARGET = LAB / "target.txt"
COMPOSER = '[data-qa="message_input"] [contenteditable="true"], [contenteditable="true"][role="textbox"]'


def launch(p, scale=1):
    return p.chromium.launch_persistent_context(
        str(PROFILE), channel="chrome", headless=False, viewport={"width": 1400, "height": 900},
        device_scale_factor=scale,
        args=["--disable-features=ExternalProtocolDialog"],
    )


def login():
    with sync_playwright() as p:
        ctx = launch(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://app.slack.com/client")
        print("Log in, then open the conversation to test in (your own DM). Waiting up to 15 min...", flush=True)
        deadline = time.time() + 900
        last = None
        while time.time() < deadline:
            try:
                if page.locator(COMPOSER).first.is_visible() and "/client/" in page.url:
                    if page.url != last:
                        last = page.url
                        TARGET.write_text(page.url + "\n")
                        print("target:", page.url, flush=True)
            except Exception:
                pass
            if (LAB / "login.done").exists():
                break
            time.sleep(2)
        ctx.close()
        print("saved target:", TARGET.read_text().strip() if TARGET.exists() else None)


def parse_case(path: Path):
    text = path.read_text()
    meta = {}
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
        text = text[m.end():]
    return text, meta


def md_to_html(md: str) -> str:
    return subprocess.run(["pandoc", "-f", "gfm", "-t", "html"], input=md, capture_output=True,
                          text=True, check=True).stdout


def extract_blocks(post: str | None):
    if not post:
        return None
    m = re.search(r'name="blocks"\r?\n\r?\n(.*?)\r?\n--', post, re.S)
    raw = m.group(1) if m else None
    if raw is None:
        from urllib.parse import parse_qs
        raw = (parse_qs(post).get("blocks") or [None])[0]
    try:
        return json.loads(raw) if raw else None
    except json.JSONDecodeError:
        return raw


def clear(page, box):
    for b in page.locator('[data-qa="texty_opaque_block_delete"]').all():
        try:
            b.click(force=True)
        except Exception:
            pass
    page.keyboard.press("Escape")
    box.click()
    for _ in range(3):
        page.keyboard.press("Meta+a")
        page.keyboard.press("Backspace")
    time.sleep(0.5)


def run(args):
    target = args.target or (TARGET.read_text().strip() if TARGET.exists() else None)
    if not target:
        sys.exit("no target: run login first or pass --target")
    cases = [Path(c) for c in args.cases] or sorted((LAB / "cases").glob("*.md"))
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = LAB / "results" / f"{stamp}-{args.mode}{'-send' if args.send else ''}"
    out_dir.mkdir(parents=True)

    with sync_playwright() as p:
        ctx = launch(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        captured = []

        def on_request(req):
            if "/api/" not in req.url or req.method != "POST":
                return
            body = req.post_data
            if body and "blocks" in body:
                captured.append({"endpoint": req.url.split("/api/")[1].split("?")[0],
                                 "blocks": extract_blocks(body)})

        page.on("request", on_request)
        page.goto(target)
        box = page.locator(COMPOSER).first
        box.wait_for(timeout=60000)
        time.sleep(3)

        for case in cases:
            web = None
            if case.suffix == ".json":  # explicit payload: {"plain": ..., "html": ..., "web": {type: value}}
                spec = json.loads(case.read_text())
                md = spec.get("plain", "")
                payload = {k: spec[k] for k in ("plain", "html") if k in spec}
                web = spec.get("web")
            else:
                md, meta = parse_case(case)
                payload = {}
                if args.mode in ("plain", "both", "synthetic"):
                    payload["plain"] = md
                if args.mode in ("html", "both"):
                    payload["html"] = meta.get("html") or md_to_html(md)
            clear(page, box)
            captured.clear()
            box.click()
            if args.mode == "synthetic":
                page.evaluate("""([sel, plain]) => {
                    const el = document.querySelector(sel); el.focus();
                    const dt = new DataTransfer(); dt.setData('text/plain', plain);
                    el.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
                }""", [COMPOSER.split(",")[0], md])
            else:
                set_clipboard(payload, web)
                page.keyboard.press("Meta+v")
            time.sleep(args.wait)
            composer_html = box.inner_html()
            opaque = page.eval_on_selector_all('[data-block-source]',
                                               "els => els.map(e => JSON.parse(e.dataset.blockSource))")
            composer_text = box.inner_text()
            shot = out_dir / f"{case.stem}.png"
            page.screenshot(path=str(shot))
            toasts = [t for t in page.locator('.p-markdown_paste_toast, [class*="toast"]').all_inner_texts() if 'arkdown' in t or 'ormat' in t]
            if args.send:
                page.keyboard.press("Enter")
                time.sleep(3)
            else:
                time.sleep(args.draft_wait)  # let drafts.* fire with the blocks
            result = {
                "case": case.name, "mode": args.mode, "payload": payload,
                "composer_text": composer_text, "composer_html": composer_html,
                "toasts": [t for t in toasts if t.strip()], "opaque_blocks": opaque, "requests": list(captured),
            }
            (out_dir / f"{case.stem}.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
            kinds = [r["endpoint"] for r in captured]
            tags = sorted(set(re.findall(r"<(\w+)", composer_html)))
            print(f"{case.stem:28s} tags={','.join(tags)} opaque={[o.get('type') for o in opaque]} toast={bool(result['toasts'])} req={kinds}", flush=True)
            if not args.send:
                clear(page, box)
        ctx.close()
    print("results:", out_dir)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login")
    sub.add_parser("pbdump", help="print every type on the macOS clipboard")
    r = sub.add_parser("run")
    r.add_argument("cases", nargs="*")
    r.add_argument("--mode", default="plain", choices=["plain", "html", "both", "synthetic"])
    r.add_argument("--send", action="store_true")
    r.add_argument("--target")
    r.add_argument("--wait", type=float, default=2.0)
    r.add_argument("--draft-wait", type=float, default=4.0)
    args = ap.parse_args()
    if args.cmd == "login":
        login()
    elif args.cmd == "pbdump":
        print(json.dumps(dump_clipboard(), indent=2, ensure_ascii=False))
    else:
        run(args)


if __name__ == "__main__":
    main()
