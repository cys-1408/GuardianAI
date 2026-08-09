"""GuardianAI Widget Library — Reusable premium UI components.

Every custom component in the command center derives from these base
widgets so the entire product belongs to one design system.
"""

from __future__ import annotations

from typing import Callable, Optional, Sequence

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, Signal
from PySide6.QtGui import (
    QColor, QPainter, QPen, QLinearGradient, QRadialGradient,
    QPainterPath,
)
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGraphicsDropShadowEffect, QSizePolicy, QLineEdit,
)

from src.ui.theme import (
    with_alpha,
    PRIMARY, SUCCESS, TEXT_PRI, TEXT_SEC, TEXT_DIM, BORDER, BORDER_STRONG,
    glass_card_qss, severity_color,
)

# ═══════════════════════════════════════════════════════════════════════
#  Effect helpers
# ═══════════════════════════════════════════════════════════════════════

def glow_effect(color: str = PRIMARY, radius: int = 24, alpha: int = 40) -> QGraphicsDropShadowEffect:
    """Soft colored glow behind a widget."""
    fx = QGraphicsDropShadowEffect()
    fx.setBlurRadius(radius)
    fx.setOffset(0, 4)
    fx.setColor(QColor(color + f"{alpha:02X}"))
    return fx


# ═══════════════════════════════════════════════════════════════════════
#  Glass surfaces
# ═══════════════════════════════════════════════════════════════════════

class GlassCard(QFrame):
    """Frosted-glass card with soft 3D surface, glow, and hover lift."""

    clicked = Signal()

    def __init__(
        self,
        title: str = "",
        accent: str = PRIMARY,
        glow: bool = True,
        clickable: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._accent = accent
        self.setObjectName("glassCard")
        self.setStyleSheet(glass_card_qss(accent))
        self.setMinimumHeight(88)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 16, 18, 16)
        self._layout.setSpacing(8)

        if glow:
            self.setGraphicsEffect(glow_effect(accent, 26, 30))

        if title:
            hdr = QHBoxLayout()
            self._title = QLabel(title)
            self._title.setStyleSheet(
                f"font-size: 11px; font-weight: 700; letter-spacing: 1px; "
                f"color: {TEXT_DIM}; background: transparent;"
            )
            hdr.addWidget(self._title)
            hdr.addStretch()
            self._layout.addLayout(hdr)

        if clickable:
            self.setCursor(Qt.PointingHandCursor)

    # ── Convenience accessors ────────────────────────────────────
    def body(self) -> QVBoxLayout:
        return self._layout

    def set_title(self, text: str) -> None:
        if hasattr(self, "_title"):
            self._title.setText(text)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class Panel(QFrame):
    """Flat darker panel surface."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{ background: #D90B0E13; border: 1px solid {BORDER}; "
            f"border-radius: 14px; }}"
        )


class SectionHeader(QWidget):
    """Page section heading with accent rule + optional action button."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        icon: str = "",
        accent: str = PRIMARY,
        action_text: str = "",
        action: Optional[Callable] = None,
    ) -> None:
        super().__init__()
        self.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        row = QHBoxLayout()
        row.setSpacing(10)

        if icon:
            ic = QLabel(icon)
            ic.setStyleSheet(f"font-size: 15px; background: transparent; color: {accent};")
            row.addWidget(ic)

        t = QLabel(title)
        t.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {TEXT_PRI}; background: transparent;"
        )
        row.addWidget(t)

        rule = QFrame()
        rule.setFixedHeight(2)
        rule.setStyleSheet(
            f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            f"stop:0 {accent}, stop:1 transparent); border: none; border-radius: 1px;"
        )
        rule.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row.addWidget(rule, 1)

        if action_text and action:
            btn = GlowButton(action_text, kind="ghost", accent=accent)
            btn.clicked.connect(action)
            row.addWidget(btn)

        lay.addLayout(row)

        if subtitle:
            s = QLabel(subtitle)
            s.setStyleSheet(f"font-size: 12px; color: {TEXT_SEC}; background: transparent;")
            s.setProperty("muted", True)
            lay.addWidget(s)


# ═══════════════════════════════════════════════════════════════════════
#  Buttons
# ═══════════════════════════════════════════════════════════════════════

