#!/usr/bin/env python3
"""
Deep QR Code Analyzer
Analyzes QR codes to determine exact generation parameters
"""

import os
import numpy as np
from PIL import Image, ImageDraw
import base64
import re
import io

def load_qr_image(svg_path):
    """Load QR code from SVG file"""
    with open(svg_path, 'r') as f:
        content = f.read()
    
    # Check for embedded PNG
    match = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)', content)
    if match:
        png_data = base64.b64decode(match.group(1))
        return Image.open(io.BytesIO(png_data))
    
    # Parse native SVG
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
    
    return img

def analyze_qr_structure(img):
    """Analyze QR code structure in detail"""
    # Convert to binary array
    arr = np.array(img.convert('L'))
    binary = (arr < 128).astype(int)
    
    # Find QR bounds
    black_pixels = np.where(binary == 1)
    if len(black_pixels[0]) == 0:
        return None
    
    min_y, max_y = black_pixels[0].min(), black_pixels[0].max()
    min_x, max_x = black_pixels[1].min(), black_pixels[1].max()
    
    qr_width = max_x - min_x + 1
    qr_height = max_y - min_y + 1
    
    # Extract QR region
    qr_region = binary[min_y:max_y+1, min_x:max_x+1]
    
    # Detect module size by analyzing finder pattern
    # Top-left finder pattern starts at (0,0) of QR region
    # Finder pattern is 7x7 modules with specific pattern
    
    # Method 1: Count consecutive black pixels in first row
    first_row = qr_region[0, :]
    black_runs = []
    current_run = 0
    
    for pixel in first_row:
        if pixel == 1:
            current_run += 1
        else:
            if current_run > 0:
                black_runs.append(current_run)
                current_run = 0
    if current_run > 0:
        black_runs.append(current_run)
    
    # The finder pattern should have a black run of 7 modules
    if black_runs:
        # The first black run should be the finder pattern
        module_size = black_runs[0] // 7
        if module_size == 0:
            module_size = 1
    else:
        module_size = 1
    
    # Calculate number of modules
    modules_x = qr_width // module_size
    modules_y = qr_height // module_size
    
    # QR version from module count
    # Version 1 = 21 modules, Version 2 = 25, etc.
    # modules = (version * 4) + 17
    version = (modules_x - 17) // 4
    
    # Detect quiet zone (border)
    quiet_zone_pixels = min_x
    quiet_zone_modules = quiet_zone_pixels // module_size
    
    # Extract format information
    # Format info is located in specific positions around finder patterns
    format_info = extract_format_info(qr_region, module_size)
    
    return {
        'image_size': img.size,
        'qr_bounds': (min_x, min_y, max_x, max_y),
        'qr_size': (qr_width, qr_height),
        'module_size': module_size,
        'modules': (modules_x, modules_y),
        'version': version,
        'quiet_zone_pixels': quiet_zone_pixels,
        'quiet_zone_modules': quiet_zone_modules,
        'format_info': format_info,
        'first_row_pattern': black_runs[:5] if black_runs else []
    }

def extract_format_info(qr_region, module_size):
    """Extract format information from QR code"""
    # Format information is stored in specific locations
    # For now, we'll analyze the pattern to infer error correction
    
    # Count total black modules to estimate density
    total_modules = qr_region.shape[0] // module_size
    black_count = 0
    total_count = 0
    
    for y in range(0, qr_region.shape[0], module_size):
        for x in range(0, qr_region.shape[1], module_size):
            if y + module_size <= qr_region.shape[0] and x + module_size <= qr_region.shape[1]:
                module = qr_region[y:y+module_size, x:x+module_size]
                if np.mean(module) > 0.5:  # Mostly black
                    black_count += 1
                total_count += 1
    
    density = black_count / total_count if total_count > 0 else 0
    
    # Estimate error correction based on density
    # Higher error correction = more black modules
    if density < 0.35:
        ec_estimate = 'L'
    elif density < 0.45:
        ec_estimate = 'M'
    elif density < 0.55:
        ec_estimate = 'Q'
    else:
        ec_estimate = 'H'
    
    return {
        'density': density,
        'black_modules': black_count,
        'total_modules': total_count,
        'ec_estimate': ec_estimate
    }

def compare_qr_patterns(file1, file2):
    """Compare two QR codes to understand differences"""
    img1 = load_qr_image(file1)
    img2 = load_qr_image(file2)
    
    analysis1 = analyze_qr_structure(img1)
    analysis2 = analyze_qr_structure(img2)
    
    print(f"\nComparing {os.path.basename(file1)} vs {os.path.basename(file2)}")
    print("="*60)
    
    if analysis1 and analysis2:
        print(f"Version: {analysis1['version']} vs {analysis2['version']}")
        print(f"Module size: {analysis1['module_size']} vs {analysis2['module_size']}")
        print(f"Modules: {analysis1['modules']} vs {analysis2['modules']}")
        print(f"Quiet zone: {analysis1['quiet_zone_modules']} vs {analysis2['quiet_zone_modules']}")
        print(f"Density: {analysis1['format_info']['density']:.3f} vs {analysis2['format_info']['density']:.3f}")
        print(f"EC estimate: {analysis1['format_info']['ec_estimate']} vs {analysis2['format_info']['ec_estimate']}")

# Analyze our QR codes
print("Analyzing Rise Gym QR Codes")
print("="*60)

# Analyze the embedded PNG one (202506010144.svg)
embedded_file = "real_qr_codes/202506010144.svg"
if os.path.exists(embedded_file):
    print(f"\nAnalyzing {embedded_file} (embedded PNG):")
    img = load_qr_image(embedded_file)
    analysis = analyze_qr_structure(img)
    
    if analysis:
        print(f"  Image size: {analysis['image_size']}")
        print(f"  QR bounds: {analysis['qr_bounds']}")
        print(f"  QR size: {analysis['qr_size']}")
        print(f"  Module size: {analysis['module_size']} pixels")
        print(f"  Modules: {analysis['modules'][0]}x{analysis['modules'][1]}")
        print(f"  Version: {analysis['version']}")
        print(f"  Quiet zone: {analysis['quiet_zone_modules']} modules ({analysis['quiet_zone_pixels']} pixels)")
        print(f"  Density: {analysis['format_info']['density']:.3f}")
        print(f"  EC estimate: {analysis['format_info']['ec_estimate']}")
        print(f"  First row pattern: {analysis['first_row_pattern']}")

# Analyze a native SVG one
native_file = "real_qr_codes/202506010748.svg"
if os.path.exists(native_file):
    print(f"\nAnalyzing {native_file} (native SVG):")
    img = load_qr_image(native_file)
    analysis = analyze_qr_structure(img)
    
    if analysis:
        print(f"  Image size: {analysis['image_size']}")
        print(f"  QR bounds: {analysis['qr_bounds']}")
        print(f"  QR size: {analysis['qr_size']}")
        print(f"  Module size: {analysis['module_size']} pixels")
        print(f"  Modules: {analysis['modules'][0]}x{analysis['modules'][1]}")
        print(f"  Version: {analysis['version']}")
        print(f"  Quiet zone: {analysis['quiet_zone_modules']} modules ({analysis['quiet_zone_pixels']} pixels)")
        print(f"  Density: {analysis['format_info']['density']:.3f}")
        print(f"  EC estimate: {analysis['format_info']['ec_estimate']}")

# Compare generated vs original
if os.path.exists("exact_qr_codes/202506010144.svg"):
    compare_qr_patterns(embedded_file, "exact_qr_codes/202506010144.svg")