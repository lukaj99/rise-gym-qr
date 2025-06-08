package com.risegym.qrpredictor.service

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * Debug version of GitHubQRService with extensive logging
 */
class GitHubQRServiceDebug(private val githubToken: String? = null) {
    companion object {
        private const val TAG = "GitHubQRServiceDebug"
        private const val REPO_NAME = "lukaj99/rise-gym-qr"
        private const val QR_DIRECTORY = "real_qr_codes"
        private const val API_BASE = "https://api.github.com"
    }

    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .addInterceptor { chain ->
            val request = chain.request()
            Log.d(TAG, "Request URL: ${request.url}")
            Log.d(TAG, "Request Headers: ${request.headers}")
            
            val response = chain.proceed(request)
            Log.d(TAG, "Response Code: ${response.code}")
            Log.d(TAG, "Response Headers: ${response.headers}")
            
            // Log rate limit info
            val rateLimit = response.header("X-RateLimit-Limit")
            val remaining = response.header("X-RateLimit-Remaining")
            Log.d(TAG, "Rate Limit: $remaining/$rateLimit")
            
            response
        }
        .build()

    suspend fun testGitHubConnection(): String = withContext(Dispatchers.IO) {
        val results = mutableListOf<String>()
        
        // Test 1: Check token format
        results.add("Token Check:")
        if (githubToken.isNullOrEmpty()) {
            results.add("  ❌ No token provided")
        } else {
            results.add("  ✓ Token length: ${githubToken.length}")
            results.add("  ✓ Token prefix: ${githubToken.take(4)}...")
            if (!githubToken.startsWith("ghp_") && !githubToken.startsWith("github_pat_")) {
                results.add("  ⚠️ Token doesn't start with expected prefix (ghp_ or github_pat_)")
            }
        }
        
        // Test 2: Test API access
        results.add("\nAPI Test:")
        try {
            val testUrl = "$API_BASE/user"
            val requestBuilder = Request.Builder()
                .url(testUrl)
                .addHeader("Accept", "application/vnd.github.v3+json")
            
            githubToken?.let {
                requestBuilder.addHeader("Authorization", "Bearer $it")
            }
            
            val request = requestBuilder.build()
            val response = client.newCall(request).execute()
            
            results.add("  API Response: ${response.code}")
            
            when (response.code) {
                200 -> {
                    val userJson = response.body?.string()?.let { JSONObject(it) }
                    val login = userJson?.optString("login", "unknown")
                    results.add("  ✓ Authenticated as: $login")
                }
                401 -> results.add("  ❌ Invalid token")
                403 -> results.add("  ❌ Forbidden - check token permissions")
                else -> results.add("  ❌ Unexpected response: ${response.code}")
            }
        } catch (e: Exception) {
            results.add("  ❌ API Error: ${e.message}")
        }
        
        // Test 3: Test repository access
        results.add("\nRepository Test:")
        try {
            val repoUrl = "$API_BASE/repos/$REPO_NAME"
            val requestBuilder = Request.Builder()
                .url(repoUrl)
                .addHeader("Accept", "application/vnd.github.v3+json")
            
            githubToken?.let {
                requestBuilder.addHeader("Authorization", "Bearer $it")
            }
            
            val request = requestBuilder.build()
            val response = client.newCall(request).execute()
            
            results.add("  Repo Response: ${response.code}")
            
            when (response.code) {
                200 -> {
                    val repoJson = response.body?.string()?.let { JSONObject(it) }
                    val isPrivate = repoJson?.optBoolean("private", false) ?: false
                    results.add("  ✓ Repository accessible (private: $isPrivate)")
                }
                404 -> results.add("  ❌ Repository not found or no access")
                else -> results.add("  ❌ Unexpected response: ${response.code}")
            }
        } catch (e: Exception) {
            results.add("  ❌ Repo Error: ${e.message}")
        }
        
        // Test 4: Test directory listing
        results.add("\nDirectory Test:")
        try {
            val dirUrl = "$API_BASE/repos/$REPO_NAME/contents/$QR_DIRECTORY"
            val requestBuilder = Request.Builder()
                .url(dirUrl)
                .addHeader("Accept", "application/vnd.github.v3+json")
            
            githubToken?.let {
                requestBuilder.addHeader("Authorization", "Bearer $it")
            }
            
            val request = requestBuilder.build()
            val response = client.newCall(request).execute()
            
            results.add("  Directory Response: ${response.code}")
            
            when (response.code) {
                200 -> {
                    val filesJson = response.body?.string()
                    val filesArray = filesJson?.let { JSONArray(it) }
                    val fileCount = filesArray?.length() ?: 0
                    results.add("  ✓ Found $fileCount files in $QR_DIRECTORY")
                    
                    // List first few files
                    if (fileCount > 0) {
                        results.add("  First files:")
                        for (i in 0 until minOf(3, fileCount)) {
                            val file = filesArray!!.getJSONObject(i)
                            val name = file.getString("name")
                            results.add("    - $name")
                        }
                    }
                }
                404 -> results.add("  ❌ Directory not found")
                else -> results.add("  ❌ Unexpected response: ${response.code}")
            }
        } catch (e: Exception) {
            results.add("  ❌ Directory Error: ${e.message}")
        }
        
        results.joinToString("\n")
    }
}