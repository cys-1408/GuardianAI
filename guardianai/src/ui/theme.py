"""GuardianAI Design System — Design Tokens & Global QSS.

Central source of truth for the premium SOC command-center theme.
All UI modules import tokens from here — never hardcode colors.
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════
#  Design Tokens (per product spec)
# ═══════════════════════════════════════════════════════════════════════

# Surfaces
BG       = "#05070B"   # app background
PANEL    = "#0E1117"   # panels
CARD     = "#151B23"   # cards
CARD_ALT = "#1A212B"   # card hover / elevated
RAISED   = "#202A36"   # raised glass surface

# Accents
PRIMARY  = "#00D4FF"   # primary
AI       = "#7C4DFF"   # AI accent
SUCCESS  = "#00E676"
WARNING  = "#FFC107"
CRITICAL = "#FF5252"
MUTED    = "#94A3B8"

# Text
TEXT_PRI = "#F1F5F9"
TEXT_SEC = "#A8B3C4"
TEXT_DIM = "#5B6B7F"

# Borders / glows
BORDER       = "#0FFFFFFF"
BORDER_STRONG = "#24FFFFFF"
GLOW         = "#2E00D4FF"
GLOW_AI      = "#337C4DFF"

# Typography
FONT_FAMILY = "'Segoe UI', 'Inter', 'Helvetica Neue', Arial, sans-serif"
FONT_MONO   = "'Cascadia Code', 'Consolas', 'Courier New', monospace"

# Radius scale
RADIUS_S = "6px"
RADIUS_M = "10px"
RADIUS_L = "16px"

# Spacing scale (used by layout code where fixed sizes are required)
SPACE_XS = 4
SPACE_S = 8
SPACE_M = 16
SPACE_L = 24
SPACE_XL = 32


# ═══════════════════════════════════════════════════════════════════════
#  Semantic helpers
# ═══════════════════════════════════════════════════════════════════════

def severity_color(severity: str) -> str:
    """Map a severity/risk/status string to its accent color."""
    key = (severity or "").lower()
    return {
        "critical": CRITICAL,
        "high": CRITICAL,
        "error": CRITICAL,
        "locked": CRITICAL,
        "warning": WARNING,
        "medium": WARNING,
        "degraded": WARNING,
        "monitoring": WARNING,
        "info": PRIMARY,
        "information": PRIMARY,
        "low": SUCCESS,
        "success": SUCCESS,
        "authenticated": SUCCESS,
        "active": SUCCESS,
        "running": SUCCESS,
        "healthy": SUCCESS,
        "ok": SUCCESS,
        "complete": SUCCESS,
        "completed": SUCCESS,
        "pending": MUTED,
        "standby": MUTED,
        "idle": MUTED,
    }.get(key, PRIMARY)


def with_alpha(hex_color: str, alpha_hex: str) -> str:
    """Return an #AARRGGBB color for a #RRGGBB color + 2-digit hex alpha.

    Qt parses 8-digit hex as alpha-FIRST (#AARRGGBB), so a naive
    concatenation like f'{PRIMARY}66' yields the wrong alpha (the first
    two digits become the alpha). Always use this helper for alpha blends.
    """
    return f"#{alpha_hex}{hex_color.lstrip('#')}"


def severity_icon(severity: str) -> str:
    """Map a severity/risk/status string to a unicode glyph."""
    key = (severity or "").lower()
    return {
        "critical": "⛔",
        "high": "⛔",
        "error": "✖",
        "warning": "⚠",
        "medium": "⚠",
        "degraded": "⚠",
        "info": "ℹ",
        "information": "ℹ",
        "low": "✔",
        "success": "✔",
        "authenticated": "✔",
        "active": "●",
        "running": "●",
        "healthy": "●",
        "pending": "◌",
        "standby": "◌",
        "idle": "◌",
    }.get(key, "•")


# ═══════════════════════════════════════════════════════════════════════
#  QSS Builders
# ═══════════════════════════════════════════════════════════════════════

def glass_card_qss(accent: str = PRIMARY, hover: bool = True) -> str:
    """Frosted-glass card surface with a soft accent edge."""
    base = f"""
        QFrame {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #EB1A212B, stop:1 #F511161E);
            border: 1px solid {BORDER};
            border-top: 1px solid #1AFFFFFF;
            border-radius: {RADIUS_L};
        }}
    """
    if hover:
        base += f"""
        QFrame:hover {{
            border: 1px solid {with_alpha(accent, '66')};
            border-top: 1px solid {with_alpha(accent, '88')};
        }}
        """
    return base


def panel_qss() -> str:
    """Flat panel surface (darker than cards)."""
    return f"""
        QFrame {{
            background: {PANEL};
            border: 1px solid {BORDER};
            border-radius: {RADIUS_L};
        }}
    """


def app_stylesheet() -> str:
    """Global application stylesheet applied to the QApplication."""
    return f"""
    * {{
        font-family: {FONT_FAMILY};
        font-size: 13px;
        color: {TEXT_PRI};
        outline: none;
    }}
    QMainWindow, QWidget {{ background: transparent; }}
    QWidget#AppRoot {{ background: {BG}; }}

    QToolTip {{
        background: {RAISED};
        color: {TEXT_PRI};
        border: 1px solid {BORDER_STRONG};
        padding: 6px 10px;
        border-radius: 6px;
        font-size: 12px;
    }}

    /* ── Scrollbars ─────────────────────────────────────────────── */
    QScrollBar:vertical {{
        background: transparent; width: 8px; margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: #1FFFFFFF;
        border-radius: 4px; min-height: 32px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {with_alpha(PRIMARY, '99')}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
    QScrollBar:horizontal {{
        background: transparent; height: 8px; margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: #1FFFFFFF;
        border-radius: 4px; min-width: 32px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

    /* ── Inputs ─────────────────────────────────────────────────── */
    QLineEdit, QPlainTextEdit, QTextEdit {{
        background: {CARD};
        color: {TEXT_PRI};
        border: 1px solid {BORDER_STRONG};
        border-radius: {RADIUS_M};
        padding: 9px 12px;
        selection-background-color: {with_alpha(PRIMARY, '66')};
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
        border: 1px solid {with_alpha(PRIMARY, '88')};
    }}
    QLineEdit:disabled {{ color: {TEXT_DIM}; background: {PANEL}; }}

    /* ── Combo / Dropdowns ──────────────────────────────────────── */
    QComboBox {{
        background: {CARD};
        color: {TEXT_PRI};
        border: 1px solid {BORDER_STRONG};
        border-radius: {RADIUS_M};
        padding: 7px 12px;
        min-width: 120px;
    }}
    QComboBox:hover {{ border: 1px solid {with_alpha(PRIMARY, '77')}; }}
    QComboBox::drop-down {{
        border: none; width: 24px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {TEXT_SEC};
        margin-right: 8px;
    }}
    QComboBox QAbstractItemView {{
        background: {PANEL};
        color: {TEXT_PRI};
        border: 1px solid {BORDER_STRONG};
        border-radius: 8px;
        selection-background-color: {with_alpha(PRIMARY, '33')};
        selection-color: {TEXT_PRI};
        padding: 4px;
    }}

    /* ── Tables ─────────────────────────────────────────────────── */
    QTableWidget {{
        background: transparent;
        alternate-background-color: #05FFFFFF;
        color: {TEXT_PRI};
        border: none;
        gridline-color: transparent;
        selection-background-color: {with_alpha(PRIMARY, '22')};
        selection-color: {TEXT_PRI};
        font-size: 12px;
    }}
    QTableWidget::item {{ padding: 6px 10px; border: none; }}
    QTableWidget::item:selected {{ background: {with_alpha(PRIMARY, '22')}; }}
    QHeaderView::section {{
        background: transparent;
        color: {TEXT_DIM};
        border: none;
        border-bottom: 1px solid {BORDER_STRONG};
        padding: 8px 10px;
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    QTableCornerButton::section {{ background: transparent; border: none; }}

    /* ── Menus ──────────────────────────────────────────────────── */
    QMenu {{
        background: {PANEL};
        color: {TEXT_PRI};
        border: 1px solid {BORDER_STRONG};
        padding: 6px;
        border-radius: 10px;
    }}
    QMenu::item {{ padding: 8px 22px; border-radius: 6px; }}
    QMenu::item:selected {{ background: {with_alpha(PRIMARY, '22')}; }}
    QMenu::item:disabled {{ color: {TEXT_DIM}; }}
    QMenu::separator {{ background: {BORDER_STRONG}; height: 1px; margin: 6px 10px; }}

    /* ── Splitters (resizable panels) ───────────────────────────── */
    QSplitter::handle {{ background: transparent; }}
    QSplitter::handle:horizontal {{ width: 3px; }}
    QSplitter::handle:vertical {{ height: 3px; }}
    QSplitter::handle:hover {{ background: {with_alpha(PRIMARY, '55')}; }}

    /* ── Progress bars ──────────────────────────────────────────── */
    QProgressBar {{
        background: #0FFFFFFF;
        border: none;
        border-radius: 4px;
        text-align: center;
        color: transparent;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {PRIMARY}, stop:1 {AI});
        border-radius: 4px;
    }}

    /* ── Checkboxes ─────────────────────────────────────────────── */
    QCheckBox {{ spacing: 10px; color: {TEXT_PRI}; }}
    QCheckBox::indicator {{
        width: 18px; height: 18px;
        border: 1px solid {BORDER_STRONG};
        border-radius: 5px;
        background: {CARD};
    }}
    QCheckBox::indicator:hover {{ border: 1px solid {with_alpha(PRIMARY, '88')}; }}
    QCheckBox::indicator:checked {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {PRIMARY}, stop:1 {AI});
        border: 1px solid transparent;
    }}

    /* ── Sliders ────────────────────────────────────────────────── */
    QSlider::groove:horizontal {{
        height: 4px;
        background: #1AFFFFFF;
        border-radius: 2px;
    }}
    QSlider::sub-page:horizontal {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {PRIMARY}, stop:1 {AI});
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        width: 16px; height: 16px;
        margin: -6px 0;
        background: {TEXT_PRI};
        border: 3px solid {PRIMARY};
        border-radius: 8px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {PRIMARY};
    }}

    /* ── Status bar / misc ──────────────────────────────────────── */
    QStatusBar {{ background: {PANEL}; color: {TEXT_SEC}; border-top: 1px solid {BORDER}; }}
    QStatusBar::item {{ border: none; }}

    QStackedWidget {{ background: transparent; }}

    QLabel[dim="true"] {{ color: {TEXT_DIM}; }}
    QLabel[muted="true"] {{ color: {TEXT_SEC}; }}
    """


def scroll_area_qss() -> str:
    """Transparent scroll area (used by page bodies)."""
    return "QScrollArea { background: transparent; border: none; }"
