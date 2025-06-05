#!/usr/bin/env python3
"""
Decode QR code from screenshot and analyze encoding/error correction
"""

import cv2
import numpy as np
from PIL import Image
import os

def decode_qr_with_opencv(image_path):
    """Decode QR code using OpenCV and get detailed information"""
    print(f"🔍 Decoding QR from: {os.path.basename(image_path)}")
    print("=" * 60)
    
    # Read the image
    img = cv2.imread(image_path)
    
    if img is None:
        print("❌ Could not read image")
        return
    
    # Initialize QR code detector
    detector = cv2.QRCodeDetector()
    
    # Detect and decode
    data, bbox, straight_qrcode = detector.detectAndDecode(img)
    
    if data:
        print(f"\n✅ QR Code Decoded Successfully!")
        print(f"📊 Content: {data}")
        print(f"📏 Length: {len(data)} characters")
        
        # Analyze the content
        if len(data) == 18 and data.startswith('9268'):
            print(f"\n📱 Rise Gym QR Pattern Detected!")
            facility = data[0:4]
            month = data[4:6]
            day = data[6:8]
            year = data[8:12]
            hour = data[12:14]
            minutes = data[14:16]
            seconds = data[16:18]
            
            print(f"   Facility: {facility}")
            print(f"   Date: {month}/{day}/{year}")
            print(f"   Time: {hour}:{minutes}:{seconds}")
            print(f"   Time Slot: {hour}:00-{int(hour)+1}:59")
        
        # If we have the straight QR code, analyze its properties
        if straight_qrcode is not None:
            print(f"\n🔧 QR Code Properties:")
            print(f"   Shape: {straight_qrcode.shape}")
            
            # Estimate QR version based on size
            if straight_qrcode.shape[0] > 0:
                modules = straight_qrcode.shape[0]
                version = (modules - 21) // 4 + 1
                print(f"   Estimated Version: {version}")
                print(f"   Module Count: {modules}x{modules}")
        
        # Additional analysis using pyzbar if available
        try:
            from pyzbar import pyzbar
            from pyzbar.pyzbar import ZBarSymbol
            
            # Convert to grayscale for pyzbar
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Decode with pyzbar for more details
            decoded_objects = pyzbar.decode(gray, symbols=[ZBarSymbol.QRCODE])
            
            if decoded_objects:
                obj = decoded_objects[0]
                print(f"\n🔍 Advanced QR Analysis (pyzbar):")
                print(f"   Type: {obj.type}")
                print(f"   Quality: {obj.quality}")
                print(f"   Orientation: {obj.orientation}")
                
                # Try to determine error correction level
                # This is tricky as it's encoded in the QR format bits
                print(f"\n📊 Error Correction Analysis:")
                print(f"   Note: Error correction level is encoded in format information")
                print(f"   Common levels: L (~7%), M (~15%), Q (~25%), H (~30%)")
                print(f"   Rise Gym likely uses L or M for maximum data capacity")
                
        except ImportError:
            print("\n💡 Install pyzbar for more detailed analysis:")
            print("   pip install pyzbar")
            print("   brew install zbar (on macOS)")
    else:
        print("❌ Could not decode QR code")
        print("   Trying alternative methods...")
        
        # Try with different preprocessing
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply threshold
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        # Try again with processed image
        data2, bbox2, straight_qrcode2 = detector.detectAndDecode(thresh)
        
        if data2:
            print(f"\n✅ Decoded with preprocessing: {data2}")
        else:
            print("❌ Still could not decode")
            
            # Show image properties
            print(f"\n📷 Image Properties:")
            print(f"   Dimensions: {img.shape[1]}x{img.shape[0]}")
            print(f"   Channels: {img.shape[2]}")

def analyze_qr_encoding():
    """Analyze QR encoding details"""
    print("\n" + "=" * 60)
    print("📚 QR Code Encoding Analysis")
    print("=" * 60)
    
    print("\n🔤 Data Encoding Modes:")
    print("   - Numeric: 0-9 (most efficient for numbers)")
    print("   - Alphanumeric: 0-9, A-Z, space, $%*+-./:") 
    print("   - Byte/Binary: Any 8-bit data")
    print("   - Kanji: Japanese characters")
    
    print("\n📊 Rise Gym QR Analysis:")
    print("   Content: 926806052025180000")
    print("   Type: Numeric only (most efficient)")
    print("   Length: 18 digits")
    print("   Encoding: Numeric mode (3.33 bits per digit)")
    print("   Total bits: ~60 bits of data")
    
    print("\n🛡️ Error Correction Levels:")
    print("   - L (Low): ~7% correction capability")
    print("   - M (Medium): ~15% correction capability")
    print("   - Q (Quartile): ~25% correction capability")
    print("   - H (High): ~30% correction capability")
    
    print("\n💡 Likely Configuration:")
    print("   - Version 1 QR (21x21 modules)")
    print("   - Numeric encoding mode")
    print("   - Error correction: L or M (for maximum capacity)")
    print("   - Mask pattern: Automatically selected")

if __name__ == "__main__":
    screenshot_path = "/Users/lukaj/Desktop/Screenshot 2025-06-05 at 19.31.40.png"
    
    # Decode the QR
    decode_qr_with_opencv(screenshot_path)
    
    # Analyze encoding
    analyze_qr_encoding()