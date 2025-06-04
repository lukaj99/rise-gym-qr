#!/usr/bin/env python3
"""
Visual QR Code Comparison Tool
Helps identify differences between generated and original QR codes
"""

import os
import base64
import re
from PIL import Image, ImageDraw, ImageFont
import io
import numpy as np
from pathlib import Path

def extract_png_from_svg(svg_path):
    """Extract PNG from SVG file"""
    with open(svg_path, 'r') as f:
        content = f.read()
    
    match = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)', content)
    if match:
        png_data = base64.b64decode(match.group(1))
        return Image.open(io.BytesIO(png_data))
    return None

def create_comparison_image(original_path, generated_path, output_path="qr_comparison.png"):
    """Create side-by-side comparison with difference visualization"""
    
    # Load images
    if original_path.endswith('.svg'):
        orig_img = extract_png_from_svg(original_path)
    else:
        orig_img = Image.open(original_path)
    
    if generated_path.endswith('.svg'):
        gen_img = extract_png_from_svg(generated_path)
    else:
        gen_img = Image.open(generated_path)
    
    if not orig_img or not gen_img:
        print("Failed to load images")
        return None
    
    # Ensure same size
    if gen_img.size != orig_img.size:
        gen_img = gen_img.resize(orig_img.size, Image.NEAREST)
    
    width, height = orig_img.size
    
    # Create comparison canvas (3 images side by side + labels)
    canvas_width = width * 3 + 40  # Extra space for gaps
    canvas_height = height + 100    # Extra space for labels
    canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
    
    # Paste original
    canvas.paste(orig_img, (10, 50))
    
    # Paste generated
    canvas.paste(gen_img, (width + 20, 50))
    
    # Create difference image
    diff_img = Image.new('RGB', (width, height), 'white')
    diff_pixels = []
    
    orig_arr = np.array(orig_img.convert('L'))
    gen_arr = np.array(gen_img.convert('L'))
    
    # Count differences
    total_diff = 0
    
    for y in range(height):
        for x in range(width):
            if orig_arr[y, x] == gen_arr[y, x]:
                diff_pixels.append((255, 255, 255))  # White for matching
            else:
                diff_pixels.append((255, 0, 0))      # Red for different
                total_diff += 1
    
    diff_img.putdata(diff_pixels)
    canvas.paste(diff_img, (width * 2 + 30, 50))
    
    # Add labels
    draw = ImageDraw.Draw(canvas)
    
    # Try to use a better font if available
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    except:
        font = ImageFont.load_default()
        small_font = font
    
    # Labels
    draw.text((width//2 - 50, 10), "Original", fill='black', font=font, anchor='mt')
    draw.text((width + width//2 + 10, 10), "Generated", fill='black', font=font, anchor='mt')
    draw.text((width*2 + width//2 + 20, 10), "Differences", fill='black', font=font, anchor='mt')
    
    # Statistics
    total_pixels = width * height
    similarity = ((total_pixels - total_diff) / total_pixels) * 100
    
    stats_text = f"Similarity: {similarity:.2f}% | Different pixels: {total_diff:,} / {total_pixels:,}"
    draw.text((canvas_width//2, canvas_height - 20), stats_text, fill='black', font=small_font, anchor='mt')
    
    # Save comparison
    canvas.save(output_path)
    print(f"Comparison saved to: {output_path}")
    
    # Also create a zoomed difference view
    create_zoomed_diff(orig_img, gen_img, output_path.replace('.png', '_zoom.png'))
    
    return {
        'output': output_path,
        'similarity': similarity,
        'different_pixels': total_diff,
        'total_pixels': total_pixels
    }

def create_zoomed_diff(orig_img, gen_img, output_path):
    """Create zoomed view of differences"""
    orig_arr = np.array(orig_img.convert('L'))
    gen_arr = np.array(gen_img.convert('L'))
    
    # Find first area with differences
    diff_mask = orig_arr != gen_arr
    diff_coords = np.where(diff_mask)
    
    if len(diff_coords[0]) == 0:
        print("No differences found")
        return
    
    # Find a region with differences
    y_coords, x_coords = diff_coords
    
    # Pick a region around the first difference
    center_y = y_coords[len(y_coords)//2]
    center_x = x_coords[len(x_coords)//2]
    
    # Extract 100x100 region
    region_size = 100
    half_size = region_size // 2
    
    y_start = max(0, center_y - half_size)
    y_end = min(orig_arr.shape[0], center_y + half_size)
    x_start = max(0, center_x - half_size)
    x_end = min(orig_arr.shape[1], center_x + half_size)
    
    # Extract regions
    orig_region = orig_arr[y_start:y_end, x_start:x_end]
    gen_region = gen_arr[y_start:y_end, x_start:x_end]
    
    # Scale up 10x
    scale = 10
    
    # Create zoomed images
    orig_zoom = Image.fromarray(orig_region).resize(
        (orig_region.shape[1] * scale, orig_region.shape[0] * scale),
        Image.NEAREST
    )
    
    gen_zoom = Image.fromarray(gen_region).resize(
        (gen_region.shape[1] * scale, gen_region.shape[0] * scale),
        Image.NEAREST
    )
    
    # Create canvas
    canvas_width = orig_zoom.width * 2 + 30
    canvas_height = orig_zoom.height + 100
    canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
    
    # Paste zoomed regions
    canvas.paste(orig_zoom, (10, 50))
    canvas.paste(gen_zoom, (orig_zoom.width + 20, 50))
    
    # Add grid overlay
    draw = ImageDraw.Draw(canvas)
    
    # Draw grid on both images
    for i in range(0, orig_zoom.width + 1, scale):
        # Original
        draw.line([(10 + i, 50), (10 + i, 50 + orig_zoom.height)], fill='gray', width=1)
        # Generated
        draw.line([(orig_zoom.width + 20 + i, 50), (orig_zoom.width + 20 + i, 50 + orig_zoom.height)], fill='gray', width=1)
    
    for i in range(0, orig_zoom.height + 1, scale):
        # Original
        draw.line([(10, 50 + i), (10 + orig_zoom.width, 50 + i)], fill='gray', width=1)
        # Generated
        draw.line([(orig_zoom.width + 20, 50 + i), (orig_zoom.width * 2 + 20, 50 + i)], fill='gray', width=1)
    
    # Labels
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except:
        font = ImageFont.load_default()
    
    draw.text((orig_zoom.width//2, 20), "Original (10x zoom)", fill='black', font=font, anchor='mt')
    draw.text((orig_zoom.width + orig_zoom.width//2 + 15, 20), "Generated (10x zoom)", fill='black', font=font, anchor='mt')
    
    info_text = f"Region: ({x_start},{y_start}) to ({x_end},{y_end})"
    draw.text((canvas_width//2, canvas_height - 20), info_text, fill='black', font=font, anchor='mt')
    
    canvas.save(output_path)
    print(f"Zoomed comparison saved to: {output_path}")

def main():
    """Compare generated QR with original"""
    original = "real_qr_codes/202506010144.svg"
    generated = "exact_qr_codes/202506010144.svg"
    
    if os.path.exists(original) and os.path.exists(generated):
        print("Creating visual comparison...")
        result = create_comparison_image(original, generated)
        
        if result:
            print(f"\nSimilarity: {result['similarity']:.2f}%")
            print(f"Different pixels: {result['different_pixels']:,}")
            print(f"\nView the comparison images to see the differences")
    else:
        print(f"Files not found:")
        print(f"  Original: {original} - {'EXISTS' if os.path.exists(original) else 'MISSING'}")
        print(f"  Generated: {generated} - {'EXISTS' if os.path.exists(generated) else 'MISSING'}")

if __name__ == "__main__":
    main()