#!/usr/bin/env python3
"""
Compare QR codes between Android app logic and actual scraped QR
"""

import os
from datetime import datetime
import xml.etree.ElementTree as ET
import re

def generate_android_qr_content():
    """Generate QR content using Android app logic"""
    FACILITY_CODE = "9268"
    
    now = datetime.now()
    
    # Get current 2-hour time block
    current_hour = now.hour
    hour_block = (current_hour // 2) * 2
    
    # Format date as MMDDYYYY
    date_str = now.strftime("%m%d%Y")
    
    # Time component: HHMMSS
    # SS is 01 for 00:00-01:59 slot, 00 for all others
    ss = "01" if hour_block == 0 else "00"
    time_str = f"{hour_block:02d}00{ss}"
    
    return f"{FACILITY_CODE}{date_str}{time_str}"

def extract_qr_content_from_svg(svg_path):
    """Extract QR content from SVG file"""
    try:
        with open(svg_path, 'r') as f:
            svg_content = f.read()
        
        # Parse SVG
        root = ET.fromstring(svg_content)
        
        # Look for text elements that might contain the QR data
        for elem in root.iter():
            if elem.text and elem.text.strip():
                # Check if it looks like our QR pattern (starts with 9268)
                if elem.text.strip().startswith('9268'):
                    return elem.text.strip()
        
        # If no text found, try to extract from path data or other attributes
        # QR codes in SVG are typically represented as path elements
        print("No direct text found in SVG, QR is encoded as graphical elements")
        return None
        
    except Exception as e:
        print(f"Error parsing SVG: {e}")
        return None

def analyze_qr_differences():
    """Main comparison function"""
    print("🔍 QR Code Comparison Tool")
    print("=" * 50)
    
    # Generate Android app QR content
    android_content = generate_android_qr_content()
    print(f"\n📱 Android App Generated Content:")
    print(f"   Content: {android_content}")
    print(f"   Length: {len(android_content)} characters")
    
    # Parse the content
    if len(android_content) == 18:
        facility = android_content[0:4]
        month = android_content[4:6]
        day = android_content[6:8]
        year = android_content[8:12]
        hour = android_content[12:14]
        minutes = android_content[14:16]
        seconds = android_content[16:18]
        
        print(f"   Facility: {facility}")
        print(f"   Date: {month}/{day}/{year}")
        print(f"   Time: {hour}:{minutes}:{seconds}")
        print(f"   Time Slot: {hour}:00-{int(hour)+1}:59")
    
    # Find the latest scraped QR code
    qr_dir = "real_qr_codes"
    if os.path.exists(qr_dir):
        svg_files = [f for f in os.listdir(qr_dir) if f.endswith('.svg')]
        if svg_files:
            latest_svg = sorted(svg_files)[-1]
            svg_path = os.path.join(qr_dir, latest_svg)
            
            print(f"\n🌐 Latest Scraped QR Code:")
            print(f"   File: {latest_svg}")
            
            # Try to extract content from SVG
            scraped_content = extract_qr_content_from_svg(svg_path)
            
            if scraped_content:
                print(f"   Content: {scraped_content}")
                print(f"   Length: {len(scraped_content)} characters")
                
                # Compare
                if android_content == scraped_content:
                    print("\n✅ QR codes match perfectly!")
                else:
                    print("\n❌ QR codes differ!")
                    print(f"   Android: {android_content}")
                    print(f"   Scraped: {scraped_content}")
            else:
                print("   ⚠️  Could not extract text content from SVG")
                print("   Note: The QR code is encoded as graphical SVG elements")
                
                # Let's check the SVG file size and structure
                with open(svg_path, 'r') as f:
                    svg_data = f.read()
                print(f"   SVG Size: {len(svg_data)} characters")
                
                # Count rect elements (typical for QR codes)
                rect_count = svg_data.count('<rect')
                print(f"   Rect elements: {rect_count}")
                
                # Show a snippet of the SVG
                print("\n   SVG Preview (first 500 chars):")
                print("   " + svg_data[:500].replace('\n', '\n   '))
        else:
            print("\n❌ No scraped QR codes found")
    else:
        print("\n❌ real_qr_codes directory not found")
    
    print("\n" + "=" * 50)
    print("📊 Summary:")
    print(f"   Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Android QR: {android_content}")
    print("   Note: Actual QR codes are visual representations")
    print("         The text content needs to be decoded from the QR image")

if __name__ == "__main__":
    analyze_qr_differences()