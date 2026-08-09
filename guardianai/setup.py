"""GuardianAI - Setup and packaging configuration."""

from setuptools import setup, find_packages

setup(
    name="guardianai",
    version="1.0.0",
    description="Privacy-Preserving Continuous Behavioral Authentication System",
    author="GuardianAI Team",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "PySide6>=6.5.0",
        "scikit-learn>=1.3.0",
        "lightgbm>=4.0.0",
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "scipy>=1.11.0",
        "pyqtgraph>=0.13.0",
        "matplotlib>=3.7.0",
        "cryptography>=41.0.0",
    ],
    extras_require={
        "win": ["pywin32>=306"],
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-qt>=4.2.0",
            "black>=23.0.0",
            "flake8>=6.1.0",
            "mypy>=1.5.0",
        ],
        "build": ["pyinstaller>=6.0.0"],
    },
    entry_points={
        "console_scripts": [
            "guardianai=src.main:main",
        ],
    },
)
