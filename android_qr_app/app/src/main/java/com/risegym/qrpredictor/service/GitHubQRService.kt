package com.risegym.qrpredictor.service

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class GitHubQRService {
    companion object {
        private const val TAG = "GitHubQRService"
        private const val REPO_NAME = "lukaj99/rise-gym-qr"
        private const val QR_DIRECTORY = "real_qr_codes"
        private const val MANIFEST_URL = "https://raw.githubusercontent.com/$REPO_NAME/master/$QR_DIRECTORY/manifest.json"
    }

    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    data class QRCodeFile(
        val name: String,
        val downloadUrl: String,
        val timestamp: String
    )

    suspend fun fetchLatestQRCode(): Result<QRCodeFile> = withContext(Dispatchers.IO) {
        try {
            // Fetch the manifest file that lists all available QR codes
            val manifestRequest = Request.Builder()
                .url(MANIFEST_URL)
                .build()

            val manifestResponse = client.newCall(manifestRequest).execute()
            if (!manifestResponse.isSuccessful) {
                Log.e(TAG, "Failed to fetch manifest: ${manifestResponse.code}")
                // If it's a 404, it might be because the repo is private
                if (manifestResponse.code == 404) {
                    return@withContext Result.failure(Exception("Cannot access private repository. Please make the repository public or use local generation."))
                }
                return@withContext Result.failure(Exception("Failed to fetch manifest: ${manifestResponse.code}"))
            }

            val manifestJson = manifestResponse.body?.string() ?: return@withContext Result.failure(Exception("Empty manifest"))
            val manifest = JSONObject(manifestJson)
            
            val qrCodesArray = manifest.getJSONArray("qr_codes")
            if (qrCodesArray.length() == 0) {
                return@withContext Result.failure(Exception("No QR codes found in manifest"))
            }

            // Get the first (latest) QR code
            val latestQR = qrCodesArray.getJSONObject(0)
            val fileName = latestQR.getString("filename")
            val timestamp = latestQR.getString("timestamp")
            val url = latestQR.getString("url")

            Result.success(QRCodeFile(fileName, url, timestamp))
        } catch (e: Exception) {
            Log.e(TAG, "Error fetching latest QR code", e)
            Result.failure(e)
        }
    }

    suspend fun downloadSVGContent(downloadUrl: String): Result<String> = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url(downloadUrl)
                .build()

            val response = client.newCall(request).execute()
            if (!response.isSuccessful) {
                return@withContext Result.failure(Exception("Failed to download SVG: ${response.code}"))
            }

            val svgContent = response.body?.string() ?: return@withContext Result.failure(Exception("Empty SVG content"))
            Result.success(svgContent)
        } catch (e: Exception) {
            Log.e(TAG, "Error downloading SVG content", e)
            Result.failure(e)
        }
    }

    suspend fun getLatestQRCodeSVG(): Result<Pair<String, String>> = withContext(Dispatchers.IO) {
        try {
            // Fetch latest QR code info
            val latestQRResult = fetchLatestQRCode()
            if (latestQRResult.isFailure) {
                return@withContext Result.failure(latestQRResult.exceptionOrNull() ?: Exception("Unknown error"))
            }

            val qrCodeFile = latestQRResult.getOrThrow()
            
            // Download the SVG content
            val svgResult = downloadSVGContent(qrCodeFile.downloadUrl)
            if (svgResult.isFailure) {
                return@withContext Result.failure(svgResult.exceptionOrNull() ?: Exception("Failed to download SVG"))
            }

            val svgContent = svgResult.getOrThrow()
            Result.success(Pair(qrCodeFile.timestamp, svgContent))
        } catch (e: Exception) {
            Log.e(TAG, "Error getting latest QR code SVG", e)
            Result.failure(e)
        }
    }
}