# Firebase Setup Guide for Rise Gym QR App

## Overview
This guide explains how to set up Firebase for the Rise Gym QR Android application. The app now uses Firebase Storage as the sole source for QR codes, eliminating all local generation and other cloud sources.

## Prerequisites
- Firebase account
- Android Studio installed
- Basic knowledge of Firebase console

## Setup Steps

### 1. Create Firebase Project
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Create a project"
3. Name it "RiseGymQR" or similar
4. Follow the setup wizard (you can disable Google Analytics if not needed)

### 2. Add Android App to Firebase
1. In Firebase Console, click "Add app" and select Android
2. Enter package name: `com.risegym.qrpredictor`
3. Download the `google-services.json` file
4. Place it in `android_qr_app/app/` directory

### 3. Enable Firebase Storage
1. In Firebase Console, go to "Storage" in the left menu
2. Click "Get Started"
3. Choose security rules (start with test mode for development):
   ```
   rules_version = '2';
   service firebase.storage {
     match /b/{bucket}/o {
       match /qr_codes/{allPaths=**} {
         allow read: if true;
         allow write: if request.auth != null;
       }
     }
   }
   ```

### 4. Storage Structure
Create the following folder structure in Firebase Storage:
```
qr_codes/
  ├── latest.svg          # Always contains the current QR code
  ├── slot_0000-0159.svg  # Time slot specific QR codes
  ├── slot_0200-0359.svg
  ├── slot_0400-0559.svg
  ├── slot_0600-0759.svg
  ├── slot_0800-0959.svg
  ├── slot_1000-1159.svg
  ├── slot_1200-1359.svg
  ├── slot_1400-1559.svg
  ├── slot_1600-1759.svg
  ├── slot_1800-1959.svg
  ├── slot_2000-2159.svg
  └── slot_2200-2359.svg
```

### 5. Upload QR Codes
You can upload QR codes manually through Firebase Console or use the provided Python script:

```python
import firebase_admin
from firebase_admin import credentials, storage
import os

# Initialize Firebase Admin
cred = credentials.Certificate('path/to/serviceAccountKey.json')
firebase_admin.initialize_app(cred, {
    'storageBucket': 'your-project-id.appspot.com'
})

bucket = storage.bucket()

# Upload a QR code
def upload_qr_code(local_path, storage_path, time_slot):
    blob = bucket.blob(storage_path)
    
    # Set metadata
    metadata = {
        'timeSlot': time_slot,
        'contentType': 'image/svg+xml'
    }
    blob.metadata = metadata
    
    # Upload file
    blob.upload_from_filename(local_path)
    print(f"Uploaded {local_path} to {storage_path}")

# Example usage
upload_qr_code('qr_1800.svg', 'qr_codes/latest.svg', '18:00-19:59')
upload_qr_code('qr_1800.svg', 'qr_codes/slot_1800-1959.svg', '18:00-19:59')
```

### 6. App Configuration
The app is already configured to use Firebase. Key components:

- **FirebaseQRService.kt**: Handles all Firebase Storage operations
- **MainActivity.kt**: Simplified to only fetch from Firebase
- **SVGUtils.kt**: Parses SVG files to display as bitmaps

### 7. Testing
1. Build and run the app
2. Check Firebase Console for read operations
3. Verify QR codes are displayed correctly
4. Monitor error logs in Android Studio

## Key Features

### Automatic Updates
- App checks for new QR codes every 30 seconds
- Fetches new QR at the start of each 2-hour time slot
- Prefetches upcoming time slots for smooth transitions

### Error Handling
- Graceful fallback if specific time slot not found
- Clear error messages displayed to user
- Automatic retry on network failures

### Performance
- SVG files are lightweight (~15KB)
- Bitmaps are recycled properly to prevent memory leaks
- Firebase Storage provides fast CDN delivery

## Security Considerations

### Production Rules
For production, update Firebase Storage rules:
```
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /qr_codes/{allPaths=**} {
      // Only allow read access
      allow read: if true;
      // Only allow write from backend/admin
      allow write: if false;
    }
  }
}
```

### Best Practices
1. Use Firebase App Check to prevent unauthorized access
2. Set up monitoring alerts for unusual read patterns
3. Implement caching to reduce Firebase usage costs
4. Use Cloud Functions to automatically update QR codes

## Troubleshooting

### Common Issues

1. **"No QR code available"**
   - Check if `latest.svg` exists in Firebase Storage
   - Verify internet connection
   - Check Firebase Storage rules

2. **"Failed to parse QR code"**
   - Ensure uploaded files are valid SVG format
   - Check SVG content structure (should contain rect elements)

3. **"Error: Permission denied"**
   - Review Firebase Storage security rules
   - Ensure app has internet permission in AndroidManifest.xml

### Debug Mode
Enable debug logging by adding to MainActivity:
```kotlin
if (BuildConfig.DEBUG) {
    FirebaseStorage.getInstance().setLogLevel(Logger.Level.DEBUG)
}
```

## Cost Optimization

Firebase Storage free tier includes:
- 5GB storage
- 1GB/day download
- 20K/day upload operations
- 50K/day download operations

To optimize costs:
1. Use appropriate SVG compression
2. Implement client-side caching
3. Set up lifecycle rules to delete old QR codes
4. Monitor usage in Firebase Console

## Next Steps

1. Set up Cloud Functions to automatically generate and upload QR codes
2. Implement Firebase Performance Monitoring
3. Add Firebase Crashlytics for error tracking
4. Consider Firebase Remote Config for feature flags