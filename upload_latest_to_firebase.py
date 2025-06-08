#!/usr/bin/env python3
"""Upload the latest scraped QR code to Firebase"""

import os
import json
from pathlib import Path
from datetime import datetime
from src.utils.firebase_uploader import FirebaseUploader

# Get the latest QR code
qr_dir = Path('real_qr_codes')
svg_files = sorted(qr_dir.glob('*.svg'), reverse=True)
if not svg_files:
    print("No SVG files found")
    exit(1)

latest_svg = svg_files[0]
print(f"Uploading latest QR code: {latest_svg}")

# Read the SVG content
with open(latest_svg, 'r') as f:
    svg_content = f.read()

# Extract timestamp and pattern
timestamp = latest_svg.stem
dt = datetime.strptime(timestamp, "%Y%m%d%H%M%S")

# Generate pattern
pattern = "9268"
pattern += dt.strftime("%m%d%Y")
hour = dt.hour
if hour % 2 == 0:
    pattern += f"{hour:02d}00"
    pattern += "00" if hour == 0 else "00"
else:
    pattern += f"{hour-1:02d}00"
    pattern += "01"

print(f"Pattern: {pattern}")

# Upload to Firebase
database_url = "https://rise-gym-qr-default-rtdb.europe-west1.firebasedatabase.app"
uploader = FirebaseUploader(database_url)

if uploader.upload_qr_code(latest_svg, pattern):
    print("Successfully uploaded to Firebase!")
else:
    print("Failed to upload")