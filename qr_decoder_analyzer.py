#!/usr/bin/env python3
"""
QR Code Decoder and Analyzer
Decodes QR codes and performs cryptographic analysis to crack encoded data
"""

import os
import sys
import json
import base64
import binascii
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re
from collections import Counter
import itertools

# For QR decoding
try:
    from PIL import Image
    from pyzbar.pyzbar import decode as pyzbar_decode
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False
    print("Warning: pyzbar not available. Install with: pip install pyzbar pillow")

# For SVG to PNG conversion
try:
    import cairosvg
    CAIRO_AVAILABLE = True
except ImportError:
    CAIRO_AVAILABLE = False
    print("Warning: cairosvg not available. Install with: pip install cairosvg")

class QRDecoder:
    """Handles QR code decoding from various formats"""
    
    def __init__(self):
        self.decoded_cache = {}
        
    def decode_svg(self, svg_path: str) -> Optional[str]:
        """Decode QR code from SVG file"""
        if not os.path.exists(svg_path):
            print(f"Error: File not found: {svg_path}")
            return None
            
        # Check if SVG contains base64 PNG data
        with open(svg_path, 'r') as f:
            svg_content = f.read()
            
        # Extract base64 PNG from SVG
        base64_match = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)', svg_content)
        if base64_match:
            try:
                # Decode base64 to PNG
                png_data = base64.b64decode(base64_match.group(1))
                
                # Save temporary PNG
                temp_png = "/tmp/temp_qr.png"
                with open(temp_png, 'wb') as f:
                    f.write(png_data)
                
                # Decode QR from PNG
                result = self.decode_png(temp_png)
                
                # Cleanup
                if os.path.exists(temp_png):
                    os.remove(temp_png)
                    
                return result
                
            except Exception as e:
                print(f"Error decoding base64 PNG: {e}")
                return None
        
        # If no embedded PNG, try converting SVG to PNG using cairosvg
        if CAIRO_AVAILABLE:
            try:
                temp_png = "/tmp/temp_qr_svg.png"
                cairosvg.svg2png(url=svg_path, write_to=temp_png)
                result = self.decode_png(temp_png)
                
                if os.path.exists(temp_png):
                    os.remove(temp_png)
                    
                return result
            except Exception as e:
                print(f"Error converting SVG to PNG: {e}")
                
        return None
    
    def decode_png(self, png_path: str) -> Optional[str]:
        """Decode QR code from PNG file"""
        if not PYZBAR_AVAILABLE:
            print("Error: pyzbar not available for QR decoding")
            return None
            
        try:
            # Open image
            img = Image.open(png_path)
            
            # Decode QR codes
            decoded_objects = pyzbar_decode(img)
            
            if decoded_objects:
                # Return first QR code data
                return decoded_objects[0].data.decode('utf-8')
            else:
                print(f"No QR code found in: {png_path}")
                return None
                
        except Exception as e:
            print(f"Error decoding PNG: {e}")
            return None

