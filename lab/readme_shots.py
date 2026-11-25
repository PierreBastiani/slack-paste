"""Send each payload to the lab channel and screenshot the sent message: readme_shots.py out_dir payload.json..."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lab import launch, COMPOSER, TARGET, clear
from clip import set_clipboard
from playwright.sync_api import sync_playwright
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
UI_PAGE = """<!doctype html><meta charset="utf-8"><style>
body{font:15px -apple-system,system-ui,sans-serif;background:#1e1e1e;color:#ddd;padding:24px}
#reply{max-width:720px} table{border-collapse:collapse} td,th{border:1px solid #555;padding:4px 10px}
code{background:#333;padding:1px 4px;border-radius:3px} pre{background:#111;padding:10px} a{color:#6af}
</style><div id="reply">{{BODY}}</div>"""
with sync_playwright() as p:
    ctx = launch(p, scale=2); page = ctx.pages[0]
    page.set_viewport_size({"width": 1100, "height": 900})
    page.goto(TARGET.read_text().strip()); box = page.locator(COMPOSER).first; box.wait_for(timeout=60000); time.sleep(3)
    for f in sys.argv[2:]:
        spec = json.loads(Path(f).read_text())
        clear(page, box)
        if "ui_markdown" in spec:
            # Render the markdown like a chat UI, select it and copy with a real Cmd+C (Chrome fills
            # the clipboard the way a VS Code webview or a ChatGPT tab does).
            import subprocess
            html = subprocess.run(["pandoc", "-f", "gfm", "-t", "html"], input=spec["ui_markdown"],
                                  capture_output=True, text=True, check=True).stdout
            ui = ctx.new_page()
            ui.set_content(UI_PAGE.replace("{{BODY}}", html))
            ui.bring_to_front(); ui.click("#reply")
            ui.evaluate("""() => { const r = document.createRange(); r.selectNodeContents(document.getElementById('reply'));
                                   const s = getSelection(); s.removeAllRanges(); s.addRange(r); }""")
            ui.keyboard.press("Meta+c"); time.sleep(0.8); ui.close()
            page.bring_to_front(); box.click()
        else:
            box.click()
            set_clipboard({k: spec[k] for k in ("plain", "html") if k in spec}, spec.get("web"))
        page.keyboard.press("Meta+v"); time.sleep(2.5); page.keyboard.press("Enter"); time.sleep(3.5)
        msgs = page.locator('[data-qa="message_container"]')
        el = msgs.nth(msgs.count() - 1)
        page.mouse.move(5, 5); time.sleep(0.5)
        body = el.locator('[data-qa="message-text"], .c-message_kit__blocks').first
        target = body if body.count() else el
        target.screenshot(path=str(out / (Path(f).stem + ".png")))
        print(Path(f).stem, el.bounding_box())
    ctx.close()
