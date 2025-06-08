# Firebase Setup Guide

This guide explains how to set up Firebase Realtime Database for instant QR code syncing.

## Benefits of Firebase Integration

- **Instant Updates**: QR codes appear on your phone the moment they're scraped
- **No Polling**: No need to repeatedly check GitHub API
- **Lower Battery Usage**: More efficient than polling
- **Real-time Sync**: Multiple devices stay in sync automatically
- **Free Tier**: Generous free tier is perfect for personal use

## Setup Steps

### 1. Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Click "Create a project"
3. Name it (e.g., "rise-gym-qr")
4. Disable Google Analytics (not needed)
5. Click "Create project"

### 2. Set up Realtime Database

1. In Firebase Console, click "Realtime Database" in the left menu
2. Click "Create Database"
3. Choose a location close to you
4. Start in "test mode" for now (we'll secure it later)
5. Click "Enable"

### 3. Get Database URL

1. In the Realtime Database section, you'll see your database URL
2. It looks like: `https://YOUR-PROJECT-ID.firebaseio.com`
3. Copy this URL

### 4. Configure Android App

1. In Firebase Console, click the gear icon → "Project settings"
2. Click "Add app" → Android
3. Enter package name: `com.risegym.qrpredictor`
4. Register the app
5. Download `google-services.json`
6. Replace the placeholder file in `android_qr_app/app/google-services.json`

### 5. Set up GitHub Actions Secrets

Add these secrets to your GitHub repository:

1. Go to your GitHub repo → Settings → Secrets and variables → Actions
2. Add new repository secrets:
   - `FIREBASE_DATABASE_URL`: Your database URL from step 3
   - `FIREBASE_AUTH_TOKEN`: (Optional) For secured databases

### 6. Secure Your Database (Important!)

Replace the default rules with these to ensure only your GitHub Actions can write:

```json
{
  "rules": {
    ".read": true,
    ".write": false,
    "latest": {
      ".write": "auth != null || true"  // Temporarily allow writes
    },
    "qr_codes": {
      ".write": "auth != null || true"  // Temporarily allow writes
    }
  }
}
```

For production, you should:
1. Enable Firebase Authentication
2. Create a service account
3. Use proper authentication in GitHub Actions

### 7. Test the Setup

1. Manually trigger the GitHub Actions workflow
2. Check Firebase Console → Realtime Database → Data
3. You should see QR codes appearing under `latest` and `qr_codes`
4. Open the Android app and select "Firebase Real-time" option
5. QR codes should appear instantly!

## Database Structure

```
{
  "latest": {
    "timestamp": "20250108120000",
    "svgContent": "<svg>...</svg>",
    "pattern": "926801082025120000",
    "uploadedAt": 1736337600000
  },
  "qr_codes": {
    "20250108120000": { ... },
    "20250108100000": { ... },
    ...
  }
}
```

## Troubleshooting

- **No data in Firebase**: Check GitHub Actions logs for errors
- **App not updating**: Make sure you replaced `google-services.json`
- **Permission denied**: Check database rules
- **Connection failed**: Verify database URL is correct

## Cost Considerations

Firebase Realtime Database free tier includes:
- 1GB stored
- 10GB/month downloaded
- 100 simultaneous connections

For personal use with QR codes updating every 30 minutes, you'll never exceed the free tier.