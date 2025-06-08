# Rise Gym QR Code App - APK Release

## Download
[Download RiseGymQR-debug.apk](./RiseGymQR-debug.apk)

## Features
- **Local Generation**: Generate QR codes using the discovered pattern
- **GitHub Sync**: Pull real QR codes from the private repository (requires Personal Access Token)
- **Toggle Mode**: Switch between local generation and GitHub sync
- **Auto-brightness**: Maximizes screen brightness for easy scanning
- **Battery Optimization**: Adaptive refresh rates based on battery level

## Installation
1. Download the APK file
2. Enable "Install from Unknown Sources" in Android settings
3. Open the APK file to install

## Setup for Private Repository Access
1. Toggle to "GitHub QR Codes" mode
2. You'll be prompted for a GitHub Personal Access Token
3. Create a token:
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Click "Generate new token (classic)"
   - Select the `repo` scope
   - Generate and copy the token
4. Paste the token in the app (format: `ghp_xxxxxxxxxxxx`)
5. Click Save

## Requirements
- Android 7.0 (API 24) or higher
- Internet connection (for GitHub mode)
- GitHub Personal Access Token (for private repo access)

## Security Note
This is a debug build and not recommended for production use. The GitHub token is stored in SharedPreferences without encryption.

## Version Info
- Build Date: June 8, 2025
- Version: Debug Build
- Package: com.risegym.qrpredictor