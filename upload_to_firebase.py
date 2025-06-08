#!/usr/bin/env python3
"""
Upload QR codes to Firebase Storage for Rise Gym QR App
"""

import firebase_admin
from firebase_admin import credentials, storage
import os
import sys
import json
from datetime import datetime
from pathlib import Path

def initialize_firebase(service_account_path, storage_bucket):
    """Initialize Firebase Admin SDK"""
    try:
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred, {
            'storageBucket': storage_bucket
        })
        print(f"✅ Firebase initialized with bucket: {storage_bucket}")
        return storage.bucket()
    except Exception as e:
        print(f"❌ Failed to initialize Firebase: {e}")
        sys.exit(1)

def upload_qr_code(bucket, local_path, storage_path, time_slot, expires_at=None):
    """Upload a single QR code to Firebase Storage"""
    try:
        blob = bucket.blob(storage_path)
        
        # Set metadata
        metadata = {
            'timeSlot': time_slot,
            'contentType': 'image/svg+xml',
            'uploadedAt': datetime.now().isoformat()
        }
        
        if expires_at:
            metadata['expiresAt'] = str(expires_at)
        
        blob.metadata = metadata
        
        # Upload file
        blob.upload_from_filename(local_path)
        
        # Make publicly accessible (read-only)
        blob.make_public()
        
        print(f"✅ Uploaded {local_path} to {storage_path}")
        print(f"   Time slot: {time_slot}")
        print(f"   Public URL: {blob.public_url}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to upload {local_path}: {e}")
        return False

def upload_all_qr_codes(bucket, qr_directory):
    """Upload all QR codes from a directory"""
    qr_dir = Path(qr_directory)
    if not qr_dir.exists():
        print(f"❌ Directory not found: {qr_directory}")
        return
    
    # Time slot mapping
    time_slots = {
        "0000": "00:00-01:59",
        "0200": "02:00-03:59",
        "0400": "04:00-05:59",
        "0600": "06:00-07:59",
        "0800": "08:00-09:59",
        "1000": "10:00-11:59",
        "1200": "12:00-13:59",
        "1400": "14:00-15:59",
        "1600": "16:00-17:59",
        "1800": "18:00-19:59",
        "2000": "20:00-21:59",
        "2200": "22:00-23:59"
    }
    
    uploaded = 0
    failed = 0
    
    # Upload time-slot specific QR codes
    for slot_key, slot_value in time_slots.items():
        # Find matching SVG file
        matching_files = list(qr_dir.glob(f"*{slot_key}*.svg"))
        
        if matching_files:
            local_file = matching_files[0]
            storage_path = f"qr_codes/slot_{slot_value.replace(':', '')}.svg"
            
            if upload_qr_code(bucket, str(local_file), storage_path, slot_value):
                uploaded += 1
                
                # If this is the current time slot, also upload as latest
                current_hour = datetime.now().hour
                slot_hour = int(slot_key[:2])
                if slot_hour <= current_hour < slot_hour + 2:
                    upload_qr_code(bucket, str(local_file), "qr_codes/latest.svg", slot_value)
            else:
                failed += 1
        else:
            print(f"⚠️  No QR code found for time slot {slot_value}")
    
    print(f"\n📊 Upload Summary:")
    print(f"   Uploaded: {uploaded}")
    print(f"   Failed: {failed}")

def upload_single_as_latest(bucket, local_path):
    """Upload a single QR code as the latest"""
    # Determine time slot from current time
    current_hour = datetime.now().hour
    slot_hour = (current_hour // 2) * 2
    time_slot = f"{slot_hour:02d}:00-{slot_hour+1:02d}:59"
    
    # Calculate expiration (next 2-hour block)
    next_slot_hour = ((current_hour // 2) + 1) * 2
    expires_at = datetime.now().replace(
        hour=next_slot_hour % 24,
        minute=0,
        second=0,
        microsecond=0
    ).timestamp() * 1000  # Convert to milliseconds
    
    return upload_qr_code(
        bucket, 
        local_path, 
        "qr_codes/latest.svg", 
        time_slot,
        expires_at
    )

def main():
    """Main function"""
    print("🔥 Firebase QR Code Uploader")
    print("=" * 50)
    
    # Check for configuration
    if len(sys.argv) < 3:
        print("\nUsage:")
        print("  python upload_to_firebase.py <service_account.json> <storage_bucket> [qr_directory]")
        print("\nExample:")
        print("  python upload_to_firebase.py ./firebase-key.json risegym.appspot.com ./real_qr_codes")
        print("\nFor single file upload:")
        print("  python upload_to_firebase.py ./firebase-key.json risegym.appspot.com --single <file.svg>")
        sys.exit(1)
    
    service_account = sys.argv[1]
    storage_bucket = sys.argv[2]
    
    # Initialize Firebase
    bucket = initialize_firebase(service_account, storage_bucket)
    
    # Check for single file mode
    if len(sys.argv) > 3 and sys.argv[3] == "--single":
        if len(sys.argv) < 5:
            print("❌ Please specify the file to upload")
            sys.exit(1)
        
        single_file = sys.argv[4]
        upload_single_as_latest(bucket, single_file)
    else:
        # Upload all QR codes from directory
        qr_directory = sys.argv[3] if len(sys.argv) > 3 else "./real_qr_codes"
        upload_all_qr_codes(bucket, qr_directory)
    
    print("\n✅ Upload complete!")

if __name__ == "__main__":
    main()