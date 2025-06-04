#!/usr/bin/env python3
"""
QR Code Brute Force Matcher
Tries different data patterns to find exact QR match
"""

import os
import base64
import re
import qrcode
from PIL import Image
import io
import numpy as np
from pathlib import Path
import itertools
from datetime import datetime

def extract_png_from_svg(svg_path):
    """Extract PNG from SVG"""
    with open(svg_path, 'r') as f:
        content = f.read()
    match = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)', content)
    if match:
        return Image.open(io.BytesIO(base64.b64decode(match.group(1))))
    return None

def compare_qr_images(img1, img2):
    """Compare two QR images"""
    if img1.size != img2.size:
        img2 = img2.resize(img1.size, Image.NEAREST)
    
    arr1 = np.array(img1.convert('L'))
    arr2 = np.array(img2.convert('L'))
    
    # Binary threshold
    arr1 = (arr1 < 128).astype(int)
    arr2 = (arr2 < 128).astype(int)
    
    matching = np.sum(arr1 == arr2)
    total = arr1.size
    
    return (matching / total) * 100

def generate_qr_with_params(data, version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, 
                           box_size=41, border=4, target_size=(1200, 1200)):
    """Generate QR with specific parameters"""
    qr = qrcode.QRCode(
        version=version,
        error_correction=error_correction,
        box_size=box_size,
        border=border,
    )
    
    qr.add_data(data)
    qr.make(fit=False)
    
    img = qr.make_image(fill_color='black', back_color='white')
    
    if img.size != target_size:
        img = img.resize(target_size, Image.NEAREST)
    
    return img

