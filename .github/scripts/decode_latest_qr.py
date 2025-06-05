#!/usr/bin/env python3
"""
Decode the latest scraped QR code and save results
"""

import os
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
import json

def find_latest_qr():
    """Find the most recent QR code file"""
    qr_dir = Path("scraped_qr_codes")
    if not qr_dir.exists():
        return None
    
    # Find all SVG files
    svg_files = list(qr_dir.rglob("*.svg"))
    if not svg_files:
        return None
    
    # Sort by modification time
    latest = max(svg_files, key=lambda f: f.stat().st_mtime)
    return latest

def decode_qr_from_file(file_path):
    """Decode QR using OpenCV (would need SVG to PNG conversion)"""
    # For now, just analyze the file
    print(f"📄 Analyzing: {file_path}")
    
    # Read file size
    size = file_path.stat().st_size
    
    # Extract timestamp from filename
    filename = file_path.name
    if filename.startswith("qr_") and filename.endswith(".svg"):
        time_part = filename[3:9]  # Extract HHMMSS
        hour = int(time_part[0:2])
        minute = int(time_part[2:4])
        second = int(time_part[4:6])
        
        hour_block = (hour // 2) * 2
        
        return {
            'file': str(file_path),
            'size': size,
            'hour': hour,
            'minute': minute,
            'second': second,
            'hour_block': hour_block,
            'timestamp': datetime.now().isoformat()
        }
    
    return None

def update_analysis_log(result):
    """Update the analysis log with new findings"""
    log_file = Path("scraped_qr_codes/analysis_log.json")
    
    # Load existing log
    if log_file.exists():
        with open(log_file, 'r') as f:
            log = json.load(f)
    else:
        log = {'entries': []}
    
    # Add new entry
    log['entries'].append(result)
    
    # Keep only last 100 entries
    log['entries'] = log['entries'][-100:]
    
    # Save updated log
    with open(log_file, 'w') as f:
        json.dump(log, f, indent=2)
    
    print(f"📊 Analysis log updated: {len(log['entries'])} entries")

def main():
    """Main function"""
    print("🔍 QR Code Decoder")
    print("=" * 40)
    
    # Find latest QR
    latest_qr = find_latest_qr()
    
    if not latest_qr:
        print("❌ No QR codes found")
        return
    
    # Analyze it
    result = decode_qr_from_file(latest_qr)
    
    if result:
        print(f"\n✅ Analysis complete:")
        print(f"   File: {result['file']}")
        print(f"   Size: {result['size']} bytes")
        print(f"   Time: {result['hour']:02d}:{result['minute']:02d}:{result['second']:02d}")
        print(f"   Hour block: {result['hour_block']:02d}:00-{result['hour_block']+1:02d}:59")
        
        # Update log
        update_analysis_log(result)
    else:
        print("❌ Failed to analyze QR code")

if __name__ == "__main__":
    main()