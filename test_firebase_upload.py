#!/usr/bin/env python3
"""Test Firebase upload with the user's database"""

import requests
import json
from datetime import datetime

# Firebase database URL from the google-services.json
DATABASE_URL = "https://rise-gym-qr-default-rtdb.europe-west1.firebasedatabase.app"

# Generate test QR data
timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
pattern = f"9268{datetime.now().strftime('%m%d%Y')}120000"

# Simple SVG QR code for testing
svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 420">
  <rect width="420" height="420" fill="white"/>
  <text x="210" y="210" text-anchor="middle" font-size="30" fill="black">TEST QR</text>
</svg>"""

qr_data = {
    "timestamp": timestamp,
    "svgContent": svg_content,
    "pattern": pattern,
    "uploadedAt": int(datetime.now().timestamp() * 1000)
}

# Upload to Firebase (public test mode)
urls = [
    f"{DATABASE_URL}/latest.json",
    f"{DATABASE_URL}/qr_codes/{timestamp}.json"
]

for url in urls:
    response = requests.put(url, json=qr_data)
    print(f"Upload to {url}")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print()

print(f"Test data uploaded with timestamp: {timestamp}")
print(f"Pattern: {pattern}")
print("Check your Android app now!")