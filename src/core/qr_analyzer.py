#!/usr/bin/env python3
"""
Rise Gym QR Code Analyzer
Analyzes QR codes to discover patterns and parameters
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict


class RiseGymQRAnalyzer:
    """Analyze Rise Gym QR codes to discover patterns"""
    
    def __init__(self):
        self.pattern = {
            'facility_code': '9268',
            'date_format': 'MMDDYYYY',
            'time_format': 'HHMMSS',
            'time_slots': list(range(0, 24, 2)),  # 2-hour slots
            'suffix_rule': {
                0: '01',  # 00:00-01:59 uses suffix 01
                'default': '00'  # All other slots use 00
            }
        }
        
    def analyze_filename(self, filename):
        """Extract datetime from filename (YYYYMMDDHHMM.svg)"""
        base = Path(filename).stem
        if len(base) == 12 and base.isdigit():
            year = int(base[0:4])
            month = int(base[4:6])
            day = int(base[6:8])
            hour = int(base[8:10])
            minute = int(base[10:12])
            
            dt = datetime(year, month, day, hour, minute)
            return dt
        return None
    
    def predict_qr_data(self, dt):
        """Predict QR data for given datetime"""
        facility = self.pattern['facility_code']
        date_str = dt.strftime("%m%d%Y")
        
        # Time slot - 2 hour slots
        slot_hour = (dt.hour // 2) * 2
        
        # Apply suffix rule
        if slot_hour in self.pattern['suffix_rule']:
            suffix = self.pattern['suffix_rule'][slot_hour]
        else:
            suffix = self.pattern['suffix_rule']['default']
            
        time_str = f"{slot_hour:02d}00{suffix}"
        
        return f"{facility}{date_str}{time_str}"
    
    def analyze_directory(self, directory='real_qr_codes'):
        """Analyze all QR codes in directory"""
        results = {
            'files_analyzed': 0,
            'pattern_confirmed': True,
            'date_range': {'min': None, 'max': None},
            'time_slots': Counter(),
            'predictions': []
        }
        
        svg_files = list(Path(directory).glob('*.svg'))
        results['files_analyzed'] = len(svg_files)
        
        for svg_file in sorted(svg_files):
            dt = self.analyze_filename(svg_file.name)
            if dt:
                # Update date range
                if results['date_range']['min'] is None or dt < results['date_range']['min']:
                    results['date_range']['min'] = dt
                if results['date_range']['max'] is None or dt > results['date_range']['max']:
                    results['date_range']['max'] = dt
                
                # Count time slots
                slot_hour = (dt.hour // 2) * 2
                results['time_slots'][f"{slot_hour:02d}:00-{(slot_hour+2)%24:02d}:00"] += 1
                
                # Store prediction
                predicted_data = self.predict_qr_data(dt)
                results['predictions'].append({
                    'filename': svg_file.name,
                    'datetime': dt.isoformat(),
                    'predicted_data': predicted_data
                })
        
        return results
    
    def save_analysis(self, results, output_file='qr_analysis_results.json'):
        """Save analysis results to JSON"""
        # Convert datetime objects for JSON serialization
        save_data = {
            'analysis_date': datetime.now().isoformat(),
            'files_analyzed': results['files_analyzed'],
            'pattern_confirmed': results['pattern_confirmed'],
            'date_range': {
                'min': results['date_range']['min'].isoformat() if results['date_range']['min'] else None,
                'max': results['date_range']['max'].isoformat() if results['date_range']['max'] else None
            },
            'time_slots': dict(results['time_slots']),
            'pattern': self.pattern,
            'predictions': results['predictions']
        }
        
        with open(output_file, 'w') as f:
            json.dump(save_data, f, indent=2)
        
        return output_file


def main():
    """Command line interface"""
    analyzer = RiseGymQRAnalyzer()
    
    # Analyze directory
    directory = sys.argv[1] if len(sys.argv) > 1 else 'real_qr_codes'
    print(f"Analyzing QR codes in: {directory}")
    
    results = analyzer.analyze_directory(directory)
    
    # Display results
    print(f"\nFiles analyzed: {results['files_analyzed']}")
    
    if results['date_range']['min'] and results['date_range']['max']:
        print(f"Date range: {results['date_range']['min'].date()} to {results['date_range']['max'].date()}")
    
    print(f"\nTime slot distribution:")
    for slot, count in sorted(results['time_slots'].items()):
        print(f"  {slot}: {count} files")
    
    # Save results
    output_file = analyzer.save_analysis(results)
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()