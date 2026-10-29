"""
AutoKetik - Simulasi pengetikan ala manusia dengan format dokumen Google Docs & HTML.
"""

from .config import (
    Config, Run, Block, StopTyping, require_pynput,
    SIZES, ALIGN_KEYS, INDENT_STEP, snap_size,
    keyboard, Controller, Key
)
from .parser import (
    DocParser, parse_html, parse_css, fetch_gdoc, normalize
)
from .planner import (
    plan, parse_range
)
from .engine import (
    Typist, GUITypist
)

__version__ = "2.1.0"
__all__ = [
    "Config",
    "Run",
    "Block",
    "StopTyping",
    "require_pynput",
    "SIZES",
    "ALIGN_KEYS",
    "INDENT_STEP",
    "snap_size",
    "keyboard",
    "Controller",
    "Key",
    "DocParser",
    "parse_html",
    "parse_css",
    "fetch_gdoc",
    "normalize",
    "plan",
    "parse_range",
    "Typist",
    "GUITypist",
]
