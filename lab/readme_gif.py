"""Before/after GIF: readme_gif.py before.png after.png out.gif "before label" "after label" """
import subprocess, sys, tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
before, after, out, lb, la = sys.argv[1:6]
W = 1000  # CSS px; rendered at 2x then scaled down by ffmpeg
PAGE = """<!doctype html><meta charset="utf-8"><style>
body{{margin:0;background:#fff;font:600 22px -apple-system,system-ui,sans-serif}}
.card{{width:{w}px;height:{h}px;padding:28px 32px;box-sizing:border-box;position:relative}}
.tag{{display:inline-block;padding:6px 12px;border-radius:6px;margin-bottom:18px;font-size:18px}}
.before .tag{{background:#fde2dd;color:#a3271a}} .after .tag{{background:#dff3e4;color:#1d6b35}}
img{{width:{iw}px;display:block}}</style><div class="card {cls}"><span class="tag">{label}</span><img src="{src}"></div>"""
with sync_playwright() as p, tempfile.TemporaryDirectory() as tmp:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(device_scale_factor=2)
    # height = tallest screenshot (2x px -> CSS px at image width W-64)
    import struct
    def size(f):
        d = Path(f).read_bytes(); return struct.unpack(">II", d[16:24])
    iw = W - 64
    h = max(int(size(f)[1] * iw / size(f)[0]) for f in (before, after)) + 110
    frames = []
    for i, (src, label, cls) in enumerate([(before, lb, "before"), (after, la, "after")]):
        pg.set_viewport_size({"width": W, "height": h})
        pg.set_content(PAGE.format(w=W, h=h, iw=iw, src="data:image/png;base64," + __import__("base64").b64encode(Path(src).read_bytes()).decode(), label=label, cls=cls))
        pg.wait_for_timeout(300); f = f"{tmp}/f{i}.png"; pg.screenshot(path=f); frames.append(f)
    b.close()
    hold, fade = 3.0, 0.6
    flt = (f"[0][1]xfade=transition=fade:duration={fade}:offset={hold}[ab];"
           f"[ab][0]xfade=transition=fade:duration={fade}:offset={2*hold+fade}[v];"
           f"[v]fps=12,scale=900:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=96[pal];[s1][pal]paletteuse=dither=none")
    T = 3 * hold + 2 * fade
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    "-loop", "1", "-t", str(T), "-i", frames[0],
                    "-loop", "1", "-t", str(T), "-i", frames[1],
                    "-filter_complex", flt, "-t", str(2 * hold + 2 * fade), "-loop", "0", out], check=True)
print(out, Path(out).stat().st_size // 1024, "KB")
