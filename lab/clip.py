"""macOS pasteboard helpers (JXA through osascript): set typed payloads, dump every type."""
import json
import subprocess

SET_JXA = r"""
ObjC.import('AppKit');
function run(argv) {
  const items = JSON.parse(argv[0]);
  const pb = $.NSPasteboard.generalPasteboard;
  pb.clearContents;
  for (const [type, text] of Object.entries(items)) {
    if (text.startsWith('base64:')) {
      const d = $.NSData.alloc.initWithBase64EncodedStringOptions($(text.slice(7)), 0);
      pb.setDataForType(d, $(type));
    } else {
      pb.setStringForType($(text), $(type));
    }
  }
}
"""

DUMP_JXA = r"""
ObjC.import('AppKit');
function run() {
  const pb = $.NSPasteboard.generalPasteboard;
  const types = ObjC.deepUnwrap(pb.types) || [];
  const out = {};
  for (const t of types) {
    const s = pb.stringForType($(t));
    if (s && !s.isNil()) { out[t] = ObjC.unwrap(s); continue; }
    const d = pb.dataForType($(t));
    out[t] = d && !d.isNil() ? ('base64:' + ObjC.unwrap(d.base64EncodedStringWithOptions(0))) : null;
  }
  return JSON.stringify(out);
}
"""

TYPES = {"plain": "public.utf8-plain-text", "html": "public.html", "rtf": "public.rtf"}


def set_clipboard(items: dict, web: dict | None = None) -> None:
    """items: {"plain": "...", "html": "..."} or raw UTI keys.
    web: web clipboard types ({"slack/block-kit": "...", "text/markdown": "..."}) packed into
    Chromium's org.chromium.web-custom-data pickle."""
    payload = {TYPES.get(k, k): v for k, v in items.items()}
    if web:
        import base64
        from webcustom import encode
        payload["org.chromium.web-custom-data"] = "base64:" + base64.b64encode(encode(web)).decode()
    subprocess.run(["osascript", "-l", "JavaScript", "-e", SET_JXA, json.dumps(payload)], check=True)


def dump_clipboard() -> dict:
    out = subprocess.run(["osascript", "-l", "JavaScript", "-e", DUMP_JXA], check=True,
                         capture_output=True, text=True).stdout
    return json.loads(out)


if __name__ == "__main__":
    print(json.dumps(dump_clipboard(), indent=2, ensure_ascii=False))
