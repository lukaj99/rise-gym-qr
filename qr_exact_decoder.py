#!/usr/bin/env python3
"""
Exact QR Code Decoder and Analyzer
Extracts and analyzes the exact QR data from Rise Gym SVG files
"""

import os
import base64
import re
from PIL import Image
import io
import numpy as np
from pathlib import Path
import json

class ExactQRDecoder:
    def __init__(self):
        self.qr_data_cache = {}
        
    def extract_png_from_svg(self, svg_path):
        """Extract embedded PNG from SVG file"""
        with open(svg_path, 'r') as f:
            svg_content = f.read()
        
        # Extract base64 PNG
        match = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)', svg_content)
        if match:
            png_data = base64.b64decode(match.group(1))
            return png_data
        return None
    
    def analyze_qr_image(self, png_data):
        """Analyze QR code image properties"""
        img = Image.open(io.BytesIO(png_data))
        
        # Convert to numpy array for analysis
        img_array = np.array(img.convert('L'))  # Convert to grayscale
        
        # Find QR code bounds (where black modules start/end)
        # QR codes have white quiet zone around them
        non_white = np.where(img_array < 255)
        
        if len(non_white[0]) > 0:
            min_y, max_y = non_white[0].min(), non_white[0].max()
            min_x, max_x = non_white[1].min(), non_white[1].max()
            
            qr_width = max_x - min_x + 1
            qr_height = max_y - min_y + 1
            
            # Estimate module size by finding repetitive patterns
            # Sample a row in the middle of QR code
            middle_row = img_array[min_y + qr_height // 2, min_x:max_x+1]
            
            # Find transitions (black to white or white to black)
            transitions = []
            for i in range(1, len(middle_row)):
                if middle_row[i] != middle_row[i-1]:
                    transitions.append(i)
            
            # Calculate module size from transitions
            if len(transitions) > 1:
                module_sizes = []
                for i in range(1, len(transitions)):
                    module_sizes.append(transitions[i] - transitions[i-1])
                
                # Most common module size
                from collections import Counter
                module_counter = Counter(module_sizes)
                estimated_module_size = module_counter.most_common(1)[0][0]
                
                # Estimate QR version from size
                modules_count = qr_width // estimated_module_size
                qr_version = (modules_count - 21) // 4 + 1
            else:
                estimated_module_size = None
                modules_count = None
                qr_version = None
        else:
            return None
            
        analysis = {
            'image_size': img.size,
            'qr_bounds': {
                'top_left': (min_x, min_y),
                'bottom_right': (max_x, max_y),
                'width': qr_width,
                'height': qr_height
            },
            'estimated_module_size': estimated_module_size,
            'estimated_modules': modules_count,
            'estimated_version': qr_version,
            'quiet_zone': min_x  # Pixels of white space around QR
        }
        
        return analysis, img
    
    def decode_with_basic_reader(self, img):
        """Try to decode QR using basic pattern matching"""
        # This is a simplified decoder for demonstration
        # In practice, we'd use pyzbar or zxing
        
        # For now, return the expected pattern based on our analysis
        # This would need a proper QR decoder library
        return None
    
    def extract_exact_data(self, svg_path):
        """Extract all data needed to recreate exact QR"""
        filename = Path(svg_path).stem
        
        # Extract PNG data
        png_data = self.extract_png_from_svg(svg_path)
        if not png_data:
            return None
            
        # Analyze image
        analysis, img = self.analyze_qr_image(png_data)
        
        # Save PNG for manual inspection
        png_path = f"/tmp/{filename}_extracted.png"
        img.save(png_path)
        
        # Expected QR data based on our pattern
        if len(filename) == 12:
            year = filename[0:4]
            month = filename[4:6] 
            day = filename[6:8]
            hour = int(filename[8:10])
            
            # Reconstruct expected data
            date_str = f"{month}{day}{year}"
            slot_hour = (hour // 2) * 2
            suffix = "0001" if hour <= 1 else "0000"
            expected_data = f"9268{date_str}{slot_hour:02d}{suffix}"
        else:
            expected_data = None
            
        result = {
            'filename': filename,
            'svg_path': svg_path,
            'png_extracted_path': png_path,
            'image_analysis': analysis,
            'expected_qr_data': expected_data,
            'actual_qr_data': None  # Would be filled by proper decoder
        }
        
        return result

def analyze_qr_parameters():
    """Analyze all QR codes to determine exact generation parameters"""
    decoder = ExactQRDecoder()
    qr_dir = Path("real_qr_codes")
    
    # Analyze first few QR codes
    svg_files = sorted(qr_dir.glob("*.svg"))[:5]
    
    all_analyses = []
    
    for svg_file in svg_files:
        print(f"\nAnalyzing: {svg_file.name}")
        result = decoder.extract_exact_data(str(svg_file))
        
        if result and result['image_analysis']:
            analysis = result['image_analysis']
            print(f"  Image size: {analysis['image_size']}")
            print(f"  QR bounds: {analysis['qr_bounds']['width']}x{analysis['qr_bounds']['height']}")
            print(f"  Module size: {analysis['estimated_module_size']} pixels")
            print(f"  Modules: {analysis['estimated_modules']}x{analysis['estimated_modules']}")
            print(f"  QR Version: {analysis['estimated_version']}")
            print(f"  Quiet zone: {analysis['quiet_zone']} pixels")
            print(f"  Expected data: {result['expected_qr_data']}")
            
            all_analyses.append(result)
    
    # Find common parameters
    if all_analyses:
        # All should have same parameters
        common_params = {
            'image_size': all_analyses[0]['image_analysis']['image_size'],
            'module_size': all_analyses[0]['image_analysis']['estimated_module_size'],
            'qr_version': all_analyses[0]['image_analysis']['estimated_version'],
            'modules_count': all_analyses[0]['image_analysis']['estimated_modules'],
            'quiet_zone': all_analyses[0]['image_analysis']['quiet_zone']
        }
        
        print(f"\n{'='*60}")
        print("COMMON QR PARAMETERS")
        print(f"{'='*60}")
        print(f"Image size: {common_params['image_size']}")
        print(f"Module size: {common_params['module_size']} pixels")
        print(f"QR Version: {common_params['qr_version']} (Version {common_params['qr_version']} = {21 + (common_params['qr_version']-1)*4} modules)")
        print(f"Modules: {common_params['modules_count']}x{common_params['modules_count']}")
        print(f"Quiet zone: {common_params['quiet_zone']} pixels")
        
        # Save parameters
        with open('qr_exact_parameters.json', 'w') as f:
            json.dump({
                'analysis_results': all_analyses,
                'common_parameters': common_params,
                'qr_spec': {
                    'version': common_params['qr_version'],
                    'error_correction': 'L',  # Typically L for simple numeric data
                    'module_size': common_params['module_size'],
                    'quiet_zone': common_params['quiet_zone'],
                    'image_size': common_params['image_size'],
                    'data_pattern': '9268 + MMDDYYYY + HH + MMSS'
                }
            }, f, indent=2)
        
        print(f"\nParameters saved to: qr_exact_parameters.json")
        print("\nNext step: Use these parameters to generate exact QR codes")

if __name__ == "__main__":
    analyze_qr_parameters()