#!/usr/bin/env python3
"""
Rise Gym QR Code Scraper - Final Working Version
Uses Playwright with proper form handling
"""

import os
import subprocess
from datetime import datetime
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
        # Try GitHub Actions env vars first, then fall back to .env
        self.username = os.getenv('RISE_GYM_EMAIL') or os.getenv('USERNAME')
        self.password = os.getenv('RISE_GYM_PASSWORD') or os.getenv('PASSWORD')
        self.login_url = "https://risegyms.ez-runner.com/login.aspx"
        
        if not self.username or not self.password:
            raise ValueError("RISE_GYM_EMAIL and RISE_GYM_PASSWORD must be set as environment variables")
        
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
                
                # In CI, list all input fields for debugging
                if os.getenv('CI'):
                    inputs = page.query_selector_all('input')
                    print(f"📝 Found {len(inputs)} input fields:")
                    for i, inp in enumerate(inputs):  # Show all
                        inp_type = inp.get_attribute('type') or 'text'
                        inp_name = inp.get_attribute('name') or 'unnamed'
                        inp_placeholder = inp.get_attribute('placeholder') or 'no-placeholder'
                        inp_id = inp.get_attribute('id') or 'no-id'
                        inp_value = inp.get_attribute('value') or ''
                        if inp_type not in ['hidden', 'password']:
                            print(f"   {i+1}. type='{inp_type}', name='{inp_name}', id='{inp_id}', placeholder='{inp_placeholder}', value='{inp_value[:20]}...'")
                        elif inp_type == 'password':
                            print(f"   {i+1}. type='{inp_type}', name='{inp_name}', id='{inp_id}', placeholder='{inp_placeholder}'")
                    
                    # Also list buttons and clickable elements
                    buttons = page.query_selector_all('button')
                    print(f"🔘 Found {len(buttons)} button elements")
                    
                    # Look for elements with "Log in" text
                    login_elements = page.query_selector_all('*:has-text("Log in")')
                    print(f"🔍 Found {len(login_elements)} elements with 'Log in' text:")
                    for i, elem in enumerate(login_elements[:3]):
                        tag_name = elem.evaluate('el => el.tagName')
                        elem_id = elem.get_attribute('id') or 'no-id'
                        elem_class = elem.get_attribute('class') or 'no-class'
                        elem_type = elem.get_attribute('type') or 'no-type'
                        print(f"   {i+1}. <{tag_name.lower()}> id='{elem_id}', class='{elem_class}', type='{elem_type}'")
                
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
                
                # Debug: Check if fields are actually filled
                if os.getenv('CI'):
                    email_val = page.evaluate('document.querySelector("input[placeholder*=\'Email\' i]")?.value || "NOT FOUND"')
                    pass_filled = page.evaluate('document.querySelector("input[type=\'password\']")?.value?.length > 0')
                    print(f"📧 Email field value: {email_val}")
                    print(f"🔑 Password field filled: {pass_filled}")
                    
                    # Check credential characteristics (without exposing them)
                    print(f"📏 Email length: {len(self.username)} chars")
                    print(f"📏 Password length: {len(self.password)} chars")
                    print(f"📧 Email has @: {'@' in self.username}")
                    print(f"📧 Email lowercase: {self.username.lower() == self.username}")
                    print(f"🔑 Password has spaces: {' ' in self.password}")
                    print(f"🔑 Password has special chars: {any(c in self.password for c in '!@#$%^&*()_+-=[]{}|;:,.<>?')}")
                
                print("🚪 Submitting login form...")
                
                # Try multiple ways to submit the form
                submit_success = False
                
                # Method 1: Look for specific login button
                login_selectors = [
                    '*:has-text("Log in"):not(:has(*))',  # Any element with exact text "Log in"
                    'a:has-text("Log in")',  # Link styled as button
                    'input[type="button"][value="Log in"]',  # Input button
                    'input[type="submit"][value="Log in"]',
                    'div:has-text("Log in"):not(:has(div))',  # Div button
                    'span:has-text("Log in")',  # Span button
                    'button:has-text("Log in")',  
                    'button:has-text("Log In")',
                    'input[type="submit"][value*="Login" i]',
                    'input[type="submit"][value*="Log" i]',
                    '#LoginButton',
                    'button[type="submit"]',
                    'input[type="submit"]'
                ]
                
                for selector in login_selectors:
                    try:
                        if page.query_selector(selector):
                            page.click(selector)
                            submit_success = True
                            print(f"✅ Clicked login button: {selector}")
                            
                            # Wait a moment for any client-side validation
                            page.wait_for_timeout(2000)
                            
                            # Check if still on login page with error
                            if "login" in page.url.lower():
                                error_elem = page.query_selector('.uk-alert-danger, .error-message, [class*="error"]')
                                if error_elem:
                                    error_text = error_elem.text_content()
                                    print(f"⚠️  Login error after click: {error_text}")
                            break
                    except:
                        continue
                
                if not submit_success:
                    # Fallback: Try clicking the visible "Log in" button directly
                    try:
                        # Wait a moment for any dynamic rendering
                        page.wait_for_timeout(500)
                        
                        # Find and click the button by its exact text
                        login_btn = page.locator('button:text-is("Log in")')
                        if login_btn.count() > 0:
                            login_btn.click()
                            print("✅ Clicked 'Log in' button by exact text")
                            submit_success = True
                    except:
                        pass
                    
                if not submit_success:
                    # Fallback: Press Enter
                    try:
                        page.keyboard.press('Enter')
                        print("✅ Submitted via Enter key")
                    except:
                        # Last resort: JavaScript submit
                        page.evaluate('document.forms[0].submit()')
                        print("✅ Submitted via JavaScript")
                
                print("⏳ Waiting for dashboard to load...")
                
                # First wait for any navigation
                try:
                    page.wait_for_load_state('load', timeout=10000)
                except:
                    pass
                
                # Wait for navigation with multiple conditions
                try:
                    # Wait for either URL change or SVG presence
                    page.wait_for_function(
                        '''() => {
                            return window.location.href.includes('BookingPortal') || 
                                   window.location.href.includes('booking') ||
                                   window.location.href.includes('dashboard') ||
                                   document.querySelector('svg') !== null ||
                                   document.querySelector('img[src*="QR" i]') !== null;
                        }''',
                        timeout=15000
                    )
                except PlaywrightTimeout:
                    print("⚠️  Timeout waiting for dashboard, checking current state...")
                
                # Take screenshot after login attempt
                if not headless:
                    page.screenshot(path="debug_after_login.png")
                
                # In CI, always take screenshot for debugging
                if os.getenv('CI'):
                    page.screenshot(path="debug_ci_after_login.png")
                    print("📸 Debug screenshot saved: debug_ci_after_login.png")
                
                # Check current URL
                current_url = page.url
                print(f"📍 Current URL: {current_url}")
                
                # Check if login was successful
                if "login" in current_url.lower():
                    print("⚠️  Still on login page - authentication may have failed")
                    # Get page title for more context
                    title = page.title()
                    print(f"📄 Page title: {title}")
                    
                    # Check for error messages
                    error_selectors = [
                        '.error', '.alert', '.warning', '.message',
                        '[class*="error"]', '[class*="alert"]', '[id*="error"]'
                    ]
                    for selector in error_selectors:
                        try:
                            error_element = page.query_selector(selector)
                            if error_element:
                                error_text = error_element.text_content()
                                if error_text and error_text.strip():
                                    print(f"❌ Error message found: {error_text.strip()}")
                                    break
                        except:
                            pass
                
                # Look for QR code
                print("🔍 Looking for QR code...")
                
                # Take a debug screenshot
                if not headless:
                    page.screenshot(path="debug_page_loaded.png")
                
                # Try to find SVG elements
                svg_elements = page.query_selector_all('svg')
                
                if not svg_elements:
                    # Wait a bit more and try again
                    page.wait_for_timeout(3000)
                    svg_elements = page.query_selector_all('svg')
                    
                # Also check for img elements that might contain QR codes
                img_elements = page.query_selector_all('img[src*="QR"], img[src*="qr"], img[alt*="QR"], img[alt*="qr"]')
                if img_elements:
                    print(f"📷 Found {len(img_elements)} QR image elements")
                
                if svg_elements:
                    print(f"✅ Found {len(svg_elements)} SVG elements")
                    
                    # Wait for QR code SVG to have proper dimensions (21x21 grid = 441+ rectangles for version 1)
                    # or at least 200+ rectangles for a valid QR code
                    print("⏳ Waiting for QR code to fully render...")
                    try:
                        page.wait_for_function(
                            '''() => {
                                const svgs = document.querySelectorAll('svg');
                                for (const svg of svgs) {
                                    const rects = svg.querySelectorAll('rect');
                                    // QR codes have many small rectangles, logos have few
                                    if (rects.length > 200) {
                                        return true;
                                    }
                                }
                                return false;
                            }''',
                            timeout=10000
                        )
                    except PlaywrightTimeout:
                        print("⚠️  Timeout waiting for QR code to render fully")
                    
                    # Find the QR code SVG specifically (has many rectangles)
                    qr_svg = None
                    max_rectangles = 0
                    
                    for i, svg in enumerate(svg_elements):
                        try:
                            # Count rectangles directly in browser for accuracy
                            rect_count = svg.evaluate('(element) => element.querySelectorAll("rect").length')
                            html = svg.evaluate('(element) => element.outerHTML')
                            
                            print(f"   SVG {i+1}: {len(html)} characters, {rect_count} rectangles")
                            
                            # QR codes have 200+ rectangles, logos typically have < 50
                            if rect_count > 200 and rect_count > max_rectangles:
                                max_rectangles = rect_count
                                qr_svg = html
                                
                            # Debug preview
                            if len(html) < 1000:
                                preview = html[:200].replace('\n', ' ')
                                print(f"   Preview: {preview}...")
                        except:
                            continue
                    
                    if qr_svg:
                        # Save QR code
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                        filename = f"real_qr_codes/{timestamp}.svg"
                        
                        with open(filename, 'w') as f:
                            f.write(qr_svg)
                        
                        print(f"💾 QR code saved: {filename}")
                        print(f"📏 Size: {len(qr_svg)} characters")
                        print(f"📊 Rectangles: {max_rectangles}")
                        
                        # Update database
                        self.update_database()
                        
                        browser.close()
                        return filename
                    else:
                        print("❌ No valid QR code SVG found (need 200+ rectangles)")
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
                print("📊 Database updated successfully")
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