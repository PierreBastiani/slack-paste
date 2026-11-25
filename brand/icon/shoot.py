import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
d = Path(__file__).parent.resolve()
keys = sorted({f.name.rsplit("-", 1)[0] for f in d.glob("*-day.svg")})
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome"); pg = b.new_page(viewport={"width": 1000, "height": 600})
    pg.goto((d / "sheet.html").as_uri()); pg.wait_for_timeout(800)
    pg.screenshot(path=str(d / "sheet.png"), full_page=True)
    pg.set_viewport_size({"width": 1024, "height": 1024})
    for k in keys:
        for m in ("day", "night"):
            pg.set_content(f'<style>body{{margin:0}}</style><img src="{(d / f"{k}-{m}.svg").as_uri()}" width="1024" height="1024">')
            pg.wait_for_timeout(400); pg.screenshot(path=str(d / f"{k}-{m}-1024.png"))
    b.close()
print(keys)
