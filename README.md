# GuardianAI

**Privacy-Preserving Continuous Behavioral Authentication System**

GuardianAI is a privacy-preserving desktop application that provides continuous user authentication using behavioral biometrics. Rather than relying solely on passwords or PINs, the system continuously observes how the user interacts with their computer and silently verifies their identity throughout the session.

## Key Features

* **Continuous Authentication** - Verifies user identity throughout every desktop session
* **Behavioral Biometrics** - Learns unique keyboard, mouse, scroll, and session patterns
* **Local AI** - All machine learning runs entirely on-device; no cloud dependency
* **Privacy First** - Behavioral data never leaves the user's device
* **Adaptive Learning** - Models evolve with the user's natural behavioral changes
* **Transparent Security** - Confidence scores, trust metrics, and risk levels provide explainable decisions
* **Trust-Based Retraining** - Only high-trust sessions influence future models, preventing model poisoning
* **Automatic Rollback** - Underperforming retrained models are rejected and the previous stable model is restored

## What Gets Collected

GuardianAI only collects interaction *timing and movement characteristics* - never content.

**Collected:** key press/release timestamps, cursor movement/click/drag timing, scroll speed and rhythm, idle/active session duration.

**Never collected:** typed characters, passwords, clipboard contents, screen recordings, audio, camera input, files, or browsing content.

## Technology Stack

* **Language:** Python 3.10+
* **Desktop:** PySide6 (Qt 6)
* **ML:** scikit-learn, LightGBM, NumPy, Pandas, SciPy
* **Database:** SQLite (encrypted)
* **Visualization:** PyQtGraph, Matplotlib
* **Security:** Cryptography (AES-256-GCM)
* **Packaging:** PyInstaller

**Supported OS:** Windows 10 / Windows 11 (64-bit)

## Installation

```
# Clone the repository
git clone https://github.com/guardianai/guardianai.git
cd guardianai

# Install dependencies
pip install -r requirements.txt

# Run the application
python build.py
```

## Quick Start

1. Launch GuardianAI
2. Register your user profile
3. Complete the 7-day behavioral enrollment (guided assignments)
4. GuardianAI trains your personalized authentication model
5. Continuous authentication begins automatically

## Architecture

The application follows a six-layer modular architecture:

* **Presentation Layer** - Dashboard, monitoring, analytics, and settings UI
* **Application Layer** - Core coordination, workflow management, configuration
* **Behavior Processing Layer** - Event capture, buffering, and feature extraction
* **AI Layer** - ML training, inference, confidence, trust, and risk assessment
* **Data Layer** - SQLite database, repositories, sliding window, backup
* **Security Layer** - Encryption, privacy enforcement, integrity, audit logging

## Project Structure

```
guardianai/
├── app/                     # Application core, workflow controller, session manager
├── behavior/                # Keyboard, mouse, scroll monitoring & event aggregation
├── ai/                      # Feature engineering, training, inference, trust engine
├── data/                    # SQLite manager, repositories, migrations
├── security/                # Encryption, secure storage, integrity, audit logging
├── ui/                      # PySide6 dashboard, enrollment wizard, analytics, settings
├── models/                  # Locally trained per-user models (gitignored)
├── config/                  # Default configuration files
├── tests/                   # Unit and integration tests
├── build.py                 # Application entry point / build script
└── requirements.txt
```

## Configuration

Application settings, retraining schedule, trust/risk thresholds, and retention policy are managed from **Settings** inside the app and stored locally in an encrypted configuration file. No manual `.env` setup is required to get started.

## Data & Privacy

* All behavioral data, models, and history are stored locally in an encrypted SQLite database.
* Nothing is synchronized to the cloud or any external server.
* Users can review, export, or permanently delete their behavioral data, authentication history, and models at any time from the **Privacy** screen.

## Roadmap

* [x] Core application framework & Windows integration
* [x] Behavioral event capture and feature extraction
* [x] Personalized model training & continuous inference
* [x] Trust-based adaptive retraining with rollback
* [ ] Cross-platform support (macOS / Linux)
* [ ] Additional behavioral modalities (touch, stylus)
* [ ] Enterprise / multi-device management console

## Contributing

Contributions are welcome. Please open an issue to discuss significant changes before submitting a pull request, and ensure new code includes relevant tests.

## License

Proprietary. See `LICENSE` for full terms.

## Disclaimer

GuardianAI provides continuous *supplementary* identity verification and does not replace your operating system's primary login authentication.
