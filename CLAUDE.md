# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python automation project for fetching QR codes from the Rise Gyms portal (https://risegyms.ez-runner.com). The application automates login and QR code retrieval using Selenium WebDriver.

## Setup Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Standard version (improved with WebDriverWait)
python qr_fetcher.py                         # Basic usage
python qr_fetcher.py --headless              # Run without opening browser window
python qr_fetcher.py --force-login           # Force fresh login (ignore saved session)

# Optimized version (requests + selenium fallback)
python qr_fetcher_optimized.py               # Hybrid approach (fastest)
python qr_fetcher_optimized.py --requests-only  # Pure requests (fastest, may fail)
python qr_fetcher_optimized.py --use-selenium   # Force Selenium usage
```

## Architecture

- `qr_fetcher.py`: Main script containing the `RiseGymQRFetcher` class
- `.env`: Contains login credentials (USERNAME and PASSWORD)
- The application uses Selenium WebDriver to navigate the login flow and extract QR codes

## Key Components

- **RiseGymQRFetcher class**: Handles browser automation, login, and QR code extraction
- **Session Management**: Saves/loads cookies to skip login on subsequent runs
- **setup_driver()**: Configures Chrome WebDriver with anti-detection features
- **login()**: Automates the login process using credentials from .env
- **try_direct_access()**: Attempts to bypass login using saved session
- **find_qr_code_fast()**: Optimized QR detection for faster execution
- **convert_svg_to_png()**: Converts SVG QR codes to PNG images

## Performance Optimizations

### Standard Version (qr_fetcher.py)
- **Session Persistence**: Saves cookies after login to skip authentication on future runs
- **Direct Dashboard Access**: Bypasses login page when valid session exists
- **WebDriverWait**: Replaced time.sleep with intelligent waiting conditions
- **Fast QR Detection**: Skips page exploration when QR element location is known

### Optimized Version (qr_fetcher_optimized.py)
- **Requests Session**: Ultra-fast HTTP requests without browser overhead
- **Intelligent Fallback**: Falls back to Selenium only when requests fail
- **BeautifulSoup Parsing**: Lightning-fast HTML parsing for QR extraction
- **Session Validation**: Tests session validity before attempting operations
- **Minimal Browser Usage**: Only launches browser when absolutely necessary

## Speed Comparison
- **Pure Requests**: ~2-5 seconds (when working)
- **Hybrid Approach**: ~5-15 seconds (requests → selenium fallback)
- **Selenium Only**: ~15-25 seconds (with WebDriverWait improvements)
- **Original**: ~60-80 seconds (with time.sleep delays)

## Dependencies

The project requires Chrome/Chromium browser and ChromeDriver for Selenium automation. Key Python packages include selenium, requests, python-dotenv, and image processing libraries.

## QR Code Pattern Discovery

Through reverse engineering Rise Gym's QR codes, we've discovered the following pattern:

### QR Content Format
- Base pattern: `9268MMDDYYYYHHSSSS`
- `9268`: Member ID (constant)
- `MMDDYYYY`: Current date (e.g., 06022025 for June 2, 2025)
- `HH`: 2-hour time block (00, 02, 04, 06, 08, 10, 12, 14, 16, 18, 20, 22)
- `SSSS`: Suffix that varies by time:
  - `0001` for 00:00-01:59 time block only
  - `0000` for all other time blocks (02:00-23:59)

### Example QR Codes
- `926806022025000001` - June 2, 2025, 00:00-01:59 (midnight block)
- `926806022025060000` - June 2, 2025, 06:00-07:59
- `926806022025140000` - June 2, 2025, 14:00-15:59

### Related Tools
- `qr_monitor_svg/predict_current_qr.py` - Predicts QR codes for any time
- `qr_monitor_svg/android_qr_app/` - Android app that generates QR codes using Gray code patterns
- `qr_monitor_svg/real_qr_codes/` - Directory containing verified real QR codes for analysis