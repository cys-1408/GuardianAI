# GuardianAI

**Privacy-Preserving Continuous Behavioral Authentication System**

GuardianAI is a privacy-preserving desktop application that provides continuous user authentication using behavioral biometrics. Rather than relying solely on passwords or PINs, the system continuously observes how the user interacts with their computer and silently verifies their identity throughout the session.

## Key Features

- **Continuous Authentication** - Verifies user identity throughout every desktop session
- **Behavioral Biometrics** - Learns unique keyboard, mouse, scroll, and session patterns
- **Local AI** - All machine learning runs entirely on-device; no cloud dependency
- **Privacy First** - Behavioral data never leaves the user's device
- **Adaptive Learning** - Models evolve with the user's natural behavioral changes
- **Transparent Security** - Confidence scores, trust metrics, and risk levels provide explainable decisions

## Technology Stack

- **Language:** Python 3.10+
- **Desktop:** PySide6 (Qt 6)
- **ML:** scikit-learn, LightGBM, NumPy, Pandas, SciPy
- **Database:** SQLite (encrypted)
- **Visualization:** PyQtGraph, Matplotlib
- **Security:** Cryptography (AES-256-GCM)
- **Packaging:** PyInstaller

## Installation

```bash
# Clone the repository
git clone https://github.com/guardianai/guardianai.git
cd guardianai

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m src.main
```

## Quick Start

1. Launch GuardianAI
2. Register your user profile
3. Complete the 7-day behavioral enrollment (guided assignments)
4. GuardianAI trains your personalized authentication model
5. Continuous authentication begins automatically

## Architecture

The application follows a six-layer modular architecture:

- **Presentation Layer** - Dashboard, monitoring, analytics, and settings UI
- **Application Layer** - Core coordination, workflow management, configuration
- **Behavior Processing Layer** - Event capture, buffering, and feature extraction
- **AI Layer** - ML training, inference, confidence, trust, and risk assessment
- **Data Layer** - SQLite database, repositories, sliding window, backup
- **Security Layer** - Encryption, privacy enforcement, integrity, audit logging

## Development

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Type checking
mypy src/

# Code formatting
black src/
```

