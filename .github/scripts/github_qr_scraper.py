#!/usr/bin/env python3
"""
GitHub Actions QR Code Scraper
Runs in GitHub Actions environment to scrape QR codes
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("❌ Playwright not installed")
    sys.exit(1)

class GitHubQRScraper:
    def __init__(self):
        self.username = os.environ.get('RISE_USERNAME')
        self.password = os.environ.get('RISE_PASSWORD')
        self.login_url = "https://risegyms.ez-runner.com/login.aspx"
        
        if not self.username or not self.password:
            raise ValueError("RISE_USERNAME and RISE_PASSWORD must be set as GitHub secrets")
        
        # Create output directory
        self.output_dir = Path("scraped_qr_codes")
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories by date
        today = datetime.now().strftime("%Y-%m-%d")
        self.date_dir = self.output_dir / today
        self.date_dir.mkdir(exist_ok=True)
    
    def scrape_qr_code(self):
        """Scrape QR code using Playwright"""
        print(f"🚀 Starting QR scrape at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        with sync_playwright() as p:
            try:
                # Launch browser in headless mode
                browser = p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
                
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
                )
                
                page = context.new_page()
                
                # Navigate and login
                print("📱 Navigating to Rise Gym...")
                page.goto(self.login_url, wait_until='networkidle')
                page.wait_for_timeout(2000)
                
                # Fill login form
                print("🔐 Logging in...")
                page.fill('input[placeholder*="Email" i]', self.username)
                page.fill('input[type="password"]', self.password)
                page.keyboard.press('Enter')
                
                # Wait for dashboard
                print("⏳ Waiting for dashboard...")
                page.wait_for_function(
                    '''() => {
                        return window.location.href.includes('BookingPortal') || 
                               document.querySelector('svg') !== null;
                    }''',
                    timeout=15000
                )
                
                # Find and save QR code
                print("🔍 Looking for QR code...")
                svg_elements = page.query_selector_all('svg')
                
                if svg_elements:
                    # Get the largest SVG
                    largest_svg = None
                    largest_size = 0
                    
                    for svg in svg_elements:
                        html = svg.evaluate('(element) => element.outerHTML')
                        if len(html) > largest_size:
                            largest_size = len(html)
                            largest_svg = html
                    
                    if largest_svg and largest_size > 1000:
                        # Save QR code with timestamp
                        timestamp = datetime.now().strftime("%H%M%S")
                        filename = self.date_dir / f"qr_{timestamp}.svg"
                        
                        with open(filename, 'w') as f:
                            f.write(largest_svg)
                        
                        print(f"✅ QR code saved: {filename}")
                        print(f"📏 Size: {largest_size} characters")
                        
                        # Also save metadata
                        metadata_file = self.date_dir / f"qr_{timestamp}_meta.txt"
                        with open(metadata_file, 'w') as f:
                            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                            f.write(f"Size: {largest_size}\n")
                            f.write(f"Hour block: {(datetime.now().hour // 2) * 2:02d}:00\n")
                        
                        browser.close()
                        return True
                    else:
                        print(f"❌ SVG too small or not found")
                else:
                    print("❌ No SVG elements found")
                
                browser.close()
                return False
                
            except Exception as e:
                print(f"❌ Error: {e}")
                if 'browser' in locals():
                    browser.close()
                return False

def main():
    """Main function"""
    print("=" * 60)
    print("GitHub Actions QR Scraper")
    print("=" * 60)
    
    try:
        scraper = GitHubQRScraper()
        success = scraper.scrape_qr_code()
        
        if success:
            print("\n✅ Scraping completed successfully!")
            
            # Create summary file
            summary_file = Path("scraped_qr_codes") / "latest_scrape.txt"
            with open(summary_file, 'w') as f:
                f.write(f"Last successful scrape: {datetime.now().isoformat()}\n")
                f.write(f"Status: SUCCESS\n")
        else:
            print("\n❌ Scraping failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()