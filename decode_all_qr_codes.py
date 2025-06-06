#!/usr/bin/env python3
"""
Decode all QR codes in a directory and save results
"""

import os
import json
import cv2
import numpy as np
from PIL import Image
import cairosvg
import io
from datetime import datetime
import pytz

def decode_qr_from_svg(svg_path):
    """Convert SVG to PNG and decode QR code"""
    try:
        # Convert SVG to PNG
        png_data = cairosvg.svg2png(url=svg_path)
        img = Image.open(io.BytesIO(png_data))
        
        # Convert to OpenCV format
        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        
        # Decode QR
        detector = cv2.QRCodeDetector()
        data, bbox, _ = detector.detectAndDecode(cv_img)
        
        return data if data else None
    except Exception as e:
        print(f"Error decoding {svg_path}: {e}")
        return None

def parse_qr_content(content):
    """Parse QR code content into components"""
    if not content or len(content) != 18:
        return None
    
    try:
        return {
            'facility': content[0:4],
            'date': f"{content[4:6]}/{content[6:8]}/{content[8:12]}",
            'time': f"{content[12:14]}:{content[14:16]}:{content[16:18]}",
            'raw': content
        }
    except:
        return None

def main():
    directory = "real_qr_codes"
    results = []
    
    # Get all SVG files
    svg_files = sorted([f for f in os.listdir(directory) if f.endswith('.svg')])
    
    print(f"🔍 Found {len(svg_files)} QR codes to decode")
    print("=" * 60)
    
    for i, filename in enumerate(svg_files, 1):
        filepath = os.path.join(directory, filename)
        print(f"\n[{i}/{len(svg_files)}] Decoding {filename}...")
        
        # Extract timestamp from filename
        timestamp = filename.replace('.svg', '')
        
        # Decode QR
        content = decode_qr_from_svg(filepath)
        
        if content:
            parsed = parse_qr_content(content)
            result = {
                'filename': filename,
                'timestamp': timestamp,
                'content': content,
                'parsed': parsed,
                'status': 'success'
            }
            print(f"  ✅ Decoded: {content}")
            if parsed:
                print(f"     Facility: {parsed['facility']}")
                print(f"     Date: {parsed['date']}")
                print(f"     Time: {parsed['time']}")
        else:
            result = {
                'filename': filename,
                'timestamp': timestamp,
                'content': None,
                'parsed': None,
                'status': 'failed'
            }
            print(f"  ❌ Failed to decode")
        
        results.append(result)
    
    # Save results
    output_file = 'qr_decode_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Summary:")
    success_count = sum(1 for r in results if r['status'] == 'success')
    print(f"  Total QR codes: {len(results)}")
    print(f"  Successfully decoded: {success_count}")
    print(f"  Failed: {len(results) - success_count}")
    print(f"  Results saved to: {output_file}")
    
    # Pattern analysis
    if success_count > 0:
        print("\n🔍 Pattern Analysis:")
        facilities = set()
        for r in results:
            if r['parsed']:
                facilities.add(r['parsed']['facility'])
        
        print(f"  Facility codes found: {', '.join(sorted(facilities))}")
        
        # Check time slots
        time_slots = {}
        for r in results:
            if r['parsed']:
                hour = r['parsed']['time'][:2]
                if hour not in time_slots:
                    time_slots[hour] = 0
                time_slots[hour] += 1
        
        print(f"  Time slots distribution:")
        for hour in sorted(time_slots.keys()):
            print(f"    {hour}:00 - {int(hour)+1:02d}:59: {time_slots[hour]} QR codes")

if __name__ == "__main__":
    main()