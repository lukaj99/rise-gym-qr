# Cleanup Guide - Files to Remove

## Overview
Since we're simplifying the app to use only Firebase as the cloud-based QR code source, many files can be removed. This guide lists all files that are no longer needed.

## Android App Files to Remove

### Local Generation Components
These files handled local QR code generation which is no longer needed:
- `android_qr_app/app/src/main/java/com/risegym/qrpredictor/QRPatternGenerator.kt`
- `android_qr_app/app/src/main/java/com/risegym/qrpredictor/QRCodeGenerator.kt` 
- `android_qr_app/app/src/main/java/com/risegym/qrpredictor/PixelOptimizer.kt`

### Scraping Components
These files handled web scraping which is no longer needed:
- `android_qr_app/app/src/main/java/com/risegym/qrpredictor/scraping/` (entire directory)
  - `HybridQRFetcher.kt`
  - `OkHttpScraper.kt`
  - `PersistentCookieJar.kt`
  - `WebScraperInterface.kt`
  - `WebViewScraper.kt`

### Alternative Services
These handled GitHub and other sources which are replaced by Firebase:
- `android_qr_app/app/src/main/java/com/risegym/qrpredictor/service/GitHubQRService.kt`
- `android_qr_app/app/src/main/java/com/risegym/qrpredictor/service/GitHubQRServiceDebug.kt`
- `android_qr_app/app/src/main/java/com/risegym/qrpredictor/service/QRUpdateWorker.kt`
- `android_qr_app/app/src/main/java/com/risegym/qrpredictor/TermuxQRService.kt`
- `android_qr_app/app/src/main/java/com/risegym/qrpredictor/TaskerActivity.kt`
- `android_qr_app/app/src/main/java/com/risegym/qrpredictor/TaskerQRService.kt`

### Security Components
No longer needed since we don't store credentials:
- `android_qr_app/app/src/main/java/com/risegym/qrpredictor/security/` (entire directory)
  - `SecureCredentialManager.kt`

## Root Directory Files to Remove

### Old Python Scripts
These scripts are no longer relevant:
- `analyze_qr_details.py`
- `analyze_qr_patterns.py` 
- `analyze_screenshot_qr.py`
- `compare_qr_codes.py`
- `decode_all_qr_codes.py`
- `decode_qr_from_svg.py`
- `decode_qr_screenshot.py`
- `generate_qr_manifest.py`
- `manual_qr_decode.py`
- `push_new_test.py`
- `qr_error_correction_test.py`
- `test_firebase_upload.py` (replaced by `upload_to_firebase.py`)
- `upload_latest_to_firebase.py` (replaced by `upload_to_firebase.py`)

### Old Documentation
- `CLAUDE.md`
- `qr_comparison_summary.md`
- `QRCodeGenerator.kt` (duplicate in root)

### Data Files
- `qr_decode_results.json`

## Files to Keep

### Android App Core Files
- `MainActivity.kt` (simplified version)
- `FirebaseQRService.kt` (new Firebase service)
- `SVGUtils.kt` (still needed for SVG parsing)
- UI theme files
- Layout resources
- App configuration files

### Documentation
- `README.md` (update with new simplified approach)
- `FIREBASE_SETUP.md` (new setup guide)
- `PROJECT_SUMMARY.md` (update to reflect changes)

### Utilities
- `upload_to_firebase.py` (new Firebase upload script)
- `requirements.txt` (update to only include firebase-admin)

## Cleanup Commands

To remove all unnecessary files, run these commands from the project root:

```bash
# Remove local generation components
rm android_qr_app/app/src/main/java/com/risegym/qrpredictor/QRPatternGenerator.kt
rm android_qr_app/app/src/main/java/com/risegym/qrpredictor/QRCodeGenerator.kt
rm android_qr_app/app/src/main/java/com/risegym/qrpredictor/PixelOptimizer.kt

# Remove scraping directory
rm -rf android_qr_app/app/src/main/java/com/risegym/qrpredictor/scraping/

# Remove alternative services
rm android_qr_app/app/src/main/java/com/risegym/qrpredictor/service/GitHubQRService.kt
rm android_qr_app/app/src/main/java/com/risegym/qrpredictor/service/GitHubQRServiceDebug.kt
rm android_qr_app/app/src/main/java/com/risegym/qrpredictor/service/QRUpdateWorker.kt
rm android_qr_app/app/src/main/java/com/risegym/qrpredictor/TermuxQRService.kt
rm android_qr_app/app/src/main/java/com/risegym/qrpredictor/TaskerActivity.kt
rm android_qr_app/app/src/main/java/com/risegym/qrpredictor/TaskerQRService.kt

# Remove security directory
rm -rf android_qr_app/app/src/main/java/com/risegym/qrpredictor/security/

# Remove old Python scripts
rm analyze_qr_details.py analyze_qr_patterns.py analyze_screenshot_qr.py
rm compare_qr_codes.py decode_all_qr_codes.py decode_qr_from_svg.py
rm decode_qr_screenshot.py generate_qr_manifest.py manual_qr_decode.py
rm push_new_test.py qr_error_correction_test.py test_firebase_upload.py
rm upload_latest_to_firebase.py

# Remove old documentation and data files
rm CLAUDE.md qr_comparison_summary.md QRCodeGenerator.kt qr_decode_results.json
```

## Update Dependencies

Update `android_qr_app/app/build.gradle.kts` to remove unused dependencies:
- Remove jsoup (web scraping)
- Keep okhttp (used by Firebase)
- Remove WorkManager if not using background updates

Update `requirements.txt` to only include:
```
firebase-admin
```

## Benefits of Cleanup

1. **Reduced APK Size**: Removing unnecessary code will significantly reduce the app size
2. **Simplified Maintenance**: Less code means easier debugging and updates
3. **Clear Architecture**: Single source of truth (Firebase) makes the app flow clearer
4. **Better Performance**: No local generation overhead or complex fallback logic
5. **Reduced Dependencies**: Fewer external libraries to maintain and update

## Post-Cleanup Steps

1. Clean and rebuild the Android project
2. Test the app thoroughly with Firebase
3. Update documentation to reflect the simplified architecture
4. Consider adding Firebase Performance Monitoring
5. Set up proper Firebase security rules for production