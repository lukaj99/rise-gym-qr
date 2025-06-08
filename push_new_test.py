#!/usr/bin/env python3
"""Push a new test to trigger real-time update"""

import requests
import json
from datetime import datetime
import time

DATABASE_URL = "https://rise-gym-qr-default-rtdb.europe-west1.firebasedatabase.app"

# Wait a moment
time.sleep(2)

# Read the latest real QR code
with open('real_qr_codes/20250608143812.svg', 'r') as f:
    svg_content = f.read()

# Update with current timestamp
timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
pattern = f"9268{datetime.now().strftime('%m%d%Y')}140000"

qr_data = {
    "timestamp": timestamp,
    "svgContent": svg_content,
    "pattern": pattern,
    "uploadedAt": int(datetime.now().timestamp() * 1000)
}

# Upload to Firebase
response = requests.put(f"{DATABASE_URL}/latest.json", json=qr_data)
print(f"Status: {response.status_code}")
print(f"Timestamp: {timestamp}")
print("Real-time update sent!")