"""Screenshot the target conversation after scrolling up N screens: shot.py N out.png"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lab import launch, COMPOSER, TARGET
from playwright.sync_api import sync_playwright
n, out = int(sys.argv[1]), sys.argv[2]
with sync_playwright() as p:
    ctx = launch(p); page = ctx.pages[0]
    page.goto(TARGET.read_text().strip()); page.locator(COMPOSER).first.wait_for(timeout=60000); time.sleep(3)
    page.mouse.move(800, 400)
    for _ in range(n):
        page.mouse.wheel(0, -600); time.sleep(0.6)
    time.sleep(1.5); page.screenshot(path=out); ctx.close()
