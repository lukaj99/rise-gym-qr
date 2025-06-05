#!/usr/bin/env python3
"""
Decode QR code from SVG file by converting to image and reading with qrcode library
"""

import os
import sys
from datetime import datetime

try:
    from PIL import Image
    import qrcode
    from qrcode.image.svg import SvgPathImage
    import cairosvg
    import io
    from pyzbar.pyzbar import decode
    LIBS_AVAILABLE = True
except ImportError as e:
    LIBS_AVAILABLE = False
    print(f"❌ Missing required libraries: {e}")
    print("Install with: pip install pillow qrcode cairosvg pyzbar")
    print("On macOS, you may also need: brew install zbar")

def decode_qr_from_svg(svg_path):
    """Convert SVG to PNG and decode QR code"""
    if not LIBS_AVAILABLE:
        return None
        
    try:
        # Convert SVG to PNG in memory
        png_data = cairosvg.svg2png(url=svg_path)
        
        # Open as PIL Image
        image = Image.open(io.BytesIO(png_data))
        
        # Try to decode QR code
        decoded_objects = decode(image)
        
        if decoded_objects:
            # Get the first QR code found
            qr_data = decoded_objects[0].data.decode('utf-8')
            return qr_data
        else:
            print("No QR code found in image")
            return None
            
    except Exception as e:
        print(f"Error decoding QR: {e}")
        return None

def compare_qr_codes_visual():
    """Compare QR codes by decoding the visual representation"""
    print("🔍 Visual QR Code Decoder & Comparison")
    print("=" * 50)
    
    # Generate Android app QR content
    FACILITY_CODE = "9268"
    now = datetime.now()
    current_hour = now.hour
    hour_block = (current_hour // 2) * 2
    date_str = now.strftime("%m%d%Y")
    ss = "01" if hour_block == 0 else "00"
    time_str = f"{hour_block:02d}00{ss}"
    android_content = f"{FACILITY_CODE}{date_str}{time_str}"
    
    print(f"\n📱 Android App Generated Content:")
    print(f"   Content: {android_content}")
    print(f"   Time slot: {hour_block:02d}:00-{hour_block+1:02d}:59")
    
    # Find and decode the latest scraped QR code
    qr_dir = "real_qr_codes"
    if os.path.exists(qr_dir):
        svg_files = [f for f in os.listdir(qr_dir) if f.endswith('.svg')]
        if svg_files:
            latest_svg = sorted(svg_files)[-1]
            svg_path = os.path.join(qr_dir, latest_svg)
            
            print(f"\n🌐 Decoding Scraped QR Code:")
            print(f"   File: {latest_svg}")
            
            if LIBS_AVAILABLE:
                decoded_content = decode_qr_from_svg(svg_path)
                
                if decoded_content:
                    print(f"   Decoded: {decoded_content}")
                    
                    # Compare
                    if android_content == decoded_content:
                        print("\n✅ SUCCESS! QR codes match perfectly!")
                    else:
                        print("\n❌ MISMATCH! QR codes differ:")
                        print(f"   Android:  {android_content}")
                        print(f"   Scraped:  {decoded_content}")
                        
                        # Analyze differences
                        if len(android_content) == len(decoded_content) == 18:
                            for i, (a, s) in enumerate(zip(android_content, decoded_content)):
                                if a != s:
                                    print(f"   Diff at position {i}: '{a}' vs '{s}'")
                else:
                    print("   ❌ Could not decode QR from SVG")
            else:
                print("   ⚠️  Required libraries not installed")
                print("   Install with: pip install pillow qrcode cairosvg pyzbar")
                print("   On macOS: brew install zbar")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    compare_qr_codes_visual()