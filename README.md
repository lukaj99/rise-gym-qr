# Rise Gym QR Android App

A simplified Android application that displays QR codes for Rise Gym access, fetching them from Firebase Storage.

## Overview

This app provides a clean, reliable way to access Rise Gym by displaying QR codes that are fetched from Firebase Storage. The app automatically updates QR codes based on 2-hour time slots throughout the day.

## Key Features

- **Cloud-Based QR Codes**: All QR codes are stored and served from Firebase Storage
- **Automatic Updates**: Fetches the latest QR code for the current time slot
- **Offline Support**: Caches the current QR code for reliability
- **Maximum Brightness**: Automatically sets screen to maximum brightness for easy scanning
- **Clean UI**: Simple, focused interface optimized for QR code display

## Architecture

The app follows a simplified cloud-first architecture:

```
Firebase Storage
      ↓
FirebaseQRService
      ↓
  MainActivity
      ↓
   SVGUtils
      ↓
QR Code Display
```

### Components

- **FirebaseQRService**: Handles all Firebase Storage operations
- **MainActivity**: Simple UI that displays the QR code
- **SVGUtils**: Parses SVG files into displayable bitmaps

## Setup

### 1. Firebase Configuration

1. Create a Firebase project in the [Firebase Console](https://console.firebase.google.com/)
2. Add your Android app (package: `com.risegym.qrpredictor`)
3. Download `google-services.json` and place it in `android_qr_app/app/`
4. Enable Firebase Storage
5. See `FIREBASE_SETUP.md` for detailed instructions

### 2. Upload QR Codes

Use the provided Python script to upload QR codes to Firebase:

```bash
pip install -r requirements.txt
python upload_to_firebase.py ./firebase-key.json your-project.appspot.com ./real_qr_codes
```

### 3. Build and Run

1. Open the project in Android Studio
2. Sync Gradle files
3. Run the app on your device

## Time Slots

The app operates on 2-hour time slots:
- 00:00 - 01:59
- 02:00 - 03:59
- 04:00 - 05:59
- 06:00 - 07:59
- 08:00 - 09:59
- 10:00 - 11:59
- 12:00 - 13:59
- 14:00 - 15:59
- 16:00 - 17:59
- 18:00 - 19:59
- 20:00 - 21:59
- 22:00 - 23:59

## Firebase Storage Structure

```
qr_codes/
├── latest.svg              # Current QR code
├── slot_0000-0159.svg     # Time slot specific QR codes
├── slot_0200-0359.svg
├── ...
└── slot_2200-2359.svg
```

## Performance

- QR codes are fetched on-demand with automatic caching
- SVG format keeps file sizes small (~15KB)
- Firebase Storage provides fast CDN delivery
- Automatic prefetching of upcoming time slots

## Security

- Read-only access to Firebase Storage
- No user authentication required
- No sensitive data stored locally
- See Firebase security rules in `FIREBASE_SETUP.md`

## Troubleshooting

### "No QR code available"
- Check internet connection
- Verify Firebase Storage has the required files
- Check Firebase console for any errors

### "Failed to parse QR code"
- Ensure uploaded SVG files are valid
- Check Android Studio logs for parsing errors

## Development

### Requirements
- Android Studio Arctic Fox or newer
- Kotlin 1.8+
- Android SDK 24+
- Firebase project with Storage enabled

### Building
```bash
cd android_qr_app
./gradlew assembleDebug
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is proprietary software for Rise Gym use only.