# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Python Development
```bash
# Install dependencies
pip install -r requirements.txt

# Generate QR code for current time
python src/core/qr_generator.py now

# Generate QR code for specific time (YYYYMMDDHHMM format)
python src/core/qr_generator.py 202506051030

# Analyze QR codes in directory
python src/core/qr_analyzer.py real_qr_codes/

# Run automated monitoring
python src/utils/qr_monitor.py

# Scrape current QR code from Rise Gym (requires RISE_GYM_EMAIL and RISE_GYM_PASSWORD env vars)
python src/utils/qr_scraper.py

# Test QR error correction levels
python qr_error_correction_test.py

# Compare QR codes visually
python compare_qr_codes.py <path1> <path2>

# Decode QR from screenshot
python decode_qr_screenshot.py <image_path>
```

### Android Development
```bash
# Navigate to Android app directory
cd android_qr_app

# Build debug APK
./gradlew assembleDebug

# Build release APK  
./gradlew assembleRelease

# Install on connected device
./gradlew installDebug

# Run tests
./gradlew test

# Clean build
./gradlew clean
```

## Architecture

This codebase reverse-engineers and generates QR codes for Rise Gym's access control system.

### QR Code Pattern
The system discovered a predictable pattern: `9268` + `MMDDYYYY` + `HHMMSS`
- `9268`: Facility code (constant)
- `MMDDYYYY`: Date in US format  
- `HH`: 2-hour time slot (00, 02, 04, ..., 22)
- `MM`: Always "00"
- `SS`: "01" for 00:00-01:59 slot, "00" for all other slots

### Python Components

**Core Modules** (`src/core/`):
- `qr_generator.py`: Generates pixel-perfect QR codes matching Rise Gym's format (version 1, error correction Q, 20px modules)
- `qr_analyzer.py`: Analyzes QR code patterns from scraped images

**Utilities** (`src/utils/`):
- `qr_scraper.py`: Web scraper using Playwright to fetch QR codes from Rise Gym website
- `qr_monitor.py`: Automated monitoring system for continuous QR code collection

**Data Management** (`src/data/`):
- `qr_database.py`: Manages QR code database with pattern analysis
- JSON files store analysis results, parameters, and pattern configurations

### Android App

The `android_qr_app/` contains a Kotlin-based Android application that:
- Generates QR codes on-device using the discovered pattern
- Optimized for Pixel devices with multi-threading support
- Includes web scraping capabilities (`scraping/` package)
- Secure credential management (`security/` package)
- Background QR update service (`service/QRUpdateWorker.kt`)
- Integration with Tasker and Termux for automation

### Automation

GitHub Actions workflow (`.github/workflows/scrape-qr-codes.yml`):
- Runs every 30 minutes to scrape latest QR codes
- Stores scraped codes in `real_qr_codes/` directory
- Updates pattern database automatically
- Requires GitHub secrets: `RISE_GYM_EMAIL` and `RISE_GYM_PASSWORD`

Manual trigger: Use GitHub Actions UI or GitHub CLI:
```bash
gh workflow run scrape-qr-codes.yml
```

### Technical Details

QR Code Parameters:
- Version: 1 (21x21 modules)
- Error Correction: Level Q (~25% recovery)
- Module Size: 20px (SVG), 41px (PNG)
- Border: 4 modules
- Time Zone: America/New_York

The system achieves 100% accuracy in predicting QR codes by using the discovered unencrypted pattern based on facility code and time slots.

### Key Files for Pattern Understanding

- `src/data/master_pattern.json`: Complete pattern specification
- `src/data/qr_pattern_analysis.json`: Detailed analysis results 
- `src/data/qr_exact_parameters.json`: Exact QR generation parameters
- `real_qr_codes/`: Directory containing scraped QR codes in SVG format