def find_exact_match(reference_svg_path):
    """Try different data patterns to find exact match"""
    print(f"Finding exact match for: {reference_svg_path}")
    
    # Extract reference image
    ref_img = extract_png_from_svg(reference_svg_path)
    if not ref_img:
        print("Failed to extract reference image")
        return None
    
    # Parse filename for timestamp
    filename = Path(reference_svg_path).stem
    year = filename[0:4]
    month = filename[4:6]
    day = filename[6:8]
    hour = int(filename[8:10])
    minute = filename[10:12]
    
    print(f"Timestamp: {year}-{month}-{day} {hour}:{minute}")
    
    # Try different data patterns
    best_match = None
    best_similarity = 0
    
    # Pattern variations to try
    patterns = []
    
    # Pattern 1: Original assumption (9268 + MMDDYYYY + HHMMSS)
    slot_hour = (hour // 2) * 2
    patterns.append(f"9268{month}{day}{year}{slot_hour:02d}{'0001' if hour <= 1 else '0000'}")
    
    # Pattern 2: Different date format (9268 + YYYYMMDD + HHMMSS)
    patterns.append(f"9268{year}{month}{day}{slot_hour:02d}{'0001' if hour <= 1 else '0000'}")
    
    # Pattern 3: With actual time instead of slot
    patterns.append(f"9268{month}{day}{year}{hour:02d}{minute}00")
    patterns.append(f"9268{year}{month}{day}{hour:02d}{minute}00")
    
    # Pattern 4: Different facility codes
    for facility in ['9268', '9628', '6928', '8926', '2689']:
        patterns.append(f"{facility}{month}{day}{year}{slot_hour:02d}0000")
        patterns.append(f"{facility}{year}{month}{day}{slot_hour:02d}0000")
    
    # Pattern 5: Try URL format
    patterns.append(f"https://risegym.com/qr/{year}{month}{day}{hour}{minute}")
    patterns.append(f"RISE{year}{month}{day}{hour}{minute}")
    
    # Pattern 6: Simple numeric patterns
    patterns.append(f"{year}{month}{day}{hour}{minute}")
    patterns.append(f"{month}{day}{year}{hour}{minute}")
    
    # Pattern 7: With different time patterns
    for h in range(0, 24, 2):
        patterns.append(f"9268{month}{day}{year}{h:02d}0000")
        patterns.append(f"9268{month}{day}{year}{h:02d}0001")
    
    # Remove duplicates
    patterns = list(set(patterns))
    
    print(f"Trying {len(patterns)} different patterns...")
    
    # Try each pattern with different QR parameters
    error_corrections = [
        qrcode.constants.ERROR_CORRECT_L,
        qrcode.constants.ERROR_CORRECT_M,
        qrcode.constants.ERROR_CORRECT_Q,
        qrcode.constants.ERROR_CORRECT_H
    ]
    
    for i, pattern in enumerate(patterns):
        for ec in error_corrections:
            try:
                # Generate QR
                test_img = generate_qr_with_params(pattern, error_correction=ec)
                
                # Compare
                similarity = compare_qr_images(ref_img, test_img)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = {
                        'data': pattern,
                        'error_correction': ec,
                        'similarity': similarity,
                        'image': test_img
                    }
                    
                    print(f"  New best: {similarity:.2f}% - Data: {pattern}")
                    
                    if similarity >= 99.9:
                        print(f"  ✅ FOUND EXACT MATCH!")
                        return best_match
                        
            except Exception as e:
                continue
    
    print(f"\nBest match: {best_similarity:.2f}%")
    return best_match

def analyze_qr_content(svg_path):
    """Try to understand QR content through pattern analysis"""
    ref_img = extract_png_from_svg(svg_path)
    if not ref_img:
        return None
    
    # Convert to binary array
    arr = np.array(ref_img.convert('L'))
    binary = (arr < 128).astype(int)
    
    # Extract QR region
    black_pixels = np.where(binary == 1)
    if len(black_pixels[0]) == 0:
        return None
    
    min_y, max_y = black_pixels[0].min(), black_pixels[0].max()
    min_x, max_x = black_pixels[1].min(), black_pixels[1].max()
    
    qr_region = binary[min_y:max_y+1, min_x:max_x+1]
    
    # Estimate modules (should be 21x21 for Version 1)
    qr_size = qr_region.shape[0]
    module_size = qr_size // 21
    
    print(f"QR Analysis:")
    print(f"  QR size: {qr_size}x{qr_size} pixels")
    print(f"  Module size: {module_size} pixels")
    print(f"  Total modules: 21x21 (Version 1)")
    
    # The data in a QR code is encoded in a specific pattern
    # For numeric mode, groups of 3 digits are encoded together
    # Let's check if the QR matches our expected patterns
    
    return {
        'qr_size': qr_size,
        'module_size': module_size,
        'binary_data': qr_region
    }

def main():
    """Find exact QR match"""
    test_file = "real_qr_codes/202506010144.svg"
    
    if not os.path.exists(test_file):
        print(f"Test file not found: {test_file}")
        return
    
    # First analyze the QR
    print("Analyzing QR structure...")
    analysis = analyze_qr_content(test_file)
    
    # Try to find exact match
    print("\nSearching for exact data match...")
    result = find_exact_match(test_file)
    
    if result and result['similarity'] >= 99.9:
        print(f"\n✅ SUCCESS! Found exact match:")
        print(f"  Data: {result['data']}")
        print(f"  Error Correction: {result['error_correction']}")
        print(f"  Similarity: {result['similarity']:.2f}%")
        
        # Save the matching QR
        output_path = "perfect_match.png"
        result['image'].save(output_path)
        print(f"  Saved to: {output_path}")
        
        # Also save as SVG with embedded PNG
        png_buffer = io.BytesIO()
        result['image'].save(png_buffer, format='PNG')
        png_base64 = base64.b64encode(png_buffer.getvalue()).decode('utf-8')
        
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 200 200">
    <image width="200" height="200" xlink:href="data:image/png;base64,{png_base64}"/>
</svg>'''
        
        with open("perfect_match.svg", 'w') as f:
            f.write(svg_content)
        
        print(f"  SVG saved to: perfect_match.svg")
        
        # Create a generator with the found pattern
        print(f"\n📝 To generate QR codes with this pattern:")
        print(f"  Data format: {result['data']}")
        print(f"  Error correction: Level {'LMQH'['LMQH'.index(str(result['error_correction']))]}")
        
    else:
        print(f"\n❌ Could not find exact match")
        print(f"  Best similarity: {result['similarity'] if result else 0:.2f}%")

if __name__ == "__main__":
    main()