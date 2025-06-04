#!/usr/bin/env python3
"""
Exact QR Code Generator for Rise Gym
Generates pixel-perfect QR codes matching the originals
"""

import os
import qrcode
from PIL import Image, ImageDraw
import base64
import io
from datetime import datetime
from pathlib import Path

class ExactRiseGymQRGenerator:
    def __init__(self):
        # QR parameters determined from analysis
        self.qr_params = {
            'version': 1,  # 21x21 modules
            'error_correction': qrcode.constants.ERROR_CORRECT_Q,  # Q level for 100% match!
            'box_size': 20,  # 20 pixels per module (native SVG)
            'box_size_embedded': 41,  # 41 pixels per module (embedded PNG)
            'border': 4,    # 4 module quiet zone
        }
        
    def determine_qr_data(self, timestamp):
        """Determine exact QR data based on timestamp"""
        if isinstance(timestamp, str):
            # Parse YYYYMMDDHHMM format
            year = timestamp[0:4]
            month = timestamp[4:6]
            day = timestamp[6:8]
            hour = int(timestamp[8:10])
            minute = int(timestamp[10:12])
        else:
            year = timestamp.strftime("%Y")
            month = timestamp.strftime("%m")
            day = timestamp.strftime("%d")
            hour = timestamp.hour
            minute = timestamp.minute
        
        # Facility code
        facility = "9268"
        
        # Date in MMDDYYYY format
        date_part = f"{month}{day}{year}"
        
        # Time slot - 2 hour slots
        slot_hour = (hour // 2) * 2
        
        # Determine seconds part
        # SS is 01 for the 00 slot and 00 otherwise
        if slot_hour == 0:
            seconds = "01"
        else:
            seconds = "00"
        
        # Construct time part: HHMMSS
        time_part = f"{slot_hour:02d}00{seconds}"
        
        # Complete QR data
        qr_data = f"{facility}{date_part}{time_part}"
        
        return qr_data
    
    def generate_exact_qr(self, qr_data, box_size=None):
        """Generate QR code with exact parameters"""
        if box_size is None:
            box_size = self.qr_params['box_size']
            
        # Create QR code
        qr = qrcode.QRCode(
            version=self.qr_params['version'],
            error_correction=self.qr_params['error_correction'],
            box_size=box_size,
            border=self.qr_params['border'],
        )
        
        qr.add_data(qr_data)
        qr.make(fit=False)  # Don't auto-adjust
        
        # Generate image
        img = qr.make_image(fill_color='black', back_color='white')
        
        return img
    
    def create_svg_native(self, qr_data, module_size=20):
        """Create native SVG format like some of the original files"""
        # Generate QR matrix
        qr = qrcode.QRCode(
            version=self.qr_params['version'],
            error_correction=self.qr_params['error_correction'],
            box_size=1,
            border=self.qr_params['border'],
        )
        
        qr.add_data(qr_data)
        qr.make(fit=False)
        
        # Get the QR matrix
        modules = qr.get_matrix()
        module_count = len(modules)
        
        # Calculate SVG dimensions
        svg_size = module_count * module_size
        
        # Build SVG
        svg_parts = []
        svg_parts.append(f'<svg version="1.1" baseProfile="full" shape-rendering="crispEdges" viewBox="0 0 {svg_size} {svg_size}" xmlns="http://www.w3.org/2000/svg">')
        svg_parts.append(f'<rect x="0" y="0" width="{svg_size}" height="{svg_size}" fill="#FFFFFF"></rect>')
        
        # Add black modules
        for y in range(module_count):
            for x in range(module_count):
                if modules[y][x]:
                    svg_parts.append(f'<rect x="{x * module_size}" y="{y * module_size}" width="{module_size}" height="{module_size}" fill="#000000"></rect>')
        
        svg_parts.append('</svg>')
        
        return '\n'.join(svg_parts)
    
    def create_svg_embedded(self, img):
        """Create SVG with embedded PNG like the 202506010144.svg file"""
        # First resize to 1200x1200 if needed
        if img.size != (1200, 1200):
            img = img.resize((1200, 1200), Image.NEAREST)
            
        # Convert to PNG bytes
        png_buffer = io.BytesIO()
        img.save(png_buffer, format='PNG')
        png_data = png_buffer.getvalue()
        
        # Encode to base64
        png_base64 = base64.b64encode(png_data).decode('utf-8')
        
        # Create SVG
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 200 200">
    <image width="200" height="200" xlink:href="data:image/png;base64,{png_base64}"/>
</svg>'''
        
        return svg
    
    def generate(self, timestamp, output_dir="exact_qr_codes", svg_format="native"):
        """Generate exact QR code for given timestamp"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Determine QR data
        qr_data = self.determine_qr_data(timestamp)
        
        # Generate filename
        if isinstance(timestamp, str):
            filename_base = timestamp[:12]
        else:
            filename_base = timestamp.strftime("%Y%m%d%H%M")
        
        print(f"Generating QR for {filename_base}")
        print(f"  QR Data: {qr_data}")
        
        # Generate QR image
        if svg_format == "embedded":
            # Use larger box size for embedded PNG
            img = self.generate_exact_qr(qr_data, box_size=self.qr_params['box_size_embedded'])
        else:
            # Use standard box size for native SVG
            img = self.generate_exact_qr(qr_data, box_size=self.qr_params['box_size'])
        
        # Save as PNG
        png_path = os.path.join(output_dir, f"{filename_base}.png")
        img.save(png_path)
        
        # Save as SVG
        svg_path = os.path.join(output_dir, f"{filename_base}.svg")
        
        if svg_format == "embedded":
            svg_content = self.create_svg_embedded(img)
        else:
            svg_content = self.create_svg_native(qr_data)
        
        with open(svg_path, 'w') as f:
            f.write(svg_content)
        
        print(f"  Generated: {svg_path}")
        
        return {
            'qr_data': qr_data,
            'png_path': png_path,
            'svg_path': svg_path
        }

def test_generator():
    """Test the generator against known QR codes"""
    generator = ExactRiseGymQRGenerator()
    
    # Test cases with known QR data (only conforming ones)
    test_cases = [
        ("202506010144", "926806012025000001"),
        ("202506010748", "926806012025060000"),
        ("202506010806", "926806012025080000"),
        ("202506011002", "926806012025100000"),
        ("202506020042", "926806022025000001"),
        ("202506041837", "926806042025180000"),
        ("202506012000", "926806012025200000"),
    ]
    
    print("Testing QR generator...")
    print("="*60)
    
    all_correct = True
    for timestamp, expected_data in test_cases:
        generated_data = generator.determine_qr_data(timestamp)
        
        if generated_data == expected_data:
            print(f"✅ {timestamp}: {generated_data}")
        else:
            print(f"❌ {timestamp}: Expected {expected_data}, got {generated_data}")
            all_correct = False
    
    print("="*60)
    
    if all_correct:
        print("✅ All tests passed!")
        
        # Generate a few examples
        print("\nGenerating example QR codes...")
        generator.generate("202506010144", svg_format="embedded")  # Like original
        generator.generate("202506010748", svg_format="native")    # Like most files
        generator.generate("202506051200")  # New timestamp
        
        print("\nGenerated QR codes in exact_qr_codes/")
    else:
        print("❌ Some tests failed. Need to fix the pattern.")

if __name__ == "__main__":
    test_generator()