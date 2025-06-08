#!/usr/bin/env python3
"""
Generate a manifest file listing all QR codes in the real_qr_codes directory
This manifest can be used by the Android app to know what QR codes are available
"""

import os
import json
from datetime import datetime
from pathlib import Path

def generate_manifest():
    qr_dir = Path("real_qr_codes")
    if not qr_dir.exists():
        print(f"Directory {qr_dir} does not exist")
        return
    
    # Get all SVG files
    svg_files = sorted(qr_dir.glob("*.svg"), reverse=True)
    
    manifest = {
        "generated": datetime.utcnow().isoformat() + "Z",
        "qr_codes": []
    }
    
    for svg_file in svg_files:
        # Extract timestamp from filename
        filename = svg_file.name
        timestamp = filename.replace(".svg", "")
        
        # Get file size
        size = svg_file.stat().st_size
        
        manifest["qr_codes"].append({
            "filename": filename,
            "timestamp": timestamp,
            "size": size,
            "url": f"https://raw.githubusercontent.com/lukaj99/rise-gym-qr/master/real_qr_codes/{filename}"
        })
    
    # Save manifest
    manifest_path = qr_dir / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"✅ Manifest generated with {len(manifest['qr_codes'])} QR codes")
    print(f"📄 Saved to: {manifest_path}")
    
    # Show latest QR codes
    if manifest["qr_codes"]:
        print(f"\n🕐 Latest QR codes:")
        for qr in manifest["qr_codes"][:5]:
            print(f"   - {qr['filename']} ({qr['size']} bytes)")

if __name__ == "__main__":
    generate_manifest()