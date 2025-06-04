#!/usr/bin/env python3
"""
Exact QR Code Matcher
Decodes actual QR data and generates pixel-perfect matches
"""

import os
import base64
import re
import qrcode
from PIL import Image
import io
import numpy as np
from pathlib import Path
from pyzbar.pyzbar import decode
import itertools

class ExactQRMatcher:
    def __init__(self):
        self.decoded_cache = {}
        
    def extract_and_decode_qr(self, svg_path):
        """Extract PNG from SVG and decode actual QR data"""
        # Extract PNG from SVG
        with open(svg_path, 'r') as f:
            svg_content = f.read()
        
        match = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)', svg_content)
        if not match:
            return None, None
            
        # Decode base64 to PNG
        png_data = base64.b64decode(match.group(1))
        img = Image.open(io.BytesIO(png_data))
        
        # Decode QR using pyzbar
        decoded_objects = decode(img)
        
        if decoded_objects:
            qr_data = decoded_objects[0].data.decode('utf-8')
            print(f"Decoded QR data: {qr_data}")
            return qr_data, img
        else:
            print("Failed to decode QR")
            return None, img
    
    def analyze_qr_structure(self, img):
        """Analyze QR code structure in detail"""
        # Convert to grayscale numpy array
        arr = np.array(img.convert('L'))
        
        # Find QR bounds
        black = np.where(arr < 128)  # Threshold for black
        if len(black[0]) == 0:
            return None
            
        min_y, max_y = black[0].min(), black[0].max()
        min_x, max_x = black[1].min(), black[1].max()
        
        qr_region = arr[min_y:max_y+1, min_x:max_x+1]
        qr_size = qr_region.shape[0]  # Should be square
        
        # Try different module counts to find the right fit
        # QR Version 1 = 21 modules, Version 2 = 25, etc.
        best_fit = None
        min_error = float('inf')
        
        for modules in range(21, 50, 4):  # Try different versions
            module_size = qr_size / modules
            if module_size != int(module_size):
                continue
                
            module_size = int(module_size)
            
            # Sample the grid at module centers
            error = 0
            samples = 0
            
            for i in range(modules):
                for j in range(modules):
                    y = i * module_size + module_size // 2
                    x = j * module_size + module_size // 2
                    
                    if y < qr_size and x < qr_size:
                        # Check if module is consistently black or white
                        module_region = qr_region[
                            i*module_size:(i+1)*module_size,
                            j*module_size:(j+1)*module_size
                        ]
                        
                        # Module should be mostly one color
                        mean_val = np.mean(module_region)
                        if mean_val < 128:  # Black module
                            error += np.sum(module_region > 128)
                        else:  # White module
                            error += np.sum(module_region < 128)
                        
                        samples += module_region.size
            
            if samples > 0:
                error_rate = error / samples
                if error_rate < min_error:
                    min_error = error_rate
                    best_fit = {
                        'modules': modules,
                        'module_size': module_size,
                        'error_rate': error_rate,
                        'version': (modules - 21) // 4 + 1
                    }
        
        # Add bounds info
        if best_fit:
            best_fit['bounds'] = (min_x, min_y, max_x, max_y)
            best_fit['qr_size'] = qr_size
            best_fit['quiet_zone'] = min_x
            best_fit['image_size'] = img.size
            
        return best_fit
    
    def find_exact_parameters(self, qr_data, reference_img):
        """Find exact parameters to generate matching QR"""
        # Analyze reference
        structure = self.analyze_qr_structure(reference_img)
        if not structure:
            print("Failed to analyze QR structure")
            return None
            
        print(f"QR Structure: Version {structure['version']}, {structure['modules']}x{structure['modules']} modules")
        
        # Try different parameter combinations
        best_match = None
        best_similarity = 0
        
        # Parameters to try
        versions = [structure['version']] if structure['version'] > 0 else [1, 2, 3]
        error_corrections = [
            qrcode.constants.ERROR_CORRECT_L,
            qrcode.constants.ERROR_CORRECT_M,
            qrcode.constants.ERROR_CORRECT_Q,
            qrcode.constants.ERROR_CORRECT_H
        ]
        
        # Fine-tune module size
        base_module_size = structure['module_size']
        module_sizes = [base_module_size - 1, base_module_size, base_module_size + 1]
        
        # Calculate border from quiet zone
        base_border = structure['quiet_zone'] // base_module_size
        borders = [base_border - 1, base_border, base_border + 1]
        borders = [b for b in borders if b >= 0]
        
        print(f"Testing combinations...")
        print(f"  Versions: {versions}")
        print(f"  Module sizes: {module_sizes}")
        print(f"  Borders: {borders}")
        
        for version, ec, module_size, border in itertools.product(
            versions, error_corrections, module_sizes, borders
        ):
            try:
                # Generate QR
                qr = qrcode.QRCode(
                    version=version,
                    error_correction=ec,
                    box_size=module_size,
                    border=border,
                )
                
                qr.add_data(qr_data)
                qr.make(fit=False)
                
                # Create image
                test_img = qr.make_image(fill_color='black', back_color='white')
                
                # Resize to match reference size
                if test_img.size != reference_img.size:
                    test_img = test_img.resize(reference_img.size, Image.NEAREST)
                
                # Compare
                similarity = self.compare_images(reference_img, test_img)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = {
                        'version': version,
                        'error_correction': ec,
                        'box_size': module_size,
                        'border': border,
                        'similarity': similarity,
                        'test_img': test_img
                    }
                    
                    print(f"  New best: {similarity:.2f}% (v={version}, ec={ec}, size={module_size}, border={border})")
                    
                    if similarity >= 99.9:  # Good enough
                        break
                        
            except Exception as e:
                continue
        
        return best_match
    
    def compare_images(self, img1, img2):
        """Compare two images and return similarity percentage"""
        # Convert to same size if needed
        if img1.size != img2.size:
            img2 = img2.resize(img1.size, Image.NEAREST)
        
        # Convert to arrays
        arr1 = np.array(img1.convert('L'))
        arr2 = np.array(img2.convert('L'))
        
        # Binary threshold
        arr1 = (arr1 < 128).astype(int)
        arr2 = (arr2 < 128).astype(int)
        
        # Calculate similarity
        matching = np.sum(arr1 == arr2)
        total = arr1.size
        
        return (matching / total) * 100
    
    def create_perfect_clone(self, svg_path, output_path=None):
        """Create perfect clone of QR code"""
        print(f"\n{'='*60}")
        print(f"Creating perfect clone of: {svg_path}")
        print(f"{'='*60}")
        
        # Decode QR
        qr_data, reference_img = self.extract_and_decode_qr(svg_path)
        if not qr_data:
            print("Failed to decode QR data")
            return None
        
        # Find exact parameters
        params = self.find_exact_parameters(qr_data, reference_img)
        if not params:
            print("Failed to find matching parameters")
            return None
        
        print(f"\nBest match parameters:")
        print(f"  Version: {params['version']}")
        print(f"  Error correction: {params['error_correction']}")
        print(f"  Module size: {params['box_size']}")
        print(f"  Border: {params['border']}")
        print(f"  Similarity: {params['similarity']:.2f}%")
        
        # Generate final QR
        qr = qrcode.QRCode(
            version=params['version'],
            error_correction=params['error_correction'],
            box_size=params['box_size'],
            border=params['border'],
        )
        
        qr.add_data(qr_data)
        qr.make(fit=False)
        
        final_img = qr.make_image(fill_color='black', back_color='white')
        
        # Resize if needed
        if final_img.size != reference_img.size:
            final_img = final_img.resize(reference_img.size, Image.NEAREST)
        
        # Save as SVG with embedded PNG
        if not output_path:
            output_path = f"perfect_clone_{Path(svg_path).stem}.svg"
        
        # Convert to PNG bytes
        png_buffer = io.BytesIO()
        final_img.save(png_buffer, format='PNG')
        png_data = png_buffer.getvalue()
        
        # Create SVG
        png_base64 = base64.b64encode(png_data).decode('utf-8')
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 200 200">
    <image width="200" height="200" xlink:href="data:image/png;base64,{png_base64}"/>
