package com.risegym.qrpredictor.service

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class GitHubQRService(private val githubToken: String? = null) {
    companion object {
        private const val TAG = "GitHubQRService"
        private const val REPO_NAME = "lukaj99/rise-gym-qr"
        private const val QR_DIRECTORY = "real_qr_codes"
        private const val API_BASE = "https://api.github.com"
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
            // Use GitHub API to list files in the directory
            val apiUrl = "$API_BASE/repos/$REPO_NAME/contents/$QR_DIRECTORY"
            val requestBuilder = Request.Builder()
                .url(apiUrl)
                .addHeader("Accept", "application/vnd.github.v3+json")
            
            // Add authentication if token is provided
            githubToken?.let {
                requestBuilder.addHeader("Authorization", "Bearer $it")
            }
            
            val request = requestBuilder.build()
            val response = client.newCall(request).execute()
            
            if (!response.isSuccessful) {
                Log.e(TAG, "Failed to fetch files: ${response.code}")
                if (response.code == 401) {
                    return@withContext Result.failure(Exception("Invalid GitHub token. Please check your personal access token."))
                } else if (response.code == 404) {
                    return@withContext Result.failure(Exception("Repository not found or no access. Please check your token has repo scope."))
                }
                return@withContext Result.failure(Exception("Failed to fetch files: ${response.code}"))
            }

            val filesJson = response.body?.string() ?: return@withContext Result.failure(Exception("Empty response"))
            val filesArray = JSONArray(filesJson)
            
            // Filter for SVG files and sort by name (timestamp)
            val svgFiles = mutableListOf<JSONObject>()
            for (i in 0 until filesArray.length()) {
                val file = filesArray.getJSONObject(i)
                val fileName = file.getString("name")
                if (fileName.endsWith(".svg")) {
                    svgFiles.add(file)
                }
            }
            
            if (svgFiles.isEmpty()) {
                return@withContext Result.failure(Exception("No QR codes found"))
            }
            
            // Sort by filename descending to get the latest
            svgFiles.sortByDescending { it.getString("name") }
            val latestFile = svgFiles.first()
            
            val fileName = latestFile.getString("name")
            val downloadUrl = latestFile.getString("download_url")
            val timestamp = fileName.removeSuffix(".svg")
            
            Result.success(QRCodeFile(fileName, downloadUrl, timestamp))
        } catch (e: Exception) {
            Log.e(TAG, "Error fetching latest QR code", e)
            Result.failure(e)
        }
    }

    suspend fun downloadSVGContent(downloadUrl: String): Result<String> = withContext(Dispatchers.IO) {
        try {
            val requestBuilder = Request.Builder()
                .url(downloadUrl)
            
            // Add authentication for private repo raw content
            githubToken?.let {
                requestBuilder.addHeader("Authorization", "Bearer $it")
            }
            
            val request = requestBuilder.build()
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

    suspend fun testConnection(): Result<Boolean> = withContext(Dispatchers.IO) {
        try {
            val apiUrl = "$API_BASE/repos/$REPO_NAME"
            val requestBuilder = Request.Builder()
                .url(apiUrl)
                .addHeader("Accept", "application/vnd.github.v3+json")
            
            githubToken?.let {
                requestBuilder.addHeader("Authorization", "Bearer $it")
            }
            
            val request = requestBuilder.build()
            val response = client.newCall(request).execute()
            
            Result.success(response.isSuccessful)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}