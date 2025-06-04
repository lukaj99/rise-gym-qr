# Rise Gym QR Code System

A complete system for analyzing and generating QR codes compatible with Rise Gym's access control system.

## Pattern Discovery

The QR codes follow a predictable pattern:
- **Format**: `9268` + `MMDDYYYY` + `HHMMSS`
- **9268**: Facility code (constant)
- **MMDDYYYY**: Date in US format
- **HH**: 2-hour time slot (00, 02, 04, ..., 22)
- **MM**: Always "00"
- **SS**: "01" for 00:00-01:59 slot, "00" for all other slots

## Project Structure

```
riseGym/
├── src/
│   ├── core/
│   │   ├── qr_generator.py    # Main QR code generator
│   │   └── qr_analyzer.py     # Pattern analyzer
│   ├── utils/
│   │   ├── qr_scraper.py      # Web scraper for Rise Gym
│   │   └── qr_monitor.py      # Automated monitoring
│   └── data/
│       ├── qr_database.py     # Database management
│       └── *.json             # Analysis data files
├── real_qr_codes/             # Scraped QR codes (SVG format)
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Generate QR Code

```bash
# Generate for current time
python src/core/qr_generator.py now

# Generate for specific time
python src/core/qr_generator.py 202506051030
```

### Analyze QR Codes

```bash
# Analyze scraped QR codes
python src/core/qr_analyzer.py real_qr_codes/
```

### Monitor and Scrape

```bash
# Run automated monitoring
python src/utils/qr_monitor.py

# Scrape current QR code
python src/utils/qr_scraper.py
```

## Technical Details

- **QR Version**: 1 (21x21 modules)
- **Error Correction**: Level Q (~25% recovery)
- **Module Size**: 20px (SVG), 41px (PNG)
- **Border**: 4 modules

## Security Notice

This project was created for educational purposes. The QR codes use unencrypted, predictable data which could be improved with proper security measures.