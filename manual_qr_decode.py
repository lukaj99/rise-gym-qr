#!/usr/bin/env python3
"""
Manual QR decoder for the specific Rise Gym pattern
Since we know the QR contains 18 characters in format: 9268MMDDYYYYHHMMSS
"""

import os
import xml.etree.ElementTree as ET
from datetime import datetime
import re

def analyze_svg_structure(svg_path):
    """Analyze the SVG structure to understand the QR code"""
    with open(svg_path, 'r') as f:
        svg_content = f.read()
    
    # Parse SVG
    root = ET.fromstring(svg_content)
    
    # Count elements
    rects = root.findall('.//{http://www.w3.org/2000/svg}rect')
    print(f"Total rectangles in QR code: {len(rects)}")
    
    # QR codes are typically square grids
    # For an 18-character string, we'd expect a 25x25 or 29x29 QR code
    # Let's analyze the grid structure
    
    positions = set()
    for rect in rects:
        x = rect.get('x', '0')
        y = rect.get('y', '0')
        if x != '0' and y != '0':  # Skip background
            positions.add((int(x), int(y)))
    
    if positions:
        x_coords = sorted(set(pos[0] for pos in positions))
        y_coords = sorted(set(pos[1] for pos in positions))
        
        print(f"Grid dimensions: {len(x_coords)} x {len(y_coords)}")
        print(f"X range: {min(x_coords)} to {max(x_coords)}")
        print(f"Y range: {min(y_coords)} to {max(y_coords)}")
        
        # Check if it's a valid QR code size
        grid_size = len(x_coords)
        if grid_size in [21, 25, 29, 33, 37, 41, 45]:  # Valid QR code sizes
            print(f"✓ Valid QR code version (size {grid_size})")
        
        return len(rects), grid_size
    
    return len(rects), 0

def compare_with_expected():
    """Compare the QR structure with what we expect"""
    print("🔍 QR Code Structure Analysis")
    print("=" * 50)
    
    # Generate expected content
    FACILITY_CODE = "9268"
    now = datetime.now()
    current_hour = now.hour
    hour_block = (current_hour // 2) * 2
    date_str = now.strftime("%m%d%Y")
    ss = "01" if hour_block == 0 else "00"
    time_str = f"{hour_block:02d}00{ss}"
    expected_content = f"{FACILITY_CODE}{date_str}{time_str}"
    
    print(f"\n📱 Expected Android App Content:")
    print(f"   Content: {expected_content}")
    print(f"   Pattern: 9268 + MMDDYYYY + HHMMSS")
    print(f"   Breakdown:")
    print(f"     - Facility: 9268")
    print(f"     - Date: {date_str[0:2]}/{date_str[2:4]}/{date_str[4:8]}")
    print(f"     - Time: {hour_block:02d}:00:{ss}")
    print(f"     - Time slot: {hour_block:02d}:00-{hour_block+1:02d}:59")
    
    # Analyze latest QR
    qr_dir = "real_qr_codes"
    if os.path.exists(qr_dir):
        svg_files = [f for f in os.listdir(qr_dir) if f.endswith('.svg')]
        if svg_files:
            latest_svg = sorted(svg_files)[-1]
            svg_path = os.path.join(qr_dir, latest_svg)
            
            print(f"\n🌐 Analyzing Scraped QR Code:")
            print(f"   File: {latest_svg}")
            print(f"   Scraped at: {latest_svg[0:12]}")  # Timestamp in filename
            
            rect_count, grid_size = analyze_svg_structure(svg_path)
            
            print(f"\n📊 Analysis Summary:")
            print(f"   - QR contains {rect_count} black modules")
            print(f"   - Grid size: {grid_size}x{grid_size}")
            print(f"   - Expected content length: 18 characters")
            print(f"   - QR capacity at this size: ~25-50 characters")
            
            # Check timing
            scraped_time = latest_svg[0:12]  # Format: YYYYMMDDHHMM
            if len(scraped_time) == 12:
                scraped_hour = int(scraped_time[8:10])
                scraped_hour_block = (scraped_hour // 2) * 2
                
                print(f"\n⏰ Timing Analysis:")
                print(f"   - Scraped at hour: {scraped_hour}:00")
                print(f"   - Scraped hour block: {scraped_hour_block:02d}:00-{scraped_hour_block+1:02d}:59")
                print(f"   - Current hour block: {hour_block:02d}:00-{hour_block+1:02d}:59")
                
                if scraped_hour_block == hour_block:
                    print("   ✓ Same time block - QR should match!")
                else:
                    print("   ⚠️  Different time blocks - QR will differ")
    
    print("\n" + "=" * 50)
    print("\n💡 Recommendation:")
    print("   To properly decode the QR, we need to either:")
    print("   1. Use a QR decoder library (requires fixing cairo installation)")
    print("   2. Manually decode the QR matrix from SVG (complex)")
    print("   3. Use the Android app to scan and compare")

if __name__ == "__main__":
    compare_with_expected()