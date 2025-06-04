#!/usr/bin/env python3
"""
Perfect QR Match Generator
Tests all error correction levels to find exact match
"""

import os
import qrcode
from PIL import Image
import numpy as np
import base64
import re
import io

def load_reference_qr(svg_path):
    """Load reference QR from SVG"""
    with open(svg_path, 'r') as f:
        content = f.read()
    
    # Check for embedded PNG
    match = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)', content)
    if match:
        png_data = base64.b64decode(match.group(1))
        return Image.open(io.BytesIO(png_data)), 'embedded'
    
    # Native SVG
    viewbox_match = re.search(r'viewBox="0 0 (\d+) (\d+)"', content)
    if viewbox_match:
        width = int(viewbox_match.group(1))
        height = int(viewbox_match.group(2))
    else:
        width = height = 580
    
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    rects = re.findall(r'<rect x="(\d+)" y="(\d+)" width="(\d+)" height="(\d+)" fill="#(\w+)"></rect>', content)
    
    for x, y, w, h, color in rects:
        x, y, w, h = int(x), int(y), int(w), int(h)
        if color == '000000':
            draw.rectangle([x, y, x+w, y+h], fill='black')
    
    return img, 'native'

def compare_images(img1, img2):
    """Compare two images pixel by pixel"""
    if img1.size != img2.size:
        return 0.0, None
    
    arr1 = np.array(img1.convert('L'))
    arr2 = np.array(img2.convert('L'))
    
    # Binary threshold
    arr1 = (arr1 < 128).astype(int)
    arr2 = (arr2 < 128).astype(int)
    
    # Compare
    diff = np.abs(arr1 - arr2)
    matching = np.sum(diff == 0)
    total = arr1.size
    
    return (matching / total) * 100, diff

def test_all_error_corrections(qr_data, reference_svg):
    """Test all error correction levels"""
    ref_img, ref_type = load_reference_qr(reference_svg)
    print(f"Reference: {reference_svg}")
    print(f"Type: {ref_type}")
    print(f"Size: {ref_img.size}")
    print(f"QR Data: {qr_data}")
    print()
    
    # Determine parameters based on type
    if ref_type == 'embedded' and ref_img.size == (1200, 1200):
        # 202506010144.svg parameters
        module_size = 41
        expected_qr_size = 21 * 41  # 861
        border_pixels = (1200 - expected_qr_size) // 2  # ~169
        border_modules = 4
    else:
        # Native SVG parameters
        module_size = 20
        border_modules = 4
    
    # Test each error correction level
    error_corrections = [
        (qrcode.constants.ERROR_CORRECT_L, 'L'),
        (qrcode.constants.ERROR_CORRECT_M, 'M'),
        (qrcode.constants.ERROR_CORRECT_Q, 'Q'),
        (qrcode.constants.ERROR_CORRECT_H, 'H')
    ]
    
    results = []
    
    for ec, ec_name in error_corrections:
        print(f"Testing Error Correction Level {ec_name}...")
        
        # Generate QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=ec,
            box_size=module_size,
            border=border_modules,
        )
        
        qr.add_data(qr_data)
        qr.make(fit=False)
        
        img = qr.make_image(fill_color='black', back_color='white')
        
        # For embedded PNG type, we might need to resize
        if ref_type == 'embedded' and img.size != ref_img.size:
            # Try exact resize
            img_resized = img.resize(ref_img.size, Image.NEAREST)
            similarity, diff = compare_images(ref_img, img_resized)
            print(f"  Generated size: {img.size}, resized to: {img_resized.size}")
        else:
            similarity, diff = compare_images(ref_img, img)
            print(f"  Generated size: {img.size}")
        
        print(f"  Similarity: {similarity:.2f}%")
        
        results.append({
            'ec': ec,
            'ec_name': ec_name,
            'similarity': similarity,
            'image': img
        })
        
        # Save comparison for best match
        if similarity > 99:
            output_name = f"test_ec_{ec_name}_{int(similarity)}.png"
            img.save(output_name)
            print(f"  Saved: {output_name}")
            
            # Save difference map
            if diff is not None:
                diff_img = Image.fromarray((diff * 255).astype(np.uint8))
                diff_img.save(f"diff_ec_{ec_name}.png")
        
        print()
    
    # Find best match
    best = max(results, key=lambda x: x['similarity'])
    print(f"Best match: Error Correction Level {best['ec_name']} with {best['similarity']:.2f}% similarity")
    
    return best

# Test with different QR codes
test_cases = [
    ("real_qr_codes/202506010144.svg", "926806012025000001"),  # Embedded PNG
    ("real_qr_codes/202506010748.svg", "926806012025060000"),  # Native SVG
]

for reference_file, qr_data in test_cases:
    if os.path.exists(reference_file):
        print("="*60)
        result = test_all_error_corrections(qr_data, reference_file)
        print("="*60)
        print()

# Now let's also test mask patterns if we still don't have 100%
print("\nNote: The python-qrcode library automatically selects the optimal mask pattern.")
print("For exact reproduction, we might need a lower-level library that allows mask control.")