class CryptoAnalyzer:
    """Performs cryptographic analysis on decoded QR data"""
    
    def __init__(self):
        self.common_xor_keys = [
            b'\x00', b'\xFF', b'\xAA', b'\x55',
            b'KEY', b'RISE', b'GYM', b'QR',
            b'2025', b'9268'
        ]
        
    def analyze_data(self, data: str) -> Dict:
        """Comprehensive analysis of QR data"""
        results = {
            'original': data,
            'length': len(data),
            'hex': data.encode().hex(),
            'analysis': {}
        }
        
        # Check if it's already plaintext (facility + date + time pattern)
        if self._check_plaintext_pattern(data):
            results['analysis']['plaintext'] = {
                'detected': True,
                'pattern': 'facility+date+time',
                'components': self._parse_plaintext_components(data)
            }
        
        # Try Base64 decoding
        base64_result = self._try_base64_decode(data)
        if base64_result:
            results['analysis']['base64'] = base64_result
            
        # Try XOR with common keys
        xor_results = self._try_xor_decode(data)
        if xor_results:
            results['analysis']['xor'] = xor_results
            
        # Frequency analysis
        freq_analysis = self._frequency_analysis(data)
        results['analysis']['frequency'] = freq_analysis
        
        # Pattern detection
        patterns = self._detect_patterns(data)
        if patterns:
            results['analysis']['patterns'] = patterns
            
        # Entropy calculation
        entropy = self._calculate_entropy(data)
        results['analysis']['entropy'] = entropy
        
        return results
    
    def _check_plaintext_pattern(self, data: str) -> bool:
        """Check if data matches known plaintext pattern"""
        # Pattern: 9268 + MMDDYYYY + HHMMSS or similar
        if len(data) == 18 and data.startswith('9268'):
            try:
                # Check if positions 4-12 could be a date
                date_part = data[4:12]
                month = int(date_part[0:2])
                day = int(date_part[2:4])
                year = int(date_part[4:8])
                
                if 1 <= month <= 12 and 1 <= day <= 31 and 2000 <= year <= 2030:
                    return True
            except:
                pass
        return False
    
    def _parse_plaintext_components(self, data: str) -> Dict:
        """Parse plaintext QR components"""
        if len(data) >= 18:
            return {
                'facility': data[0:4],
                'date': data[4:12],
                'time': data[12:18] if len(data) >= 18 else data[12:],
                'date_formatted': f"{data[4:6]}/{data[6:8]}/{data[8:12]}",
                'time_formatted': f"{data[12:14]}:{data[14:16]}:{data[16:18]}" if len(data) >= 18 else "partial"
            }
        return {}
    
    def _try_base64_decode(self, data: str) -> Optional[Dict]:
        """Try to decode as base64"""
        # Try standard base64
        for padding in ['', '=', '==']:
            try:
                decoded = base64.b64decode(data + padding)
                return {
                    'decoded': decoded.hex(),
                    'decoded_ascii': decoded.decode('utf-8', errors='ignore'),
                    'padding': padding
                }
            except:
                pass
                
        # Try base64 URL safe
        try:
            decoded = base64.urlsafe_b64decode(data + '==')
            return {
                'decoded': decoded.hex(),
                'decoded_ascii': decoded.decode('utf-8', errors='ignore'),
                'type': 'urlsafe'
            }
        except:
            pass
            
        return None
    
    def _try_xor_decode(self, data: str) -> List[Dict]:
        """Try XOR decoding with common keys"""
        results = []
        data_bytes = data.encode()
        
        for key in self.common_xor_keys:
            # Single byte XOR
            if len(key) == 1:
                xored = bytes([b ^ key[0] for b in data_bytes])
            else:
                # Multi-byte XOR (repeating key)
                xored = bytes([data_bytes[i] ^ key[i % len(key)] for i in range(len(data_bytes))])
            
            # Check if result looks meaningful
            try:
                decoded_str = xored.decode('utf-8', errors='ignore')
                if self._is_meaningful(decoded_str):
                    results.append({
                        'key': key.hex(),
                        'key_ascii': key.decode('utf-8', errors='ignore'),
                        'result': xored.hex(),
                        'result_ascii': decoded_str
                    })
            except:
                pass
                
        return results
    
    def _frequency_analysis(self, data: str) -> Dict:
        """Perform frequency analysis on the data"""
        char_freq = Counter(data)
        byte_freq = Counter(data.encode())
        
        # Calculate character distribution
        total_chars = len(data)
        char_distribution = {char: count/total_chars for char, count in char_freq.most_common()}
        
        # Check for patterns
        repeated_chars = [char for char, count in char_freq.items() if count > total_chars * 0.1]
        
        return {
            'character_frequency': dict(char_freq.most_common(10)),
            'byte_frequency': {f"0x{b:02x}": count for b, count in byte_freq.most_common(10)},
            'repeated_characters': repeated_chars,
            'unique_characters': len(char_freq),
            'distribution': char_distribution
        }
    
    def _detect_patterns(self, data: str) -> Dict:
        """Detect patterns in the data"""
        patterns = {}
        
        # Check for repeating sequences
        for length in range(2, min(len(data)//2, 10)):
            for i in range(len(data) - length):
                substring = data[i:i+length]
                if data.count(substring) > 1:
                    if substring not in patterns:
                        patterns[substring] = data.count(substring)
        
        # Sort by frequency
        sorted_patterns = dict(sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:10])
        
        return {
            'repeating_sequences': sorted_patterns,
            'has_numeric_pattern': bool(re.search(r'\d{4,}', data)),
            'has_date_pattern': bool(re.search(r'\d{2}/\d{2}/\d{4}|\d{8}', data)),
            'has_time_pattern': bool(re.search(r'\d{2}:\d{2}:\d{2}|\d{6}', data))
        }
    
    def _calculate_entropy(self, data: str) -> float:
        """Calculate Shannon entropy of the data"""
        if not data:
            return 0.0
            
        entropy = 0
        for char in set(data):
            p_x = data.count(char) / len(data)
            if p_x > 0:
                import math
                entropy += - p_x * math.log2(p_x)
                
        return round(entropy, 4)
    
    def _is_meaningful(self, text: str) -> bool:
        """Check if decoded text appears meaningful"""
        # Check for high proportion of printable characters
        printable_chars = sum(1 for c in text if c.isprintable())
        if printable_chars / len(text) < 0.8:
            return False
            
        # Check for common patterns
        if any(pattern in text.lower() for pattern in ['rise', 'gym', 'qr', 'date', 'time']):
            return True
            
        # Check for date/time patterns
        if re.search(r'\d{4,}', text):
            return True
            
        return False

class QRCracker:
    """Main class to orchestrate QR code cracking"""
    
    def __init__(self):
        self.decoder = QRDecoder()
        self.analyzer = CryptoAnalyzer()
        self.results = {}
        
    def crack_single_qr(self, file_path: str) -> Dict:
        """Crack a single QR code file"""
        print(f"\n{'='*60}")
        print(f"Analyzing: {file_path}")
        print(f"{'='*60}")
        
        # Decode QR
        if file_path.endswith('.svg'):
            decoded_data = self.decoder.decode_svg(file_path)
        elif file_path.endswith('.png'):
            decoded_data = self.decoder.decode_png(file_path)
        else:
            print(f"Unsupported file format: {file_path}")
            return {}
            
        if not decoded_data:
            print("Failed to decode QR code")
            return {}
            
        print(f"Decoded QR data: {decoded_data}")
        
        # Analyze decoded data
        analysis = self.analyzer.analyze_data(decoded_data)
        
        # Pretty print results
        self._print_analysis(analysis)
        
        return analysis
    
    def crack_all_qrs(self, directory: str = "real_qr_codes") -> Dict:
        """Crack all QR codes in directory"""
        qr_dir = Path(directory)
        if not qr_dir.exists():
            print(f"Error: Directory not found: {directory}")
            return {}
            
        svg_files = sorted(qr_dir.glob("*.svg"))
        png_files = sorted(qr_dir.glob("*.png"))
        all_files = svg_files + png_files
        
        print(f"Found {len(all_files)} QR code files")
        
        all_results = {}
        pattern_summary = {
            'plaintext_count': 0,
            'encoded_count': 0,
            'unique_patterns': set(),
            'facility_codes': set(),
            'time_patterns': {}
        }
        
        for file_path in all_files:
            result = self.crack_single_qr(str(file_path))
            if result:
                all_results[file_path.name] = result
                
                # Update summary
                if result.get('analysis', {}).get('plaintext', {}).get('detected'):
                    pattern_summary['plaintext_count'] += 1
                    components = result['analysis']['plaintext']['components']
                    if 'facility' in components:
                        pattern_summary['facility_codes'].add(components['facility'])
                    if 'time' in components:
                        time_key = components['time'][:2]  # Hour
                        pattern_summary['time_patterns'][time_key] = pattern_summary['time_patterns'].get(time_key, 0) + 1
                else:
                    pattern_summary['encoded_count'] += 1
                    
                pattern_summary['unique_patterns'].add(result.get('original', ''))
        
        # Save results
        output_file = Path("qr_analysis_results.json")
        with open(output_file, 'w') as f:
            json.dump({
                'metadata': {
                    'analyzed_at': datetime.now().isoformat(),
                    'total_files': len(all_results),
                    'decoder_available': PYZBAR_AVAILABLE,
                    'cairo_available': CAIRO_AVAILABLE
                },
                'summary': {
                    'plaintext_qrs': pattern_summary['plaintext_count'],
                    'encoded_qrs': pattern_summary['encoded_count'],
                    'unique_patterns': len(pattern_summary['unique_patterns']),
                    'facility_codes': list(pattern_summary['facility_codes']),
                    'time_distribution': pattern_summary['time_patterns']
                },
                'detailed_results': all_results
            }, f, indent=2)
            
        print(f"\n{'='*60}")
        print("ANALYSIS COMPLETE")
        print(f"{'='*60}")
        print(f"Total QR codes analyzed: {len(all_results)}")
        print(f"Plaintext QRs: {pattern_summary['plaintext_count']}")
        print(f"Encoded QRs: {pattern_summary['encoded_count']}")
        print(f"Unique patterns: {len(pattern_summary['unique_patterns'])}")
        print(f"Results saved to: {output_file}")
        
        return all_results
    
    def _print_analysis(self, analysis: Dict):
        """Pretty print analysis results"""
        print("\n--- Analysis Results ---")
        
        # Original data
        print(f"Original: {analysis['original']}")
        print(f"Length: {analysis['length']}")
        print(f"Hex: {analysis['hex']}")
        
        # Plaintext detection
        if analysis['analysis'].get('plaintext', {}).get('detected'):
            print("\n✓ PLAINTEXT PATTERN DETECTED")
            components = analysis['analysis']['plaintext']['components']
            print(f"  Facility: {components.get('facility')}")
            print(f"  Date: {components.get('date_formatted')}")
            print(f"  Time: {components.get('time_formatted')}")
        
        # Base64 results
        if 'base64' in analysis['analysis']:
            print("\n✓ BASE64 DECODED")
            print(f"  Hex: {analysis['analysis']['base64']['decoded']}")
            print(f"  ASCII: {analysis['analysis']['base64']['decoded_ascii']}")
        
        # XOR results
        if 'xor' in analysis['analysis']:
            print("\n✓ XOR DECODING RESULTS")
            for xor_result in analysis['analysis']['xor'][:3]:  # Show top 3
                print(f"  Key: {xor_result['key_ascii']} (0x{xor_result['key']})")
                print(f"  Result: {xor_result['result_ascii']}")
        
        # Entropy
        if 'entropy' in analysis['analysis']:
            print(f"\nEntropy: {analysis['analysis']['entropy']}")
        
        # Patterns
        if 'patterns' in analysis['analysis']:
            patterns = analysis['analysis']['patterns']
            if patterns.get('repeating_sequences'):
                print("\nRepeating sequences:")
                for seq, count in list(patterns['repeating_sequences'].items())[:5]:
                    print(f"  '{seq}': {count} times")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='QR Code Decoder and Cryptographic Analyzer')
    parser.add_argument('--file', '-f', help='Analyze single QR code file')
    parser.add_argument('--directory', '-d', default='real_qr_codes', 
                       help='Directory containing QR codes (default: real_qr_codes)')
    parser.add_argument('--all', '-a', action='store_true',
                       help='Analyze all QR codes in directory')
    
    args = parser.parse_args()
    
    cracker = QRCracker()
    
    if args.file:
        cracker.crack_single_qr(args.file)
    elif args.all:
        cracker.crack_all_qrs(args.directory)
    else:
        print("Usage: python qr_decoder_analyzer.py --file <qr_file> or --all")
        print("\nThis tool will:")
        print("1. Decode QR codes using ZXing/pyzbar")
        print("2. Analyze decoded data for encryption/encoding")
        print("3. Try Base64 decoding")
        print("4. Attempt XOR with common keys")
        print("5. Perform frequency analysis")
        print("6. Detect patterns and calculate entropy")

if __name__ == "__main__":
    main()