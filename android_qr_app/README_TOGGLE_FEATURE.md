# Toggle Feature: GitHub vs Local QR Generation

## Overview
The Android app now includes a toggle switch that allows users to choose between:
1. **GitHub QR Codes**: Fetches the latest QR code from the GitHub repository
2. **Generated QR Codes**: Generates QR codes locally using the discovered pattern

## How It Works

### GitHub Mode
- Fetches QR codes from: `https://github.com/lukaj99/rise-gym-qr/tree/master/real_qr_codes`
- Gets the latest SVG file based on timestamp
- Parses SVG to display as bitmap
- Updates every 30 seconds (since GitHub Actions runs every 30 minutes)
- Shows "FROM GITHUB" status

### Local Mode
- Uses the discovered pattern: `9268 + MMDDYYYY + HHMMSS`
- Generates QR codes in real-time
- Updates based on battery status and interaction
- Shows "GENERATED" status

## User Interface

The toggle switch appears below the Rise Gym header:
- **Title**: Shows current mode ("GitHub QR Codes" or "Generated QR Codes")
- **Subtitle**: Brief description of the mode
- **Switch**: Toggle between modes
- **Preference**: The selection is saved and persists between app launches

## Error Handling

If GitHub mode fails:
- Shows error icon and message in the QR code area
- Common errors:
  - Network connection issues
  - GitHub API rate limits
  - SVG parsing failures

## Implementation Details

### New Classes
1. **GitHubQRService.kt**: Handles GitHub API calls and SVG downloads
2. **SVGUtils.kt**: Parses SVG XML and converts to Bitmap

### Modified Files
1. **MainActivity.kt**: Added toggle UI and dual-mode logic
2. **AndroidManifest.xml**: Already had INTERNET permission

### Dependencies
- OkHttp: For network requests (already included)
- XML Pull Parser: For SVG parsing (built-in)

## Testing

To test the feature:
1. Build and install the app
2. Toggle the switch to "GitHub QR Codes"
3. Wait for the QR code to load from GitHub
4. Toggle back to "Generated QR Codes" 
5. Verify local generation still works

## Future Enhancements
- Cache GitHub QR codes for offline use
- Show timestamp of GitHub QR code
- Add manual refresh button for GitHub mode
- Support for multiple GitHub repositories