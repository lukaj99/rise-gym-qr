#!/usr/bin/env python3
"""
Perfect QR Code Clone Generator
Creates exact replicas of Rise Gym QR codes
"""

import os
import base64
import re
import qrcode
import qrcode.image.svg
from PIL import Image
import io
import numpy as np
from pathlib import Path
import json
from datetime import datetime

class QRPerfectCloner:
    def __init__(self):
        # Based on analysis of actual QR codes
        self.qr_params = {
            'version': 1,  # QR Version 1 (21x21 modules)
            'error_correction': qrcode.constants.ERROR_CORRECT_L,
            'box_size': 40,  # Size of each module in pixels
            'border': 4,     # White border in modules (quiet zone)
            'image_size': (1200, 1200),
            'data_pattern': '9268{date}{time}'
        }
        
    def extract_reference_qr(self, svg_path):
        """Extract reference QR from SVG for comparison"""
        with open(svg_path, 'r') as f:
            svg_content = f.read()
        
        # Extract base64 PNG
        match = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)', svg_content)
        if match:
            png_data = base64.b64decode(match.group(1))
            img = Image.open(io.BytesIO(png_data))
            return img
        return None
    
    def analyze_reference_qr(self, img):
        """Analyze reference QR to determine exact parameters"""
        # Convert to numpy array
        img_array = np.array(img.convert('L'))
        
        # Find the QR code region (black modules)
        black_pixels = np.where(img_array == 0)
        
        if len(black_pixels[0]) > 0:
            # Find bounds
            min_y, max_y = black_pixels[0].min(), black_pixels[0].max()
            min_x, max_x = black_pixels[1].min(), black_pixels[1].max()
            
            # QR code dimensions
            qr_width = max_x - min_x + 1
            qr_height = max_y - min_y + 1
            
            # Find module size by analyzing finder pattern
            # Top-left finder pattern starts at the QR boundary
            # Finder pattern is 7 modules wide
            finder_width = 0
            for x in range(min_x, max_x):
                if img_array[min_y, x] == 0:  # Black pixel
                    finder_width += 1
                else:
                    break
            
            # Module size calculation
            # Finder pattern outer square is 7 modules
            # But we need to find the actual black square width
            # Scan for the first white pixel after black
            black_run = 0
            for x in range(min_x, min_x + finder_width):
                if img_array[min_y + 10, x] == 0:  # Sample inside finder
                    black_run += 1
                elif black_run > 0:
                    break
            
            # Estimate module size
            module_size = black_run // 7 if black_run > 0 else (qr_width // 21)
            
            # Calculate number of modules
            modules = qr_width // module_size if module_size > 0 else 21
            
            # QR version from modules count
            # Version 1 = 21 modules, Version 2 = 25, etc.
            version = (modules - 21) // 4 + 1
            
            return {
                'bounds': (min_x, min_y, max_x, max_y),
                'qr_size': (qr_width, qr_height),
                'module_size': module_size,
                'modules': modules,
                'version': version,
                'quiet_zone': min_x,
                'image_size': img.size
            }
        
        return None
    
    def generate_qr_data(self, timestamp):
        """Generate QR data for given timestamp"""
        # Extract date and time components
        year = timestamp[0:4]
        month = timestamp[4:6]
        day = timestamp[6:8]
        hour = int(timestamp[8:10])
        minute = timestamp[10:12]
        
        # Format: 9268 + MMDDYYYY + HHMMSS
        date_str = f"{month}{day}{year}"
        
        # Calculate time slot
        slot_hour = (hour // 2) * 2
        
        # Special suffix for 00:00-01:59
        if hour >= 0 and hour <= 1:
            suffix = "0001"
        else:
            suffix = "0000"
        
        time_str = f"{slot_hour:02d}{suffix}"
        
        # Combine
        qr_data = f"9268{date_str}{time_str}"
        
        return qr_data
    
    def generate_exact_qr(self, qr_data, reference_params=None):
        """Generate QR code with exact parameters"""
        # Use reference parameters if available
        if reference_params:
            version = reference_params.get('version', 1)
            module_size = reference_params.get('module_size', 40)
            border = reference_params.get('quiet_zone', 166) // module_size
        else:
            version = 1
            module_size = 40
            border = 4
        
        # Create QR code
        qr = qrcode.QRCode(
            version=version,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=module_size,
            border=border,
        )
        
        qr.add_data(qr_data)
        qr.make(fit=False)  # Don't auto-adjust version
        
        # Create image
        img = qr.make_image(fill_color='black', back_color='white')
        
        # Resize to exact dimensions if needed
        if reference_params and 'image_size' in reference_params:
            target_size = reference_params['image_size']
            if img.size != target_size:
                # Calculate scaling to maintain module alignment
                img = img.resize(target_size, Image.NEAREST)
        
        return img
    
    def generate_svg_with_embedded_png(self, img, output_path):
        """Generate SVG with embedded PNG like the originals"""
        # Convert PIL image to PNG bytes
        png_buffer = io.BytesIO()
        img.save(png_buffer, format='PNG')
        png_data = png_buffer.getvalue()
        
        # Encode to base64
        png_base64 = base64.b64encode(png_data).decode('utf-8')
        
        # Create SVG with embedded PNG
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 200 200">
    <image width="200" height="200" xlink:href="data:image/png;base64,{png_base64}"/>
</svg>'''
        
        # Save SVG
        with open(output_path, 'w') as f:
            f.write(svg_content)
        
        return output_path
    
    def clone_qr(self, reference_svg, output_path=None):
        """Create exact clone of reference QR"""
        print(f"Cloning QR from: {reference_svg}")
        
        # Extract reference
        ref_img = self.extract_reference_qr(reference_svg)
        if not ref_img:
            print("Failed to extract reference QR")
            return None
        
        # Analyze reference
        ref_params = self.analyze_reference_qr(ref_img)
        print(f"Reference parameters: {ref_params}")
        
        # Generate QR data from filename
        filename = Path(reference_svg).stem
        qr_data = self.generate_qr_data(filename)
        print(f"QR data: {qr_data}")
        
        # Generate exact QR
        new_img = self.generate_exact_qr(qr_data, ref_params)
        
        # Save as SVG with embedded PNG
        if not output_path:
            output_path = f"cloned_{filename}.svg"
        
        self.generate_svg_with_embedded_png(new_img, output_path)
        print(f"Cloned QR saved to: {output_path}")
        
        # Also save PNG for comparison
        png_path = output_path.replace('.svg', '.png')
        new_img.save(png_path)
        
        # Save reference PNG
        ref_png_path = output_path.replace('.svg', '_reference.png')
        ref_img.save(ref_png_path)
        
        return {
            'output_svg': output_path,
            'output_png': png_path,
            'reference_png': ref_png_path,
            'qr_data': qr_data,
            'parameters': ref_params
        }
    
    def compare_images(self, img1_path, img2_path):
        """Compare two images pixel by pixel"""
        img1 = Image.open(img1_path).convert('L')
        img2 = Image.open(img2_path).convert('L')
        
        # Resize to same size if needed
        if img1.size != img2.size:
            img2 = img2.resize(img1.size, Image.NEAREST)
        
        # Convert to arrays
        arr1 = np.array(img1)
        arr2 = np.array(img2)
        
        # Calculate difference
        diff = np.abs(arr1.astype(int) - arr2.astype(int))
        
        # Metrics
        identical_pixels = np.sum(diff == 0)
        total_pixels = diff.size
        similarity = identical_pixels / total_pixels * 100
        
        # Find different regions
        different_pixels = np.where(diff > 0)
        
        return {
            'identical': similarity == 100,
            'similarity_percent': similarity,
            'different_pixels': len(different_pixels[0]),
            'total_pixels': total_pixels
        }

def test_perfect_clone():
    """Test the perfect cloning system"""
    cloner = QRPerfectCloner()
    
    # Test with first QR code
    test_file = "real_qr_codes/202506010144.svg"
    
    if os.path.exists(test_file):
        print(f"\n{'='*60}")
        print("TESTING PERFECT QR CLONE")
        print(f"{'='*60}\n")
        
        # Clone the QR
        result = cloner.clone_qr(test_file, "test_clone.svg")
        
        if result:
            # Compare the images
            print(f"\nComparing cloned QR with original...")
            comparison = cloner.compare_images(
                result['reference_png'],
                result['output_png']
            )
            
            print(f"Similarity: {comparison['similarity_percent']:.2f}%")
            print(f"Different pixels: {comparison['different_pixels']} / {comparison['total_pixels']}")
            
            if comparison['identical']:
                print("✅ PERFECT CLONE - Images are identical!")
            else:
                print("❌ Not identical - needs parameter adjustment")
                
            # Generate a few more for testing
            print(f"\n{'='*60}")
            print("GENERATING QR CODES FOR DIFFERENT TIMES")
            print(f"{'='*60}\n")
            
            test_times = [
                "202506050800",  # 8 AM - should use 080000
                "202506050130",  # 1:30 AM - should use 000001
                "202506051400",  # 2 PM - should use 140000
                "202506052300",  # 11 PM - should use 220000
            ]
            
            for timestamp in test_times:
                qr_data = cloner.generate_qr_data(timestamp)
                print(f"{timestamp} -> {qr_data}")
                
                # Generate QR
                img = cloner.generate_exact_qr(qr_data, result['parameters'])
                output_file = f"generated_{timestamp}.svg"
                cloner.generate_svg_with_embedded_png(img, output_file)
                print(f"  Generated: {output_file}")

if __name__ == "__main__":
    test_perfect_clone()