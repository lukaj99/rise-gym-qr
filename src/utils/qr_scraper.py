#!/usr/bin/env python3
"""
Rise Gym QR Code Scraper - Final Working Version
Uses Playwright with proper form handling
"""

import os
import time
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("❌ Playwright not installed. Install with: pip install playwright && python -m playwright install")
    exit(1)

class RiseGymQRScraperFinal:
    def __init__(self):
        load_dotenv()
        self.username = os.getenv('USERNAME')
        self.password = os.getenv('PASSWORD')
        self.login_url = "https://risegyms.ez-runner.com/login.aspx"
        
        if not self.username or not self.password:
            raise ValueError("USERNAME and PASSWORD must be set in .env file")
        
        # Ensure real_qr_codes directory exists
        os.makedirs("real_qr_codes", exist_ok=True)
    
    def scrape_qr_code(self, headless=True):
        """Scrape QR code using Playwright"""
        print("🚀 Starting QR code scrape with Playwright...")
        
        with sync_playwright() as p:
            try:
                # Launch browser
                print("🌐 Launching browser...")
                browser = p.chromium.launch(
                    headless=headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox'
                    ]
                )
                
                # Create context
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                page = context.new_page()
                
                # Navigate to login page
                print("📱 Navigating to Rise Gym login...")
                page.goto(self.login_url, wait_until='networkidle')
                
                # Wait a bit for any dynamic content
                page.wait_for_timeout(2000)
                
                # Take screenshot for debugging
                if not headless:
                    page.screenshot(path="debug_login_page.png")
                
                print("🔍 Finding login form elements...")
                
                # Find and fill email field
                # Try multiple selectors
                email_filled = False
                for selector in ['input[type="email"]', 'input[placeholder*="Email" i]', 'input[name*="email" i]', 'input:first-of-type']:
                    try:
                        page.wait_for_selector(selector, timeout=2000)
                        page.fill(selector, self.username)
                        email_filled = True
                        print(f"✅ Email filled using selector: {selector}")
                        break
                    except:
                        continue
                
                if not email_filled:
                    raise Exception("Could not find email input field")
                
                # Find and fill password field
                password_filled = False
                for selector in ['input[type="password"]', 'input[placeholder*="Password" i]', 'input[name*="password" i]']:
                    try:
                        page.wait_for_selector(selector, timeout=2000)
                        page.fill(selector, self.password)
                        password_filled = True
                        print(f"✅ Password filled using selector: {selector}")
                        break
                    except:
                        continue
                
                if not password_filled:
                    raise Exception("Could not find password input field")
                
                # Wait a moment before submitting
                page.wait_for_timeout(1000)
                
                print("🚪 Submitting login form...")
                
                # Try multiple ways to submit the form
                try:
                    # Method 1: Press Enter on password field
                    page.keyboard.press('Enter')
                except:
                    try:
                        # Method 2: Click submit button
                        page.click('button[type="submit"], input[type="submit"], button:has-text("Log In")')
                    except:
                        # Method 3: Submit via JavaScript
                        page.evaluate('document.forms[0].submit()')
                
                print("⏳ Waiting for dashboard to load...")
                
                # Wait for navigation with multiple conditions
                try:
                    # Wait for either URL change or SVG presence
                    page.wait_for_function(
                        '''() => {
                            return window.location.href.includes('BookingPortal') || 
                                   document.querySelector('svg') !== null ||
                                   document.body.textContent.toLowerCase().includes('hello');
                        }''',
                        timeout=15000
                    )
                except PlaywrightTimeout:
                    print("⚠️  Timeout waiting for dashboard, checking current state...")
                
                # Take screenshot after login attempt
                if not headless:
                    page.screenshot(path="debug_after_login.png")
                
                # Check current URL
                current_url = page.url
                print(f"📍 Current URL: {current_url}")
                
                # Look for QR code
                print("🔍 Looking for QR code...")
                
                # Try to find SVG elements
                svg_elements = page.query_selector_all('svg')
                
                if not svg_elements:
                    # Wait a bit more and try again
                    page.wait_for_timeout(3000)
                    svg_elements = page.query_selector_all('svg')
                
                if svg_elements:
                    print(f"✅ Found {len(svg_elements)} SVG elements")
                    
                    # Get the largest SVG (likely the QR code)
                    largest_svg = None
                    largest_size = 0
                    
                    for svg in svg_elements:
                        try:
                            html = svg.evaluate('(element) => element.outerHTML')
                            if len(html) > largest_size:
                                largest_size = len(html)
                                largest_svg = html
                        except:
                            continue
                    
                    if largest_svg and largest_size > 1000:
                        # Save QR code
                        timestamp = datetime.now().strftime("%Y%m%d%H%M")
                        filename = f"real_qr_codes/{timestamp}.svg"
                        
                        with open(filename, 'w') as f:
                            f.write(largest_svg)
                        
                        print(f"💾 QR code saved: {filename}")
                        print(f"📏 Size: {largest_size} characters")
                        
                        # Update database
                        self.update_database()
                        
                        browser.close()
                        return filename
                    else:
                        print(f"❌ SVG too small ({largest_size} chars) or not found")
                else:
                    print("❌ No SVG elements found on page")
                    
                    # Debug: print page content snippet
                    content = page.content()
                    print(f"📄 Page content preview: {content[:500]}...")
                
                browser.close()
                return None
                
            except Exception as e:
                print(f"❌ Error during scraping: {e}")
                if 'browser' in locals():
                    browser.close()
                return None
    
    def update_database(self):
        """Update the QR code database"""
        try:
            result = subprocess.run(['python', 'qr_database.py'], 
                                  capture_output=True, text=True, cwd='.')
            if result.returncode == 0:
                print(f"📊 Database updated successfully")
            else:
                print(f"⚠️  Database update warning: {result.stderr}")
        except Exception as e:
            print(f"⚠️  Could not update database: {e}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Rise Gym QR Scraper (Final)')
    parser.add_argument('--debug', action='store_true', 
                       help='Run in debug mode (visible browser)')
    
    args = parser.parse_args()
    
    scraper = RiseGymQRScraperFinal()
    result = scraper.scrape_qr_code(headless=not args.debug)
    
    if result:
        print(f"✅ Success! QR code scraped: {result}")
        return True
    else:
        print("❌ Failed to scrape QR code")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)