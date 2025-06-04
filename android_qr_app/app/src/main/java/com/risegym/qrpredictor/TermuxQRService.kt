package com.risegym.qrpredictor

import android.content.Context
import android.graphics.Bitmap
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.TimeUnit

/**
 * Service to communicate with Termux QR fetcher
 * Provides fallback mechanism for live QR code fetching
 */
class TermuxQRService(private val context: Context) {
    
    companion object {
        private const val TAG = "TermuxQRService"
        // Use localhost for Termux running on the same device
        private const val TERMUX_SERVER_URL = "http://127.0.0.1:8080"
        private const val HEALTH_CHECK_TIMEOUT = 2000 // 2 seconds
        private const val QR_FETCH_TIMEOUT = 10000 // 10 seconds
    }
    
    data class QRResult(
        val success: Boolean,
        val content: String? = null,
        val svg: String? = null,
        val bitmap: Bitmap? = null,
        val error: String? = null,
        val source: String = "termux"
    )
    
    /**
     * Check if Termux server is running
     */
    suspend fun isTermuxAvailable(): Boolean = withContext(Dispatchers.IO) {
        try {
            val url = URL("$TERMUX_SERVER_URL/health")
            val connection = url.openConnection() as HttpURLConnection
            connection.connectTimeout = HEALTH_CHECK_TIMEOUT
            connection.readTimeout = HEALTH_CHECK_TIMEOUT
            connection.requestMethod = "GET"
            
            val responseCode = connection.responseCode
            connection.disconnect()
            
            responseCode == 200
        } catch (e: Exception) {
            Log.d(TAG, "Termux server not available: ${e.message}")
            false
        }
    }
    
    /**
     * Fetch live QR code from Rise Gym via Termux
     */
    suspend fun fetchLiveQR(useCached: Boolean = true): QRResult = withContext(Dispatchers.IO) {
        try {
            val endpoint = if (useCached) "/qr/cached" else "/qr"
            val url = URL("$TERMUX_SERVER_URL$endpoint")
            val connection = url.openConnection() as HttpURLConnection
            connection.connectTimeout = QR_FETCH_TIMEOUT
            connection.readTimeout = QR_FETCH_TIMEOUT
            connection.requestMethod = "GET"
            
            if (connection.responseCode == 200) {
                val response = BufferedReader(InputStreamReader(connection.inputStream)).use {
                    it.readText()
                }
                connection.disconnect()
                
                val json = JSONObject(response)
                
                if (json.optBoolean("success", false)) {
                    val content = json.optString("content", null)
                    val svg = json.optString("svg", null)
                    
                    // Convert SVG to bitmap if available
                    val bitmap = svg?.let { svgToBitmap(it) }
                    
                    QRResult(
                        success = true,
                        content = content,
                        svg = svg,
                        bitmap = bitmap,
                        source = json.optString("source", "termux")
                    )
                } else {
                    QRResult(
                        success = false,
                        error = json.optString("error", "Unknown error")
                    )
                }
            } else {
                connection.disconnect()
                QRResult(
                    success = false,
                    error = "Server returned ${connection.responseCode}"
                )
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to fetch QR from Termux", e)
            QRResult(
                success = false,
                error = e.message ?: "Connection failed"
            )
        }
    }
    
    /**
     * Validate if fetched QR content matches expected pattern
     */
    fun validateQRContent(content: String): Boolean {
        // QR pattern: 9268MMDDYYYYHHSSSS
        val pattern = Regex("^9268\\d{14}$")
        return pattern.matches(content)
    }
    
    /**
     * Compare live QR with predicted QR
     */
    fun compareWithPredicted(liveContent: String, predictedContent: String): ComparisonResult {
        val isValid = validateQRContent(liveContent)
        val matches = liveContent == predictedContent
        
        val details = if (!matches && isValid) {
            analyzeDifference(liveContent, predictedContent)
        } else null
        
        return ComparisonResult(
            matches = matches,
            liveContent = liveContent,
            predictedContent = predictedContent,
            isValidFormat = isValid,
            differenceDetails = details
        )
    }
    
    data class ComparisonResult(
        val matches: Boolean,
        val liveContent: String,
        val predictedContent: String,
        val isValidFormat: Boolean,
        val differenceDetails: String? = null
    )
    
    private fun analyzeDifference(live: String, predicted: String): String {
        if (live.length != predicted.length) {
            return "Length mismatch: live=${live.length}, predicted=${predicted.length}"
        }
        
        // Find where they differ
        val differences = mutableListOf<String>()
        
        // Check member ID (first 4 digits)
        if (live.substring(0, 4) != predicted.substring(0, 4)) {
            differences.add("Member ID mismatch")
        }
        
        // Check date (MMDDYYYY)
        if (live.substring(4, 12) != predicted.substring(4, 12)) {
            differences.add("Date mismatch: live=${live.substring(4, 12)}, predicted=${predicted.substring(4, 12)}")
        }
        
        // Check hour block (HH)
        if (live.substring(12, 14) != predicted.substring(12, 14)) {
            val liveHour = live.substring(12, 14).toIntOrNull() ?: -1
            val predictedHour = predicted.substring(12, 14).toIntOrNull() ?: -1
            differences.add("Hour block mismatch: live=$liveHour, predicted=$predictedHour")
        }
        
        // Check suffix (SSSS)
        if (live.substring(14, 18) != predicted.substring(14, 18)) {
            differences.add("Suffix mismatch: live=${live.substring(14, 18)}, predicted=${predicted.substring(14, 18)}")
        }
        
        return differences.joinToString("; ")
    }
    
    /**
     * Convert SVG string to Bitmap
     * Note: This is a simplified version. In production, you'd use a proper SVG library
     */
    private fun svgToBitmap(svg: String): Bitmap? {
        // TODO: Implement SVG to Bitmap conversion
        // For now, return null - the app will fall back to generated QR
        return null
    }
    
    /**
     * Start Termux server if not running
     * Requires Termux to be installed and configured
     */
    fun startTermuxServer() {
        try {
            // Try to start Termux with the QR server
            val intent = context.packageManager.getLaunchIntentForPackage("com.termux")
            intent?.let {
                it.putExtra("com.termux.RUN_COMMAND_PATH", "/data/data/com.termux/files/home/risegym/start-server.sh")
                it.putExtra("com.termux.RUN_COMMAND_BACKGROUND", true)
                context.startActivity(it)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start Termux server", e)
        }
    }
}