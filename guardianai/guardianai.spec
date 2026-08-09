# -*- mode: python ; coding: utf-8 -*-
"""
GuardianAI - PyInstaller Build Specification.

Builds a single-directory Windows executable with all dependencies.
Run from the project root:
    python -m PyInstaller guardianai.spec --noconfirm

Note: This build takes 5-15 minutes due to scikit-learn/scipy analysis.
"""

import os
import sys

sys.setrecursionlimit(10000)

PROJECT_ROOT = os.getcwd()

# ── Hidden imports ──────────────────────────────────────────────────
#
# PyInstaller's static analysis traces module-level imports, but
# src/application/core.py uses lazy local imports inside its
# initialize() method (inside a try block, not at module scope).
# Those modules must be explicitly listed here.
#
HIDDEN_IMPORTS = [
    # Security layer (loaded via local imports in core.py)
    "src.security.encryption",
    "src.security.privacy",
    "src.security.integrity",
    "src.security.secure_storage",
    "src.security.logging_manager",
    # Behavioral collection layer
    "src.behavior.event_buffer",
    "src.behavior.event_aggregator",
    "src.behavior.keyboard",
    "src.behavior.mouse",
    "src.behavior.scroll",
    "src.behavior.idle_detector",
    "src.behavior.windows_integration",
    # AI / ML layer
    "src.ai.features",
    "src.ai.normalization",
    "src.ai.dataset",
    "src.ai.confidence",
    "src.ai.trust",
    "src.ai.risk",
    "src.ai.authentication",
    "src.ai.inference",
    "src.ai.repository",
    "src.ai.training",
    "src.ai.validator",
    "src.ai.version",
    "src.ai.retraining",
    "src.ai.scheduler",
    "src.ai.model_wrapper",
    # Enrollment system
    "src.enrollment.manager",
    "src.enrollment.assignments",
    "src.enrollment.progress",
    "src.enrollment.calendar",
    "src.enrollment.validator",
    # UI layer (command center)
    "src.ui.main_window",
    "src.ui.theme",
    "src.ui.widgets",
    "src.ui.state",
    "src.ui.lock_screen",
    "src.ui.enrollment_wizard",
    "src.ui.enrollment_overlay",
    "src.ui.pages.dashboard",
    "src.ui.pages.live_monitor",
    "src.ui.pages.behavior_analytics",
    "src.ui.pages.ai_agents",
    "src.ui.pages.alerts",
    "src.ui.pages.devices",
    "src.ui.pages.endpoints",
    "src.ui.pages.identity",
    "src.ui.pages.audit_logs",
    "src.ui.pages.settings",
    "src.ui.pages.reports",
    "src.ui.pages.threat_intel",
    "src.ui.pages.incident_response",
    "src.ui.pages.threat_hunting",
    "src.ui.pages.quarantine",
    "src.ui.pages.firewall",
    "src.ui.pages.attack_graph",
    "src.ui.pages.network_map",
    "src.ui.pages.chat",
    # Third-party known misses
    "sklearn.ensemble",
    "sklearn.svm",
    "sklearn.preprocessing",
    "sklearn.metrics",
    "lightgbm",
    "lightgbm.basic",
    "cryptography.fernet",
    "cryptography.hazmat.primitives.ciphers.aead",
    "pyqtgraph",
    "matplotlib.backends.backend_agg",
    "matplotlib.backends.backend_qtagg",
]

# Collect LightGBM dynamic library (DLL on Windows)
from PyInstaller.utils.hooks import collect_dynamic_libs
lgbm_binaries = collect_dynamic_libs("lightgbm")

# Exclude PyQt5 (conflicts with PySide6) and heavy dev tools
EXCLUDES = [
    "PyQt5", "PyQt5.QtCore", "PyQt5.QtGui", "PyQt5.QtWidgets",
    "PyQt5.QtNetwork", "PyQt5.QtSvg", "PyQt5.sip",
    "PyQtWebEngine",
    "IPython", "jedi", "parso", "nbformat", "jsonschema",
    "rich", "zmq", "orjson", "lxml",            "tkinter", "test", "tests",
    "pip",
    "hypothesis", "Faker",
]

# NOTE: setuptools is NOT excluded because PyInstaller's built-in
# pyi_rth_pkgres runtime hook needs it (via pkg_resources) at startup.
# Excluding it causes: "The 'jaraco' package is required" error.

a = Analysis(
    ["src/main.py"],
    pathex=[PROJECT_ROOT],
    binaries=lgbm_binaries,
    datas=[],
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="GuardianAI",
    debug=False,
    console=True,           # Show console for error visibility during startup
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=None,
    uac_admin=False,
    uac_uiaccess=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="GuardianAI",
)
