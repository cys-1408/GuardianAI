#!/usr/bin/env python3
"""
GuardianAI Build Script.

Builds a Windows executable using PyInstaller with the guardianai.spec config.

⚠️  IMPORTANT: This build takes 5-15 minutes due to scikit-learn,
   scipy, matplotlib, and LightGBM dependency analysis. It cannot
   complete within normal agent timeout limits — run it locally!

Usage:
    cd guardianai
    python build.py                  # Build executable
    python build.py --clean          # Clean + build
    python build.py --onefile        # Single-file executable (experimental)

Prerequisites:
    pip install pyinstaller

The output will be in:
    dist/GuardianAI/GuardianAI.exe
"""

import sys
import shutil
import subprocess
from pathlib import Path


APP_NAME = "GuardianAI"
DIST_DIR = Path("dist")
BUILD_DIR = Path("build")
SPEC_FILE = Path("guardianai.spec")


def clean() -> None:
    """Remove previous build artifacts."""
    print("Cleaning previous build artifacts...")
    for path in [DIST_DIR, BUILD_DIR]:
        if path.exists():
            shutil.rmtree(path)
            print(f"  Removed {path}")
    hooks_dir = Path("_pyinstaller_hooks_")
    if hooks_dir.exists():
        shutil.rmtree(hooks_dir)


def build(onefile: bool = False) -> int:
    """Run PyInstaller with the spec file.

    Args:
        onefile: If True, build a single .exe instead of a directory

    Returns:
        Exit code (0 = success)
    """
    if not SPEC_FILE.exists():
        print(f"Error: {SPEC_FILE} not found!", file=sys.stderr)
        return 1

    print(f"Building {APP_NAME} executable...")
    print(f"  Spec file: {SPEC_FILE}")
    print(f"  Mode: {'one-file' if onefile else 'directory'}")
    print()
    print("⚠️  This will take 5-15 minutes. Please wait...")
    print()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(SPEC_FILE),
        "--noconfirm",
        "--log-level=INFO",
    ]

    if onefile:
        # Override the spec for one-file mode by passing CLI args
        cmd.extend(["--onefile", "--distpath", "dist/single"])

    result = subprocess.run(cmd, cwd=Path.cwd())

    if result.returncode == 0:
        build_dir = "dist/single" if onefile else f"dist/{APP_NAME}"
        exe_path = Path(build_dir) / f"{APP_NAME}.exe"
        print()
        print("=" * 60)
        print(f"  ✅ Build successful!")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"  📦 Executable: {exe_path}")
            print(f"  📏 Size: {size_mb:.1f} MB")
        print("=" * 60)
    else:
        print(f"❌ Build failed with exit code {result.returncode}", file=sys.stderr)

    return result.returncode


def main() -> int:
    """Main entry point."""
    # NOTE: --onefile is NOT supported because CLI flags bypass
    # the spec file's critical hidden imports for local-imported
    # modules. Always use the spec file for building.
    if "--onefile" in sys.argv:
        print("Error: --onefile is not supported. Use the spec file instead.",
              file=sys.stderr)
        print("  python -m PyInstaller guardianai.spec --noconfirm", file=sys.stderr)
        return 1

    if "--clean" in sys.argv:
        clean()

    return build(onefile=False)


if __name__ == "__main__":
    print()
    print("=" * 60)
    print(f"  {APP_NAME} Builder")
    print(f"  Run: python build.py [--clean]")
    print("=" * 60)
    print()
    sys.exit(main())
