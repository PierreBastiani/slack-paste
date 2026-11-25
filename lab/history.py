"""Fetch the last N messages of the target conversation with the web client's own session (xoxc token)."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lab import launch, COMPOSER, TARGET
from playwright.sync_api import sync_playwright
n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
out = Path(sys.argv[2]) if len(sys.argv) > 2 else None
url = TARGET.read_text().strip(); team, chan = url.split("/client/")[1].split("/")[:2]
with sync_playwright() as p:
    ctx = launch(p); page = ctx.pages[0]
    page.goto(url); page.locator(COMPOSER).first.wait_for(timeout=60000); time.sleep(2)
    res = page.evaluate("""async ([team, chan, n]) => {
        const cfg = JSON.parse(localStorage.getItem('localConfig_v2'));
        const token = cfg.teams[team].token;
        const fd = new FormData(); fd.append('token', token); fd.append('channel', chan); fd.append('limit', String(n));
        const r = await fetch('/api/conversations.history', {method: 'POST', body: fd, credentials: 'include'});
        return await r.json();
    }""", [team, chan, n])
    page.screenshot(path=str(out.with_suffix(".png")) if out else "/dev/null", full_page=False)
    ctx.close()
msgs = res.get("messages", [])
if not res.get("ok"): print(res)
if out: out.write_text(json.dumps(msgs, indent=1, ensure_ascii=False))
for m in reversed(msgs):
    print("---", m.get("ts"), [b.get("type") for b in m.get("blocks", [])], repr(m.get("text", ""))[:100])
