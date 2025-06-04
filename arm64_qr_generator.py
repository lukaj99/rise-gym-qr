#!/usr/bin/env python3
"""
ARM64 QR Generator for Rise Gym QR Codes
Uses master_pattern.json to generate QR codes without Selenium
Designed specifically for ARM64 devices where ChromeDriver may not be available
"""

import json
import os
import qrcode
from datetime import datetime
from PIL import Image
import requests
from io import BytesIO

class ARM64QRGenerator:
    def __init__(self, pattern_file="master_pattern.json"):
        self.pattern_file = pattern_file
        self.master_pattern = None
        self.load_master_pattern()
        
    def load_master_pattern(self):
        """Load master pattern from JSON file"""
        try:
            if not os.path.exists(self.pattern_file):
                raise FileNotFoundError(f"Master pattern file not found: {self.pattern_file}")
            
            with open(self.pattern_file, 'r') as f:
                self.master_pattern = json.load(f)
            
            print(f"✅ Loaded master pattern from {self.pattern_file}")
            print(f"   Version: {self.master_pattern.get('version', 'unknown')}")
            print(f"   Extracted: {self.master_pattern.get('extracted_date', 'unknown')}")
            print(f"   Encoding: {self.master_pattern.get('time_encoding', {}).get('type', 'unknown')}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading master pattern: {e}")
            self.master_pattern = None
            return False
    
    def calculate_time_component(self, timestamp=None):
        """Calculate time component based on extracted pattern"""
        if not self.master_pattern:
            raise ValueError("Master pattern not loaded")
        
        if timestamp is None:
            timestamp = datetime.now()
        
        encoding_type = self.master_pattern.get('time_encoding', {}).get('type', 'unknown')
        
        print(f"🕐 Calculating time component for {timestamp.strftime('%H:%M:%S')}")
        print(f"   Encoding type: {encoding_type}")
        
        if encoding_type == "2hour_slots":
            # Calculate 2-hour slot (0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22)
            slot_hour = (timestamp.hour // 2) * 2
            
            # Determine suffix based on time slot
            if timestamp.hour >= 0 and timestamp.hour <= 1:
                suffix = "0001"  # 00:00-01:59 uses 0001
            else:
                suffix = "0000"  # All other slots use 0000
                
            time_component = f"{slot_hour:02d}{suffix}"
            
        else:
            # Fallback to hour-based encoding
            time_component = f"{timestamp.hour:02d}0000"
        
        print(f"   Generated time component: {time_component}")
        return time_component
    
    def generate_qr_data(self, timestamp=None, custom_date=None):
        """Generate QR data string based on master pattern"""
        if not self.master_pattern:
            raise ValueError("Master pattern not loaded")
        
        if timestamp is None:
            timestamp = datetime.now()
        
        # Get structure components
        structure = self.master_pattern.get('qr_structure', {})
        facility = structure.get('facility', {}).get('value', '9268')
        
        # Generate date component
        if custom_date:
            date_str = custom_date
        else:
            date_format = self.master_pattern.get('generation_rules', {}).get('date_format', 'MMDDYYYY')
            if date_format == 'MMDDYYYY':
                date_str = timestamp.strftime("%m%d%Y")
            else:
                date_str = timestamp.strftime("%m%d%Y")  # fallback
        
        # Calculate time component
        time_component = self.calculate_time_component(timestamp)
        
        # Combine components (structure: 9268 + 8-digit date + 6-digit time)
        qr_data = f"{facility}{date_str}{time_component}"
        
        print(f"🔢 Generated QR data: {qr_data}")
        print(f"   Facility: {facility}")
        print(f"   Date: {date_str}")
        print(f"   Time: {time_component}")
        
        # Validate against pattern
        validation_pattern = self.master_pattern.get('generation_rules', {}).get('validation_pattern')
        if validation_pattern:
            import re
            if not re.match(validation_pattern, qr_data):
                print(f"⚠️  Generated QR data doesn't match validation pattern: {validation_pattern}")
        
        return qr_data
    
    def create_qr_image(self, qr_data, size=580, format='PNG'):
        """Create QR code image with exact Rise Gym specifications"""
        try:
            # Based on reverse engineering: 29x29 modules, Version 11
            qr = qrcode.QRCode(
                version=11,  # Force Version 11 (29x29 modules)
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=20,  # 20 pixels per module
                border=4,     # 4 module border
            )
            
            qr.add_data(qr_data)
            qr.make(fit=False)  # Don't auto-adjust version
            
            # Create image
            img = qr.make_image(fill_color='black', back_color='white')
            
            # Resize to exact dimensions if needed
            if img.size != (size, size):
                img = img.resize((size, size), Image.NEAREST)
            
            print(f"📱 Created QR image:")
            print(f"   Size: {img.size}")
            print(f"   Version: {qr.version}")
            print(f"   Modules: {qr.modules_count}x{qr.modules_count}")
            
            return img
            
        except Exception as e:
            print(f"❌ Error creating QR image: {e}")
            return None
    
    def save_qr_code(self, qr_data=None, filename=None, timestamp=None, format='SVG'):
        """Generate and save QR code to real_qr_codes folder"""
        try:
            if qr_data is None:
                qr_data = self.generate_qr_data(timestamp)
            
            current_time = timestamp or datetime.now()
            
            # Always save SVG to real_qr_codes folder with timestamp filename
            os.makedirs("real_qr_codes", exist_ok=True)
            svg_filename = f"real_qr_codes/{current_time.strftime('%Y%m%d%H%M')}.svg"
            
            # Save as SVG
            if self.save_as_svg(qr_data, svg_filename):
                print(f"💾 QR code saved: {svg_filename}")
                
                # Update database
                self.update_database()
                
                return svg_filename
            else:
                return False
            
        except Exception as e:
            print(f"❌ Error saving QR code: {e}")
            return False
    
    def save_as_svg(self, qr_data, filename):
        """Save QR code as SVG (Rise Gym compatible format)"""
        try:
            import qrcode.image.svg
            
            # Create SVG QR code
            factory = qrcode.image.svg.SvgPathImage
            qr = qrcode.QRCode(
                version=11,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=20,
                border=4,
                image_factory=factory
            )
            
            qr.add_data(qr_data)
            qr.make(fit=False)
            
            img = qr.make_image()
            
            # Save SVG
            with open(filename, 'wb') as f:
                img.save(f)
            
            print(f"📄 SVG saved: {filename}")
            return True
            
        except Exception as e:
            print(f"⚠️  SVG save failed: {e}")
            return False
    
    def update_database(self):
        """Update the QR code database after generating a new file"""
        try:
            import subprocess
            result = subprocess.run(['python', 'qr_database.py'], 
                                  capture_output=True, text=True, cwd='.')
            if result.returncode == 0:
                print(f"📊 Database updated successfully")
            else:
                print(f"⚠️  Database update warning: {result.stderr}")
        except Exception as e:
            print(f"⚠️  Could not update database: {e}")
    
    def validate_qr_data(self, qr_data):
        """Validate generated QR data against known patterns"""
        if not self.master_pattern:
            return False
        
        validation_rules = []
        
        # Check length
        expected_length = 18
        if len(qr_data) != expected_length:
            validation_rules.append(f"Length mismatch: expected {expected_length}, got {len(qr_data)}")
        
        # Check facility code
        expected_facility = self.master_pattern.get('qr_structure', {}).get('facility', {}).get('value', '9268')
        if not qr_data.startswith(expected_facility):
            validation_rules.append(f"Facility code mismatch: expected '{expected_facility}', got '{qr_data[:4]}'")
        
        # Check date format (positions 4-12)
        date_part = qr_data[4:12]
        try:
            datetime.strptime(date_part, "%m%d%Y")
        except ValueError:
            validation_rules.append(f"Invalid date format in position 4-12: '{date_part}'")
        
        # Check overall pattern
        validation_pattern = self.master_pattern.get('generation_rules', {}).get('validation_pattern')
        if validation_pattern:
            import re
            if not re.match(validation_pattern, qr_data):
                validation_rules.append(f"Pattern validation failed: {validation_pattern}")
        
        if validation_rules:
            print(f"⚠️  Validation issues:")
            for rule in validation_rules:
                print(f"     - {rule}")
            return False
        
        print(f"✅ QR data validation passed")
        return True
    
    def generate_for_time_range(self, start_time, end_time, interval_minutes=10, output_dir="qr_range"):
        """Generate QR codes for a time range"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            current_time = start_time
            generated_files = []
            
            print(f"📅 Generating QR codes from {start_time} to {end_time}")
            print(f"   Interval: {interval_minutes} minutes")
            print(f"   Output dir: {output_dir}")
            
            while current_time <= end_time:
                qr_data = self.generate_qr_data(current_time)
                
                if self.validate_qr_data(qr_data):
                    filename = os.path.join(output_dir, f"qr_{current_time.strftime('%H%M')}.png")
                    saved_file = self.save_qr_code(qr_data, filename, current_time)
                    
                    if saved_file:
                        generated_files.append(saved_file)
                
                # Advance time
                current_time += timedelta(minutes=interval_minutes)
            
            print(f"✅ Generated {len(generated_files)} QR codes in {output_dir}")
            return generated_files
            
        except Exception as e:
            print(f"❌ Error generating time range: {e}")
            return []
    
    def get_current_qr(self):
        """Get current QR code for immediate use"""
        print(f"🚀 Generating current QR code...")
        
        current_time = datetime.now()
        qr_data = self.generate_qr_data(current_time)
        
        if self.validate_qr_data(qr_data):
            filename = self.save_qr_code(qr_data, timestamp=current_time)
            
            if filename:
                print(f"✅ Current QR generated: {filename}")
                return {
                    "qr_data": qr_data,
                    "filename": filename,
                    "timestamp": current_time.isoformat(),
                    "valid_until": "estimated based on pattern"
                }
        
        return None

def main():
    """Main function for command-line usage"""
    import argparse
    from datetime import timedelta
    
    parser = argparse.ArgumentParser(description='ARM64 QR Generator for Rise Gym')
    parser.add_argument('--pattern-file', '-p', default='master_pattern.json',
                       help='Master pattern JSON file (default: master_pattern.json)')
    parser.add_argument('--output', '-o', help='Output filename')
    parser.add_argument('--current', action='store_true',
                       help='Generate QR for current time')
    parser.add_argument('--time-range', action='store_true',
                       help='Generate QRs for time range (use with --start-time and --end-time)')
    parser.add_argument('--start-time', help='Start time (HH:MM format)')
    parser.add_argument('--end-time', help='End time (HH:MM format)')
    parser.add_argument('--interval', type=int, default=10,
                       help='Interval in minutes for time range generation (default: 10)')
    parser.add_argument('--validate-only', help='Validate QR data string without generating image')
    parser.add_argument('--format', choices=['PNG', 'SVG'], default='PNG',
                       help='Output format (default: PNG)')
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = ARM64QRGenerator(args.pattern_file)
    
    if not generator.master_pattern:
        print("❌ Cannot proceed without master pattern")
        return False
    
    if args.validate_only:
        # Validate QR data string
        result = generator.validate_qr_data(args.validate_only)
        print(f"Validation result: {'✅ VALID' if result else '❌ INVALID'}")
        return result
    
    elif args.current:
        # Generate current QR
        result = generator.get_current_qr()
        return result is not None
    
    elif args.time_range:
        # Generate time range
        if not args.start_time or not args.end_time:
            print("❌ --start-time and --end-time required for time range generation")
            return False
        
        try:
            today = datetime.now().date()
            start_time = datetime.combine(today, datetime.strptime(args.start_time, "%H:%M").time())
            end_time = datetime.combine(today, datetime.strptime(args.end_time, "%H:%M").time())
            
            if end_time <= start_time:
                end_time += timedelta(days=1)  # Next day
            
            files = generator.generate_for_time_range(start_time, end_time, args.interval)
            return len(files) > 0
            
        except ValueError as e:
            print(f"❌ Invalid time format: {e}")
            return False
    
    else:
        # Generate single QR for current time
        result = generator.get_current_qr()
        return result is not None

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)