"""Defense layer 1 (code): turn a document into the text a person would actually see, then scrub it.

Drops: HTML comments, scripts, hidden/zero-size/white/off-screen HTML text, invisible or tiny or white or
off-page PDF text, the HTML half of an email when a plain-text half exists, zero-width characters,
links, and lines that give orders to an AI. Every removal is recorded in a report.
"""
import email
import re
import unicodedata
from email import policy
from html.parser import HTMLParser
from pathlib import Path

from pypdf import PdfReader
from pypdf.generic import ContentStream

VOID = {"br", "hr", "img", "meta", "link", "input", "area", "base", "col", "source", "wbr"}
BLOCK = {"tr", "p", "br", "h1", "h2", "h3", "li", "div", "header", "footer", "table"}
WHITE = re.compile(r"(?<![\w#-])(#fff(?:fff)?|white|rgb\(\s*255\s*,\s*255\s*,\s*255\s*\))\b", re.I)
URL = re.compile(r"(?:https?://|ftp://|www\.)\S+", re.I)
INJECTION = re.compile(
    r"send_email|approve_payment|system note|note to (?:the )?(?:ai|assistant)|standing instruction|"
    r"(?:ignore|disregard|override|forget)\b.{0,50}\b(?:instruction|rules?|handbook|prompt|policy|above)", re.I)


NAMED_LIGHT = {"white", "ivory", "snow", "whitesmoke", "ghostwhite", "floralwhite", "seashell", "azure", "mintcream",
               "aliceblue", "honeydew", "lavenderblush", "oldlace", "linen", "beige", "transparent"}


def _rgba(value: str) -> tuple[float, float, float, float] | None:
    v = value.strip().lower()
    if v in NAMED_LIGHT:
        return (0.0, 0.0, 0.0, 0.0) if v == "transparent" else (255.0, 255.0, 255.0, 1.0)
    m = re.fullmatch(r"#([0-9a-f]{3,8})", v)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a
    m = re.fullmatch(r"rgba?\(([^)]*)\)", v)
    if m:
        n = [float(x.strip().rstrip("%")) for x in re.split(r"[,\s/]+", m.group(1).strip()) if x.strip()]
        if len(n) >= 3:
            return n[0], n[1], n[2], n[3] if len(n) > 3 else 1.0
    return None


def _invisible_color(color: str, background: str = "") -> bool:
    """True if the text color is transparent, near-white (the pages are white), or equal to its own background."""
    c = _rgba(color)
    if not c:
        return False
    if c[3] < 0.1 or min(c[:3]) >= 238:  # transparent, or lighter than about 93 percent white
        return True
    return bool(background) and background.strip().lower() == color.strip().lower()


def _px(value: str) -> float | None:
    m = re.match(r"\s*(-?[\d.]+)\s*(px|pt|em|rem|%)?", value)
    if not m:
        return None
    n = float(m.group(1))
    return n * {"pt": 1.33, "em": 16, "rem": 16, "%": 0.16}.get(m.group(2) or "px", 1)


def _style_hidden(style: str) -> str | None:
    props = {k.strip().lower(): v.strip().lower() for k, v in
             (p.split(":", 1) for p in style.split(";") if ":" in p)}
    if props.get("display") == "none":
        return "display:none"
    if props.get("visibility") in ("hidden", "collapse"):
        return "visibility:hidden"
    if "opacity" in props and (_px(props["opacity"]) or 0) < 0.1:
        return "opacity:0"
    if "font-size" in props and (_px(props["font-size"]) is not None) and _px(props["font-size"]) < 4:
        return "tiny font"
    if "color" in props and _invisible_color(props["color"], props.get("background-color", props.get("background", ""))):
        return "invisible colored text"
    for k in ("left", "top", "right", "bottom", "text-indent", "margin-left"):
        if k in props and (_px(props[k]) or 0) <= -500:
            return "off-screen"
    if props.get("height") in ("0", "0px") and props.get("overflow") == "hidden":
        return "zero height"
    return None


