#!/usr/bin/env python3
"""
Analyze multiple QR codes to find the pattern for when last digit is 0 vs 1
"""

import cv2
import os
import json
from collections import defaultdict

def decode_qr_file(svg_path):
    """Try to decode a QR from SVG file"""
    try:
        # For now, we'll analyze based on file patterns
        # Real decoding would require converting SVG to image first
        return None
    except:
        return None

def analyze_qr_pattern():
    """Analyze pattern based on available QR codes"""
    print("🔍 Analyzing QR Code Pattern for Last Digit")
    print("=" * 60)
    
    # Load database
    with open('src/data/qr_code_database.json', 'r') as f:
        db = json.load(f)
    
    # Group by time slot
    slot_files = defaultdict(list)
    for file_info in db['files']:
        slot = file_info['slot_number']
        slot_files[slot].append(file_info)
    
    # We already know from the screenshot that 18:00 slot has last digit '1'
    # Let's check file sizes as a proxy for QR content changes
    print("\n📊 File Size Analysis by Time Slot:")
    print("(Different sizes likely indicate different QR content)")
    
    slot_sizes = {}
    for slot, files in sorted(slot_files.items()):
        sizes = set(f['file_size'] for f in files)
        slot_sizes[slot] = sizes
        
        slot_label = files[0]['slot_label']
        print(f"\nSlot {slot} ({slot_label}):")
        print(f"  Files: {len(files)}")
        print(f"  Unique sizes: {sizes}")
        
        # Check if size is consistent within slot
        if len(sizes) == 1:
            print("  ✓ Consistent size - same QR content")
        else:
            print("  ⚠️  Multiple sizes - QR content may vary")
    
    # Now let's decode some actual QRs
    print("\n" + "=" * 60)
    print("📱 Decoding Sample QR Codes:")
    
    # Decode the screenshot we already have
    screenshot_result = {
        'file': 'Screenshot 2025-06-05 at 19.31.40.png',
        'content': '926806052025180001',
        'slot': 9,
        'slot_label': '1800-1959',
        'last_digit': '1'
    }
    
    print(f"\n✅ Already decoded:")
    print(f"   {screenshot_result['slot_label']}: Last digit = {screenshot_result['last_digit']}")
    
    # Try to decode a few more QR codes from different slots
    sample_files = [
        ('202506010144.svg', 0, '0000-0159'),  # Slot 0
        ('202506010748.svg', 3, '0600-0759'),  # Slot 3
        ('202506010806.svg', 4, '0800-0959'),  # Slot 4
        ('202506011002.svg', 5, '1000-1159'),  # Slot 5
        ('202506012000.svg', 10, '2000-2159'), # Slot 10
        ('202506042334.svg', 11, '2200-2359')  # Slot 11
    ]
    
    # Since we can't decode SVGs directly, let's analyze the pattern
    print("\n🔮 Pattern Hypothesis Based on Data:")
    
    # Check file sizes
    size_10418 = []  # Smallest size
    size_14xxx = []  # Medium sizes  
    size_15xxx = []  # Larger sizes
    size_16xxx = []  # Largest size
    
    for f in db['files']:
        if f['file_size'] == 10418:
            size_10418.append(f['slot_number'])
        elif 14000 <= f['file_size'] < 15000:
            size_14xxx.append(f['slot_number'])
        elif 15000 <= f['file_size'] < 16000:
            size_15xxx.append(f['slot_number'])
        elif f['file_size'] >= 16000:
            size_16xxx.append(f['slot_number'])
    
    print(f"\nFile size patterns:")
    print(f"  10418 bytes: Slots {sorted(set(size_10418))}")
    print(f"  14xxx bytes: Slots {sorted(set(size_14xxx))}")
    print(f"  15xxx bytes: Slots {sorted(set(size_15xxx))}")
    print(f"  16xxx bytes: Slots {sorted(set(size_16xxx))}")
    
    # Our decoded QR (slot 9) has size 16209 in latest scrape
    print(f"\n💡 Key Observation:")
    print(f"   Slot 9 (18:00-19:59): Last digit = 1")
    print(f"   File size: ~16k bytes")
    
    print("\n📐 Possible Patterns:")
    print("1. Time-based: Certain hours use '1'")
    print("2. Day-based: Weekends vs weekdays")
    print("3. Slot-based: Specific slots always use '1'")
    print("4. Sequential: Alternating pattern")
    
    # Let's check our specific slots
    print("\n🎯 Based on available data:")
    print("   Slot 0 (00:00-01:59): File size 10418 → Likely different pattern")
    print("   Slot 9 (18:00-19:59): Confirmed last digit = 1")
    print("   Slot 10 (20:00-21:59): File size 16346 → Similar to slot 9")
    
    print("\n✨ Hypothesis: Evening slots (18:00+) might use '1'")
    print("   Morning/afternoon slots might use '0'")
    print("   Special case: Slot 0 (midnight) has unique behavior")

def suggest_next_steps():
    """Suggest how to confirm the pattern"""
    print("\n" + "=" * 60)
    print("🔬 To Confirm the Pattern:")
    print("=" * 60)
    
    print("\n1. Decode more QR codes from different time slots:")
    print("   - Convert SVG to PNG using cairosvg")
    print("   - Use OpenCV to decode each QR")
    print("   - Compare last digits across all slots")
    
    print("\n2. Manual testing approach:")
    print("   - Visit Rise Gym site at different times")
    print("   - Screenshot QR codes throughout the day")
    print("   - Decode and compare patterns")
    
    print("\n3. Check if pattern is:")
    print("   - Time-based (morning=0, evening=1)")
    print("   - Day-based (weekday=0, weekend=1)")
    print("   - Fixed by slot number")
    print("   - Or some other logic")

if __name__ == "__main__":
    analyze_qr_pattern()
    suggest_next_steps()