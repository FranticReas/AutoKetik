"""
autoketik.parser - Parser HTML dokumen Google Docs dan pengambil sumber teks.
"""

from html.parser import HTMLParser
import re
from .config import Block, Run, ALIGN_KEYS


def _pt(v):
    m = re.match(r"\s*(-?[\d.]+)\s*(pt|px|in|cm)?", v or "")
    if not m:
        return 0.0
    try:
        x = float(m.group(1))
    except ValueError:
        return 0.0
    return x * {"pt": 1, "px": 0.75, "in": 72, "cm": 28.35}[m.group(2) or "pt"]


def _line(v):
    v = (v or "").strip()
    try:
        if v.endswith("%"):
            return float(v[:-1]) / 100
        if v.endswith("pt") or v.endswith("px"):
            return 0.0
        return float(v)
    except ValueError:
        return 0.0


def parse_css(html: str) -> dict:
    css = {}
    for style in re.findall(r"<style[^>]*>(.*?)</style>", html, re.S | re.I):
        for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", style):
            props = {}
            for kv in body.split(";"):
                if ":" in kv:
                    k, v = kv.split(":", 1)
                    props[k.strip().lower()] = v.strip().lower()
            for s in sel.split(","):
                m = re.fullmatch(r"\.([\w-]+)", s.strip())
                if m:
                    css.setdefault(m.group(1), {}).update(props)
    return css


class DocParser(HTMLParser):
    BLOCKS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li"}
    INLINE = {"span", "a", "b", "strong", "i", "em", "u"}

    def __init__(self, css):
        super().__init__(convert_charrefs=True)
        self.css = css
        self.blocks = []
        self.cur = None
        self.stack = []
        self.lists = []
        self.skip = 0

    def _props(self, attrs):
        a = dict(attrs)
        d = {}
        for c in (a.get("class") or "").split():
            d.update(self.css.get(c, {}))
        for kv in (a.get("style") or "").split(";"):
            if ":" in kv:
                k, v = kv.split(":", 1)
                d[k.strip().lower()] = v.strip().lower()
        return d

    def end_block(self):
        if self.cur is not None:
            self.blocks.append(self.cur)
            self.cur = None
            self.stack = []

    def add(self, s):
        if self.cur is None or not s:
            return
        eff = {}
        for _, d in self.stack:
            eff.update(d)
        w = eff.get("font-weight", "400")
        bold = w in ("bold", "bolder") or (w.isdigit() and int(w) >= 600)
        ital = eff.get("font-style") == "italic"
        und = "underline" in eff.get("text-decoration", "")
        sz = _pt(eff.get("font-size"))
        runs = self.cur.runs
        if runs and (runs[-1].b, runs[-1].i, runs[-1].u, runs[-1].size) == (bold, ital, und, sz):
            runs[-1].text += s
        else:
            runs.append(Run(s, bold, ital, und, sz))

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "title"):
            self.skip += 1
            return
        if tag in ("ul", "ol"):
            self.end_block()
            self.lists.append(tag)
            return
        if tag in self.BLOCKS:
            if tag == "p" and self.cur is not None and self.cur.lst:
                return  # <p> di dalam <li>: tetap satu item
            self.end_block()
            d = self._props(attrs)
            b = Block()
            if tag[0] == "h" and len(tag) == 2:
                b.heading = int(tag[1])
            al = d.get("text-align", "left")
            b.align = al if al in ALIGN_KEYS else "left"
            b.first = _pt(d.get("text-indent"))
            b.line = _line(d.get("line-height"))
            b.before = _pt(d.get("padding-top"))
            b.after = _pt(d.get("padding-bottom"))
            if tag == "li":
                b.lst = self.lists[-1] if self.lists else "ul"
                b.depth = max(1, len(self.lists))
            else:
                b.left = _pt(d.get("margin-left"))
            self.cur = b
            return
        if tag == "br":
            self.add("\v")
            return
        if tag in self.INLINE:
            d = self._props(attrs)
            if tag in ("b", "strong"):
                d["font-weight"] = "700"
            if tag in ("i", "em"):
                d["font-style"] = "italic"
            if tag == "u":
                d["text-decoration"] = "underline"
            self.stack.append((tag, d))

    def handle_endtag(self, tag):
        if tag in ("style", "script", "title"):
            self.skip = max(0, self.skip - 1)
            return
        if tag in ("ul", "ol"):
            self.end_block()
            if self.lists:
                self.lists.pop()
            return
        if tag in self.BLOCKS:
            if tag == "p" and self.cur is not None and self.cur.lst:
                return
            self.end_block()
            return
        if tag in self.INLINE:
            for k in range(len(self.stack) - 1, -1, -1):
                if self.stack[k][0] == tag:
                    del self.stack[k]
                    break

    def handle_data(self, data):
        if self.skip:
            return
        self.add(data.replace("\xa0", " ").replace("\n", " "))


def parse_html(html: str):
    p = DocParser(parse_css(html))
    p.feed(html)
    p.end_block()
    blocks = p.blocks
    while blocks and not blocks[0].text.strip():
        blocks.pop(0)
    while blocks and not blocks[-1].text.strip():
        blocks.pop()
    return blocks


def fetch_gdoc(url_or_id: str, fmt: str = "html") -> str:
    import requests

    m = re.search(r"/document/d/([a-zA-Z0-9_-]+)", url_or_id)
    doc_id = m.group(1) if m else url_or_id.strip()
    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format={fmt}"
    r = requests.get(export_url, timeout=30)
    if r.status_code != 200 or "accounts.google.com" in r.url:
        raise RuntimeError(
            "Gagal membaca Google Docs. Pastikan sharing diatur ke "
            "'Anyone with the link' (Viewer), atau pakai opsi File / Clipboard."
        )
    r.encoding = "utf-8"
    return r.text


def normalize(text: str) -> str:
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    return text.rstrip("\n")
