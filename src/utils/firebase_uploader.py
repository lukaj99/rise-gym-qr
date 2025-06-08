#!/usr/bin/env python3
"""
Firebase QR Code Uploader
Uploads QR codes to Firebase Realtime Database for instant mobile app updates
"""

import os
import sys
import json
import base64
import logging
from datetime import datetime
from pathlib import Path
import requests
from PIL import Image
import io

# Try to import cairosvg, but don't fail if it's not available
try:
    import cairosvg
    HAS_CAIROSVG = True
except ImportError:
    HAS_CAIROSVG = False
    logging.warning("cairosvg not available - bitmap generation will be skipped")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FirebaseUploader:
    def __init__(self, database_url: str, auth_token: str = None):
        """
        Initialize Firebase uploader
        
        Args:
            database_url: Firebase Realtime Database URL
            auth_token: Optional authentication token
        """
        self.database_url = database_url.rstrip('/')
        self.auth_token = auth_token
        
    def upload_qr_code(self, svg_path: str, pattern: str) -> bool:
        """
        Upload QR code to Firebase with both SVG and bitmap versions
        
        Args:
            svg_path: Path to SVG file
            pattern: QR code pattern (e.g., "926806082025120000")
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Read SVG content
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            
            # Generate high-quality PNG bitmap from SVG if cairosvg is available
            bitmap_base64 = ""
            if HAS_CAIROSVG:
                try:
                    png_data = cairosvg.svg2png(
                        bytestring=svg_content.encode('utf-8'),
                        output_width=800,
                        output_height=800,
                        dpi=300
                    )
                    # Convert PNG to base64 for storage
                    bitmap_base64 = base64.b64encode(png_data).decode('utf-8')
                    logger.info(f"Generated bitmap: {len(bitmap_base64)} chars")
                except Exception as e:
                    logger.warning(f"Failed to generate bitmap: {e}")
            else:
                logger.warning("Skipping bitmap generation (cairosvg not available)")
            
            # Extract timestamp from filename
            filename = os.path.basename(svg_path)
            timestamp = filename.replace('.svg', '')
            
            # Prepare data with both SVG and bitmap
            qr_data = {
                'timestamp': timestamp,
                'svgContent': svg_content,
                'bitmapBase64': bitmap_base64,
                'pattern': pattern,
                'uploadedAt': int(datetime.now().timestamp() * 1000)  # milliseconds
            }
            
            # Upload to Firebase
            # Update both /latest and /qr_codes/{timestamp}
            urls = [
                f"{self.database_url}/latest.json",
                f"{self.database_url}/qr_codes/{timestamp}.json"
            ]
            
            headers = {'Content-Type': 'application/json'}
            if self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
            
            for url in urls:
                response = requests.put(url, json=qr_data, headers=headers)
                if response.status_code not in [200, 201]:
                    logger.error(f"Failed to upload to {url}: {response.status_code} - {response.text}")
                    return False
                logger.info(f"Successfully uploaded to {url}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error uploading QR code: {e}")
            return False
    
    def cleanup_old_codes(self, keep_count: int = 100):
        """
        Remove old QR codes from Firebase, keeping only the most recent ones
        
        Args:
            keep_count: Number of recent codes to keep
        """
        try:
            # Get all QR codes
            url = f"{self.database_url}/qr_codes.json"
            headers = {}
            if self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
            
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Failed to fetch QR codes: {response.status_code}")
                return
            
            qr_codes = response.json() or {}
            
            # Sort by timestamp (filename format: YYYYMMDDHHMMSS)
            sorted_codes = sorted(qr_codes.keys(), reverse=True)
            
            # Delete old codes
            codes_to_delete = sorted_codes[keep_count:]
            for code_id in codes_to_delete:
                delete_url = f"{self.database_url}/qr_codes/{code_id}.json"
                response = requests.delete(delete_url, headers=headers)
                if response.status_code == 200:
                    logger.info(f"Deleted old QR code: {code_id}")
                else:
                    logger.error(f"Failed to delete {code_id}: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error cleaning up old codes: {e}")

def main():
    """Main function to upload QR code from GitHub Actions"""
    
    # Get Firebase configuration from environment
    database_url = os.environ.get('FIREBASE_DATABASE_URL')
    if not database_url:
        logger.error("FIREBASE_DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Optional: Firebase auth token (for secured databases)
    auth_token = os.environ.get('FIREBASE_AUTH_TOKEN')
    
    # Get the latest QR code
    qr_dir = Path('real_qr_codes')
    if not qr_dir.exists():
        logger.error("real_qr_codes directory not found")
        sys.exit(1)
    
    # Find the latest SVG file
    svg_files = sorted(qr_dir.glob('*.svg'), reverse=True)
    if not svg_files:
        logger.error("No SVG files found")
        sys.exit(1)
    
    latest_svg = svg_files[0]
    logger.info(f"Uploading latest QR code: {latest_svg}")
    
    # Extract pattern from filename
    # Filename format: YYYYMMDDHHMMSS.svg
    timestamp = latest_svg.stem
    
    # Generate pattern based on Rise Gym format
    try:
        # Parse timestamp
        dt = datetime.strptime(timestamp, "%Y%m%d%H%M%S")
        
        # Generate pattern: 9268 + MMDDYYYY + HHMMSS
        pattern = "9268"
        pattern += dt.strftime("%m%d%Y")
        
        # Determine time slot
        hour = dt.hour
        if hour % 2 == 0:
            pattern += f"{hour:02d}00"
            pattern += "00" if hour == 0 else "00"
        else:
            pattern += f"{hour-1:02d}00"
            pattern += "01"
            
        logger.info(f"Generated pattern: {pattern}")
        
    except Exception as e:
        logger.error(f"Error generating pattern: {e}")
        pattern = timestamp  # Fallback to timestamp
    
    # Upload to Firebase
    uploader = FirebaseUploader(database_url, auth_token)
    
    if uploader.upload_qr_code(latest_svg, pattern):
        logger.info("Successfully uploaded QR code to Firebase")
        
        # Cleanup old codes
        uploader.cleanup_old_codes(keep_count=50)
    else:
        logger.error("Failed to upload QR code")
        sys.exit(1)

if __name__ == "__main__":
    main()