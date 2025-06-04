#!/usr/bin/env python3
"""
QR Hourly Monitor - Background QR code collection every hour
Monitors for QR code changes over time with automatic PNG conversion
"""

import os
import time
import hashlib
import schedule
import logging
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
import subprocess

class QRHourlyMonitor:
    def __init__(self):
        # Load environment
        load_dotenv()
        self.username = os.getenv('USERNAME')
        self.password = os.getenv('PASSWORD')
        self.login_url = "https://risegyms.ez-runner.com/login.aspx"
        
        # Setup directories
        self.svg_dir = Path("real_qr_codes")
        self.png_dir = Path("qr_monitor_png") 
        self.svg_dir.mkdir(exist_ok=True)
        self.png_dir.mkdir(exist_ok=True)
        
        # Setup logging (silent - only errors to file)
        logging.basicConfig(
            filename='qr_monitor.log',
            level=logging.ERROR,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Track last known hash and comparison
        self.last_hash = None
        self.last_svg_content = None
        self.change_count = 0
        self.total_samples = 0
        
        # Load previous state if available
        self.load_previous_state()
    
    def load_previous_state(self):
        """Load previous monitoring state from file"""
        try:
            import json
            state_file = Path('qr_monitor_state.json')
            
            # If state file exists, load it
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)
                
                self.last_hash = state.get('last_hash')
                self.change_count = state.get('change_count', 0)
                self.total_samples = state.get('total_samples', 0)
            else:
                # No state file - check if we have existing SVG files
                svg_files = list(self.svg_dir.glob('*.svg'))
                if svg_files:
                    # Initialize state from existing files
                    self.total_samples = len(svg_files)
                    latest_svg = max(svg_files, key=lambda p: p.stat().st_mtime)
                    
                    # Load the most recent SVG to use as comparison baseline
                    try:
                        with open(latest_svg, 'r') as f:
                            self.last_svg_content = f.read()
                            self.last_hash = hashlib.md5(self.last_svg_content.encode()).hexdigest()
                    except:
                        pass
            
            # Always try to load the latest SVG content if we have a hash
            if self.last_hash:
                svg_files = list(self.svg_dir.glob('*.svg'))
                if svg_files:
                    latest_svg = max(svg_files, key=lambda p: p.stat().st_mtime)
                    try:
                        with open(latest_svg, 'r') as f:
                            content = f.read()
                            content_hash = hashlib.md5(content.encode()).hexdigest()
                            if content_hash == self.last_hash:
                                self.last_svg_content = content
                    except:
                        pass
                        
        except Exception:
            pass  # Start fresh if state loading fails
    
    def save_state(self):
        """Save current monitoring state to file"""
        try:
            import json
            state = {
                'last_hash': self.last_hash,
                'change_count': self.change_count,
                'total_samples': self.total_samples,
                'last_update': datetime.now().isoformat()
            }
            
            with open('qr_monitor_state.json', 'w') as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass  # Fail silently
    
    def update_database(self):
        """Update the QR code database after saving a new file"""
        try:
            result = subprocess.run(['python', 'qr_database.py'], 
                                  capture_output=True, text=True, cwd='.')
            if result.returncode != 0:
                logging.error(f"Database update failed: {result.stderr}")
        except Exception as e:
            logging.error(f"Could not update database: {e}")
        
    def get_current_timestamp(self):
        """Get current timestamp in YYYYMMDDHHMM format"""
        return datetime.now().strftime("%Y%m%d%H%M")
    
    def setup_headless_driver(self):
        """Setup headless Chrome driver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--log-level=3")
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            return driver
        except Exception:
            return None
    
    def login_silently(self, driver):
        """Login to Rise Gym (silent failure)"""
        try:
            driver.get(self.login_url)
            wait = WebDriverWait(driver, 15)
            
            # Wait for page load and form
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "form")))
            time.sleep(2)  # Extra wait for form to be ready
            
            # Find email input using multiple strategies
            email_input = None
            email_selectors = [
                'input[type="email"]',
                'input[name*="email" i]',
                'input[id*="email" i]',
                'input[placeholder*="email" i]'
            ]
            
            for selector in email_selectors:
                try:
                    email_input = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if not email_input:
                # Fallback - find first input in form
                email_input = driver.find_element(By.CSS_SELECTOR, 'form input:first-of-type')
            
            # Ensure element is interactable
            wait.until(EC.element_to_be_clickable(email_input))
            email_input.clear()
            email_input.send_keys(self.username)
            
            # Find password input using multiple strategies
            password_input = None
            password_selectors = [
                'input[type="password"]',
                'input[name*="password" i]',
                'input[id*="password" i]',
                'input[placeholder*="password" i]'
            ]
            
            for selector in password_selectors:
                try:
                    password_input = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if not password_input:
                # Fallback - find second input in form
                inputs = driver.find_elements(By.CSS_SELECTOR, 'form input')
                if len(inputs) >= 2:
                    password_input = inputs[1]
            
            # Ensure element is interactable
            wait.until(EC.element_to_be_clickable(password_input))
            password_input.clear()
            password_input.send_keys(self.password)
            
            # Submit form using JavaScript (most reliable)
            time.sleep(1)
            driver.execute_script("document.forms[0].submit();")
            
            # Wait for navigation away from login page
            time.sleep(5)
            
            # Check if login was successful by looking for QR or welcome message
            try:
                wait.until(lambda d: "hello" in d.page_source.lower() or 
                                   d.find_elements(By.TAG_NAME, "svg"))
                return True
            except:
                return False
            
        except Exception as e:
            logging.error(f"Login failed: {e}")
            return False
    
    def extract_qr_svg(self, driver, timestamp):
        """Extract QR SVG content and save"""
        try:
            wait = WebDriverWait(driver, 10)
            
            # Wait for SVG elements to be present (the QR code)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "svg")))
            
            # Find SVG elements
            svg_elements = driver.find_elements(By.TAG_NAME, "svg")
            
            if not svg_elements:
                return None
            
            # Get the first (and likely only) SVG - this should be the QR code
            svg_element = svg_elements[0]
            svg_content = svg_element.get_attribute('outerHTML')
            
            if not svg_content or len(svg_content) < 1000:
                return None
            
            # Create hash for comparison
            svg_hash = hashlib.md5(svg_content.encode()).hexdigest()
            
            # Compare with previous QR
            comparison_result = self.compare_with_previous(svg_content, svg_hash)
            
            # Save SVG file
            svg_filename = f"{timestamp}.svg"
            svg_path = self.svg_dir / svg_filename
            
            with open(svg_path, 'w') as f:
                f.write(svg_content)
            
            # Convert to PNG
            png_success = self.convert_svg_to_png(svg_path, timestamp)
            
            # Update tracking
            self.last_hash = svg_hash
            self.last_svg_content = svg_content
            self.total_samples += 1
            
            # Save state for persistence
            self.save_state()
            
            # Update database
            self.update_database()
            
            return {
                'timestamp': timestamp,
                'hash': svg_hash,
                'length': len(svg_content),
                'comparison': comparison_result,
                'png_converted': png_success,
                'saved': True
            }
            
        except Exception as e:
            logging.error(f"QR extraction failed: {e}")
            return None
    
    def compare_with_previous(self, current_svg, current_hash):
        """Compare current QR with previous QR and return comparison result"""
        if self.last_hash is None:
            # First sample
            return {
                'status': 'FIRST',
                'message': 'This is the FIRST QR code sample',
                'is_different': False
            }
        
        if current_hash == self.last_hash:
            # Same QR
            return {
                'status': 'SAME',
                'message': 'This is the SAME as the previous QR code',
                'is_different': False
            }
        else:
            # Different QR
            self.change_count += 1
            logging.error(f"QR CHANGE DETECTED! Count: {self.change_count}, New Hash: {current_hash}, Previous: {self.last_hash}")
            
            # Try to identify what changed
            differences = self.analyze_differences(current_svg, self.last_svg_content)
            
            return {
                'status': 'DIFFERENT',
                'message': 'This is DIFFERENT from the previous QR code',
                'is_different': True,
                'change_count': self.change_count,
                'differences': differences,
                'new_hash': current_hash,
                'previous_hash': self.last_hash
            }
    
    def analyze_differences(self, current_svg, previous_svg):
        """Analyze what differences exist between two SVG contents"""
        if not previous_svg:
            return "No previous SVG to compare"
        
        differences = []
        
        # Length comparison
        if len(current_svg) != len(previous_svg):
            differences.append(f"Length changed: {len(previous_svg)} → {len(current_svg)}")
        
        # Simple character-level differences
        if current_svg != previous_svg:
            # Count differing positions
            diff_count = sum(1 for a, b in zip(current_svg, previous_svg) if a != b)
            if len(current_svg) != len(previous_svg):
                diff_count += abs(len(current_svg) - len(previous_svg))
            
            differences.append(f"Character differences: {diff_count}")
            
            # Try to find specific patterns that changed
            import re
            current_rects = re.findall(r'<rect[^>]+>', current_svg)
            previous_rects = re.findall(r'<rect[^>]+>', previous_svg)
            
            if len(current_rects) != len(previous_rects):
                differences.append(f"Rectangle count changed: {len(previous_rects)} → {len(current_rects)}")
            
        return differences if differences else ["Content differs but specific changes unclear"]
    
    def convert_svg_to_png(self, svg_path, timestamp):
        """Convert SVG to PNG using available tools"""
        try:
            png_filename = f"{timestamp}.png"
            png_path = self.png_dir / png_filename
            
            # Try cairosvg first (if available)
            try:
                import cairosvg
                cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=580, output_height=580)
                return True
            except (ImportError, Exception):
                pass
            
            # Try rsvg-convert (usually available on macOS with brew)
            try:
                result = subprocess.run([
                    'rsvg-convert',
                    '-w', '580', '-h', '580',
                    '-o', str(png_path),
                    str(svg_path)
                ], capture_output=True, timeout=30, check=False)
                if result.returncode == 0 and png_path.exists():
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            # Try convert (ImageMagick)
            try:
                result = subprocess.run([
                    'convert',
                    '-background', 'white',
                    '-density', '200',
                    str(svg_path),
                    str(png_path)
                ], capture_output=True, timeout=30, check=False)
                if result.returncode == 0 and png_path.exists():
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            # Try inkscape
            try:
                result = subprocess.run([
                    'inkscape', 
                    '--export-type=png',
                    '--export-filename', str(png_path),
                    '--export-width', '580',
                    '--export-height', '580',
                    str(svg_path)
                ], capture_output=True, timeout=30, check=False)
                if result.returncode == 0 and png_path.exists():
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            # Simple fallback - just copy SVG as text reference
            try:
                with open(png_path.with_suffix('.txt'), 'w') as f:
                    f.write(f"SVG->PNG conversion failed for {svg_path.name}\n")
                    f.write("Install: brew install librsvg imagemagick\n")
                    f.write(f"Original SVG: {svg_path}")
                return False
            except:
                pass
                
            return False
            
        except Exception as e:
            logging.error(f"PNG conversion failed: {e}")
            return False
    
    def collect_qr_sample(self):
        """Collect a single QR sample (main scheduled function)"""
        timestamp = self.get_current_timestamp()
        driver = None
        
        try:
            # Setup driver
            driver = self.setup_headless_driver()
            if not driver:
                return
            
            # Login
            if not self.login_silently(driver):
                return
            
            # Extract QR
            result = self.extract_qr_svg(driver, timestamp)
            
            if result:
                # Display comparison result prominently
                comparison = result['comparison']
                print(f"\n🔍 COMPARISON RESULT:")
                print(f"   {comparison['message']}")
                
                if comparison['status'] == 'DIFFERENT':
                    print(f"   🚨 CHANGE #{comparison['change_count']} DETECTED!")
                    print(f"   Previous hash: {comparison['previous_hash']}")
                    print(f"   New hash: {comparison['new_hash']}")
                    if 'differences' in comparison:
                        print(f"   Differences: {', '.join(comparison['differences'])}")
                elif comparison['status'] == 'SAME':
                    print(f"   ✅ No changes detected")
                elif comparison['status'] == 'FIRST':
                    print(f"   📊 Starting comparison baseline")
                
                # Create status file for monitoring
                status = {
                    'last_collection': timestamp,
                    'total_samples': self.total_samples,
                    'changes_detected': self.change_count,
                    'last_hash': self.last_hash,
                    'last_comparison': comparison['status']
                }
                
                with open('qr_monitor_status.txt', 'w') as f:
                    f.write(f"Last: {timestamp}\n")
                    f.write(f"Samples: {self.total_samples}\n")
                    f.write(f"Changes: {self.change_count}\n")
                    f.write(f"Last comparison: {comparison['status']}\n")
                    f.write(f"Hash: {self.last_hash}\n")
            
        except Exception as e:
            logging.error(f"Collection failed: {e}")
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    def start_interactive_monitoring(self):
        """Start interactive command-based monitoring"""
        print("🕐 QR Interactive Monitor")
        print(f"📁 SVG files: {self.svg_dir}")
        print(f"📁 PNG files: {self.png_dir}")
        print("🔕 Fails silently - check qr_monitor.log for errors")
        print("📊 Status: qr_monitor_status.txt")
        print("\n💡 Commands:")
        print("  'c' or 'collect' - Collect QR sample now")
        print("  's' or 'status'  - Show current status")
        print("  'q' or 'quit'    - Exit monitor")
        print("  'h' or 'help'    - Show this help")
        print("\n✅ Ready for commands (press Enter after each command):\n")
        
        try:
            while True:
                try:
                    command = input("QR Monitor> ").strip().lower()
                    
                    if command in ['c', 'collect']:
                        print("📊 Collecting QR sample...")
                        self.collect_qr_sample()
                        print(f"✅ Sample collected. Total: {self.total_samples}, Changes: {self.change_count}")
                        
                    elif command in ['s', 'status']:
                        self.quick_status()
                        
                    elif command in ['q', 'quit', 'exit']:
                        break
                        
                    elif command in ['h', 'help']:
                        print("\n💡 Commands:")
                        print("  'c' or 'collect' - Collect QR sample now")
                        print("  's' or 'status'  - Show current status")
                        print("  'q' or 'quit'    - Exit monitor")
                        print("  'h' or 'help'    - Show this help")
                        print()
                        
                    elif command == '':
                        continue  # Empty input, just prompt again
                        
                    else:
                        print(f"❓ Unknown command: '{command}'. Type 'h' for help.")
                        
                except EOFError:
                    break
                except KeyboardInterrupt:
                    break
                    
        except KeyboardInterrupt:
            pass
            
        print(f"\n🛑 Monitor stopped")
        print(f"📊 Total samples collected: {len(list(self.svg_dir.glob('*.svg')))}")
        print(f"🔄 Changes detected: {self.change_count}")
    
    def start_auto_monitoring(self):
        """Start automatic hourly monitoring (original behavior)"""
        print("🕐 QR Auto Monitor Started")
        print(f"📁 SVG files: {self.svg_dir}")
        print(f"📁 PNG files: {self.png_dir}")
        print("⏰ Collecting every hour at :00 minutes")
        print("🔕 Running silently - check qr_monitor.log for errors")
        print("📊 Status: qr_monitor_status.txt")
        print("\n✅ Press Ctrl+C to stop\n")
        
        # Schedule hourly collection at the top of each hour
        schedule.every().hour.at(":00").do(self.collect_qr_sample)
        
        # Also collect one sample now for immediate feedback
        print(f"📊 Collecting initial sample...")
        self.collect_qr_sample()
        
        initial_samples = len(list(self.svg_dir.glob('*.svg')))
        print(f"✅ Initial sample collected. Total samples: {initial_samples}")
        
        # Run scheduler
        try:
            while True:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds
        except KeyboardInterrupt:
            print(f"\n🛑 Monitoring stopped")
            print(f"📊 Total samples collected: {len(list(self.svg_dir.glob('*.svg')))}")
            print(f"🔄 Changes detected: {self.change_count}")
    
    def quick_status(self):
        """Show current monitoring status"""
        svg_count = len(list(self.svg_dir.glob('*.svg')))
        png_count = len(list(self.png_dir.glob('*.png')))
        
        print(f"📊 QR Monitor Status:")
        print(f"   Total samples: {self.total_samples}")
        print(f"   SVG files: {svg_count}")
        print(f"   PNG files: {png_count}")
        print(f"   Changes detected: {self.change_count}")
        print(f"   Last hash: {self.last_hash}")
        
        if svg_count > 0:
            latest_svg = max(self.svg_dir.glob('*.svg'), key=lambda p: p.stat().st_mtime)
            print(f"   Latest sample: {latest_svg.name}")
            
        if self.total_samples == 0:
            print(f"   Status: No samples collected yet")
        elif self.change_count == 0 and self.total_samples > 1:
            print(f"   Status: All QR codes are IDENTICAL")
        elif self.change_count > 0:
            print(f"   Status: {self.change_count} change(s) detected!")
        else:
            print(f"   Status: Ready for comparison")

def install_dependencies():
    """Try to install cairosvg for better PNG conversion"""
    try:
        import cairosvg
        print("✅ cairosvg already available")
    except (ImportError, OSError) as e:
        if "cairo" in str(e).lower():
            print("⚠️  Cairo library not found - will use system tools for PNG conversion")
        else:
            print("📦 Installing cairosvg for PNG conversion...")
            try:
                subprocess.run(['pip', 'install', 'cairosvg'], capture_output=True)
                print("✅ cairosvg installed")
            except:
                print("⚠️  cairosvg install failed - will use system tools")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        monitor = QRHourlyMonitor()
        monitor.quick_status()
    elif len(sys.argv) > 1 and sys.argv[1] == "--install":
        install_dependencies()
    elif len(sys.argv) > 1 and sys.argv[1] == "--auto":
        print("🔬 QR Auto Monitor")
        print("Automated QR code collection every hour")
        print("=" * 50)
        
        # Try to install dependencies
        install_dependencies()
        
        # Start automatic monitoring
        monitor = QRHourlyMonitor()
        monitor.start_auto_monitoring()
    elif len(sys.argv) > 1 and sys.argv[1] == "--collect":
        # Single collection
        print("📊 Single QR Collection")
        print("=" * 30)
        monitor = QRHourlyMonitor()
        monitor.collect_qr_sample()
        monitor.quick_status()
    elif len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("🔬 QR Monitor - Usage")
        print("=" * 30)
        print("python qr_hourly_monitor.py                # Interactive mode")
        print("python qr_hourly_monitor.py --auto         # Auto hourly collection")
        print("python qr_hourly_monitor.py --collect      # Single collection")
        print("python qr_hourly_monitor.py --status       # Show status")
        print("python qr_hourly_monitor.py --install      # Install dependencies")
        print("python qr_hourly_monitor.py --help         # Show this help")
        print()
        print("📁 Files saved to:")
        print("   qr_monitor_svg/     # SVG files")
        print("   qr_monitor_png/     # PNG files")
        print("   qr_monitor.log      # Error log")
        print("   qr_monitor_status.txt # Current status")
    else:
        print("🔬 QR Interactive Monitor")
        print("Manual QR code collection on command")
        print("=" * 50)
        
        # Try to install dependencies
        install_dependencies()
        
        # Start interactive monitoring (default mode)
        monitor = QRHourlyMonitor()
        monitor.start_interactive_monitoring()