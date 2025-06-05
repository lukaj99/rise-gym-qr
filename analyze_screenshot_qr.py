#!/usr/bin/env python3
"""
Analyze the QR code from screenshot and compare with Android app logic
"""

from datetime import datetime

def analyze_qr_timing():
    """Analyze QR code timing based on screenshot time"""
    
    # Screenshot taken at 19:31 (7:31 PM)
    screenshot_time = "19:31"
    screenshot_hour = 19
    
    # Calculate the 2-hour block for screenshot time
    screenshot_hour_block = (screenshot_hour // 2) * 2  # = 18
    
    # Current time analysis
    now = datetime.now()
    current_hour = now.hour
    current_hour_block = (current_hour // 2) * 2
    
    print("🔍 QR Code Screenshot Analysis")
    print("=" * 50)
    
    print(f"\n📸 Screenshot Details:")
    print(f"   Taken at: {screenshot_time} (7:31 PM)")
    print(f"   Time block: {screenshot_hour_block:02d}:00-{screenshot_hour_block+1:02d}:59")
    
    print(f"\n⏰ Current Time:")
    print(f"   Time: {now.strftime('%H:%M')} ({now.strftime('%-I:%M %p')})")
    print(f"   Time block: {current_hour_block:02d}:00-{current_hour_block+1:02d}:59")
    
    # Generate what Android app would create for screenshot time
    FACILITY_CODE = "9268"
    
    # For screenshot time (19:31 = hour block 18)
    screenshot_date = now.strftime("%m%d%Y")  # Assuming screenshot is from today
    ss_screenshot = "01" if screenshot_hour_block == 0 else "00"
    screenshot_qr_content = f"{FACILITY_CODE}{screenshot_date}{screenshot_hour_block:02d}00{ss_screenshot}"
    
    # For current time
    current_date = now.strftime("%m%d%Y")
    ss_current = "01" if current_hour_block == 0 else "00"
    current_qr_content = f"{FACILITY_CODE}{current_date}{current_hour_block:02d}00{ss_current}"
    
    print(f"\n📱 Android App QR Content:")
    print(f"   For screenshot time ({screenshot_hour_block:02d}:00): {screenshot_qr_content}")
    print(f"   For current time ({current_hour_block:02d}:00): {current_qr_content}")
    
    if screenshot_hour_block == current_hour_block:
        print(f"\n✅ Same time block! QR should be: {current_qr_content}")
    else:
        print(f"\n⚠️  Different time blocks!")
        print(f"   Screenshot block: {screenshot_hour_block:02d}:00-{screenshot_hour_block+1:02d}:59")
        print(f"   Current block: {current_hour_block:02d}:00-{current_hour_block+1:02d}:59")
    
    print(f"\n📊 QR Pattern Breakdown:")
    print(f"   Facility: 9268")
    print(f"   Date: {current_date[0:2]}/{current_date[2:4]}/{current_date[4:8]}")
    print(f"   Hour: {current_hour_block:02d}")
    print(f"   Minutes: 00")
    print(f"   Seconds: {ss_current}")
    
    print("\n💡 Note: The QR in the screenshot encodes this data visually.")
    print("   To verify exact match, we would need to decode the QR image.")

if __name__ == "__main__":
    analyze_qr_timing()