</svg>'''
        
        with open(output_path, 'w') as f:
            f.write(svg_content)
        
        print(f"\nPerfect clone saved to: {output_path}")
        
        # Also save comparison images
        final_img.save(output_path.replace('.svg', '.png'))
        reference_img.save(output_path.replace('.svg', '_reference.png'))
        
        # Create difference image
        diff = Image.new('RGB', reference_img.size)
        pixels = []
        ref_arr = np.array(reference_img.convert('L'))
        final_arr = np.array(final_img.convert('L'))
        
        for y in range(ref_arr.shape[0]):
            for x in range(ref_arr.shape[1]):
                if ref_arr[y, x] == final_arr[y, x]:
                    pixels.append((0, 0, 0))  # Black for matching
                else:
                    pixels.append((255, 0, 0))  # Red for different
        
        diff.putdata(pixels)
        diff.save(output_path.replace('.svg', '_diff.png'))
        
        return {
            'output': output_path,
            'qr_data': qr_data,
            'parameters': params,
            'similarity': params['similarity']
        }

def test_exact_matching():
    """Test exact QR matching"""
    matcher = ExactQRMatcher()
    
    # Test with first QR
    test_file = "real_qr_codes/202506010144.svg"
    
    if os.path.exists(test_file):
        result = matcher.create_perfect_clone(test_file)
        
        if result and result['similarity'] >= 99:
            print(f"\n✅ SUCCESS! Created perfect clone with {result['similarity']:.2f}% match")
            
            # Now generate QR for any timestamp
            print(f"\n{'='*60}")
            print("GENERATING QR FOR CUSTOM TIMESTAMP")
            print(f"{'='*60}")
            
            # Use the discovered parameters
            params = result['parameters']
            
            # Generate for current time
            from datetime import datetime
            now = datetime.now()
            
            # Format timestamp
            timestamp = now.strftime("%Y%m%d%H%M")
            
            # Generate QR data
            year = timestamp[0:4]
            month = timestamp[4:6]
            day = timestamp[6:8]
            hour = int(timestamp[8:10])
            
            # Calculate time slot
            slot_hour = (hour // 2) * 2
            suffix = "0001" if hour <= 1 else "0000"
            
            qr_data = f"9268{month}{day}{year}{slot_hour:02d}{suffix}"
            
            print(f"Current time: {now}")
            print(f"QR data: {qr_data}")
            
            # Generate QR
            qr = qrcode.QRCode(
                version=params['version'],
                error_correction=params['error_correction'],
                box_size=params['box_size'],
                border=params['border'],
            )
            
            qr.add_data(qr_data)
            qr.make(fit=False)
            
            img = qr.make_image(fill_color='black', back_color='white')
            img = img.resize((1200, 1200), Image.NEAREST)
            
            output = f"qr_current_time_{timestamp}.png"
            img.save(output)
            print(f"Generated: {output}")

if __name__ == "__main__":
    test_exact_matching()