#!/usr/bin/env python3
"""
Find exact QR parameters by testing all combinations
"""

import os
import qrcode
from PIL import Image
import base64
import re
import io
import numpy as np
import itertools

def extract_png_from_svg(svg_path):
    """Extract PNG from SVG"""
    with open(svg_path, 'r') as f:
        content = f.read()
    match = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)', content)
    if match:
        return Image.open(io.BytesIO(base64.b64decode(match.group(1))))
    return None

def convert_svg_to_png(svg_path):
    """Convert native SVG to PNG"""
    with open(svg_path, 'r') as f:
        content = f.read()
    
    # Parse SVG dimensions
    viewbox_match = re.search(r'viewBox="0 0 (\d+) (\d+)"', content)
    if viewbox_match:
        width = int(viewbox_match.group(1))
        height = int(viewbox_match.group(2))
    else:
        width = height = 580  # Default
    
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # Extract rectangles
    rects = re.findall(r'<rect x="(\d+)" y="(\d+)" width="(\d+)" height="(\d+)" fill="#(\w+)"></rect>', content)
    
    for x, y, w, h, color in rects:
        x, y, w, h = int(x), int(y), int(w), int(h)
        if color == '000000':  # Black
            draw.rectangle([x, y, x+w, y+h], fill='black')
    
    return img

def compare_qr_images(img1, img2):
    """Compare two QR images"""
    if img1.size != img2.size:
        return 0.0
    
    arr1 = np.array(img1.convert('L'))
    arr2 = np.array(img2.convert('L'))
    
    # Binary threshold
    arr1 = (arr1 < 128).astype(int)
    arr2 = (arr2 < 128).astype(int)
    
    matching = np.sum(arr1 == arr2)
    total = arr1.size
    
    return (matching / total) * 100

def find_exact_parameters(qr_data, reference_svg):
    """Try all parameter combinations to find exact match"""
    print(f"Finding parameters for: {reference_svg}")
    print(f"QR Data: {qr_data}")
    
    # Load reference image
    if 'data:image/png;base64' in open(reference_svg).read():
        ref_img = extract_png_from_svg(reference_svg)
    else:
        ref_img = convert_svg_to_png(reference_svg)
    
    if not ref_img:
        print("Failed to load reference image")
        return None
    
    print(f"Reference image size: {ref_img.size}")
    
    best_match = None
    best_similarity = 0
    
    # Parameters to test
    versions = [None, 1, 2, 3]  # None = auto
    error_corrections = [
        qrcode.constants.ERROR_CORRECT_L,
        qrcode.constants.ERROR_CORRECT_M,
        qrcode.constants.ERROR_CORRECT_Q,
        qrcode.constants.ERROR_CORRECT_H
    ]
    box_sizes = range(10, 50, 1)
    borders = range(0, 10)
    
    # Quick test with common parameters
    quick_tests = [
        (1, qrcode.constants.ERROR_CORRECT_L, 20, 4),
        (1, qrcode.constants.ERROR_CORRECT_M, 20, 4),
        (None, qrcode.constants.ERROR_CORRECT_L, 20, 4),
        (None, qrcode.constants.ERROR_CORRECT_M, 20, 4),
    ]
    
    print("Running quick tests...")
    for version, ec, box_size, border in quick_tests:
        try:
            qr = qrcode.QRCode(
                version=version,
                error_correction=ec,
                box_size=box_size,
                border=border,
            )
            
            qr.add_data(qr_data)
            qr.make(fit=version is None)
            
            img = qr.make_image(fill_color='black', back_color='white')
            
            # Test at original size
            similarity = compare_qr_images(ref_img, img)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = {
                    'version': version if version else qr.version,
                    'error_correction': ec,
                    'box_size': box_size,
                    'border': border,
                    'similarity': similarity,
                    'actual_version': qr.version,
                    'size': img.size
                }
                print(f"  Better match: {similarity:.2f}% - v={best_match['actual_version']}, ec={ec}, size={box_size}, border={border}")
                
                if similarity >= 99.9:
                    print("  Found perfect match!")
                    return best_match
                    
        except Exception as e:
            pass
    
    # If no perfect match, try resizing
    if best_similarity < 99.9:
        print("\nTrying with resize...")
        target_size = ref_img.size
        
        for version, ec in itertools.product([None, 1], error_corrections):
            try:
                qr = qrcode.QRCode(
                    version=version,
                    error_correction=ec,
                    box_size=10,  # Start small
                    border=4,
                )
                
                qr.add_data(qr_data)
                qr.make(fit=version is None)
                
                # Calculate ideal box size for target size
                modules = qr.modules_count
                ideal_box_size = target_size[0] // modules
                
                # Regenerate with ideal size
                qr2 = qrcode.QRCode(
                    version=qr.version,
                    error_correction=ec,
                    box_size=ideal_box_size,
                    border=4,
                )
                
                qr2.add_data(qr_data)
                qr2.make(fit=False)
                
                img = qr2.make_image(fill_color='black', back_color='white')
                
                # Resize if needed
                if img.size != target_size:
                    img = img.resize(target_size, Image.NEAREST)
                
                similarity = compare_qr_images(ref_img, img)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = {
                        'version': qr.version,
                        'error_correction': ec,
                        'box_size': ideal_box_size,
                        'border': 4,
                        'similarity': similarity,
                        'needs_resize': True,
                        'target_size': target_size
                    }
                    print(f"  Better match with resize: {similarity:.2f}% - v={qr.version}, ec={ec}")
                    
                    if similarity >= 99.9:
                        print("  Found perfect match with resize!")
                        return best_match
                        
            except Exception as e:
                pass
    
    return best_match

# Test with known QR
from PIL import ImageDraw

# First, let's check the 202506010144.svg file which uses embedded PNG
reference_file = "real_qr_codes/202506010144.svg"
qr_data = "926806012025000001"

result = find_exact_parameters(qr_data, reference_file)

if result:
    print(f"\nBest parameters found:")
    print(f"  Version: {result['version']}")
    print(f"  Error correction: {result['error_correction']}")
    print(f"  Box size: {result['box_size']}")
    print(f"  Border: {result['border']}")
    print(f"  Similarity: {result['similarity']:.2f}%")
    
    if 'needs_resize' in result:
        print(f"  Needs resize to: {result['target_size']}")
        
    # Save the error correction mapping
    ec_names = {
        qrcode.constants.ERROR_CORRECT_L: 'L',
        qrcode.constants.ERROR_CORRECT_M: 'M',
        qrcode.constants.ERROR_CORRECT_Q: 'Q',
        qrcode.constants.ERROR_CORRECT_H: 'H'
    }
    print(f"  Error correction level: {ec_names[result['error_correction']]}")
else:
    print("Failed to find matching parameters")