class GlowButton(QPushButton):
    """Premium button — solid (gradient+glow), outline, or ghost."""

    def __init__(
        self,
        text: str = "",
        kind: str = "solid",       # solid | outline | ghost
        accent: str = PRIMARY,
        icon: str = "",
    ) -> None:
        super().__init__()
        self._accent = accent
        label = f"{icon}  {text}" if icon else text
        self.setText(label)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(34)
        self.setStyleSheet(self._qss(kind, accent))

        if kind == "solid":
            fx = QGraphicsDropShadowEffect()
            fx.setBlurRadius(18)
            fx.setOffset(0, 3)
            fx.setColor(QColor(with_alpha(accent, '55')))
            self.setGraphicsEffect(fx)

    @staticmethod
    def _qss(kind: str, accent: str) -> str:
        if kind == "solid":
            return f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {accent}, stop:1 {with_alpha(accent, 'AA')});
                    color: #04121A;
                    font-weight: 700;
                    border: none; border-radius: 9px;
                    padding: 8px 18px;
                }}
                QPushButton:hover {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {with_alpha(accent, 'E6')}, stop:1 {with_alpha(accent, 'CC')}); }}
                QPushButton:pressed {{ padding-top: 9px; }}
                QPushButton:disabled {{ background: #12FFFFFF; color: {TEXT_DIM}; }}
            """
        if kind == "outline":
            return f"""
                QPushButton {{
                    background: transparent;
                    color: {accent};
                    font-weight: 600;
                    border: 1px solid {with_alpha(accent, '88')}; border-radius: 9px;
                    padding: 8px 18px;
                }}
                QPushButton:hover {{ background: {with_alpha(accent, '1A')}; border-color: {accent}; }}
                QPushButton:pressed {{ background: {with_alpha(accent, '2E')}; }}
                QPushButton:disabled {{ color: {TEXT_DIM}; border-color: {BORDER_STRONG}; }}
            """
        # ghost
        return f"""
            QPushButton {{
                background: transparent;
                color: {TEXT_SEC};
                border: none; border-radius: 8px;
                padding: 7px 14px; font-size: 12px;
            }}
            QPushButton:hover {{ background: #0FFFFFFF; color: {TEXT_PRI}; }}
            QPushButton:pressed {{ background: #1AFFFFFF; }}
            QPushButton:disabled {{ color: {TEXT_DIM}; }}
        """


class IconButton(QPushButton):
    """Compact icon-only button (label is the glyph)."""

    def __init__(self, glyph: str, tooltip: str = "", accent: str = PRIMARY) -> None:
        super().__init__(glyph)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(32, 32)
        if tooltip:
            self.setToolTip(tooltip)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {TEXT_SEC};
                border: none; border-radius: 8px; font-size: 15px;
            }}
            QPushButton:hover {{ background: #12FFFFFF; color: {accent}; }}
        """)


# ═══════════════════════════════════════════════════════════════════════
#  Badges / pills
# ═══════════════════════════════════════════════════════════════════════

class Badge(QLabel):
    """Status pill with semantic color."""

    def __init__(self, text: str = "", severity: str = "info", dot: bool = True) -> None:
        super().__init__()
        self._severity = severity
        self.set_severity(severity)
        self.setText(text)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

    def set_severity(self, severity: str) -> None:
        self._severity = severity
        c = severity_color(severity)
        self.setStyleSheet(f"""
            QLabel {{
                color: {c};
                background: {with_alpha(c, '1F')};
                border: 1px solid {with_alpha(c, '55')};
                border-radius: 11px;
                padding: 3px 12px;
                font-size: 11px; font-weight: 700;
                letter-spacing: 0.5px;
            }}
        """)

    def set_text(self, text: str) -> None:
        self.setText(text)


class Dot(QLabel):
    """Animated status dot with soft glow."""

    def __init__(self, color: str = SUCCESS, size: int = 10) -> None:
        super().__init__("●")
        self.set_color(color)
        self.setFixedSize(size + 6, size + 6)
        self.setAlignment(Qt.AlignCenter)
        fx = QGraphicsDropShadowEffect()
        fx.setBlurRadius(8)
        fx.setOffset(0, 0)
        fx.setColor(QColor(with_alpha(color, '99')))
        self.setGraphicsEffect(fx)

    def set_color(self, color: str) -> None:
        self.setStyleSheet(f"font-size: 10px; color: {color}; background: transparent;")


class Sparkline(QWidget):
    """Minimal real-data line/area chart — no fake points, only fed data."""

    def __init__(self, color: str = PRIMARY, fill: bool = True, height: int = 48) -> None:
        super().__init__()
        self._data: list[float] = []
        self._color = QColor(color)
        self.setMinimumHeight(height)
        self.setMaximumHeight(height * 2)

    def set_data(self, values: Sequence[float]) -> None:
        self._data = list(values)[-200:]
        self.update()

    def add_point(self, value: float) -> None:
        self._data.append(value)
        if len(self._data) > 200:
            self._data.pop(0)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        if len(self._data) < 2:
            p.setPen(QPen(QColor(BORDER_STRONG), 1))
            p.drawLine(0, h // 2, w, h // 2)
            p.end()
            return

        mn, mx = min(self._data), max(self._data)
        span = (mx - mn) or 1.0
        step_x = w / (len(self._data) - 1)
        pts: list[QPointF] = []
        for i, v in enumerate(self._data):
            x = i * step_x
            y = h - 6 - ((v - mn) / span) * (h - 12)
            pts.append(QPointF(x, y))

        path = QPainterPath()
        path.moveTo(pts[0])
        for pt in pts[1:]:
            path.lineTo(pt)

        if self._color.alpha() > 0:
            p.setPen(QPen(self._color, 2))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

        if self._fill:
            fill_path = QPainterPath(path)
            fill_path.lineTo(pts[-1].x(), h)
            fill_path.lineTo(pts[0].x(), h)
            fill_path.closeSubpath()
            g = QLinearGradient(0, 0, 0, h)
            c = QColor(self._color)
            c.setAlpha(28)
            g.setColorAt(0, c)
            c2 = QColor(self._color)
            c2.setAlpha(0)
            g.setColorAt(1, c2)
            p.fillPath(fill_path, g)

        p.end()


# ═══════════════════════════════════════════════════════════════════════
#  Radar sweep (decorative, non-data — motion only)
# ═══════════════════════════════════════════════════════════════════════

class RadarSweep(QWidget):
    """Animated radar with rotating sweep beam. Purely decorative motion."""

    def __init__(self, size: int = 180, accent: str = PRIMARY) -> None:
        super().__init__()
        self._angle = 0
        self._accent = QColor(accent)
        self.setFixedSize(size, size)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

    def _tick(self) -> None:
        self._angle = (self._angle + 2) % 360
        self.update()

    def set_accent(self, accent: str) -> None:
        """Update the sweep accent color at runtime."""
        self._accent = QColor(accent)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self.width()
        cx, cy = s / 2, s / 2
        r = s / 2 - 6
        self._accent = QColor(self._accent)  # coerce str → QColor (safe reassignment)

        p.setPen(QPen(QColor(BORDER_STRONG), 1))
        for ring in (0.33, 0.66, 1.0):
            p.drawEllipse(QPointF(cx, cy), r * ring, r * ring)
        p.drawLine(QPointF(cx - r, cy), QPointF(cx + r, cy))
        p.drawLine(QPointF(cx, cy - r), QPointF(cx, cy + r))

        # Sweep beam
        beam = QPainterPath()
        beam.moveTo(cx, cy)
        rad = r * 0.98
        a0 = self._angle - 30
        beam.arcTo(QRectF(cx - rad, cy - rad, rad * 2, rad * 2), a0, 60)
        beam.closeSubpath()
        g = QRadialGradient(cx, cy, rad)
        c = QColor(self._accent)
        c.setAlpha(55)
        g.setColorAt(0, c)
        c2 = QColor(self._accent)
        c2.setAlpha(0)
        g.setColorAt(1, c2)
        p.fillPath(beam, g)

        # Sweep line
        import math
        a = math.radians(self._angle)
        p.setPen(QPen(self._accent, 1.5))
        p.drawLine(QPointF(cx, cy), QPointF(cx + math.cos(a) * r, cy + math.sin(a) * r))

        # Center dot
        p.setBrush(self._accent)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), 3, 3)
        p.end()


# ═══════════════════════════════════════════════════════════════════════
#  Empty state
# ═══════════════════════════════════════════════════════════════════════

class EmptyState(QWidget):
    """Elegant empty state with guidance — shown when a module has no real data."""

    def __init__(
        self,
        icon: str = "🛰",
        title: str = "No data available",
        description: str = "",
        guidance: str = "",
        accent: str = PRIMARY,
    ) -> None:
        super().__init__()
        self.setStyleSheet("background: transparent;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(10)
        lay.setContentsMargins(40, 40, 40, 40)

        ic = QLabel(icon)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet(f"font-size: 42px; background: transparent;")
        ic.setGraphicsEffect(glow_effect(accent, 40, 35))
        lay.addWidget(ic)

        t = QLabel(title)
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet(
            f"font-size: 17px; font-weight: 700; color: {TEXT_PRI}; background: transparent;"
        )
        lay.addWidget(t)

        if description:
            d = QLabel(description)
            d.setAlignment(Qt.AlignCenter)
            d.setWordWrap(True)
            d.setStyleSheet(f"font-size: 13px; color: {TEXT_SEC}; background: transparent;")
            d.setMaximumWidth(520)
            lay.addWidget(d)

        if guidance:
            g = QFrame()
            g.setStyleSheet(f"""
                QFrame {{
                    background: {with_alpha(accent, '12')};
                    border: 1px solid {with_alpha(accent, '44')};
                    border-radius: 10px;
                    padding: 10px 16px;
                }}
            """)
            gl = QHBoxLayout(g)
            gl.setContentsMargins(14, 8, 14, 8)
            gl.setSpacing(8)
            gi = QLabel("💡")
            gi.setStyleSheet("background: transparent;")
            gl.addWidget(gi)
            gt = QLabel(guidance)
            gt.setWordWrap(True)
            gt.setStyleSheet(f"font-size: 12px; color: {accent}; background: transparent;")
            gl.addWidget(gt, 1)
            lay.addWidget(g, 0, Qt.AlignCenter)


# ═══════════════════════════════════════════════════════════════════════
#  Search input
# ═══════════════════════════════════════════════════════════════════════

class SearchInput(QLineEdit):
    """Glass search field with hint text."""

    def __init__(self, placeholder: str = "Search…") -> None:
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self.setFixedHeight(34)
        self.setMinimumWidth(200)


# ═══════════════════════════════════════════════════════════════════════
#  Pulse / wave visual (decorative motion)
# ═══════════════════════════════════════════════════════════════════════

class PulseRing(QWidget):
    """Expanding pulse rings around a node (network map / attack graph)."""

    def __init__(self, color: str = PRIMARY, diameter: int = 140) -> None:
        super().__init__()
        self._color = QColor(color)
        self._phase = 0
        self.setFixedSize(diameter, diameter)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)

    def _tick(self) -> None:
        self._phase = (self._phase + 1) % 30
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        base = min(self.width(), self.height()) / 2 - 4
        for i in range(3):
            t = ((self._phase / 30) + i / 3) % 1.0
            r = base * (0.3 + t * 0.7)
            c = QColor(self._color)
            c.setAlpha(int(90 * (1 - t)))
            p.setPen(QPen(c, 1.5))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(cx, cy), r, r)
        c = QColor(self._color)
        p.setBrush(c)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), 4, 4)
        p.end()


# ═══════════════════════════════════════════════════════════════════════
#  Metric tile (big number + label + sub)
# ═══════════════════════════════════════════════════════════════════════

class MetricTile(QFrame):
    """Command-center metric tile showing one real value."""

    def __init__(
        self,
        title: str,
        icon: str = "",
        accent: str = PRIMARY,
        value: str = "—",
        sub: str = "",
    ) -> None:
        super().__init__()
        self._accent = accent
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F2181F29, stop:1 #FA0F131A);
                border: 1px solid {with_alpha(accent, '33')};
                border-left: 3px solid {accent};
                border-radius: 12px;
            }}
            QFrame:hover {{ border: 1px solid {with_alpha(accent, '66')}; border-left: 3px solid {accent}; }}
        """)
        self.setGraphicsEffect(glow_effect(accent, 20, 22))
        self.setMinimumHeight(92)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(2)

        top = QHBoxLayout()
        top.setSpacing(8)
        if icon:
            ic = QLabel(icon)
            ic.setStyleSheet(f"font-size: 16px; background: transparent;")
            top.addWidget(ic)
        t = QLabel(title.upper())
        t.setStyleSheet(f"font-size: 10px; font-weight: 700; letter-spacing: 1px; color: {TEXT_DIM}; background: transparent;")
        top.addWidget(t)
        top.addStretch()
        lay.addLayout(top)

        self._value = QLabel(value)
        self._value.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {accent}; background: transparent;")
        lay.addWidget(self._value)

        self._sub = QLabel(sub)
        self._sub.setStyleSheet(f"font-size: 11px; color: {TEXT_SEC}; background: transparent;")
        lay.addWidget(self._sub)

    def set_value(self, text: str, color: Optional[str] = None) -> None:
        c = color or self._accent
        self._value.setText(text)
        self._value.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {c}; background: transparent;")

    def set_sub(self, text: str) -> None:
        self._sub.setText(text)
