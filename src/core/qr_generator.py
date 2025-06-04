#!/usr/bin/env python3
"""
Rise Gym QR Code Generator
Generates pixel-perfect QR codes matching Rise Gym's format

Pattern: 9268 + MMDDYYYY + HHMMSS
- 9268: Facility code
- MMDDYYYY: Date in US format
- HH: 2-hour time slot (00, 02, 04, ..., 22)
- MM: Always "00"
- SS: "01" for 00:00-01:59 slot, "00" for all other slots
"""

import os
import sys
import qrcode
from PIL import Image
import base64
import io
from datetime import datetime, timedelta
import pytz
from pathlib import Path
import json


class RiseGymQRGenerator:
    """Generate QR codes matching Rise Gym's exact format"""
    
    def __init__(self):
        # QR parameters determined from reverse engineering
        self.qr_params = {
            'version': 1,  # 21x21 modules
            'error_correction': qrcode.constants.ERROR_CORRECT_Q,  # Q level for 100% match
            'box_size': 20,  # 20 pixels per module (native SVG)
            'box_size_embedded': 41,  # 41 pixels per module (embedded PNG)
            'border': 4,    # 4 module quiet zone
        }
        
        # Time zone for Rise Gym (Eastern Time)
        self.timezone = pytz.timezone('America/New_York')
        
    def generate_qr_data(self, dt):
        """Generate QR data string for given datetime"""
        # Ensure datetime is in correct timezone
        if dt.tzinfo is None:
            dt = self.timezone.localize(dt)
        else:
            dt = dt.astimezone(self.timezone)
            
        # Components
        facility = "9268"
        date_str = dt.strftime("%m%d%Y")
        
        # Time slot - 2 hour slots
        slot_hour = (dt.hour // 2) * 2
        
        # Special rule: SS is 01 for 00:00-01:59 slot, 00 otherwise
        if slot_hour == 0:
            seconds = "01"
        else:
            seconds = "00"
            
        time_str = f"{slot_hour:02d}00{seconds}"
        
        return f"{facility}{date_str}{time_str}"
    
    def generate_qr_image(self, data, format='native'):
        """Generate QR code image
        
        Args:
            data: QR data string
            format: 'native' for SVG-style, 'embedded' for PNG-style
            
        Returns:
            PIL Image object
        """
        qr = qrcode.QRCode(
            version=self.qr_params['version'],
            error_correction=self.qr_params['error_correction'],
            box_size=self.qr_params['box_size'] if format == 'native' else self.qr_params['box_size_embedded'],
            border=self.qr_params['border'],
        )
        
        qr.add_data(data)
        qr.make(fit=False)  # Don't auto-fit since we know version=1
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        return img
    
    def generate_svg_native(self, data):
        """Generate native SVG format (rectangles)"""
        qr = qrcode.QRCode(
            version=self.qr_params['version'],
            error_correction=self.qr_params['error_correction'],
            box_size=self.qr_params['box_size'],
            border=self.qr_params['border'],
        )
        
        qr.add_data(data)
        qr.make(fit=False)
        
        # Generate SVG manually to match exact format
        modules = qr.get_matrix()
        module_count = len(modules)
        box_size = self.qr_params['box_size']
        border = self.qr_params['border']
        width = (module_count + border * 2) * box_size
        
        svg_parts = []
        svg_parts.append(f'<svg version="1.1" baseProfile="full" shape-rendering="crispEdges" viewBox="0 0 {width} {width}" xmlns="http://www.w3.org/2000/svg">')
        svg_parts.append(f'<rect x="0" y="0" width="{width}" height="{width}" fill="#FFFFFF"></rect>')
        
        # Draw modules
        for row in range(module_count):
            for col in range(module_count):
                if modules[row][col]:
                    x = (col + border) * box_size
                    y = (row + border) * box_size
                    svg_parts.append(f'<rect x="{x}" y="{y}" width="{box_size}" height="{box_size}" fill="#000000"></rect>')
        
        svg_parts.append('</svg>')
        
        return '\n'.join(svg_parts)
    
    def generate_svg_embedded(self, data):
        """Generate embedded PNG in SVG format"""
        # Generate PNG image
        img = self.generate_qr_image(data, format='embedded')
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        png_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Create SVG with embedded image
        width = img.size[0]
        svg = f'''<svg version="1.1" baseProfile="full" viewBox="0 0 {width} {width}" xmlns="http://www.w3.org/2000/svg">
<image x="0" y="0" width="{width}" height="{width}" href="data:image/png;base64,{png_data}"/>
</svg>'''
        
        return svg
    
    def generate_for_datetime(self, dt, output_format='image'):
        """Generate QR code for specific datetime
        
        Args:
            dt: datetime object
            output_format: 'image', 'svg_native', or 'svg_embedded'
            
        Returns:
            PIL Image or SVG string depending on format
        """
        data = self.generate_qr_data(dt)
        
        if output_format == 'image':
            return self.generate_qr_image(data)
        elif output_format == 'svg_native':
            return self.generate_svg_native(data)
        elif output_format == 'svg_embedded':
            return self.generate_svg_embedded(data)
        else:
            raise ValueError(f"Unknown output format: {output_format}")
    
    def generate_current(self, output_format='image'):
        """Generate QR code for current time"""
        return self.generate_for_datetime(datetime.now(self.timezone), output_format)
    
    def save_qr_code(self, dt, filepath, format='svg_native'):
        """Save QR code to file
        
        Args:
            dt: datetime object
            filepath: path to save file
            format: 'png', 'svg_native', or 'svg_embedded'
        """
        if format == 'png':
            img = self.generate_for_datetime(dt, 'image')
            img.save(filepath)
        elif format in ['svg_native', 'svg_embedded']:
            svg_content = self.generate_for_datetime(dt, format)
            with open(filepath, 'w') as f:
                f.write(svg_content)
        else:
            raise ValueError(f"Unknown format: {format}")


def main():
    """Command line interface"""
    generator = RiseGymQRGenerator()
    
    if len(sys.argv) > 1:
        # Parse datetime argument
        if sys.argv[1] == 'now':
            dt = datetime.now(generator.timezone)
        else:
            try:
                # Try parsing as YYYYMMDDHHMM
                dt_str = sys.argv[1]
                dt = datetime.strptime(dt_str, "%Y%m%d%H%M")
                dt = generator.timezone.localize(dt)
            except ValueError:
                print("Usage: python qr_generator.py [now|YYYYMMDDHHMM]")
                print("Example: python qr_generator.py 202506051030")
                sys.exit(1)
    else:
        dt = datetime.now(generator.timezone)
    
    # Generate QR data
    qr_data = generator.generate_qr_data(dt)
    print(f"DateTime: {dt}")
    print(f"QR Data: {qr_data}")
    print(f"Time Slot: {dt.strftime('%H:00')}-{((dt.hour // 2) * 2 + 2) % 24:02d}:00")
    
    # Save in multiple formats
    timestamp = dt.strftime("%Y%m%d%H%M")
    
    # PNG format
    generator.save_qr_code(dt, f"qr_{timestamp}.png", 'png')
    print(f"Saved: qr_{timestamp}.png")
    
    # SVG native format
    generator.save_qr_code(dt, f"qr_{timestamp}_native.svg", 'svg_native')
    print(f"Saved: qr_{timestamp}_native.svg")
    
    # SVG embedded format
    generator.save_qr_code(dt, f"qr_{timestamp}_embedded.svg", 'svg_embedded')
    print(f"Saved: qr_{timestamp}_embedded.svg")


if __name__ == "__main__":
    main()