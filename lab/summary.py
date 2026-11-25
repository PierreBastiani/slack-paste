"""Summarise a results run: one line per case with what the composer holds."""
import json, re, sys
from pathlib import Path
run = Path(sys.argv[1]) if len(sys.argv) > 1 else sorted((Path(__file__).parent / "results").iterdir())[-1]
print(run.name)
for f in sorted(run.glob("*.json")):
    r = json.loads(f.read_text())
    html = r["composer_html"]
    html = re.sub(r'<div class="c-texty_opaque_block.*?</div></div>', "[BLOCK]", html, flags=re.S)
    html = re.sub(r'\s(class|data-[\w-]+|spellcheck|dir|rel|target)="[^"]*"', "", html)
    plain = r["payload"].get("plain", "")
    literal = bool(plain) and all(line.strip() in r["composer_text"] for line in plain.splitlines() if line.strip()) and not r["opaque_blocks"] and "<strong>" not in html and "<em>" not in html and "<a " not in html and "<code" not in html and "<ol" not in html and "<ul" not in html and "<blockquote" not in html
    ob = [(o["type"], json.dumps(o, ensure_ascii=False)[:160]) for o in r.get("opaque_blocks", [])]
    print(f"\n## {f.stem}  {'LITERAL' if literal else 'CONVERTED'}  toast={r['toasts'][:1]}")
    print("   ", html[:400])
    for t, j in ob:
        print("    block:", j)