class _Visible(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.removed: list[str] = []
        self.stack: list[tuple[str, str | None, str | None]] = []  # (tag, reason this element is hidden, href)

    def _hidden(self) -> str | None:
        return next((r for _, r, _h in reversed(self.stack) if r), None)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in VOID:
            if tag == "br" and not self._hidden():
                self.parts.append("\n")
            return
        reason = None
        if tag in ("script", "style", "noscript", "template", "head", "title", "iframe", "object"):
            reason = f"<{tag}>"
        elif "hidden" in a or a.get("aria-hidden") == "true":
            reason = "hidden attribute"
        elif a.get("style"):
            reason = _style_hidden(a["style"])
        elif a.get("color") and _invisible_color(a["color"]):
            reason = "invisible colored text"
        self.stack.append((tag, reason, a.get("href")))
        if tag in BLOCK and not self._hidden():
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break
        if tag in ("th", "td") and not self._hidden():
            self.parts.append(" ")

    def handle_data(self, data):
        why = self._hidden()
        if why:
            if data.strip() and why not in ("<title>", "<style>", "<head>"):
                link = next((h for _t, _r, h in reversed(self.stack) if h), None)
                self.removed.append(f"hidden link ({link[:80]}) text, {why}: {data.strip()[:120]}" if link else f"{why}: {data.strip()[:120]}")
        else:
            self.parts.append(data)

    def handle_comment(self, data):
        if data.strip():
            self.removed.append(f"html comment: {data.strip()[:120]}")


def html_visible(markup: str) -> tuple[str, list[str]]:
    p = _Visible()
    p.feed(markup)
    return "".join(p.parts), p.removed


def pdf_visible(path: str) -> tuple[str, list[str]]:
    reader = PdfReader(path)
    lines, removed = [], []
    for page in reader.pages:
        w, h = float(page.mediabox.width), float(page.mediabox.height)
        fill, size, mode, pos, saved = (0, 0, 0), 12.0, 0, (0.0, 0.0), []
        for ops, op in ContentStream(page.get_contents(), reader).operations:
            if op == b"q":
                saved.append((fill, size, mode))
            elif op == b"Q" and saved:
                fill, size, mode = saved.pop()
            elif op == b"rg":
                fill = tuple(float(x) for x in ops)
            elif op == b"g":
                fill = (float(ops[0]),) * 3
            elif op == b"k":
                c, m, y, k = (float(x) for x in ops)
                fill = tuple(1 - min(1, v + k) for v in (c, m, y))
            elif op == b"Tf":
                size = abs(float(ops[1]))
            elif op == b"Tr":
                mode = int(ops[0])
            elif op == b"BT":
                pos = (0.0, 0.0)
            elif op == b"Tm":
                pos = (float(ops[4]), float(ops[5]))
            elif op in (b"Td", b"TD"):
                pos = (pos[0] + float(ops[0]), pos[1] + float(ops[1]))
            elif op in (b"Tj", b"TJ", b"'", b'"'):
                shown = ops[-1]
                parts = shown if isinstance(shown, list) else [shown]
                text = "".join(x if isinstance(x, str) else x.decode("latin1") for x in parts if not isinstance(x, (int, float)))
                if not text.strip():
                    continue
                why = ("invisible render mode" if mode == 3 else "tiny font" if size < 4 else
                       "invisible colored text" if min(fill) > 0.93 else
                       "off the page" if not (-1 <= pos[0] <= w + 1 and -1 <= pos[1] <= h + 1) else None)
                if why:
                    removed.append(f"{why}: {text.strip()[:120]}")
                else:
                    lines.append(text)
    return "\n".join(lines), removed


def eml_visible(path: str) -> tuple[str, list[str]]:
    msg = email.message_from_bytes(Path(path).read_bytes(), policy=policy.default)
    head = "\n".join(f"{h}: {msg[h]}" for h in ("From", "To", "Subject", "Date") if msg[h])
    plain, html = msg.get_body(("plain",)), msg.get_body(("html",))
    removed: list[str] = []
    if plain:  # a person reading plain text sees exactly this; the HTML twin is not trusted
        body = plain.get_content()
        if html:
            removed.append("html part of email skipped (plain-text part used)")
    elif html:
        body, removed = html_visible(html.get_content())
    else:
        body = ""
    return f"{head}\n\n{body}", removed


def scrub(text: str) -> tuple[str, list[str]]:
    """Normalize characters, cut links, cut instruction-like lines, tidy blank lines."""
    removed = []
    text = unicodedata.normalize("NFKC", text)
    n = sum(1 for c in text if (unicodedata.category(c) in ("Cf", "Cc") and c not in "\n\t")
            or 0xFE00 <= ord(c) <= 0xFE0F or 0xE0100 <= ord(c) <= 0xE01EF)
    if n:
        removed.append(f"{n} invisible/control characters")
    text = "".join(c for c in text if (unicodedata.category(c) not in ("Cf", "Cc") or c in "\n\t")
                   and not (0xFE00 <= ord(c) <= 0xFE0F or 0xE0100 <= ord(c) <= 0xE01EF))
    for u in URL.findall(text):
        removed.append(f"link: {u[:120]}")
    text = URL.sub("[link removed]", text)
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if INJECTION.search(line):
            removed.append(f"instruction aimed at the AI: {line[:120]}")
            out.append("[line removed: it gave instructions to the AI]")
        else:
            out.append(line)
    return "\n".join(out), removed


def read_clean(path: str) -> tuple[str, list[str]]:
    ext = Path(path).suffix.lower()
    raw, removed = {".html": lambda: html_visible(Path(path).read_text(encoding="utf-8", errors="replace")),
                    ".htm": lambda: html_visible(Path(path).read_text(encoding="utf-8", errors="replace")),
                    ".pdf": lambda: pdf_visible(path), ".eml": lambda: eml_visible(path)}[ext]()
    text, more = scrub(raw)
    return text, removed + more


# Same names as the raw readers in tools.py so the model sees the same tool menu either way.
def read_html(path: str) -> str:
    """Read an HTML vendor quote or catalog page and return its visible text."""
    return read_clean(path)[0]


def read_pdf(path: str) -> str:
    """Read a PDF vendor quote and return its text."""
    return read_clean(path)[0]


def read_eml(path: str) -> str:
    """Read a .eml supplier email and return its headers (From, To, Subject, Date) and plain-text body."""
    return read_clean(path)[0]
