#!/usr/bin/env python3
"""
Perfect QR Code Generator for Rise Gym
Creates exact visual matches based on analysis of original QR codes
"""

import os
import base64
import qrcode
import qrcode.image.svg
from PIL import Image
import io
import numpy as np
from pathlib import Path
from datetime import datetime
import json
import re

class RiseGymQRGenerator:
    def __init__(self):
        # These parameters were determined through analysis
        # Rise Gym uses QR Version 1 (21x21 modules)
        self.qr_params = {
            'version': 1,
            'error_correction': qrcode.constants.ERROR_CORRECT_L,
            'box_size': 41,  # Pixels per module (868 QR size / 21 modules ≈ 41)
            'border': 4,     # Standard 4-module quiet zone
            'facility_code': '9268',
            'image_size': (1200, 1200)
        }
        
    def generate_qr_data(self, timestamp=None):
        """Generate QR data string for given timestamp"""
        if timestamp is None:
            timestamp = datetime.now()
        elif isinstance(timestamp, str):
            # Parse string timestamp YYYYMMDDHHMM
            timestamp = datetime.strptime(timestamp[:12], "%Y%m%d%H%M")
        
        # Extract components
        month = timestamp.strftime("%m")
        day = timestamp.strftime("%d")
        year = timestamp.strftime("%Y")
        hour = timestamp.hour
        
        # Format date as MMDDYYYY
        date_str = f"{month}{day}{year}"
        
        # Calculate 2-hour time slot
        slot_hour = (hour // 2) * 2
        
        # Determine suffix
        if 0 <= hour <= 1:
            suffix = "0001"
        else:
            suffix = "0000"
        
        # Combine: 9268 + MMDDYYYY + HH + MMSS
        qr_data = f"{self.qr_params['facility_code']}{date_str}{slot_hour:02d}{suffix}"
        
        return qr_data, {
            'timestamp': timestamp.isoformat(),
            'date': date_str,
            'slot_hour': slot_hour,
            'suffix': suffix,
            'slot_range': f"{slot_hour:02d}:00-{slot_hour+1:02d}:59"
        }
    
    def generate_exact_qr_image(self, qr_data):
        """Generate QR image with exact Rise Gym parameters"""
        # Create QR code
        qr = qrcode.QRCode(
            version=self.qr_params['version'],
            error_correction=self.qr_params['error_correction'],
            box_size=self.qr_params['box_size'],
            border=self.qr_params['border'],
        )
        
        qr.add_data(qr_data)
        qr.make(fit=False)  # Important: don't auto-adjust version
        
        # Generate image
        img = qr.make_image(fill_color='black', back_color='white')
        
        # The generated image should be 1066x1066 pixels
        # (21 modules + 8 border) * 41 pixels = 1189 pixels
        # But Rise Gym uses 1200x1200, so we need to resize
        
        # First, let's check the actual size
        actual_size = img.size[0]
        target_size = self.qr_params['image_size'][0]
        
        if actual_size != target_size:
            # Calculate the exact scaling needed
            # We want to maintain module boundaries
            modules_with_border = 21 + (self.qr_params['border'] * 2)
            pixels_per_module = target_size / modules_with_border
            
            # Recreate with adjusted box_size
            adjusted_box_size = int(pixels_per_module)
            
            qr = qrcode.QRCode(
                version=self.qr_params['version'],
                error_correction=self.qr_params['error_correction'],
                box_size=adjusted_box_size,
                border=self.qr_params['border'],
            )
            
            qr.add_data(qr_data)
            qr.make(fit=False)
            
            img = qr.make_image(fill_color='black', back_color='white')
            
            # Final resize if still needed
            if img.size != self.qr_params['image_size']:
                img = img.resize(self.qr_params['image_size'], Image.NEAREST)
        
        return img
    
    def create_svg_with_embedded_png(self, img):
        """Create SVG with embedded PNG matching Rise Gym format"""
        # Convert to PNG bytes
        png_buffer = io.BytesIO()
        img.save(png_buffer, format='PNG', optimize=False, compress_level=0)
        png_data = png_buffer.getvalue()
        
        # Encode to base64
        png_base64 = base64.b64encode(png_data).decode('utf-8')
        
        # Create SVG exactly like Rise Gym
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 200 200">
    <image width="200" height="200" xlink:href="data:image/png;base64,{png_base64}"/>
</svg>'''
        
        return svg_content
    
    def generate_qr(self, timestamp=None, output_dir="generated_qr_codes"):
        """Generate Rise Gym QR code for given timestamp"""
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate QR data
        qr_data, metadata = self.generate_qr_data(timestamp)
        
        print(f"Generating QR code:")
        print(f"  Timestamp: {metadata['timestamp']}")
        print(f"  QR Data: {qr_data}")
        print(f"  Time Slot: {metadata['slot_range']}")
        
        # Generate QR image
        img = self.generate_exact_qr_image(qr_data)
        
        # Create filename
        if isinstance(timestamp, datetime):
            filename_base = timestamp.strftime("%Y%m%d%H%M")
        elif isinstance(timestamp, str):
            filename_base = timestamp[:12]
        else:
            filename_base = datetime.now().strftime("%Y%m%d%H%M")
        
        # Save as SVG
        svg_path = os.path.join(output_dir, f"{filename_base}.svg")
        svg_content = self.create_svg_with_embedded_png(img)
        
        with open(svg_path, 'w') as f:
            f.write(svg_content)
        
        # Also save PNG for reference
        png_path = os.path.join(output_dir, f"{filename_base}.png")
        img.save(png_path)
        
        print(f"  Generated: {svg_path}")
        print(f"  PNG copy: {png_path}")
        
        return {
            'svg_path': svg_path,
            'png_path': png_path,
            'qr_data': qr_data,
            'metadata': metadata
        }
    
    def validate_against_original(self, generated_path, original_path):
        """Compare generated QR with original"""
        # Extract PNGs from both SVGs
        def extract_png(svg_path):
            with open(svg_path, 'r') as f:
                content = f.read()
            match = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)', content)
            if match:
                return Image.open(io.BytesIO(base64.b64decode(match.group(1))))
            return None
        
        gen_img = extract_png(generated_path) if generated_path.endswith('.svg') else Image.open(generated_path)
        orig_img = extract_png(original_path) if original_path.endswith('.svg') else Image.open(original_path)
        
        if not gen_img or not orig_img:
            return None
        
        # Convert to same size
        if gen_img.size != orig_img.size:
            gen_img = gen_img.resize(orig_img.size, Image.NEAREST)
        
        # Compare pixels
        gen_arr = np.array(gen_img.convert('L'))
        orig_arr = np.array(orig_img.convert('L'))
        
        # Binary threshold
        gen_bin = (gen_arr < 128).astype(int)
        orig_bin = (orig_arr < 128).astype(int)
        
        # Calculate similarity
        matching = np.sum(gen_bin == orig_bin)
        total = gen_bin.size
        similarity = (matching / total) * 100
        
        # Find differences
        diff_pixels = np.sum(gen_bin != orig_bin)
        
        return {
            'similarity': similarity,
            'matching_pixels': matching,
            'total_pixels': total,
            'different_pixels': diff_pixels,
            'identical': similarity > 99.9
        }

def test_generator():
    """Test the QR generator"""
    generator = RiseGymQRGenerator()
    
    print("="*60)
    print("RISE GYM QR CODE GENERATOR TEST")
    print("="*60)
    
    # Test 1: Generate current time QR
    print("\n1. Generating QR for current time:")
    result = generator.generate_qr()
    
    # Test 2: Generate specific times
    print("\n2. Generating QRs for specific time slots:")
    test_times = [
        ("202506070000", "Midnight slot (should use 0001)"),
        ("202506070130", "1:30 AM (should use 0001)"),
        ("202506070800", "8:00 AM (should use 0000)"),
        ("202506071400", "2:00 PM (should use 0000)"),
        ("202506072300", "11:00 PM (should use 0000)")
    ]
    
    for timestamp, description in test_times:
        print(f"\n  {description}")
        result = generator.generate_qr(timestamp)
    
    # Test 3: Validate against original if available
    print("\n3. Validating against original QR codes:")
    original_qr = "real_qr_codes/202506010144.svg"
    
    if os.path.exists(original_qr):
        # Generate matching QR
        test_result = generator.generate_qr("202506010144")
        
        # Validate
        validation = generator.validate_against_original(
            test_result['svg_path'],
            original_qr
        )
        
        if validation:
            print(f"\n  Similarity: {validation['similarity']:.2f}%")
            print(f"  Different pixels: {validation['different_pixels']} / {validation['total_pixels']}")
            
            if validation['identical']:
                print("  ✅ PERFECT MATCH!")
            else:
                print("  ❌ Not identical - may need parameter adjustment")
    
    print("\n" + "="*60)
    print("QR codes generated in: generated_qr_codes/")
    print("="*60)

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Rise Gym QR Code Generator')
    parser.add_argument('--time', '-t', help='Timestamp (YYYYMMDDHHMM) or "now"')
    parser.add_argument('--output', '-o', help='Output directory', default='generated_qr_codes')
    parser.add_argument('--test', action='store_true', help='Run test suite')
    
    args = parser.parse_args()
    
    if args.test:
        test_generator()
    else:
        generator = RiseGymQRGenerator()
        
        if args.time == 'now' or not args.time:
            timestamp = None
        else:
            timestamp = args.time
        
        result = generator.generate_qr(timestamp, args.output)
        
        print(f"\n✅ QR Code generated successfully!")
        print(f"QR Data: {result['qr_data']}")
        print(f"Valid for: {result['metadata']['slot_range']}")

if __name__ == "__main__":
    main()