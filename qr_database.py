#!/usr/bin/env python3
"""
QR Code Database Generator
Creates a database of all scraped SVG QR codes with timestamps and metadata.
"""

import os
import json
from datetime import datetime
from pathlib import Path

def create_qr_database():
    """Create a comprehensive database of all scraped QR code SVG files."""
    
    real_qr_codes_dir = Path("real_qr_codes")
    
    if not real_qr_codes_dir.exists():
        print(f"Error: Directory {real_qr_codes_dir} not found")
        return
    
    database = {
        "metadata": {
            "created": datetime.now().isoformat(),
            "total_files": 0,
            "date_range": {
                "earliest": None,
                "latest": None
            },
            "time_coverage": {
                "hours": [],
                "unique_dates": []
            }
        },
        "files": []
    }
    
    svg_files = sorted([f for f in real_qr_codes_dir.iterdir() if f.suffix == '.svg'])
    
    for svg_file in svg_files:
        filename = svg_file.name
        timestamp_str = filename.replace('.svg', '')
        
        # Parse timestamp: YYYYMMDDHHMMM format
        if len(timestamp_str) == 12:
            try:
                year = int(timestamp_str[:4])
                month = int(timestamp_str[4:6])
                day = int(timestamp_str[6:8])
                hour = int(timestamp_str[8:10])
                minute = int(timestamp_str[10:12])
                
                # Create datetime object
                dt = datetime(year, month, day, hour, minute)
                
                # Calculate 2-hour slot (0-11)
                slot_number = hour // 2
                slot_start_hour = slot_number * 2
                slot_end_hour = slot_start_hour + 1
                slot_label = f"{slot_start_hour:02d}00-{slot_end_hour:02d}59"
                
                # File info
                file_info = {
                    "filename": filename,
                    "timestamp": timestamp_str,
                    "datetime": dt.isoformat(),
                    "date": dt.strftime("%Y-%m-%d"),
                    "time": dt.strftime("%H:%M"),
                    "weekday": dt.strftime("%A"),
                    "file_size": svg_file.stat().st_size,
                    "year": year,
                    "month": month,
                    "day": day,
                    "hour": hour,
                    "minute": minute,
                    "slot_number": slot_number,
                    "slot_label": slot_label
                }
                
                database["files"].append(file_info)
                
                # Update metadata
                date_str = dt.strftime("%Y-%m-%d")
                if date_str not in database["metadata"]["time_coverage"]["unique_dates"]:
                    database["metadata"]["time_coverage"]["unique_dates"].append(date_str)
                
                if hour not in database["metadata"]["time_coverage"]["hours"]:
                    database["metadata"]["time_coverage"]["hours"].append(hour)
                
                if slot_number not in database["metadata"]["time_coverage"].get("slots", []):
                    if "slots" not in database["metadata"]["time_coverage"]:
                        database["metadata"]["time_coverage"]["slots"] = []
                    database["metadata"]["time_coverage"]["slots"].append(slot_number)
                
                # Update date range
                if database["metadata"]["date_range"]["earliest"] is None or dt < datetime.fromisoformat(database["metadata"]["date_range"]["earliest"]):
                    database["metadata"]["date_range"]["earliest"] = dt.isoformat()
                
                if database["metadata"]["date_range"]["latest"] is None or dt > datetime.fromisoformat(database["metadata"]["date_range"]["latest"]):
                    database["metadata"]["date_range"]["latest"] = dt.isoformat()
                    
            except ValueError as e:
                print(f"Warning: Could not parse timestamp from {filename}: {e}")
                continue
    
    # Sort files by datetime
    database["files"].sort(key=lambda x: x["datetime"])
    
    # Sort metadata lists
    database["metadata"]["time_coverage"]["unique_dates"].sort()
    database["metadata"]["time_coverage"]["hours"].sort()
    if "slots" in database["metadata"]["time_coverage"]:
        database["metadata"]["time_coverage"]["slots"].sort()
    
    # Update total count
    database["metadata"]["total_files"] = len(database["files"])
    
    # Save database
    database_file = Path("qr_code_database.json")
    with open(database_file, 'w') as f:
        json.dump(database, f, indent=2)
    
    # Print summary
    print(f"QR Code Database Created: {database_file}")
    print(f"Total SVG files: {database['metadata']['total_files']}")
    print(f"Date range: {database['metadata']['date_range']['earliest'][:10]} to {database['metadata']['date_range']['latest'][:10]}")
    print(f"Unique dates: {len(database['metadata']['time_coverage']['unique_dates'])}")
    print(f"Hours covered: {sorted(database['metadata']['time_coverage']['hours'])}")
    if "slots" in database["metadata"]["time_coverage"]:
        slots = database["metadata"]["time_coverage"]["slots"]
        slot_labels = [f"Slot {s}: {s*2:02d}00-{s*2+1:02d}59" for s in sorted(slots)]
        print(f"2-hour slots: {slot_labels}")
    
    # Create human-readable summary
    summary = []
    summary.append("# QR Code Database Summary")
    summary.append(f"Generated: {database['metadata']['created']}")
    summary.append(f"Total files: {database['metadata']['total_files']}")
    summary.append("")
    summary.append("## Date Coverage")
    for date in database['metadata']['time_coverage']['unique_dates']:
        date_files = [f for f in database['files'] if f['date'] == date]
        summary.append(f"- {date}: {len(date_files)} files")
    
    summary.append("")
    summary.append("## Time Coverage")
    summary.append(f"Hours: {sorted(database['metadata']['time_coverage']['hours'])}")
    if "slots" in database["metadata"]["time_coverage"]:
        slots = database["metadata"]["time_coverage"]["slots"]
        summary.append("")
        summary.append("## 2-Hour Slots")
        for slot in sorted(slots):
            slot_files = [f for f in database['files'] if f.get('slot_number') == slot]
            slot_label = f"{slot*2:02d}00-{slot*2+1:02d}59"
            summary.append(f"- Slot {slot} ({slot_label}): {len(slot_files)} files")
    
    summary.append("")
    summary.append("## All Files")
    for file_info in database['files']:
        slot_info = ""
        if 'slot_number' in file_info:
            slot_info = f" [Slot {file_info['slot_number']}: {file_info['slot_label']}]"
        summary.append(f"- {file_info['filename']} ({file_info['datetime']}) - {file_info['file_size']} bytes{slot_info}")
    
    summary_file = Path("qr_database_summary.md")
    with open(summary_file, 'w') as f:
        f.write('\n'.join(summary))
    
    print(f"Summary created: {summary_file}")
    
    return database

if __name__ == "__main__":
    create_qr_database()